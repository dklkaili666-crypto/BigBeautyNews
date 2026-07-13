# BigBeautyNews 配置文件
# 敏感信息通过 GitHub Secrets 注入，开发时可用 .env 文件本地测试

import os
from dotenv import load_dotenv

load_dotenv()

# --- Server酱 ---
SERVERCHAN_SENDKEY = os.getenv("SERVERCHAN_SENDKEY", "")

# --- LLM API (OpenAI 兼容接口) ---
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE") or "https://api.openai.com/v1"
LLM_MODEL = os.getenv("LLM_MODEL") or "gpt-4o-mini"
LLM_MAX_TOKENS = 4096
LLM_TEMPERATURE = 0.3        # 低温度，保证翻译一致性

# --- RSS 数据源 ---
RSS_SOURCES: list[dict] = [
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "type": "rss",
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "type": "rss",
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "type": "rss",
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "type": "rss",
    },
    {
        "name": "Wired",
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "type": "rss",
    },
    {
        "name": "GitHub Trending",
        "url": "https://github.com/trending?since=daily",
        "type": "github_trending",
    },
    {
        "name": "Hacker News",
        "url": "https://hacker-news.firebaseio.com/v0",
        "type": "hn_api",
    },
]

GEOPOLITICS_RSS_SOURCES: list[dict] = [
    {
        "name": "SCMP China",
        "url": "https://www.scmp.com/rss/4/feed",
        "type": "rss",
    },
    {
        "name": "SCMP Global Economy",
        "url": "https://www.scmp.com/rss/12/feed",
        "type": "rss",
    },
    {
        "name": "NPR Politics",
        "url": "https://feeds.npr.org/1014/rss.xml",
        "type": "rss",
    },
    {
        "name": "NPR Business",
        "url": "https://feeds.npr.org/1006/rss.xml",
        "type": "rss",
    },
    {
        "name": "NPR World",
        "url": "https://feeds.npr.org/1004/rss.xml",
        "type": "rss",
    },
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "type": "rss",
    },
    {
        "name": "BBC Business",
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "type": "rss",
    },
    {
        "name": "The Guardian World",
        "url": "https://www.theguardian.com/world/rss",
        "type": "rss",
    },
]

# --- 候选池设置 ---
MAX_CANDIDATES_PER_SOURCE = 20   # 每个源最多取多少篇进候选池
TOP_K = 5                         # 最终选出 5 条

# --- 输出路径 ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DAILY_JSON_PATH = os.path.join(DATA_DIR, "daily-5-things.json")
HISTORY_JSON_PATH = os.path.join(DATA_DIR, "history.json")
PUSH_HISTORY_PATH = os.path.join(DATA_DIR, "push-history.json")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
