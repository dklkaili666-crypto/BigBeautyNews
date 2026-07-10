# 🤖 BigBeautyNews

> 每日 AI 五件事 · 投研视角

每天自动从北美主流科技媒体、GitHub Trending 和 Hacker News 抓取 AI 领域最重要的 5 条新闻，按投研视角做去重、评分、筛选和翻译，推送到微信，同时输出 JSON 数据给 [投研日历](https://github.com/) 项目。

## 功能

- 🌐 **多源抓取**：The Verge / TechCrunch / Ars Technica / MIT Tech Review / Wired + GitHub Trending + Hacker News
- 🧭 **投研增强**：来源分层、AI 投研实体词典、URL 标准化、最小可用 eventId、GitHub repo 冷却
- 🧠 **AI 排序**：规则预评分 + LLM 复核选出 Top 5（大厂动态 > 竞品格局 > 产品发布 > 融资 > 学术）
- 🌏 **中文翻译**：全部翻译为简体中文，标题 + 摘要 + 原文链接
- 📱 **微信推送**：每天早上 7:45 通过 Server酱推送到微信
- 📅 **投研日历集成**：输出标准化 JSON 供投研日历 L2 导入
- 📖 **本地网页**：按日期浏览历史所有 5 件事
- 🔎 **可观测性**：输出 `run-status.json` / `run-history.json` / `error-log/YYYY-MM-DD.json`

## 项目结构

```
BigBeautyNews/
├── .github/workflows/daily.yml  # GitHub Actions 云端执行器
├── scripts/                     # 外部调度配置与验证
├── src/
│   ├── main.py                  # 主入口（编排整个流水线）
│   ├── config.py                # 配置
│   ├── fetchers/                # 数据抓取
│   │   ├── rss_fetcher.py       # RSS 通用抓取
│   │   ├── github_trending.py   # GitHub Trending
│   │   └── hacker_news.py       # Hacker News
│   ├── pipeline/                # 处理流水线
│   │   ├── dedup.py             # 去重 + 合并
│   │   ├── enrichment.py        # 来源分层、eventId、规则评分
│   │   ├── filter.py            # AI 投研实体词典过滤
│   │   ├── ranker.py            # LLM 排序 Top 5
│   │   └── translator.py        # LLM 翻译中文
│   └── outputs/                 # 输出模块
│       ├── serverchan.py        # Server酱微信推送
│       ├── json_writer.py       # 投研日历 JSON
│       ├── status.py            # 运行状态与错误日志
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
3. 启用 Actions
4. 运行外部调度配置器：

```bash
python scripts/configure_external_scheduler.py
python scripts/configure_external_scheduler.py --smoke
```

配置器会安全提示输入一个仅限本仓库、只有 Actions 写权限的 GitHub 细粒度令牌，以及一个 cron-job.org API Key。两项凭证仅在当前进程内使用，不写入仓库或 `.env`。第一条命令创建并回读两条 `Asia/Shanghai` 定时任务：7:45 主触发、8:15 幂等兜底；第二条命令通过一次自动删除的临时任务验证完整触发链路。

### 手机手动推送

如果当天自动推送没有触发，可以在手机上操作：

1. 打开 GitHub 仓库的 Issues
2. 新建 issue，选择“手机手动推送”模板
3. 直接提交 issue

模板里默认包含 `/push-force`，会强制触发一次当天微信推送。也可以在任意 issue 下评论：

- `/push`：今天还没成功推送时推送一次
- `/push-force`：即使今天已有成功记录，也强制再推送一次

也可以在 Actions 页面手动运行 workflow，并设置：

- `force_push=true`：强制重发今天日报
- `push_test=true`：只发送一条 Server酱测试消息，不跑抓取/LLM/归档流水线

### 5. 打开本地网页

```bash
# 必须在项目根目录执行，历史数据路径才能正常访问
python -m http.server 8080
# 浏览器打开 http://localhost:8080/web/
```

## 技术栈

- **语言**：Python 3.12+
- **调度**：cron-job.org（北京时间 7:45 主触发、8:15 幂等兜底）+ GitHub Actions 执行器；支持手机 issue 手动触发
- **LLM**：OpenAI 兼容 API (gpt-4o-mini / deepseek-chat 等)
- **推送**：Server酱 Turbo API
- **网页**：纯静态 HTML + CSS + Vanilla JS
