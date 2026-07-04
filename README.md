# 🤖 BigBeautyNews

> 每日 AI 五件事 · 投研视角

每天自动从北美主流科技媒体和 GitHub Trending 抓取 AI 领域最重要的 5 条新闻，翻译为简体中文，推送到微信，同时输出 JSON 数据给 [投研日历](https://github.com/) 项目。

## 功能

- 🌐 **多源抓取**：The Verge / TechCrunch / Ars Technica / MIT Tech Review / Wired + GitHub Trending + Hacker News
- 🧠 **AI 排序**：LLM 按投研视角权重选出 Top 5（大厂动态 > 竞品格局 > 产品发布 > 融资 > 学术）
- 🌏 **中文翻译**：全部翻译为简体中文，标题 + 摘要 + 原文链接
- 📱 **微信推送**：每天早上 7:45 通过 Server酱推送到微信
- 📅 **投研日历集成**：输出标准化 JSON 供投研日历 L2 导入
- 📖 **本地网页**：按日期浏览历史所有 5 件事

## 项目结构

```
BigBeautyNews/
├── .github/workflows/daily.yml  # GitHub Actions 定时任务
├── src/
│   ├── main.py                  # 主入口（编排整个流水线）
│   ├── config.py                # 配置
│   ├── fetchers/                # 数据抓取
│   │   ├── rss_fetcher.py       # RSS 通用抓取
│   │   ├── github_trending.py   # GitHub Trending
│   │   └── hacker_news.py       # Hacker News
│   ├── pipeline/                # 处理流水线
│   │   ├── dedup.py             # 去重 + 合并
│   │   ├── filter.py            # AI 关键词过滤
│   │   ├── ranker.py            # LLM 排序 Top 5
│   │   └── translator.py        # LLM 翻译中文
│   └── outputs/                 # 输出模块
│       ├── serverchan.py        # Server酱微信推送
│       ├── json_writer.py       # 投研日历 JSON
│       └── web_builder.py       # 网页数据
├── data/                        # 产出数据（Git 追踪）
├── web/                         # 静态网页
└── PRD.md                       # 产品需求文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置密钥

```bash
cp .env.example .env
# 编辑 .env 填入：
#   SERVERCHAN_SENDKEY  → 从 sct.ftqq.com 获取（Server酱 Turbo）
#   LLM_API_KEY         → LLM API Key (OpenAI 兼容)
#   LLM_API_BASE        → API Base URL
#   LLM_MODEL           → 模型名（默认 gpt-4o-mini）
```

### 3. 本地运行

```bash
# 干跑模式（不推送、不写文件）
python src/main.py --dry-run

# 正式运行
python src/main.py

# 当天已经推送过但确实需要人工重发
python src/main.py --force-push
```

### 4. GitHub Actions 部署

1. 将仓库推送到 GitHub
2. 在 `Settings → Secrets → Actions` 中添加：
   - `SERVERCHAN_SENDKEY`
   - `LLM_API_KEY`
   - `LLM_API_BASE`
   - `LLM_MODEL`
3. 启用 Actions，每天早上 7:45（北京时间）自动运行

### 5. 打开本地网页

```bash
# 必须在项目根目录执行，历史数据路径才能正常访问
python -m http.server 8080
# 浏览器打开 http://localhost:8080/web/
```

## 技术栈

- **语言**：Python 3.12+
- **调度**：GitHub Actions (cron: `45 23 * * *` UTC，即北京时间次日 7:45)
- **LLM**：OpenAI 兼容 API (gpt-4o-mini / deepseek-chat 等)
- **推送**：Server酱 Turbo API
- **网页**：纯静态 HTML + CSS + Vanilla JS
