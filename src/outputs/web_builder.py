"""
静态网页构建器。
更新 web/ 目录下的当日 JSON 数据文件（供 index.html 加载）。
历史索引由 outputs.json_writer.update_history_index 维护。
（注：web/ 的 HTML/CSS/JS 是手写的静态文件，不需要动态生成）
"""
from __future__ import annotations
from typing import Any
import json
import os
import logging

logger = logging.getLogger(__name__)


def write_web_data(
    digest: dict[str, Any],
    web_dir: str,
) -> str:
    """
    将当日简报数据写入 web/ 目录，供网页 JS 加载。

    写出一个文件：
    - web/data.json: 当天数据（网页默认加载）

    Args:
        digest: build_daily_digest 的返回值
        web_dir: web 静态文件目录

    Returns:
        写入的 data.json 路径
    """
    os.makedirs(web_dir, exist_ok=True)

    # 当天数据
    data_path = os.path.join(web_dir, "data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)
    logger.info(f"Web data.json 已更新: {data_path}")

    return data_path
