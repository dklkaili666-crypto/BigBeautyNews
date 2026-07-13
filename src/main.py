"""
BigBeautyNews — 每日 AI 与全球地缘政经双榜单
================================
主入口。编排整个数据处理流水线：

1. 并行抓取（RSS + GitHub Trending + HN）
2. 去重 + 合并同事件报道
3. AI 关键词预过滤
4. LLM 排序 → 选出 Top 5
5. LLM 翻译为简体中文
6. 多渠道输出：
   - Server酱 → 微信推送
   - JSON → 投研日历 L2 数据
   - 静态网页数据更新

用法：
    python main.py                  # 本地运行
    python main.py --dry-run        # 干跑模式（不推送，只打印）

环境变量：
    SERVERCHAN_SENDKEY  Server酱 SendKey
    LLM_API_KEY         LLM API Key
    LLM_API_BASE        LLM API Base URL（默认 OpenAI）
    LLM_MODEL           LLM 模型名（默认 gpt-4o-mini）
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha1
import json
import logging
import sys
from datetime import datetime, timezone
from time import perf_counter
from zoneinfo import ZoneInfo
from collections.abc import Callable
from typing import Any

# 把 src 加入 path，方便直接 python src/main.py 运行
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    RSS_SOURCES,
    GEOPOLITICS_RSS_SOURCES,
    TOP_K,
    SERVERCHAN_SENDKEY,
    LLM_API_KEY,
    LLM_API_BASE,
    LLM_MODEL,
    DATA_DIR,
    DAILY_JSON_PATH,
    HISTORY_JSON_PATH,
    PUSH_HISTORY_PATH,
    ARCHIVE_DIR,
    WEB_DIR,
)
from fetchers.rss_fetcher import fetch_all_sources
from fetchers.github_trending import fetch_trending
from fetchers.hacker_news import fetch_hn_top_ai
from pipeline.dedup import dedup_candidates, is_same_event
from pipeline.enrichment import enrich_articles
from pipeline.filter import (
    exclude_historical_duplicates,
    filter_ai_related,
    filter_recent_articles,
)
from pipeline.ranker import select_top5, call_llm_ranking
from pipeline.geopolitics import (
    classify_primary_board,
    filter_geopolitics_related,
    geopolitics_rule_score,
    select_fresh_geopolitics_window,
)
from pipeline.geopolitics_ranker import (
    call_geopolitics_ranking,
    select_geopolitics_top5,
)
from pipeline.translator import translate_top5, translate_geopolitics_top5
from outputs.serverchan import push_to_wechat_with_result
from outputs.json_writer import (
    build_internal_digest,
    build_external_digest,
    validate_external_digest,
    validate_internal_digest,
    write_daily_json,
    archive_daily_json,
    load_recent_archive_items,
    update_history_index,
)
from outputs.web_builder import write_web_data
from outputs.push_state import mark_pushed, was_pushed
from outputs.status import build_run_status, write_run_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def _select_ai_freshness_window(
    articles: list[dict[str, Any]],
    *,
    now: datetime,
) -> list[dict[str, Any]]:
    recent_48h = filter_recent_articles(articles, now=now, max_age_hours=48)
    if len(recent_48h) >= TOP_K:
        return recent_48h
    recent_72h = filter_recent_articles(articles, now=now, max_age_hours=72)
    if len(recent_72h) >= TOP_K:
        return recent_72h
    return articles


def _replacement(
    candidates: list[dict[str, Any]],
    ai_selected: list[dict[str, Any]],
    geopolitics_selected: list[dict[str, Any]],
    *,
    board: str,
) -> dict[str, Any] | None:
    selected = [*ai_selected, *geopolitics_selected]
    available = [
        candidate
        for candidate in candidates
        if classify_primary_board(candidate) == board
        and not any(is_same_event(candidate, item) for item in selected)
    ]
    if board == "geopolitics":
        available.sort(
            key=lambda item: float(
                item.get("geopoliticsRuleScore") or geopolitics_rule_score(item)
            ),
            reverse=True,
        )
    else:
        available.sort(
            key=lambda item: float(item.get("totalScore") or 0),
            reverse=True,
        )
    return dict(available[0]) if available else None


def resolve_cross_board_duplicates(
    ai_selected: list[dict[str, Any]],
    geopolitics_selected: list[dict[str, Any]],
    ai_candidates: list[dict[str, Any]],
    geopolitics_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按主要影响保留交叉事件，并从对应候选池确定性补位。"""
    ai_result = [dict(item) for item in ai_selected]
    geopolitics_result = [dict(item) for item in geopolitics_selected]
    while True:
        duplicate_pair = next(
            (
                (ai_index, geopolitics_index)
                for ai_index, ai_item in enumerate(ai_result)
                for geopolitics_index, geopolitics_item in enumerate(geopolitics_result)
                if is_same_event(ai_item, geopolitics_item)
            ),
            None,
        )
        if duplicate_pair is None:
            break
        ai_index, geopolitics_index = duplicate_pair
        combined = {
            "title": " ".join(
                str(item.get("title") or "")
                for item in (ai_result[ai_index], geopolitics_result[geopolitics_index])
            ),
            "summary": " ".join(
                str(item.get("summary") or "")
                for item in (ai_result[ai_index], geopolitics_result[geopolitics_index])
            ),
        }
        primary_board = classify_primary_board(combined)
        if primary_board == "geopolitics":
            replacement = _replacement(
                ai_candidates,
                ai_result,
                geopolitics_result,
                board="ai",
            )
            if replacement is None:
                raise ValueError("AI 榜单跨榜单去重后无法补足 5 条")
            replacement.update({
                "rank": ai_result[ai_index].get("rank", ai_index + 1),
                "reason": "跨榜单重复后按规则分数补位",
                "tags": list(replacement.get("tags") or []),
            })
            ai_result[ai_index] = replacement
        else:
            replacement = _replacement(
                geopolitics_candidates,
                ai_result,
                geopolitics_result,
                board="geopolitics",
            )
            if replacement is None:
                raise ValueError("政经榜单跨榜单去重后无法补足 5 条")
            replacement.update({
                "rank": geopolitics_result[geopolitics_index].get(
                    "rank", geopolitics_index + 1
                ),
                "reason": "跨榜单重复后按规则分数补位",
                "tags": list(replacement.get("tags") or []),
            })
            geopolitics_result[geopolitics_index] = replacement
    return ai_result, geopolitics_result


def fetch_source_pools() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[str],
]:
    """并行抓取 AI 与政经来源，返回两个原始候选池和来源错误。"""
    ai_articles: list[dict[str, Any]] = []
    geopolitics_articles: list[dict[str, Any]] = []
    errors: list[str] = []
    rss_sources = [source for source in RSS_SOURCES if source.get("type") == "rss"]
    geopolitics_rss_sources = [
        source for source in GEOPOLITICS_RSS_SOURCES
        if source.get("type") == "rss"
    ]

    def fetch_community(
        fetcher: Callable[[], list[dict[str, Any]]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        return fetcher(), []

    fetch_jobs: dict[
        str,
        tuple[str, Callable[[], tuple[list[dict[str, Any]], list[str]]]],
    ] = {
        "AI RSS": ("ai", lambda: fetch_all_sources(rss_sources)),
        "政经 RSS": (
            "geopolitics",
            lambda: fetch_all_sources(geopolitics_rss_sources),
        ),
        "GitHub Trending": ("ai", lambda: fetch_community(fetch_trending)),
        "Hacker News": ("ai", lambda: fetch_community(fetch_hn_top_ai)),
    }
    with ThreadPoolExecutor(max_workers=len(fetch_jobs)) as executor:
        futures = {
            executor.submit(job): (name, board)
            for name, (board, job) in fetch_jobs.items()
        }
        for future in as_completed(futures):
            name, board = futures[future]
            try:
                articles, source_errors = future.result()
                errors.extend(f"{board}: {error}" for error in source_errors)
                if board == "geopolitics":
                    geopolitics_articles.extend(articles)
                else:
                    ai_articles.extend(articles)
                logger.info("  %s: %s 篇", name, len(articles))
            except Exception as exc:
                suffix = "（非致命）" if name == "Hacker News" else ""
                logger.warning("  %s 抓取失败%s: %s", name, suffix, exc)
                if name != "Hacker News":
                    errors.append(f"{board}: {name}")
    return ai_articles, geopolitics_articles, errors


def prepare_candidate_pools(
    ai_articles: list[dict[str, Any]],
    geopolitics_articles: list[dict[str, Any]],
    *,
    today: str,
    now: datetime,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """完成去重、历史排除、过滤、时效窗口和主板块归类。"""
    logger.info("[2/6] 去重 & 合并同事件...")
    deduped = dedup_candidates(ai_articles)
    geopolitics_deduped = dedup_candidates(geopolitics_articles)
    logger.info(
        "  去重后: %s 篇 (减少 %s)",
        len(deduped),
        len(ai_articles) - len(deduped),
    )
    logger.info(
        "  政经去重后: %s 篇 (减少 %s)",
        len(geopolitics_deduped),
        len(geopolitics_articles) - len(geopolitics_deduped),
    )

    logger.info("[3/6] AI 关键词预过滤...")
    historical_items = load_recent_archive_items(
        ARCHIVE_DIR,
        before_date=today,
        days=7,
    )
    historical_geopolitics_items = load_recent_archive_items(
        ARCHIVE_DIR,
        before_date=today,
        days=7,
        item_field="geopoliticsItems",
    )
    unseen = exclude_historical_duplicates(deduped, historical_items)
    geopolitics_unseen = exclude_historical_duplicates(
        geopolitics_deduped,
        historical_geopolitics_items,
    )
    logger.info(
        "  跨日去重后: %s 篇 (排除 %s 篇)",
        len(unseen),
        len(deduped) - len(unseen),
    )
    filtered = filter_ai_related(unseen)
    geopolitics_filtered = filter_geopolitics_related(geopolitics_unseen)
    logger.info("  AI 过滤后: %s 篇 (减少 %s)", len(filtered), len(unseen) - len(filtered))
    if len(filtered) < TOP_K:
        logger.warning("AI 过滤后不足 %s 篇，使用跨日去重后全量", TOP_K)
        filtered = unseen

    filtered = _select_ai_freshness_window(filtered, now=now)
    geopolitics_filtered, geopolitics_window = select_fresh_geopolitics_window(
        geopolitics_filtered,
        now=now,
        top_k=TOP_K,
    )
    if geopolitics_window:
        logger.info(
            "  政经使用 %s 小时时效窗口: %s 篇",
            geopolitics_window,
            len(geopolitics_filtered),
        )
    else:
        logger.warning("  政经 72 小时候选不足，保留全部未推送候选")

    ai_primary = [
        article for article in filtered
        if classify_primary_board(article) == "ai"
    ]
    geopolitics_from_ai = filter_geopolitics_related([
        article for article in filtered
        if classify_primary_board(article) == "geopolitics"
    ])
    ai_from_geopolitics = filter_ai_related([
        article for article in geopolitics_filtered
        if classify_primary_board(article) == "ai"
    ])
    geopolitics_primary = [
        article for article in geopolitics_filtered
        if classify_primary_board(article) == "geopolitics"
    ]
    filtered = dedup_candidates([*ai_primary, *ai_from_geopolitics])
    geopolitics_filtered = dedup_candidates([
        *geopolitics_primary,
        *geopolitics_from_ai,
    ])
    filtered = exclude_historical_duplicates(filtered, historical_items)
    geopolitics_filtered = exclude_historical_duplicates(
        geopolitics_filtered,
        historical_geopolitics_items,
    )
    logger.info(
        "  主板块分类后: AI %s 篇，政经 %s 篇",
        len(filtered),
        len(geopolitics_filtered),
    )
    return deduped, filtered, geopolitics_filtered


def rank_candidate_pools(
    ai_candidates: list[dict[str, Any]],
    geopolitics_candidates: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    str,
    str,
    list[str],
]:
    """分别排序两个候选池并完成跨榜单补位。"""
    ranking_stage = "AI"
    try:
        ranking_result = call_llm_ranking(
            ai_candidates,
            api_key=LLM_API_KEY,
            api_base=LLM_API_BASE,
            model=LLM_MODEL,
        )
        top5 = select_top5(ai_candidates, ranking_result)
        ranking_stage = "政经"
        geopolitics_ranking_result = call_geopolitics_ranking(
            geopolitics_candidates,
            api_key=LLM_API_KEY,
            api_base=LLM_API_BASE,
            model=LLM_MODEL,
        )
        geopolitics_top5 = select_geopolitics_top5(
            geopolitics_candidates,
            geopolitics_ranking_result,
        )
        ranking_stage = "跨榜单去重补位"
        top5, geopolitics_top5 = resolve_cross_board_duplicates(
            top5,
            geopolitics_top5,
            ai_candidates,
            geopolitics_candidates,
        )
    except Exception as exc:
        raise RuntimeError(f"{ranking_stage}排序失败: {exc}") from exc

    stage_warnings = [
        str(value) for value in ranking_result.get("warnings", [])
    ]
    stage_warnings.extend(
        f"政经: {value}"
        for value in geopolitics_ranking_result.get("warnings", [])
    )
    return (
        top5,
        geopolitics_top5,
        str(ranking_result.get("daily_theme", "")),
        str(geopolitics_ranking_result.get("geopolitics_theme", "")),
        stage_warnings,
    )


def translate_selected_items(
    ai_items: list[dict[str, Any]],
    geopolitics_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """分别翻译两个榜单，保持每个榜单一次 LLM 调用。"""
    translation_stage = "AI"
    try:
        translated = translate_top5(
            ai_items,
            LLM_API_KEY,
            LLM_API_BASE,
            LLM_MODEL,
        )
        translation_stage = "政经"
        geopolitics_translated = translate_geopolitics_top5(
            geopolitics_items,
            LLM_API_KEY,
            LLM_API_BASE,
            LLM_MODEL,
        )
    except Exception as exc:
        raise RuntimeError(f"{translation_stage}翻译失败: {exc}") from exc
    return translated, geopolitics_translated


def persist_digest_outputs(
    ai_items: list[dict[str, Any]],
    geopolitics_items: list[dict[str, Any]],
    *,
    daily_theme: str,
    geopolitics_theme: str,
    today: str,
    dry_run: bool,
) -> str:
    """校验并写出投研日历 JSON、归档和本地网页数据。"""
    internal_digest = build_internal_digest(
        ai_items,
        daily_theme,
        geopolitics_items=geopolitics_items,
        geopolitics_theme=geopolitics_theme,
        date_str=today,
    )
    external_digest = build_external_digest(internal_digest)
    digest_hash = sha1(
        json.dumps(external_digest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    validate_internal_digest(internal_digest)
    validate_external_digest(external_digest)
    if dry_run:
        logger.info("  [DRY-RUN] 跳过 JSON 写出")
        logger.info("  [DRY-RUN] 跳过网页数据更新")
    else:
        write_daily_json(external_digest, DAILY_JSON_PATH)
        archive_daily_json(internal_digest, ARCHIVE_DIR)
        update_history_index(HISTORY_JSON_PATH, today)
        write_web_data(internal_digest, WEB_DIR)
    return digest_hash


def deliver_wechat_push(
    ai_items: list[dict[str, Any]],
    geopolitics_items: list[dict[str, Any]],
    *,
    daily_theme: str,
    geopolitics_theme: str,
    today: str,
    force_push: bool,
) -> dict[str, Any]:
    """执行幂等的单次双榜单 Server酱推送。"""
    if was_pushed(PUSH_HISTORY_PATH, today) and not force_push:
        logger.info("  微信推送: 今日已成功发送，跳过重复推送")
        return {"ok": True, "pushSkippedReason": "already_pushed"}
    result = push_to_wechat_with_result(
        SERVERCHAN_SENDKEY,
        ai_items,
        today,
        daily_theme,
        geopolitics_items=geopolitics_items,
        geopolitics_theme=geopolitics_theme,
    )
    if result.get("ok"):
        mark_pushed(PUSH_HISTORY_PATH, today)
    return result


def run_pipeline(dry_run: bool = False, force_push: bool = False) -> dict:
    """
    执行完整的数据处理流水线。

    Args:
        dry_run: True 时不推送微信、不写文件
        force_push: True 时忽略当天已推送记录，强制再次发送

    Returns:
        处理结果摘要字典
    """
    started_at = perf_counter()
    started_at_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    logger.info(f"=== BigBeautyNews 开始运行 === 日期: {today}")
    candidate_count = 0
    selected_count = 0
    geopolitics_candidate_count = 0
    geopolitics_selected_count = 0
    source_count = 0
    warnings: list[str] = []
    status_extra: dict[str, Any] = {
        "trigger": os.getenv("BIGBEAUTYNEWS_TRIGGER")
        or os.getenv("GITHUB_EVENT_NAME", "local"),
        "scheduleSlot": os.getenv("BIGBEAUTYNEWS_SCHEDULE_SLOT", ""),
        "workflowRunId": os.getenv("GITHUB_RUN_ID", ""),
        "isDryRun": dry_run,
        "sendkeyPresent": bool(SERVERCHAN_SENDKEY),
        "pushAttempted": False,
        "pushAttemptedAt": "",
        "pushSkippedReason": "",
        "pushHttpStatus": None,
        "pushResponseCode": None,
        "pushResponseMessage": "",
        "pushResponseBodyPreview": "",
        "serverchanEndpointType": "unknown",
        "pushId": "",
        "digestHash": "",
    }

    def finish_status(
        *,
        status: str,
        generated: bool,
        pushed: bool,
        schema_valid: bool,
        errors_for_status: list[str] | None = None,
    ) -> None:
        if dry_run:
            return
        status_extra.update({
            "aiCandidateCount": candidate_count,
            "aiSelectedCount": selected_count,
            "geopoliticsCandidateCount": geopolitics_candidate_count,
            "geopoliticsSelectedCount": geopolitics_selected_count,
        })
        write_run_status(
            build_run_status(
                date_str=today,
                status=status,
                started_at=started_at_iso,
                finished_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                candidate_count=candidate_count,
                selected_count=selected_count,
                geopolitics_candidate_count=geopolitics_candidate_count,
                geopolitics_selected_count=geopolitics_selected_count,
                sources_available=source_count,
                llm_model=LLM_MODEL,
                generated=generated,
                pushed=pushed,
                committed=False,
                schema_valid=schema_valid,
                warnings=warnings,
                errors=errors_for_status or [],
                extra=status_extra,
            ),
            DATA_DIR,
        )

    # ============================================================
    # 第 1 步：并行抓取所有数据源
    # ============================================================
    logger.info("[1/6] 并行抓取数据源...")
    all_articles, geopolitics_articles, errors = fetch_source_pools()

    logger.info(
        "  候选池总计: AI %s 篇，政经 %s 篇",
        len(all_articles),
        len(geopolitics_articles),
    )
    warnings.extend(f"数据源错误: {error}" for error in errors)
    all_articles = enrich_articles(all_articles)
    geopolitics_articles = enrich_articles(geopolitics_articles)
    candidate_count = len(all_articles)
    geopolitics_candidate_count = len(geopolitics_articles)
    source_count = len({
        str(article.get("source", ""))
        for article in [*all_articles, *geopolitics_articles]
        if article.get("source")
    })

    if len(all_articles) < TOP_K or len(geopolitics_articles) < TOP_K:
        reason = (
            f"原始候选不足：AI {len(all_articles)} 篇，"
            f"政经 {len(geopolitics_articles)} 篇"
        )
        logger.error(reason)
        finish_status(
            status="failed",
            generated=False,
            pushed=False,
            schema_valid=False,
            errors_for_status=[reason],
        )
        return {"status": "error", "reason": reason}

    deduped, filtered, geopolitics_filtered = prepare_candidate_pools(
        all_articles,
        geopolitics_articles,
        today=today,
        now=datetime.now(timezone.utc),
    )
    candidate_count = len(filtered)
    geopolitics_candidate_count = len(geopolitics_filtered)
    logger.info(
        "  主板块分类后: AI %s 篇，政经 %s 篇",
        candidate_count,
        geopolitics_candidate_count,
    )

    if len(filtered) < TOP_K or len(geopolitics_filtered) < TOP_K:
        reason = (
            f"过滤后候选不足：AI {len(filtered)} 篇，"
            f"政经 {len(geopolitics_filtered)} 篇"
        )
        finish_status(
            status="failed",
            generated=False,
            pushed=False,
            schema_valid=False,
            errors_for_status=[reason],
        )
        return {
            "status": "error",
            "reason": reason,
        }

    # ============================================================
    # 第 4 步：LLM 排序 → Top 5
    # ============================================================
    logger.info("[4/6] LLM 排序 → 选出 Top 5...")
    if not LLM_API_KEY:
        logger.error("LLM_API_KEY 未配置，无法进行 LLM 排序")
        finish_status(
            status="failed",
            generated=False,
            pushed=False,
            schema_valid=False,
            errors_for_status=["LLM_API_KEY 未配置"],
        )
        return {"status": "error", "reason": "LLM_API_KEY 未配置"}

    try:
        (
            top5,
            geopolitics_top5,
            daily_theme,
            geopolitics_theme,
            ranking_warnings,
        ) = rank_candidate_pools(
            filtered,
            geopolitics_filtered,
        )
    except RuntimeError as exc:
        finish_status(
            status="failed",
            generated=False,
            pushed=False,
            schema_valid=False,
            errors_for_status=[str(exc)],
        )
        return {"status": "error", "reason": str(exc)}
    warnings.extend(ranking_warnings)
    selected_count = len(top5)
    geopolitics_selected_count = len(geopolitics_top5)
    logger.info("  AI Top 5 已选出, 主题: %s", daily_theme)
    logger.info("  政经 Top 5 已选出, 主题: %s", geopolitics_theme)

    # ============================================================
    # 第 5 步：LLM 翻译为简体中文
    # ============================================================
    logger.info("[5/6] LLM 翻译为简体中文...")
    try:
        translated, geopolitics_translated = translate_selected_items(
            top5,
            geopolitics_top5,
        )
    except RuntimeError as exc:
        finish_status(
            status="failed",
            generated=False,
            pushed=False,
            schema_valid=False,
            errors_for_status=[str(exc)],
        )
        return {"status": "error", "reason": str(exc)}
    logger.info(
        "  翻译完成: AI %s 条，政经 %s 条",
        len(translated),
        len(geopolitics_translated),
    )

    # ============================================================
    # 第 6 步：多渠道输出
    # ============================================================
    logger.info("[6/6] 多渠道输出...")

    # 6a. Server酱推送在持久化完成后执行
    if dry_run:
        logger.info("  [DRY-RUN] 跳过微信推送")

    try:
        status_extra["digestHash"] = persist_digest_outputs(
            translated,
            geopolitics_translated,
            daily_theme=daily_theme,
            geopolitics_theme=geopolitics_theme,
            today=today,
            dry_run=dry_run,
        )
    except ValueError as exc:
        finish_status(
            status="failed",
            generated=False,
            pushed=False,
            schema_valid=False,
            errors_for_status=[str(exc)],
        )
        return {"status": "error", "reason": str(exc)}
    # 6b. Server酱推送是非阻断输出，放在持久化之后避免写盘失败时误推送
    if not dry_run:
        push_result = deliver_wechat_push(
                translated,
                geopolitics_translated,
                daily_theme=daily_theme,
                geopolitics_theme=geopolitics_theme,
                today=today,
                force_push=force_push,
        )
        status_extra.update({
            key: value
            for key, value in push_result.items()
            if key != "ok"
        })
        push_ok = bool(push_result.get("ok"))
        if not push_ok:
            warnings.append("Server酱推送失败")
            finish_status(
                status="partial",
                generated=True,
                pushed=False,
                schema_valid=True,
                errors_for_status=["Server酱推送失败"],
            )
            return {"status": "error", "reason": "Server酱推送失败"}
        if not push_result.get("pushSkippedReason"):
            logger.info("  微信推送: 成功")
        finish_status(
            status="success",
            generated=True,
            pushed=push_ok,
            schema_valid=True,
        )

    logger.info("=== BigBeautyNews 运行完成，耗时 %.2fs ===", perf_counter() - started_at)
    return {
        "status": "ok",
        "date": today,
        "candidate_count": len(all_articles),
        "deduped_count": len(deduped),
        "filtered_count": len(filtered),
        "geopolitics_candidate_count": len(geopolitics_articles),
        "geopolitics_filtered_count": len(geopolitics_filtered),
        "daily_theme": daily_theme,
        "geopolitics_theme": geopolitics_theme,
        "source_errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="BigBeautyNews — 每日投研双榜单")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式：抓取+排序+翻译，但不推送/写文件",
    )
    parser.add_argument(
        "--force-push",
        action="store_true",
        help="忽略当天成功记录，强制再次推送微信",
    )
    args = parser.parse_args()

    result = run_pipeline(dry_run=args.dry_run, force_push=args.force_push)
    if result["status"] == "error":
        logger.error(f"流水线失败: {result.get('reason')}")
        sys.exit(1)

    # 打印摘要
    print("\n" + "=" * 60)
    print(f"  BigBeautyNews — {result['date']}")
    print(f"  AI 候选: {result['candidate_count']} → 去重: {result['deduped_count']} → 过滤: {result['filtered_count']} → Top 5")
    print(f"  政经候选: {result['geopolitics_candidate_count']} → 过滤: {result['geopolitics_filtered_count']} → Top 5")
    print(f"  AI 主题: {result.get('daily_theme', 'N/A')}")
    print(f"  政经主题: {result.get('geopolitics_theme', 'N/A')}")
    if result.get("source_errors"):
        print(f"  数据源错误: {', '.join(result['source_errors'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
