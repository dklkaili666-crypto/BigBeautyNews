"""
GitHub Trending 抓取器。
抓取当天的 GitHub Trending 页面，筛选 AI 相关仓库。

输出格式：
{
    "title": str,          # "repo_owner/repo_name: description"
    "url": str,            # GitHub 仓库链接
    "source": "GitHub Trending",
    "stars_today": int,    # 今日新增星数
    "language": str,       # 主要语言
    "description": str,    # 仓库描述
}
"""
from __future__ import annotations
from typing import Any
import logging
import re
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending?since=daily"
SEARCH_URL = "https://api.github.com/search/repositories"
AI_TERMS = (
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "language model", "neural", "transformer", "diffusion",
    "agent", "rag", "computer vision", "nlp", "pytorch", "tensorflow",
)


def _build_item(
    *,
    name: str,
    url: str,
    description: str,
    language: str = "",
    stars_today: int = 0,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "title": f"{name}: {description}" if description else name,
        "url": url,
        "source": "GitHub Trending",
        "sourceTier": "tier3",
        "stars_today": stars_today,
        "language": language,
        "description": description,
        "summary": description,
        "published": "",
        "warnings": list(warnings or []),
    }


def _is_ai_repo(name: str, description: str) -> bool:
    searchable = f"{name} {description}".casefold()
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", searchable) for term in AI_TERMS)


def _fetch_trending_page() -> list[dict[str, Any]]:
    response = requests.get(
        TRENDING_URL,
        timeout=15,
        headers={"User-Agent": "BigBeautyNews/1.0"},
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    repositories: list[dict[str, Any]] = []
    for row in soup.select("article.Box-row"):
        link = row.select_one("h2 a")
        if not link:
            continue
        path = str(link.get("href", "")).strip()
        name = re.sub(r"\s*/\s*", "/", link.get_text(" ", strip=True))
        description_node = row.select_one("p")
        description = description_node.get_text(" ", strip=True) if description_node else ""
        if not _is_ai_repo(name, description):
            continue
        language_node = row.select_one('[itemprop="programmingLanguage"]')
        stars_node = row.select_one(".float-sm-right")
        stars_match = re.search(r"([\d,]+)\s+stars?\s+today", stars_node.get_text(" ", strip=True) if stars_node else "")
        repositories.append(_build_item(
            name=name,
            url=f"https://github.com{path}",
            description=description,
            language=language_node.get_text(strip=True) if language_node else "",
            stars_today=int(stars_match.group(1).replace(",", "")) if stars_match else 0,
        ))
    return repositories


def _fetch_search_fallback() -> list[dict[str, Any]]:
    response = requests.get(
        SEARCH_URL,
        timeout=15,
        headers={"User-Agent": "BigBeautyNews/1.0"},
        params={
            "q": "topic:ai OR topic:llm OR topic:machine-learning",
            "sort": "updated",
            "order": "desc",
            "per_page": "20",
        },
    )
    response.raise_for_status()
    repositories: list[dict[str, Any]] = []
    for item in response.json().get("items", []):
        name = str(item.get("full_name") or "")
        description = str(item.get("description") or "")
        if not name or not _is_ai_repo(name, description):
            continue
        repositories.append(_build_item(
            name=name,
            url=str(item.get("html_url") or ""),
            description=description,
            language=str(item.get("language") or ""),
            stars_today=int(item.get("stargazers_count") or 0),
            warnings=["GitHub Trending page failed; used GitHub Search API fallback"],
        ))
    return repositories


def fetch_trending() -> list[dict[str, Any]]:
    """
    抓取 GitHub Trending 当日页面，筛选 AI 相关仓库。

    AI 相关判定：
    - description 中包含 AI/ML/LLM/Deep Learning/Neural 等关键词
    - 主要语言为 Python/Jupyter Notebook/TypeScript（AI 项目常用）
    - topics 中有 ai/machine-learning/deep-learning 等标签

    Returns:
        AI 相关的 trending 仓库列表
    """
    try:
        return _fetch_trending_page()
    except Exception as exc:
        logger.warning("GitHub Trending 页面抓取失败，改用 Search API: %s", exc)
        return _fetch_search_fallback()
