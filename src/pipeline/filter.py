"""
预过滤器：基于关键词快速淘汰明显非 AI 相关的内容。
在 LLM 排序之前执行，减少 LLM 调用的 token 开销。
"""
from __future__ import annotations
from typing import Any
import re

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
]

# 必须包含的关键词（至少命中一个才算 AI 相关）
MIN_AI_KEYWORD_MATCHES = 1


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
    patterns = [
        re.compile(rf"(?<!\w){re.escape(keyword.casefold())}(?!\w)")
        for keyword in selected_keywords
    ]
    result: list[dict[str, Any]] = []
    for article in articles:
        if article.get("source") == "GitHub Trending":
            result.append(article)
            continue
        text = " ".join(
            str(article.get(field) or "")
            for field in ("title", "summary", "description")
        ).casefold()
        matches = sum(bool(pattern.search(text)) for pattern in patterns)
        if matches >= min_matches:
            result.append(article)
    return result
