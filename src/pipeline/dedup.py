"""
候选文章去重与合并。
1. 标题相似度 > 0.8 的文章视为同一事件，合并
2. 合并时保留最早来源的信息、汇总所有来源名称
"""
from __future__ import annotations
from typing import Any
from difflib import SequenceMatcher
import re


def _normalized_title(title: str) -> str:
    return " ".join(re.findall(r"\w+", title.casefold()))


def dedup_candidates(
    articles: list[dict[str, Any]],
    threshold: float = 0.8,
) -> list[dict[str, Any]]:
    """
    对候选文章列表去重。

    - 基于标题文本相似度（difflib.SequenceMatcher 或简单的 token overlap）
    - 同一事件的报道合并为一条：
      - title 保留原文中最具代表性的一条
      - sources 字段列出所有报道来源
      - 同事件多源报道 → 在 LLM 排序时视为更高权重（多源交叉验证 = 大事）

    Args:
        articles: 原始文章列表
        threshold: 相似度阈值，0.8 表示标题 80% 相似的视为同一事件

    Returns:
        去重后的文章列表，每篇可能多出 merged_sources 字段
    """
    if not 0 <= threshold <= 1:
        raise ValueError("threshold 必须在 0 到 1 之间")

    deduped: list[dict[str, Any]] = []
    for article in articles:
        candidate = dict(article)
        source = str(candidate.get("source", "")).strip()
        candidate["merged_sources"] = list(
            dict.fromkeys(candidate.get("merged_sources") or ([source] if source else []))
        )
        normalized = _normalized_title(str(candidate.get("title", "")))

        match = None
        for existing in deduped:
            similarity = SequenceMatcher(
                None,
                normalized,
                _normalized_title(str(existing.get("title", ""))),
            ).ratio()
            if similarity >= threshold:
                match = existing
                break

        if match is None:
            deduped.append(candidate)
            continue

        for merged_source in candidate["merged_sources"]:
            if merged_source not in match["merged_sources"]:
                match["merged_sources"].append(merged_source)
        if len(str(candidate.get("summary", ""))) > len(str(match.get("summary", ""))):
            match["summary"] = candidate.get("summary")

    return deduped
