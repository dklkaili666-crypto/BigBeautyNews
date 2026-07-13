"""全球地缘与政经候选的确定性预过滤和分类。"""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from pipeline.enrichment import has_ai_context
from pipeline.filter import filter_recent_articles


REGION_TERMS = {
    "china": (
        "china", "chinese", "beijing", "xi jinping", "communist party",
        "people's bank of china", "pboc", "yuan", "renminbi", "taiwan",
        "hong kong",
    ),
    "us": (
        "united states", "u.s.", "american", "white house", "washington",
        "federal reserve", "the fed", "fed", "congress", "senate", "trump",
    ),
    "global": (
        "european union", "eu", "russia", "russian", "ukraine", "israel",
        "iran", "middle east", "nato", "japan", "india", "south korea",
        "united kingdom", "britain", "france", "germany", "imf",
        "world bank", "opec", "united nations", "european central bank",
        "ecb", "bank of japan", "boj",
    ),
}

EVENT_TERMS = {
    "geopolitics": (
        "sanction", "tariff", "export control", "export controls", "trade war", "diplomacy",
        "diplomatic", "summit", "treaty", "ceasefire", "war", "military",
        "missile", "invasion", "conflict", "security alliance",
    ),
    "policy": (
        "central bank", "interest rate", "rate cut", "rate hike", "monetary policy",
        "fiscal policy", "budget", "tax", "regulation", "regulator", "legislation",
        "bill", "executive order", "industrial policy", "stimulus",
    ),
    "macro": (
        "inflation", "consumer prices", "gdp", "economic growth", "recession",
        "employment", "unemployment", "jobs report", "government debt",
        "sovereign debt", "currency", "devaluation",
    ),
    "supply_chain": (
        "oil", "natural gas", "lng", "shipping", "red sea", "strait",
        "critical minerals", "rare earth", "semiconductor", "supply chain",
        "food security", "grain",
    ),
    "election": (
        "election", "vote", "ballot", "presidential race", "prime minister",
        "coalition government",
    ),
}

OPINION_MARKERS = (
    "opinion:", "commentary:", "letters:", "editorial:", "what i think",
)

STRONG_GEOPOLITICS_TERMS = (
    "sanction", "tariff", "export control", "export controls", "trade war", "war", "military",
    "ceasefire", "central bank", "interest rate", "election", "executive order",
)


def _text(article: dict[str, Any]) -> str:
    return " ".join(
        str(article.get(field) or "")
        for field in ("title", "summary", "description")
    ).casefold()


def _contains(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", text))


def classify_regions(article: dict[str, Any]) -> list[str]:
    """按事件主体标注中国、美国和其他全球地区。"""
    text = _text(article)
    return [
        region
        for region, terms in REGION_TERMS.items()
        if any(_contains(text, term) for term in terms)
    ]


def matched_event_types(article: dict[str, Any]) -> list[str]:
    text = _text(article)
    return [
        event_type
        for event_type, terms in EVENT_TERMS.items()
        if any(_contains(text, term) for term in terms)
    ]


def filter_geopolitics_related(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """仅保留同时具备重要主体和政策/地缘/宏观事件信号的候选。"""
    result: list[dict[str, Any]] = []
    for article in articles:
        title = str(article.get("title") or "").strip().casefold()
        if any(title.startswith(marker) for marker in OPINION_MARKERS):
            continue
        regions = classify_regions(article)
        event_types = matched_event_types(article)
        if not regions or not event_types:
            continue
        item = dict(article)
        item["regions"] = regions
        item["geopoliticsEventTypes"] = event_types
        item["geopoliticsRuleScore"] = geopolitics_rule_score(item)
        result.append(item)
    return result


def geopolitics_rule_score(article: dict[str, Any]) -> float:
    """为跨榜单补位提供可复现的本地排序分数，不替代 LLM 排序。"""
    regions = article.get("regions") or classify_regions(article)
    event_types = article.get("geopoliticsEventTypes") or matched_event_types(article)
    score = 1.0
    if "china" in regions:
        score += 1.0
    if "us" in regions:
        score += 1.0
    if "china" in regions and "us" in regions:
        score += 1.0
    weights = {
        "geopolitics": 2.0,
        "policy": 1.5,
        "macro": 1.25,
        "supply_chain": 1.0,
        "election": 1.0,
    }
    score += sum(weights.get(event_type, 0.0) for event_type in event_types)
    return round(score, 2)


def classify_primary_board(article: dict[str, Any]) -> str:
    """将 AI/政经交叉事件按主要影响归入一个板块。"""
    text = _text(article)
    if not classify_regions(article) or not matched_event_types(article):
        return "ai"
    if not has_ai_context(text):
        return "geopolitics"
    if any(_contains(text, term) for term in STRONG_GEOPOLITICS_TERMS):
        return "geopolitics"
    return "ai"


def select_fresh_geopolitics_window(
    articles: list[dict[str, Any]],
    *,
    now: datetime,
    top_k: int = 5,
) -> tuple[list[dict[str, Any]], int | None]:
    """优先 48 小时，候选不足时扩大到 72 小时，再不足保留全量。"""
    recent_48h = filter_recent_articles(articles, now=now, max_age_hours=48)
    if len(recent_48h) >= top_k:
        return recent_48h, 48
    recent_72h = filter_recent_articles(articles, now=now, max_age_hours=72)
    if len(recent_72h) >= top_k:
        return recent_72h, 72
    return articles, None
