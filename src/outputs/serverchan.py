"""
Server酱 Turbo 推送模块。
通过 HTTP POST 将每日 5 件事推送到微信。

API: https://sctapi.ftqq.com/{sendkey}.send
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import argparse
import json
import logging
import os
import requests

logger = logging.getLogger(__name__)

# Server酱 Turbo 推送 API
SERVERCHAN_URL = "https://sctapi.ftqq.com/{sendkey}.send"

# 免费会员每天 5 条消息额度
# 内容最大 64KB，支持 Markdown
MAX_TITLE_LENGTH = 256
MAX_DESP_LENGTH = 64 * 1024
BODY_PREVIEW_LENGTH = 500


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _key_type(sendkey: str) -> str:
    key = str(sendkey or "").strip().casefold()
    if key.startswith("sct"):
        return "sct"
    if key.startswith("sc"):
        return "sc3"
    return "unknown"


def _preview(value: Any) -> str:
    return str(value)[:BODY_PREVIEW_LENGTH]


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
    return bool(push_to_wechat_with_result(sendkey, items, date_str, daily_theme).get("ok"))


def push_to_wechat_with_result(
    sendkey: str,
    items: list[dict[str, Any]],
    date_str: str,
    daily_theme: str = "",
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "pushAttempted": False,
        "pushAttemptedAt": "",
        "sendkeyPresent": bool(sendkey),
        "serverchanEndpointType": _key_type(sendkey),
        "pushHttpStatus": None,
        "pushResponseCode": None,
        "pushResponseMessage": "",
        "pushResponseBodyPreview": "",
        "pushId": "",
    }
    if not sendkey:
        logger.warning("SERVERCHAN_SENDKEY 未配置，跳过微信推送")
        result["pushSkippedReason"] = "missing_sendkey"
        return result
    try:
        title, desp, _ = build_markdown_message(items, date_str, daily_theme)
        url = SERVERCHAN_URL.format(sendkey=sendkey)
        result["pushAttempted"] = True
        result["pushAttemptedAt"] = _utc_now()
        resp = requests.post(
            url,
            data={"title": title[:MAX_TITLE_LENGTH], "desp": desp},
            timeout=10,
        )
        result["pushHttpStatus"] = resp.status_code
        result["pushResponseBodyPreview"] = _preview(resp.text)
        try:
            response_json = resp.json()
        except ValueError:
            result["pushResponseMessage"] = "invalid_json_response"
            logger.error("Server酱推送失败: invalid JSON: %s", result["pushResponseBodyPreview"])
            return result
        result["pushResponseCode"] = response_json.get("code")
        result["pushResponseMessage"] = str(
            response_json.get("message") or response_json.get("msg") or ""
        )
        response_data = response_json.get("data")
        if isinstance(response_data, dict):
            result["pushId"] = str(response_data.get("pushid") or "")
        result["ok"] = resp.status_code == 200 and response_json.get("code") == 0
        if result["ok"]:
            logger.info(f"Server酱推送成功: pushid={result.get('pushId')}")
        else:
            logger.error(f"Server酱推送失败: {response_json}")
        return result
    except Exception as e:
        logger.error(f"Server酱推送异常: {e}")
        result["pushResponseMessage"] = _preview(e)
        return result


def _test_items() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "title_cn": "Server酱通道测试",
            "summary_cn": "这是一条 BigBeautyNews 推送通道冒烟测试消息。",
            "source": "BigBeautyNews",
            "url": "https://github.com/dklkaili666-crypto/BigBeautyNews",
        }
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Server酱推送通道工具")
    parser.add_argument("--test", action="store_true", help="发送一条 Server酱测试消息")
    args = parser.parse_args()
    if not args.test:
        parser.error("only --test is supported")
    push_result = push_to_wechat_with_result(
        os.getenv("SERVERCHAN_SENDKEY", ""),
        _test_items(),
        datetime.now().strftime("%Y-%m-%d"),
        "BigBeautyNews 推送通道测试",
    )
    print(json.dumps(push_result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if push_result.get("ok") else 1)


if __name__ == "__main__":
    main()
