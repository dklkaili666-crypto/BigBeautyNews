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
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def build_internal_digest(
    items: list[dict[str, Any]],
    daily_theme: str = "",
    *,
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
    if len(items) != 5:
        raise ValueError("内部日报必须包含恰好 5 条新闻")
    for item in items:
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
        "items": [
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{today}:{item.get('url', '')}")),
                "date": today,
                "title": item.get("title_cn", item.get("title", "")),
                "summary": item.get("summary_cn", item.get("summary", "")),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "tags": list(item.get("tags") or []),
                "rank": int(item.get("rank", index)),
                "originalTitle": item.get("originalTitle", item.get("title", "")),
                "createdAt": exported_at,
            }
            for index, item in enumerate(items, start=1)
        ],
    }


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


def build_daily_digest(items: list[dict[str, Any]]) -> dict[str, Any]:
    """兼容旧调用：构建投研日历对外日报。"""
    return build_external_digest(build_internal_digest(items))


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
