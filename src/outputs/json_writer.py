"""
JSON 输出模块。
将每日 5 件事写出为 JSON 文件，供投研日历项目导入。
同时维护历史归档和索引。

输出格式严格遵循投研日历 PRD §2.6 的 Schema：
{
  "project": "daily-ai-5",
  "exportedAt": "2026-07-01T08:00:00Z",
  "items": [
    {
      "date": "2026-07-01",
      "title": "新闻标题",
      "summary": "新闻摘要",
      "url": "https://...",
      "source": "来源名称"
    }
  ]
}
"""
from __future__ import annotations
from typing import Any
import json
import os
import uuid
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


def build_internal_digest(
    items: list[dict[str, Any]],
    daily_theme: str = "",
    *,
    geopolitics_items: list[dict[str, Any]],
    geopolitics_theme: str = "",
    date_str: str | None = None,
    exported_at: str | None = None,
) -> dict[str, Any]:
    """
    将翻译后的 5 条消息构建为投研日历要求的 JSON 格式。

    Args:
        items: 翻译后的 5 条消息

    Returns:
        符合投研日历 Schema 的字典
    """
    if len(items) != 5 or len(geopolitics_items) != 5:
        raise ValueError("内部日报必须包含恰好 5 条 AI 新闻和 5 条政经新闻")
    for item in [*items, *geopolitics_items]:
        parsed_url = urlparse(str(item.get("url", "")))
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError(f"新闻链接必须是有效的 HTTP(S) URL: {item.get('url', '')}")

    now = datetime.now(timezone.utc)
    today = date_str or now.strftime("%Y-%m-%d")
    exported_at = exported_at or now.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "project": "daily-ai-5",
        "exportedAt": exported_at,
        "dailyTheme": daily_theme,
        "geopoliticsTheme": geopolitics_theme,
        "items": _build_internal_items(items, today, exported_at),
        "geopoliticsItems": _build_internal_items(
            geopolitics_items, today, exported_at
        ),
    }


def _build_internal_items(
    items: list[dict[str, Any]],
    today: str,
    exported_at: str,
) -> list[dict[str, Any]]:
    return [
        {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{today}:{item.get('url', '')}")),
                "date": today,
                "title": item.get("title_cn", item.get("title", "")),
                "summary": item.get("summary_cn", item.get("summary", "")),
                "url": item.get("url", ""),
                "canonicalUrl": item.get("canonicalUrl", item.get("url", "")),
                "source": item.get("source", ""),
                "sourceTier": item.get("sourceTier", ""),
                "isPrimarySource": bool(item.get("isPrimarySource", False)),
                "tags": list(item.get("tags") or []),
                "rank": int(item.get("rank", index)),
                "eventId": item.get("eventId", ""),
                "eventType": item.get("eventType", "unknown"),
                "entities": list(item.get("entities") or []),
                "tickers": list(item.get("tickers") or []),
                "sourceCredibilityScore": float(item.get("sourceCredibilityScore", 0)),
                "marketImpactScore": float(item.get("marketImpactScore", 0)),
                "noveltyScore": float(item.get("noveltyScore", 0)),
                "timelinessScore": float(item.get("timelinessScore", 0)),
                "entityImportanceScore": float(item.get("entityImportanceScore", 0)),
                "confidenceScore": float(item.get("confidenceScore", 0)),
                "totalScore": float(item.get("totalScore", 0)),
                "whyItMatters": item.get("whyItMatters", ""),
                "investmentImplication": item.get("investmentImplication", ""),
                "riskNote": item.get("riskNote", ""),
                "originalTitle": item.get("originalTitle", item.get("title", "")),
                "published": item.get("published", ""),
                "mergedSources": list(item.get("merged_sources") or []),
                "relatedUrls": list(item.get("relatedUrls") or []),
                "primarySource": item.get("primarySource", item.get("source", "")),
                "selectionReason": item.get("reason", ""),
                "promptVersion": item.get("promptVersion", ""),
                "modelUsed": item.get("modelUsed", ""),
                "rawPayloadHash": item.get("rawPayloadHash", ""),
                "warnings": list(item.get("warnings") or []),
                "regions": list(item.get("regions") or []),
                "geopoliticsEventTypes": list(item.get("geopoliticsEventTypes") or []),
                "geopoliticsRuleScore": float(item.get("geopoliticsRuleScore", 0)),
                "createdAt": exported_at,
        }
        for index, item in enumerate(items, start=1)
    ]


def build_external_digest(internal_digest: dict[str, Any]) -> dict[str, Any]:
    """从内部日报生成投研日历的稳定五字段契约。"""
    fields = ("date", "title", "summary", "url", "source")
    return {
        "project": internal_digest["project"],
        "exportedAt": internal_digest["exportedAt"],
        "items": [
            {field: item.get(field, "") for field in fields}
            for item in internal_digest.get("items", [])
        ],
    }


def validate_external_digest(digest: dict[str, Any]) -> None:
    """校验投研日历对外 5 字段契约。"""
    if digest.get("project") != "daily-ai-5":
        raise ValueError("project 必须是 daily-ai-5")
    if not isinstance(digest.get("exportedAt"), str) or not digest["exportedAt"]:
        raise ValueError("exportedAt 必须是非空字符串")
    items = digest.get("items")
    if not isinstance(items, list) or len(items) != 5:
        raise ValueError("items 必须包含恰好 5 条")
    fields = {"date", "title", "summary", "url", "source"}
    for index, item in enumerate(items, start=1):
        if set(item) != fields:
            missing = fields - set(item)
            raise ValueError(f"第 {index} 条缺少字段: {', '.join(sorted(missing))}")
        parsed_url = urlparse(str(item.get("url", "")))
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError(f"第 {index} 条 url 非法")


def validate_internal_digest(digest: dict[str, Any]) -> None:
    """校验内部归档字段，防止后续投研字段缺失。"""
    required = {
        "date", "title", "summary", "url", "source", "rank",
        "eventId", "canonicalUrl", "sourceTier", "eventType", "entities",
        "sourceCredibilityScore", "marketImpactScore", "noveltyScore",
        "timelinessScore", "entityImportanceScore", "confidenceScore",
        "totalScore", "warnings",
    }
    for field in ("items", "geopoliticsItems"):
        items = digest.get(field)
        if not isinstance(items, list) or len(items) != 5:
            raise ValueError(f"内部 {field} 必须包含恰好 5 条")
        for index, item in enumerate(items, start=1):
            missing = required - set(item)
            if missing:
                raise ValueError(
                    f"内部 {field} 第 {index} 条缺少字段: {', '.join(sorted(missing))}"
                )
    if not isinstance(digest.get("dailyTheme"), str):
        raise ValueError("dailyTheme 必须是字符串")
    if not isinstance(digest.get("geopoliticsTheme"), str):
        raise ValueError("geopoliticsTheme 必须是字符串")


def build_daily_digest(items: list[dict[str, Any]]) -> dict[str, Any]:
    """兼容旧调用：构建投研日历对外日报。"""
    now = datetime.now(timezone.utc)
    legacy_internal = {
        "project": "daily-ai-5",
        "exportedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": _build_internal_items(
            items,
            now.strftime("%Y-%m-%d"),
            now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    }
    return build_external_digest(legacy_internal)


def write_daily_json(
    digest: dict[str, Any],
    output_path: str,
) -> str:
    """
    写出每日 JSON 文件（覆盖 daily-5-things.json）。

    Args:
        digest: build_daily_digest 的返回值
        output_path: 输出路径

    Returns:
        写入的文件路径
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)
    logger.info(f"每日 JSON 已写出: {output_path}")
    return output_path


def archive_daily_json(
    digest: dict[str, Any],
    archive_dir: str,
) -> str:
    """
    归档每日 JSON（不覆盖，按日期命名）。

    Args:
        digest: build_daily_digest 的返回值
        archive_dir: 归档目录路径

    Returns:
        归档文件路径
    """
    items = digest.get("items") or []
    today = str(items[0].get("date")) if items else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_path = os.path.join(archive_dir, f"{today}.json")
    os.makedirs(archive_dir, exist_ok=True)
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)
    logger.info(f"归档 JSON 已写出: {archive_path}")
    return archive_path


def load_recent_archive_items(
    archive_dir: str,
    *,
    before_date: str,
    days: int,
    item_field: str = "items",
) -> list[dict[str, Any]]:
    """读取指定日期之前若干天的归档条目。"""
    if item_field not in {"items", "geopoliticsItems"}:
        raise ValueError("item_field 必须是 items 或 geopoliticsItems")
    before = datetime.strptime(before_date, "%Y-%m-%d").date()
    earliest = before - timedelta(days=days)
    items: list[dict[str, Any]] = []
    if not os.path.isdir(archive_dir):
        return items
    for filename in sorted(os.listdir(archive_dir)):
        if not filename.endswith(".json"):
            continue
        try:
            archive_date = datetime.strptime(filename[:-5], "%Y-%m-%d").date()
        except ValueError:
            continue
        if not earliest <= archive_date < before:
            continue
        path = os.path.join(archive_dir, filename)
        try:
            with open(path, encoding="utf-8") as file:
                digest = json.load(file)
            archived_items = digest.get(item_field, [])
            if isinstance(archived_items, list):
                items.extend(
                    item for item in archived_items if isinstance(item, dict)
                )
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("历史归档读取失败，跳过 %s: %s", path, exc)
    return items


def update_history_index(
    history_path: str,
    date_str: str,
) -> dict[str, Any]:
    """
    更新历史索引文件：追加当天日期（如不存在）。

    Args:
        history_path: history.json 的路径
        date_str: 日期字符串 "2026-07-01"

    Returns:
        更新后的索引字典 {"dates": [...], "updatedAt": "..."}
    """
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    history: dict[str, Any] = {"dates": []}
    if os.path.exists(history_path):
        try:
            with open(history_path, encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, dict):
                history = loaded
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("历史索引读取失败，将重新创建: %s", exc)
    dates = {
        value for value in history.get("dates", [])
        if isinstance(value, str)
    }
    dates.add(date_str)
    history = {
        "dates": sorted(dates, reverse=True),
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(history_path, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
    return history
