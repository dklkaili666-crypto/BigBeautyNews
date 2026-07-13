# 🤖 BigBeautyNews

> 每日 AI Top 5 + 全球地缘政经 Top 5 · 投研视角

每天分别选出 AI 领域最重要的 5 条新闻和全球地缘政经最重要的 5 条新闻（中国、美国优先），在一条 Server酱消息中分板块推送。投研日历继续通过固定 raw URL 自动拉取原 AI Top 5 五字段 JSON。

## 功能

- 🌐 **多源抓取**：The Verge / TechCrunch / Ars Technica / MIT Tech Review / Wired + GitHub Trending + Hacker News
- 🌍 **免费政经来源**：SCMP China / SCMP Global Economy / NPR Politics / NPR Business / NPR World / BBC World / BBC Business / The Guardian World
- 🧭 **投研增强**：来源分层、AI 投研实体词典、URL 标准化、最小可用 eventId、GitHub repo 冷却
- 🧠 **双榜单排序**：AI 与政经候选池分别规则预过滤、LLM 复核和翻译；正常每天共 4 次 LLM 调用
- 🌏 **中文翻译**：全部翻译为简体中文，标题 + 摘要 + 原文链接
- 📱 **微信推送**：每天早上 7:45 通过一条 Server酱消息推送两个 Top 5
- 📅 **投研日历集成**：`data/daily-5-things.json` 仍只输出 AI 5 条，保持既有 L2 自动拉取契约
- 📖 **本地网页**：按日期分板块浏览 AI 与政经历史；旧归档保持兼容
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
│   │   ├── geopolitics.py       # 政经过滤、地域与主板块分类
│   │   ├── geopolitics_ranker.py # 政经 LLM 排序 Top 5
│   │   └── translator.py        # LLM 翻译中文
│   └── outputs/                 # 输出模块
│       ├── serverchan.py        # Server酱微信推送
│       ├── json_writer.py       # 投研日历 JSON
│       ├── status.py            # 运行状态与错误日志
│       └── web_builder.py       # 网页数据
├── data/                        # 产出数据（Git 追踪）
├── web/                         # 静态网页
├── docs/archive/                # 历史 PRD、实施计划与验收记录
├── PRD.md                       # 当前 v1.8 产品需求文档
├── IMPLEMENTATION_PLAN-v1.8.md  # 当前实施计划
└── TRACEABILITY-v1.8.md         # 当前需求追踪与验收
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt -c constraints.txt

# 开发与验证
pip install -r requirements-dev.txt -c constraints.txt
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

日报 workflow 不包含 GitHub Pages 部署步骤，但仓库的 Pages 设置当前仍为公开 built 状态；这是项目所有者在 v1.8 明确接受且暂不处理的例外。仓库必须保持 Public，因为投研日历页面会匿名读取：

```text
https://raw.githubusercontent.com/dklkaili666-crypto/BigBeautyNews/master/data/daily-5-things.json
```

仓库、raw JSON 与现有 Pages 入口均可能公开访问。本地网页功能和仓库内历史数据继续保留；v1.8 不修改 Pages 设置。

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
- **新闻数据费用**：新增政经来源均为公开免费 RSS，无新闻 API Key 或付费新闻 API
