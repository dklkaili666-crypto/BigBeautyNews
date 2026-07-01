"""
RSS 通用抓取器。
从配置的 RSS 源读取文章，返回统一格式的候选条目。

每篇文章输出格式：
{
    "title": str,          # 原始标题
    "url": str,            # 文章链接
    "source": str,         # 来源名称 (如 "TechCrunch")
    "published": str,      # 发布时间 ISO 8601
    "summary": str | None, # RSS 摘要（如有）
}
"""
from __future__ import annotations
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import feedparser
import logging
import requests
from bs4 import BeautifulSoup

from config import MAX_CANDIDATES_PER_SOURCE

logger = logging.getLogger(__name__)

# 每个源抓取超时（秒）
FETCH_TIMEOUT = 15
# 并行抓取线程数
MAX_WORKERS = 5


def _fetch_one_source(source: dict) -> list[dict[str, Any]]:
    """
    抓取单个 RSS 源，返回文章列表。

    Args:
        source: 配置文件中的源定义，包含 name/url/type

    Returns:
        文章列表，每篇包含 title/url/source/published/summary
    """
    response = requests.get(
        source["url"],
        timeout=FETCH_TIMEOUT,
        headers={"User-Agent": "BigBeautyNews/1.0 (+RSS reader)"},
    )
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if getattr(feed, "bozo", False) and not feed.entries:
        raise ValueError(f"RSS 解析失败: {feed.bozo_exception}")

    articles: list[dict[str, Any]] = []
    for entry in feed.entries[:MAX_CANDIDATES_PER_SOURCE]:
        published = ""
        parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed_time:
            published = datetime(
                parsed_time[0],
                parsed_time[1],
                parsed_time[2],
                parsed_time[3],
                parsed_time[4],
                parsed_time[5],
                tzinfo=timezone.utc,
            ).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        raw_summary = str(entry.get("summary", "")).strip()
        summary = BeautifulSoup(raw_summary, "lxml").get_text(" ", strip=True) if raw_summary else None
        articles.append({
            "title": str(entry.get("title", "")).strip(),
            "url": str(entry.get("link", "")).strip(),
            "source": source["name"],
            "published": published,
            "summary": summary,
        })
    return [article for article in articles if article["title"] and article["url"]]


def fetch_all_sources(sources: list[dict]) -> tuple[list[dict[str, Any]], list[str]]:
    """
    并行抓取所有 RSS 源。

    Args:
        sources: 源定义列表（来自 config.RSS_SOURCES 中 type="rss" 的项）

    Returns:
        (articles, errors)
        - articles: 所有文章合并后的列表
        - errors: 抓取失败的源名称列表
    """
    articles: list[dict[str, Any]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, len(sources)))) as executor:
        futures = {executor.submit(_fetch_one_source, source): source for source in sources}
        for future in as_completed(futures):
            source = futures[future]
            try:
                articles.extend(future.result())
            except Exception as exc:
                name = str(source.get("name", source.get("url", "unknown")))
                errors.append(name)
                logger.warning("RSS 源抓取失败 [%s]: %s", name, exc)
    return articles, errors
