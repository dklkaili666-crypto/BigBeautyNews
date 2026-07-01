"""
Hacker News API 抓取器（可选模块）。
抓取当日 HN 热门，筛选 AI/tech 相关讨论。

输出格式：
{
    "title": str,
    "url": str,
    "source": "Hacker News",
    "score": int,          # 投票数
    "comments": int,       # 评论数
}
"""
from __future__ import annotations
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import logging
import re
import requests

logger = logging.getLogger(__name__)

HN_API = "https://hacker-news.firebaseio.com/v0"
AI_TERMS = (
    "ai", "artificial intelligence", "machine learning", "llm", "gpt",
    "claude", "gemini", "openai", "anthropic", "deepmind", "nvidia",
    "neural", "transformer", "agent", "robot",
)


def fetch_hn_top_ai(
    limit: int = 30,
    min_score: int = 50,
) -> list[dict[str, Any]]:
    """
    抓取 Hacker News top stories，筛选 AI 相关。

    Args:
        limit: 从 top stories 中取前 N 条检查
        min_score: 最低投票数门槛

    Returns:
        AI 相关的 HN 帖子列表
    """
    response = requests.get(f"{HN_API}/topstories.json", timeout=10)
    response.raise_for_status()
    story_ids = response.json()[:limit]

    def fetch_story(story_id: int) -> dict[str, Any] | None:
        item_response = requests.get(f"{HN_API}/item/{story_id}.json", timeout=10)
        item_response.raise_for_status()
        return item_response.json()

    with ThreadPoolExecutor(max_workers=10) as executor:
        stories = list(executor.map(fetch_story, story_ids))

    result: list[dict[str, Any]] = []
    for story in stories:
        if not story or story.get("type", "story") != "story":
            continue
        title = str(story.get("title", ""))
        score = int(story.get("score", 0))
        text = title.casefold()
        if score < min_score or not any(
            re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in AI_TERMS
        ):
            continue
        story_id = story.get("id")
        result.append({
            "title": title,
            "url": story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
            "source": "Hacker News",
            "score": score,
            "comments": int(story.get("descendants", 0)),
            "summary": "",
            "published": (
                datetime.fromtimestamp(story["time"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if story.get("time") else ""
            ),
        })
    return result
