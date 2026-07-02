"""持久化微信推送成功状态，避免同一天重复发送。"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _load_state(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {"dates": []}
    try:
        with open(path, encoding="utf-8") as file:
            state = json.load(file)
        if isinstance(state, dict) and isinstance(state.get("dates"), list):
            return state
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("推送状态读取失败，将按未推送处理: %s", exc)
    return {"dates": []}


def was_pushed(path: str, date_str: str) -> bool:
    """返回指定日期是否已经成功推送。"""
    return date_str in _load_state(path)["dates"]


def mark_pushed(path: str, date_str: str) -> None:
    """在推送成功后记录日期。"""
    state = _load_state(path)
    dates = {
        value for value in state["dates"]
        if isinstance(value, str)
    }
    dates.add(date_str)
    output = {
        "dates": sorted(dates, reverse=True),
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
        file.write("\n")
