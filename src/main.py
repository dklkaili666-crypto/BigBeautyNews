"""
BigBeautyNews — 每日 AI 5 件事
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
import logging
import sys
from datetime import datetime
from time import perf_counter
from zoneinfo import ZoneInfo
from collections.abc import Callable
from typing import Any

# 把 src 加入 path，方便直接 python src/main.py 运行
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    RSS_SOURCES,
    TOP_K,
    SERVERCHAN_SENDKEY,
    LLM_API_KEY,
    LLM_API_BASE,
    LLM_MODEL,
    DAILY_JSON_PATH,
    HISTORY_JSON_PATH,
    PUSH_HISTORY_PATH,
    ARCHIVE_DIR,
    WEB_DIR,
)
from fetchers.rss_fetcher import fetch_all_sources
from fetchers.github_trending import fetch_trending
from fetchers.hacker_news import fetch_hn_top_ai
from pipeline.dedup import dedup_candidates
from pipeline.filter import filter_ai_related
from pipeline.ranker import select_top5, call_llm_ranking
from pipeline.translator import translate_top5
from outputs.serverchan import push_to_wechat
from outputs.json_writer import (
    build_internal_digest,
    build_external_digest,
    write_daily_json,
    archive_daily_json,
    update_history_index,
)
from outputs.web_builder import write_web_data
from outputs.push_state import mark_pushed, was_pushed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


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
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    logger.info(f"=== BigBeautyNews 开始运行 === 日期: {today}")

    # ============================================================
    # 第 1 步：并行抓取所有数据源
    # ============================================================
    logger.info("[1/6] 并行抓取数据源...")
    all_articles: list[dict] = []
    errors: list[str] = []

    rss_sources = [s for s in RSS_SOURCES if s.get("type") == "rss"]
    def fetch_community(fetcher: Callable[[], list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[str]]:
        return fetcher(), []

    fetch_jobs: dict[
        str,
        Callable[[], tuple[list[dict[str, Any]], list[str]]],
    ] = {
        "RSS": lambda: fetch_all_sources(rss_sources),
        "GitHub Trending": lambda: fetch_community(fetch_trending),
        "Hacker News": lambda: fetch_community(fetch_hn_top_ai),
    }
    with ThreadPoolExecutor(max_workers=len(fetch_jobs)) as executor:
        futures = {executor.submit(job): name for name, job in fetch_jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                articles, source_errors = future.result()
                errors.extend(source_errors)
                all_articles.extend(articles)
                logger.info("  %s: %s 篇", name, len(articles))
            except Exception as exc:
                logger.warning("  %s 抓取失败%s: %s", name, "（非致命）" if name == "Hacker News" else "", exc)
                if name != "Hacker News":
                    errors.append(name)

    logger.info(f"  候选池总计: {len(all_articles)} 篇")

    if len(all_articles) < TOP_K:
        logger.error(f"候选文章不足 {TOP_K} 篇，无法生成简报")
        return {"status": "error", "reason": f"候选文章仅 {len(all_articles)} 篇"}

    # ============================================================
    # 第 2 步：去重 + 合并同事件
    # ============================================================
    logger.info("[2/6] 去重 & 合并同事件...")
    deduped = dedup_candidates(all_articles)
    logger.info(f"  去重后: {len(deduped)} 篇 (减少 {len(all_articles) - len(deduped)})")

    # ============================================================
    # 第 3 步：AI 关键词预过滤
    # ============================================================
    logger.info("[3/6] AI 关键词预过滤...")
    filtered = filter_ai_related(deduped)
    logger.info(f"  过滤后: {len(filtered)} 篇 (减少 {len(deduped) - len(filtered)})")

    if len(filtered) < TOP_K:
        logger.warning(f"过滤后不足 {TOP_K} 篇，使用去重后全量")
        filtered = deduped

    # ============================================================
    # 第 4 步：LLM 排序 → Top 5
    # ============================================================
    logger.info("[4/6] LLM 排序 → 选出 Top 5...")
    if not LLM_API_KEY:
        logger.error("LLM_API_KEY 未配置，无法进行 LLM 排序")
        return {"status": "error", "reason": "LLM_API_KEY 未配置"}

    ranking_result = call_llm_ranking(
        filtered,
        api_key=LLM_API_KEY,
        api_base=LLM_API_BASE,
        model=LLM_MODEL,
    )
    top5 = select_top5(filtered, ranking_result)
    daily_theme = ranking_result.get("daily_theme", "")
    logger.info(f"  Top 5 已选出, 主题: {daily_theme}")

    # ============================================================
    # 第 5 步：LLM 翻译为简体中文
    # ============================================================
    logger.info("[5/6] LLM 翻译为简体中文...")
    translated = translate_top5(top5, LLM_API_KEY, LLM_API_BASE, LLM_MODEL)
    logger.info(f"  翻译完成: {len(translated)} 条")

    # ============================================================
    # 第 6 步：多渠道输出
    # ============================================================
    logger.info("[6/6] 多渠道输出...")

    # 6a. Server酱推送在持久化完成后执行
    if dry_run:
        logger.info("  [DRY-RUN] 跳过微信推送")

    # 6b. JSON → 投研日历
    internal_digest = build_internal_digest(
        translated,
        daily_theme,
        date_str=today,
    )
    external_digest = build_external_digest(internal_digest)
    if dry_run:
        logger.info("  [DRY-RUN] 跳过 JSON 写出")
    else:
        write_daily_json(external_digest, DAILY_JSON_PATH)
        archive_daily_json(internal_digest, ARCHIVE_DIR)
        update_history_index(HISTORY_JSON_PATH, today)

    # 6c. 网页数据
    if dry_run:
        logger.info("  [DRY-RUN] 跳过网页数据更新")
    else:
        write_web_data(internal_digest, WEB_DIR)

    # 6d. Server酱推送是非阻断输出，放在持久化之后避免写盘失败时误推送
    if not dry_run:
        if was_pushed(PUSH_HISTORY_PATH, today) and not force_push:
            logger.info("  微信推送: 今日已成功发送，跳过重复推送")
        else:
            push_ok = push_to_wechat(
                SERVERCHAN_SENDKEY, translated, today, daily_theme
            )
            if push_ok:
                mark_pushed(PUSH_HISTORY_PATH, today)
            else:
                return {"status": "error", "reason": "Server酱推送失败"}
            logger.info(f"  微信推送: {'成功' if push_ok else '失败/跳过'}")

    logger.info("=== BigBeautyNews 运行完成，耗时 %.2fs ===", perf_counter() - started_at)
    return {
        "status": "ok",
        "date": today,
        "candidate_count": len(all_articles),
        "deduped_count": len(deduped),
        "filtered_count": len(filtered),
        "daily_theme": daily_theme,
        "source_errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="BigBeautyNews — 每日 AI 5 件事")
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
    print(f"  候选: {result['candidate_count']} → 去重: {result['deduped_count']} → 过滤: {result['filtered_count']} → Top 5")
    print(f"  主题: {result.get('daily_theme', 'N/A')}")
    if result.get("source_errors"):
        print(f"  数据源错误: {', '.join(result['source_errors'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
