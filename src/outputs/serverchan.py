"""
Server酱 Turbo 推送模块。
通过 HTTP POST 将每日 5 件事推送到微信。

API: https://sctapi.ftqq.com/{sendkey}.send
"""
from __future__ import annotations
from typing import Any
import logging
import requests

logger = logging.getLogger(__name__)

# Server酱 Turbo 推送 API
SERVERCHAN_URL = "https://sctapi.ftqq.com/{sendkey}.send"

# 免费会员每天 5 条消息额度
# 内容最大 64KB，支持 Markdown
MAX_TITLE_LENGTH = 256
MAX_DESP_LENGTH = 64 * 1024


def build_markdown_message(
    items: list[dict[str, Any]],
    date_str: str,
    daily_theme: str = "",
) -> tuple[str, str, str]:
    """
    将 5 条消息构建为 Server酱 Markdown 格式。

    Args:
        items: 翻译后的 5 条消息（含 title_cn/summary_cn/url/source/rank）
        date_str: 日期字符串 "2026-07-01"
        daily_theme: 当日主题概况

    Returns:
        (title, desp_markdown, desp_plaintext)
        - title: 推送标题（用于通知栏）
        - desp_markdown: Markdown 正文（Server酱支持）
        - desp_plaintext: 纯文本正文（降级方案）
    """
    title = f"🤖 AI 每日 5 件事 | {date_str}"
    markdown_lines = []
    plain_lines = []
    if daily_theme:
        markdown_lines.extend([f"> **今日主题：** {daily_theme}", ""])
        plain_lines.append(f"今日主题：{daily_theme}")
    for index, item in enumerate(items, start=1):
        rank = item.get("rank", index)
        item_title = str(item.get("title_cn") or item.get("title") or "")
        summary = str(item.get("summary_cn") or item.get("summary") or "")
        source = str(item.get("source") or "")
        url = str(item.get("url") or "")
        markdown_lines.extend([
            f"## {rank}. {item_title}",
            f"**来源：** {source}",
            "",
            summary,
            "",
            f"[阅读原文]({url})",
            "",
            "---",
            "",
        ])
        plain_lines.append(f"{rank}. {item_title}\n来源：{source}\n{summary}\n{url}")
    markdown = "\n".join(markdown_lines)
    if len(markdown.encode("utf-8")) > MAX_DESP_LENGTH:
        raise ValueError("推送内容超过 Server酱 Turbo 64KB 限制")
    return title, markdown, "\n\n".join(plain_lines)


def push_to_wechat(
    sendkey: str,
    items: list[dict[str, Any]],
    date_str: str,
    daily_theme: str = "",
) -> bool:
    """
    通过 Server酱 Turbo API 推送消息到微信。

    Args:
        sendkey: Server酱 SendKey
        items: 翻译后的 5 条消息
        date_str: 日期字符串
        daily_theme: 当日主题概况

    Returns:
        True 推送成功，False 推送失败
    """
    title, desp, _ = build_markdown_message(items, date_str, daily_theme)

    if not sendkey:
        logger.warning("SERVERCHAN_SENDKEY 未配置，跳过微信推送")
        return False

    try:
        url = SERVERCHAN_URL.format(sendkey=sendkey)
        resp = requests.post(
            url,
            data={"title": title[:MAX_TITLE_LENGTH], "desp": desp},
            timeout=10,
        )
        result = resp.json()
        if result.get("code") == 0:
            logger.info(f"Server酱推送成功: pushid={result.get('data', {}).get('pushid')}")
            return True
        else:
            logger.error(f"Server酱推送失败: {result}")
            return False
    except Exception as e:
        logger.error(f"Server酱推送异常: {e}")
        return False
