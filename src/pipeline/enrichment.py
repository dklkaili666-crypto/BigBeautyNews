"""候选新闻投研元数据增强：来源分层、实体、事件 ID 与规则评分。"""
from __future__ import annotations

from hashlib import sha1
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


SOURCE_TIERS = {
    "OpenAI Blog": "tier0",
    "Anthropic News": "tier0",
    "Google DeepMind Blog": "tier0",
    "Meta AI Blog": "tier0",
    "NVIDIA Blog": "tier0",
    "Microsoft Azure Blog": "tier0",
    "AWS Blog": "tier0",
    "SemiAnalysis": "tier1",
    "ServeTheHome": "tier1",
    "Hugging Face Blog": "tier1",
    "The Verge": "tier2",
    "TechCrunch": "tier2",
    "Ars Technica": "tier2",
    "MIT Technology Review": "tier2",
    "Wired": "tier2",
    "GitHub Trending": "tier3",
    "Hacker News": "tier3",
}

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid"}

ENTITY_PATTERNS = {
    "OpenAI": ("openai", "chatgpt", "gpt"),
    "Anthropic": ("anthropic", "claude"),
    "Google": ("google", "deepmind", "gemini"),
    "Microsoft": ("microsoft", "azure", "github copilot"),
    "NVIDIA": ("nvidia", "cuda", "gpu"),
    "Meta": ("meta", "llama"),
    "Amazon": ("amazon", "aws"),
    "Apple": ("apple",),
    "TSMC": ("tsmc", "cowos"),
    "Broadcom": ("broadcom",),
    "Hugging Face": ("hugging face",),
}

INVESTMENT_TERMS = (
    "llm", "large language model", "foundation model", "reasoning model",
    "agent", "inference", "gpu", "asic", "tpu", "accelerator", "hbm",
    "cowos", "cuda", "capex", "data center", "datacenter", "power",
    "cooling", "networking", "optics", "transceiver", "800g", "1.6t",
    "cpo", "silicon photonics", "hugging face", "openrouter", "vllm",
    "tensorrt", "pytorch", "order", "guidance", "supply constraint",
    "capacity", "partnership", "azure", "aws", "google cloud",
)

EVENT_TYPE_TERMS = {
    "model_release": ("model", "gpt", "claude", "gemini", "llama"),
    "product_launch": ("launch", "release", "feature", "api", "copilot"),
    "capex": ("capex", "data center", "datacenter", "power", "capacity"),
    "funding": ("funding", "raised", "raises", "valuation", "ipo"),
    "regulation": ("regulation", "policy", "ban", "export control", "sec"),
    "open_source": ("open source", "github", "repo"),
    "supply_chain": ("hbm", "cowos", "tsmc", "supplier", "accelerator"),
}


def canonicalize_url(url: str) -> str:
    """标准化 URL，去掉 fragment 和常见 tracking 参数。"""
    parsed = urlparse(str(url).strip())
    if not parsed.scheme or not parsed.netloc:
        return str(url).strip()
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith(TRACKING_QUERY_PREFIXES)
        and key.casefold() not in TRACKING_QUERY_KEYS
    ]
    path = parsed.path.rstrip("/") or parsed.path
    return urlunparse((
        parsed.scheme.casefold(),
        parsed.netloc.casefold(),
        path,
        "",
        urlencode(query),
        "",
    ))


def _fingerprint(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))[:120]


def extract_entities(text: str) -> list[str]:
    text_cf = text.casefold()
    return [
        entity
        for entity, patterns in ENTITY_PATTERNS.items()
        if any(pattern in text_cf for pattern in patterns)
    ]


def classify_event_type(text: str) -> str:
    text_cf = text.casefold()
    for event_type, patterns in EVENT_TYPE_TERMS.items():
        if any(pattern in text_cf for pattern in patterns):
            return event_type
    return "unknown"


def _score_article(article: dict[str, Any]) -> dict[str, float]:
    source_tier = str(article.get("sourceTier") or "")
    tier_score = {"tier0": 5, "tier1": 4, "tier2": 3, "tier3": 2}.get(source_tier, 2)
    text = " ".join(str(article.get(field) or "") for field in ("title", "summary", "description")).casefold()
    entities = article.get("entities") or []
    event_type = article.get("eventType")
    market = 2.0
    if event_type in {"capex", "supply_chain", "regulation"}:
        market = 4.0
    if any(term in text for term in ("nvidia", "microsoft", "openai", "anthropic", "gpu", "capex")):
        market = min(5.0, market + 1.0)
    novelty = 4.0
    timeliness = 5.0 if article.get("published") else 3.0
    entity_importance = min(5.0, 2.0 + len(entities))
    confidence = min(5.0, tier_score + (1 if len(article.get("merged_sources") or []) > 1 else 0))
    total = market * 0.35 + tier_score * 0.20 + novelty * 0.20 + entity_importance * 0.15 + timeliness * 0.10
    return {
        "sourceCredibilityScore": float(tier_score),
        "marketImpactScore": float(market),
        "noveltyScore": novelty,
        "timelinessScore": timeliness,
        "entityImportanceScore": entity_importance,
        "confidenceScore": confidence,
        "totalScore": round(total, 2),
    }


def enrich_article(article: dict[str, Any]) -> dict[str, Any]:
    item = dict(article)
    source = str(item.get("source") or "")
    item["sourceTier"] = item.get("sourceTier") or SOURCE_TIERS.get(source, "tier2")
    item["isPrimarySource"] = item["sourceTier"] == "tier0"
    item["canonicalUrl"] = item.get("canonicalUrl") or canonicalize_url(str(item.get("url") or ""))
    text = " ".join(str(item.get(field) or "") for field in ("title", "summary", "description"))
    entities = list(dict.fromkeys(item.get("entities") or extract_entities(text)))
    item["entities"] = entities
    item["eventType"] = item.get("eventType") or classify_event_type(text)
    event_basis = "|".join([
        str(item["eventType"]),
        ",".join(sorted(entities)),
        _fingerprint(str(item.get("title") or "")) or str(item["canonicalUrl"]),
    ])
    if not entities:
        event_basis = str(item["canonicalUrl"])
    item["eventId"] = item.get("eventId") or sha1(event_basis.encode("utf-8")).hexdigest()
    item["tickers"] = list(item.get("tickers") or [])
    item["relatedUrls"] = list(item.get("relatedUrls") or [])
    item["primarySource"] = item.get("primarySource") or source
    item["whyItMatters"] = item.get("whyItMatters", "")
    item["investmentImplication"] = item.get("investmentImplication", "")
    item["riskNote"] = item.get("riskNote", "")
    item["warnings"] = list(item.get("warnings") or [])
    item.update(_score_article(item))
    return item


def enrich_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_article(article) for article in articles]
