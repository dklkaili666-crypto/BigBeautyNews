"""
预过滤器：基于关键词快速淘汰明显非 AI 相关的内容。
在 LLM 排序之前执行，减少 LLM 调用的 token 开销。
"""
from __future__ import annotations
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any
import re
from pipeline.enrichment import INVESTMENT_TERMS, canonicalize_url

# AI 相关关键词（英文，不区分大小写）
AI_KEYWORDS: list[str] = [
    "artificial intelligence", "machine learning", "deep learning",
    "large language model", "llm", "gpt", "claude", "gemini", "llama",
    "openai", "anthropic", "google deepmind", "meta ai", "microsoft ai",
    "nvidia", "gpu", "tpu", "chip", "neural network", "transformer",
    "stable diffusion", "midjourney", "dall-e", "diffusion model",
    "open source model", "foundation model", "fine-tun",
    "generative ai", "gen ai", "agent", "rag", "retrieval",
    "reinforcement learning", "rlhf", "alignment",
    "semiconductor", "datacenter", "data center", "cloud ai",
    "robot", "autonomous", "self-driving",
    "copilot", "assistant", "chatbot",
    "benchmark", "superintelligence", "agi",
    "startup", "funding", "raise", "series", "valuation", "ipo",
    "regulation", "policy", "ban", "executive order",
    "safety", "security", "jailbreak", "red team",
    "ai", "ml", "nlp", "cv",
    *INVESTMENT_TERMS,
]

CONTEXT_ONLY_KEYWORDS: set[str] = {
    "regulation",
    "policy",
    "ban",
    "executive order",
    "order",
    "safety",
    "security",
}
WEAK_SHORT_CONTEXT_KEYWORDS: set[str] = {"ai", "ml", "nlp", "cv"}

# 必须包含的关键词（至少命中一个才算 AI 相关）
MIN_AI_KEYWORD_MATCHES = 1


def _normalized_title(title: str) -> str:
    return " ".join(re.findall(r"\w+", title.casefold()))


def exclude_historical_duplicates(
    articles: list[dict[str, Any]],
    historical_items: list[dict[str, Any]],
    title_threshold: float = 0.85,
) -> list[dict[str, Any]]:
    """排除近期已推送的 URL 和近似相同事件。"""
    historical_urls = {
        str(item.get("url", "")).strip()
        for item in historical_items
        if item.get("url")
    }
    historical_canonical_urls = {
        str(item.get("canonicalUrl") or canonicalize_url(str(item.get("url", "")))).strip()
        for item in historical_items
        if item.get("canonicalUrl") or item.get("url")
    }
    historical_event_ids = {
        str(item.get("eventId", "")).strip()
        for item in historical_items
        if item.get("eventId")
    }
    historical_titles = [
        _normalized_title(
            str(item.get("originalTitle") or item.get("title") or "")
        )
        for item in historical_items
    ]
    historical_titles = [title for title in historical_titles if title]

    result: list[dict[str, Any]] = []
    for article in articles:
        if str(article.get("url", "")).strip() in historical_urls:
            continue
        canonical_url = str(article.get("canonicalUrl") or canonicalize_url(str(article.get("url", "")))).strip()
        if canonical_url and canonical_url in historical_canonical_urls:
            continue
        event_id = str(article.get("eventId", "")).strip()
        if event_id and event_id in historical_event_ids and not article.get("isFollowUp"):
            continue
        title = _normalized_title(str(article.get("title", "")))
        if title and any(
            SequenceMatcher(None, title, historical_title).ratio() >= title_threshold
            for historical_title in historical_titles
        ):
            continue
        result.append(article)
    return result


def filter_recent_articles(
    articles: list[dict[str, Any]],
    *,
    now: datetime,
    max_age_hours: int,
) -> list[dict[str, Any]]:
    """保留时效窗口内文章；无发布时间的实时来源不在此处淘汰。"""
    if now.tzinfo is None:
        raise ValueError("now 必须包含时区")
    result: list[dict[str, Any]] = []
    for article in articles:
        published_text = str(article.get("published") or "").strip()
        if not published_text:
            result.append(article)
            continue
        try:
            published = datetime.fromisoformat(
                published_text.replace("Z", "+00:00")
            )
        except ValueError:
            result.append(article)
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        age_hours = (
            now.astimezone(timezone.utc) - published.astimezone(timezone.utc)
        ).total_seconds() / 3600
        if age_hours <= max_age_hours:
            result.append(article)
    return result


def filter_ai_related(
    articles: list[dict[str, Any]],
    keywords: list[str] | None = None,
    min_matches: int = MIN_AI_KEYWORD_MATCHES,
) -> list[dict[str, Any]]:
    """
    过滤出 AI 相关的文章。

    匹配规则：
    - title 或 summary/description 中至少命中 min_matches 个 AI 关键词
    - 不区分大小写
    - GitHub Trending 数据源跳过此过滤器（已经在抓取时筛选过）

    Args:
        articles: 去重后的文章列表
        keywords: 自定义关键词列表，默认用 AI_KEYWORDS
        min_matches: 最少命中次数

    Returns:
        过滤后的文章列表
    """
    selected_keywords = keywords or AI_KEYWORDS
    keyword_patterns = [
        (
            keyword.casefold(),
            re.compile(rf"(?<!\w){re.escape(keyword.casefold())}(?!\w)"),
        )
        for keyword in selected_keywords
    ]
    enforce_context = keywords is None
    result: list[dict[str, Any]] = []
    for article in articles:
        if article.get("source") == "GitHub Trending":
            result.append(article)
            continue
        text = " ".join(
            str(article.get(field) or "")
            for field in ("title", "summary", "description")
        ).casefold()
        title_text = str(article.get("title") or "").casefold()
        matched_keywords = [
            keyword
            for keyword, pattern in keyword_patterns
            if pattern.search(text)
        ]
        matched_title_keywords = [
            keyword
            for keyword, pattern in keyword_patterns
            if pattern.search(title_text)
        ]
        matches = len(matched_keywords)
        if (
            enforce_context
            and matched_keywords
            and all(keyword in CONTEXT_ONLY_KEYWORDS for keyword in matched_keywords)
        ):
            continue
        if enforce_context and any(
            keyword in CONTEXT_ONLY_KEYWORDS for keyword in matched_keywords
        ):
            has_title_ai_context = any(
                keyword not in CONTEXT_ONLY_KEYWORDS
                for keyword in matched_title_keywords
            )
            has_strong_ai_context = any(
                keyword not in CONTEXT_ONLY_KEYWORDS
                and keyword not in WEAK_SHORT_CONTEXT_KEYWORDS
                for keyword in matched_keywords
            )
            if not has_title_ai_context and not has_strong_ai_context:
                continue
        if matches >= min_matches:
            result.append(article)
    return result
