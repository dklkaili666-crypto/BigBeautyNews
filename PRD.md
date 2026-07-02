# BigBeautyNews PRD

> 版本：v1.2 | 日期：2026-07-01 | 状态：已定稿 | 变更：修正 Server酱版本、Schema 分层、LLM 调用次数、网页方案、RSS 源 URL、Actions 权限等骨架校对问题

---

## 1. 产品概述

### 1.1 核心定位

**BigBeautyNews** — 面向 AI 投资者的每日 5 件事简报系统。每天自动从北美主流科技媒体和 GitHub Trending 抓取 AI 领域最重要的 5 条新闻，翻译为简体中文，推送到微信和本地网页，同时以标准化 JSON 接口输出给 AI 投研日历项目。

### 1.2 目标用户

- 用户自己（个人使用，无需多用户/权限）
- 投研日历项目的 L2 数据订阅方

### 1.3 使用场景

| 场景 | 描述 |
|---|---|
| **晨间阅读** | 每天早上 8:00，微信收到 5 条 AI 大事件推送 |
| **本地浏览** | 打开本地网页，按日期浏览历史所有日期的 5 件事 |
| **日历联动** | 投研日历自动导入今日 5 件事，在日历上以 L2 蓝色事件条展示 |
| **深度阅读** | 点击任意消息跳转原文 |

### 1.4 项目名称

- 英文名：**BigBeautyNews**
- 中文描述：每日 AI 五件事

---

## 2. 功能需求

### 2.1 数据源

#### 北美科技媒体（RSS / API / 爬虫）

| 来源 | 方式 | 说明 |
|---|---|---|
| **The Verge** | RSS (`theverge.com/rss/ai-artificial-intelligence/index.xml`) | AI 专版 |
| **TechCrunch** | RSS (`techcrunch.com/category/artificial-intelligence/feed/`) | AI 板块 |
| **Ars Technica** | RSS (`feeds.arstechnica.com/arstechnica/technology-lab`) | Technology Lab（含 AI 内容） |
| **MIT Technology Review** | RSS (`www.technologyreview.com/feed/`) | 科技前沿 |
| **Wired** | RSS (`www.wired.com/feed/tag/ai/latest/rss`) | AI 标签 |

> **注意**：RSS 源 URL 可能随时间变化，抓取模块应以实际 HTTP 200 为准，404 的源自动跳过不阻塞整体流程。

#### 开发者社区

| 来源 | 方式 | 说明 |
|---|---|---|
| **GitHub Trending** | GitHub API / 网页爬取 | AI 相关仓库，按投研视角筛选 |
| **Hacker News** | HN API (`hacker-news.firebaseio.com`) | 可选补充，AI 相关热门讨论 |

### 2.2 数据处理流水线

```
┌──────────────────────────────────────────────────────────────────────┐
│                    每日自动执行（GitHub Actions）                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐              │
│  │ 媒体 RSS 抓取  │   │ GitHub       │   │ HN API       │              │
│  │ (5源, 并行)   │   │ Trending     │   │ (可选)        │              │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘              │
│         │                  │                  │                       │
│         └──────────────────┼──────────────────┘                       │
│                            ▼                                          │
│              ┌─────────────────────────┐                             │
│              │  候选池（原始数据集合）      │                             │
│              │  去重 + 合并同事件报道      │                             │
│              │  预过滤：标题/内容含 AI     │                             │
│              └────────────┬────────────┘                             │
│                           ▼                                           │
│              ┌─────────────────────────┐                             │
│              │  LLM 排序 + 筛选 Top 5   │                             │
│              │  投研视角权重排序：        │                             │
│              │  大厂动态 > 竞品格局 >     │                             │
│              │  产品发布 > 融资 > 学术    │                             │
│              └────────────┬────────────┘                             │
│                           ▼                                           │
│              ┌─────────────────────────┐                             │
│              │  LLM 翻译为简体中文       │                             │
│              │  生成：标题 + 摘要 + 保持原文链接│                        │
│              └────────────┬────────────┘                             │
│                           ▼                                           │
│         ┌─────────────────┼─────────────────┐                        │
│         ▼                 ▼                   ▼                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐              │
│  │ Server酱     │  │ JSON 文件    │  │ 静态网页         │              │
│  │ → 微信推送    │  │ → 投研日历    │  │ → 本地浏览器查看   │              │
│  │ (Markdown)   │  │   L2 导入    │  │   (GitHub Pages)  │              │
│  └─────────────┘  └─────────────┘  └─────────────────┘              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 LLM 排序策略（核心）

每天候选池约 50–80 篇文章，LLM 按以下权重筛出 Top 5：

| 权重优先级 | 类别 | 示例 |
|---|---|---|
| **P0（最高）** | 大厂战略动态 | 英伟达/谷歌/Meta/微软/亚马逊/苹果/特斯拉的 AI 策略调整、并购、重大发布 |
| **P1** | 竞争格局变化 | 新模型开源（如 Llama 4）、竞品关系变化、芯片供应链变动 |
| **P2** | 产品/服务发布 | 新 AI 产品上线、新功能推出、API 开放 |
| **P3** | 融资/估值事件 | AI 独角兽融资、IPO 动向、估值变化 |
| **P4** | 学术/技术突破 | 架构创新、训练方法突破、benchmark 刷新 |
| **P5（最低）** | 社区趋势 | GitHub Trending 热门仓库、HN 热门讨论 |

**排序原则：**
- 同一条新闻的多家媒体报道合并为一条
- 优先"对 AI 投资决策有实质影响"的事件，而不是"有趣但无关"
- LLM 用结构化 JSON 输出，便于后续自动化处理

### 2.4 翻译要求

- **必须翻译为简体中文**，不发送英文原文
- 每条消息结构：**中文标题 + 中文摘要（目标 100–200 字）+ 原文链接（附在末尾）**
- 长度容错：摘要在 **50–500 字**内仍可产出，但记录 warning；超出该范围才重试或失败，避免 LLM 轻微偏离目标导致整条流水线中断
- 翻译质量：投研用语的准确翻译（如 "LLM → 大语言模型"、"benchmark → 基准测试"、"open source → 开源"）
- 保留关键英文专有名词（如公司名、产品名、股票代码）

### 2.5 推送渠道

#### A. 微信推送（Server酱 Turbo）

- **方式**：Server酱 Turbo API，HTTP POST
- **API**：`https://sctapi.ftqq.com/<SENDKEY>.send`
- **注册**：[sct.ftqq.com](https://sct.ftqq.com) 微信扫码登录 → 获取 SendKey
- **时间**：每天早上 8:00（北京时间）
- **格式**：Markdown，`title` 为日期标题，`desp` 为 5 条消息的 Markdown 正文
- **免费额度**：每天 5 条（每次推送算 1 条，刚好够）
- **注意**：Server酱 Turbo 和 Server酱³ 是不同的产品，SendKey 不通用

#### B. 投研日历 JSON 输出

- **输出路径**：`data/daily-5-things.json`
- **Schema** 严格按照投研日历 PRD §2.6 的要求：

```json
{
  "project": "daily-ai-5",
  "exportedAt": "2026-07-01T08:00:00Z",
  "items": [
    {
      "date": "2026-07-01",
      "title": "OpenAI 发布 GPT-5，推理能力超越人类专家",
      "summary": "OpenAI 今日正式发布 GPT-5 模型，在 MMLU、GPQA 等基准测试中全面超越人类专家水平...(100-200字中文摘要)",
      "url": "https://techcrunch.com/2026/07/01/...",
      "source": "TechCrunch"
    }
  ]
}
```

- 投研日历侧通过"导入 JSON 文件"功能读取 → 展示为 L2 蓝色事件条
- **后续可改为 HTTP 接口**：投研日历的 GitHub Actions 直接 `curl` 下载我们仓库 raw 文件，实现完全自动化

#### C. 本地网页

- **方式**：静态 HTML + JSON 数据驱动
- **本地运行**：从项目根目录启动 HTTP 服务：`python -m http.server 8080`，浏览器打开 `http://localhost:8080/web/`
- **远程部署**：GitHub Actions 将 `web/` 与 `data/archive/` 按原目录结构组装为 Pages artifact 并部署；页面入口为站点的 `/web/`
- **功能**：
  - 按日期列表展示每天 5 则消息
  - 默认显示当天，可翻看历史
  - 每条显示：排序数字、中文标题、来源标签、标签、摘要、原文链接
  - 历史数据路径：`../data/archive/YYYY-MM-DD.json`（从 `web/` 目录的相对路径）
  - 响应式布局
- **数据协议**：网页数据文件（`web/data.json`）保留完整内部字段（含 `rank`/`tags`/`dailyTheme`），不裁剪为对外 5 字段

### 2.6 定时执行

- **引擎**：GitHub Actions `schedule` cron
- **时间**：`cron: '0 0 * * *'`（UTC），即北京时间早上 8:00
- **无需本地电脑开机**：所有抓取、处理、推送均在 GitHub 云服务器上完成
- **手动触发**：支持 `workflow_dispatch`，手动运行一次
- **注意事项**：
  - GitHub Actions 延迟：免费用户排队约 0–40 分钟
  - 仓库 60 天无提交会自动停用 schedule，需定期 commit 保持活跃

---

## 3. 数据模型

### 3.1 对外 Schema（投研日历 L2 导入格式）

> 遵循投研日历 PRD §2.6 的约定。**这是写给投研日历的接口契约，只包含投研日历需要的 5 个字段。**

```json
{
  "project": "daily-ai-5",
  "exportedAt": "2026-07-01T08:00:00Z",
  "items": [
    {
      "date": "2026-07-01",
      "title": "中文标题",
      "summary": "中文摘要",
      "url": "https://...",
      "source": "来源名称"
    }
  ]
}
```

### 3.2 内部数据模型

> 系统内部使用更丰富的字段，但写给投研日历的 JSON 只取上述 5 个字段。网页数据（`web/data.json`）和归档（`data/archive/`）保留完整字段。

```typescript
// 单条新闻（内部模型）
interface NewsItem {
  id: string;                    // UUID，唯一标识
  date: string;                  // 日期 ISO 8601 (YYYY-MM-DD)
  title: string;                 // 中文标题（≤ 50 字，概括核心信息）
  summary: string;               // 中文摘要（目标 100–200 字，容错 50–500 字）
  url: string;                   // 原文链接
  source: string;                // 来源名称（如 "TechCrunch" / "GitHub Trending"）
  tags: string[];                // 标签（如 ["大模型", "OpenAI", "融资"]）
  rank: number;                  // 当日排序 1–5
  originalTitle?: string;        // 原文标题（保留，用于溯源）
  createdAt: string;             // 生成时间 ISO 8601
}

// 每日产出文件（对外 = 投研日历 L2）
// → 仅含 5 字段，见 §3.1

// 网页数据文件（内部，保留完整字段）
// → 含 all 字段，供网页渲染 rank/tags/theme
interface DailyDigest {
  project: "daily-ai-5";
  exportedAt: string;            // ISO 8601
  dailyTheme: string;            // 当日主题
  items: NewsItem[];             // 固定 5 条（完整字段）
}

// 历史索引（供网页浏览）
interface HistoryIndex {
  dates: string[];               // 已生成简报的所有日期
  updatedAt: string;
}
```

### 3.3 数据产出总结

| 产出文件 | Schema | 用途 |
|---|---|---|
| `data/daily-5-things.json` | 对外 5 字段（§3.1） | 投研日历导入 |
| `data/archive/YYYY-MM-DD.json` | 内部完整字段（§3.2） | 网页历史浏览 |
| `web/data.json` | 内部完整字段（§3.2） | 网页当日加载 |

### 3.4 内部与外部的字段映射

| 内部字段 | 对外字段 | 规则 |
|---|---|---|
| `date` | `date` | 原样输出，格式 `YYYY-MM-DD` |
| `title` | `title` | 中文标题 |
| `summary` | `summary` | 中文摘要 |
| `url` | `url` | 原文 HTTP(S) 链接 |
| `source` | `source` | 来源名称 |
| `id/tags/rank/originalTitle/createdAt` | — | 仅内部、网页与归档使用，不写入对外 JSON |
| `dailyTheme` | — | 日报级内部字段，不写入对外 JSON |

---

## 4. 技术方案

### 4.1 技术选型

| 维度 | 选择 | 理由 |
|---|---|---|
| **语言** | Python 3.12+ | RSS 解析、HTTP 请求生态成熟（`feedparser`/`requests`/`beautifulsoup4`） |
| **调度** | GitHub Actions | 免费、无需服务器、与 GitHub 生态深度整合 |
| **LLM** | Claude API / OpenAI API / 免费 LLM API | 排序 1 次 + 翻译 1 次 = 每天 2 次调用，成本极低 |
| **微信推送** | Server酱 Turbo API | 免费、一条 HTTP 请求、无需部署 |
| **网页** | 纯静态 HTML + JSON，从项目根目录起 HTTP 服务 | 本地 `python -m http.server 8080` 打开；或 GitHub Pages 发布 `web/` 目录 |
| **数据持久化** | Git 仓库内 JSON 文件 + GitHub Pages artifact | 历史可用 Git 追溯，网页发布物不混入数据分支 |
| **参考基座** | kkkano/tech-digest-daily + easychen/rsspush | 技术架构最接近，可直接 Fork 改造 |

### 4.2 参考项目

| 项目 | 借鉴内容 | GitHub |
|---|---|---|
| **tech-digest-daily** | 多源并发抓取 + LLM 排序 + GitHub Actions + 中文翻译 | [kkkano/tech-digest-daily](https://github.com/kkkano/tech-digest-daily) |
| **rsspush** | Server酱集成 + AI 翻译 + RSS 监控 | [easychen/rsspush](https://github.com/easychen/rsspush) |
| **auto-news-aggregator** | 北美5大媒体 RSS 抓取 + Gemini 摘要 | [4uffin/auto-news-aggregator](https://github.com/4uffin/auto-news-aggregator) |
| **github-trending** | GitHub Trending + LLM 摘要 + 邮件推送 | [oranger0611/github-trending](https://github.com/oranger0611/github-trending) |

### 4.3 项目目录结构

```
BigBeautyNews/
├── .github/workflows/
│   └── daily.yml                # GitHub Actions 定时任务
├── src/
│   ├── main.py                  # 主入口（编排整个流水线）
│   ├── fetchers/                # 数据抓取模块
│   │   ├── __init__.py
│   │   ├── rss_fetcher.py       # RSS 通用抓取器
│   │   ├── github_trending.py   # GitHub Trending 抓取
│   │   └── hacker_news.py       # HN API（可选）
│   ├── pipeline/                # 处理流水线
│   │   ├── __init__.py
│   │   ├── dedup.py             # 去重 + 合并同事件
│   │   ├── filter.py            # 预过滤（AI 关键词）
│   │   ├── ranker.py            # LLM 排序（Top 5）
│   │   └── translator.py        # LLM 翻译
│   ├── outputs/                 # 输出模块
│   │   ├── __init__.py
│   │   ├── serverchan.py        # Server酱推送
│   │   ├── json_writer.py       # 写出投研日历 JSON
│   │   └── web_builder.py       # 更新静态网页
│   └── config.py                # 配置（RSS 源列表、Key 等）
├── data/                        # 产出数据（Git 追踪）
│   ├── daily-5-things.json      # 今日 5 件事（投研日历导入格式，5 字段）
│   ├── history.json             # 历史索引
│   └── archive/                 # 历史归档（完整字段）
│       └── 2026-07-01.json
├── web/                         # 静态网页（从项目根目录起 HTTP 服务）
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
├── README.md
└── CHANGELOG.md
```

### 4.4 架构图（运行流程）

```
GitHub Actions 触发（每天 UTC 00:00 = 北京 08:00）
        │
        ▼
┌───────────────────────────────────┐
│  main.py                          │
│                                    │
│  1. 并行抓取（所有源同时发起）       │
│     ├─ RSS: 5 个北美媒体           │
│     ├─ GitHub Trending             │
│     └─ HN API (可选)               │
│                                    │
│  2. 候选池清洗                     │
│     ├─ 去重（标题相似度 > 0.8）     │
│     ├─ 合并同事件多源报道           │
│     └─ AI 关键词预过滤             │
│                                    │
│  3. LLM 排序 (Top 5)  ← 第 1 次调用│
│                                    │
│  4. LLM 翻译 + 摘要生成  ← 第 2 次  │
│                                    │
│  5. 产出                           │
│     ├─ Server酱推送 → 微信         │
│     ├─ 写出对外 JSON (5字段)→ 投研日历│
│     ├─ 写出内部 JSON (完整字段)→ 网页│
│     └─ 归档历史数据                │
│                                    │
│  6. Git commit & push              │
│     └─ 数据归档到仓库              │
└───────────────────────────────────┘
```

---

## 5. 版本规划

| 版本 | 内容 | 预计产出 |
|---|---|---|
| **v0.1** | 项目骨架搭建 + RSS 抓取 + LLM 排序/翻译 + Server酱推送 | 可运行的每日推送流水线 |
| **v0.2** | 投研日历 JSON 输出 + 历史归档 + GitHub Actions 定时 | 投研日历可导入 L2 数据 |
| **v0.3** | 本地网页（按日期浏览历史 5 则消息） | 浏览器打开即可查看 |
| **v0.4** | GitHub Trending + HN 数据源接入 | 数据源完整覆盖 |
| **v0.5** | 优化：LLM 排序 prompt 迭代 + 翻译质量打磨 + 网页美化 | 稳定运行版本 |

---

## 6. 关键风险 & 对策

| 风险 | 对策 |
|---|---|
| **Server酱免费额度 5 条/天** | 每天只推 1 条消息（内含 5 则，用 Markdown 排版），刚好在免费额度内 |
| **GitHub Actions 延迟** | 接受 0–40 分钟延迟，不是强实时需求 |
| **LLM API 成本** | 每天调用约 2 次（排序 + 翻译），用 cost-optimized 模型（如 deepseek-chat 或 GPT-4o-mini），成本 < ¥0.1/天 |
| **RSS 源不可用** | 多源冗余（5 个媒体源），一个挂了不影响整体；后续可加 web scraping 备用方案 |
| **翻译质量不稳定** | Prompt 中锁定翻译风格 + 术语表，减少 LLM 随意发挥 |

---

## 7. 与投研日历的协作约定

| 约定项 | 约定 |
|---|---|
| **数据格式** | 严格遵循投研日历 PRD §2.6 的 JSON Schema |
| **文件路径** | `data/daily-5-things.json`（固定路径） |
| **推送方式（阶段一）** | 投研日历手动导入 JSON 文件 |
| **推送方式（阶段二）** | 投研日历 GitHub Actions 直接 `curl` 拉取 BigBeautyNews 仓库的 raw JSON URL |
| **文件名** | 固定文件名 `daily-5-things.json`，每次运行覆盖最新内容 |
| **历史归档** | `data/archive/YYYY-MM-DD.json` 保留每天历史，不覆盖 |

---

## 8. 需求确认 Checklist

| # | 需求点 | 确认 |
|---|---|---|
| 1 | 数据源：北美 5 大媒体 (The Verge/TechCrunch/Ars Technica/MIT Tech Review/Wired) | ✓ |
| 2 | 数据源：GitHub Trending（AI 投研相关）+ Hacker News（可选） | ✓ |
| 3 | 筛选策略：LLM 混合排序，投研视角权重（大厂>竞品>产品>融资>学术>社区） | ✓ |
| 4 | 翻译为简体中文，不发送英文原文，末尾附原文链接 | ✓ |
| 5 | 推送：Server酱 Turbo → 微信，每天早上 8:00 | ✓ |
| 6 | 推送：对外 JSON（5 字段）输出给投研日历；内部 JSON（完整字段）供网页 | ✓ |
| 7 | 展示：本地网页，按日期浏览历史 | ✓ |
| 8 | 项目名：BigBeautyNews | ✓ |
| 9 | 运行方式：GitHub Actions，无需本地电脑开机 | ✓ |
| 10 | 实现策略：基于现有开源项目改造 | ✓ |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v1.0 | 2026-07-01 | 初稿，基于与用户的完整需求讨论 |
| v1.1 | 2026-07-01 | 新增 Code Review Checklist（附录） |
| v1.2 | 2026-07-01 | 骨架校对修正：Server酱改为 Turbo、Schema 分层（对外 5 字段 vs 内部完整）、LLM 调用次数修正为 2 次、网页方案明确（项目根起 HTTP 服务）、Ars Technica RSS URL 修正、目录结构注释更新、Checklist 细化和迭代 |

---

---
---

## 附录：Code Review Checklist

> 本 Checklist 供 Claude 对照 PRD 审核 Codex 交付的代码。每次 Review 时复制一份，逐项验证后填写结论。Codex 根据结论修复后重新提交。

### 使用方式
1. Claude 读取 Codex 输出的代码文件
2. 逐项对照 Checklist 验证
3. 打 ✓ / ✗，底部写结论
4. 用户将结论反馈给 Codex

---

### A. 项目骨架 & 工程规范

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| A1 | 项目基于 Python 3.12+，`requirements.txt` 中依赖可正常安装 | PRD §4.1 | |
| A2 | 项目目录结构与 PRD §4.3 一致（`src/fetchers/`, `src/pipeline/`, `src/outputs/`, `data/`, `web/`, `.github/workflows/`） | PRD §4.3 | |
| A3 | `.gitignore` 排除了 `.env`、`__pycache__` 等敏感/临时文件 | 工程规范 | |
| A4 | `README.md` 包含完整的项目说明和运行方式 | 工程规范 | |

### B. RSS 数据抓取模块

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| B1 | 正确抓取 5 个北美媒体 RSS 源：The Verge / TechCrunch / Ars Technica / MIT Tech Review / Wired | PRD §2.1 | |
| B2 | 使用 `feedparser` 解析 RSS，正确处理 `entries` 中的 `title`/`link`/`published`/`summary` | PRD §4.1 | |
| B3 | 并行抓取（`ThreadPoolExecutor` 或 `asyncio`），单源超时 ≤ 15s | PRD §2.2 | |
| B4 | 单一源失败不阻塞整体流程，记录错误日志后继续 | PRD §2.2 | |
| B5 | 每篇文章输出包含：`title`/`url`/`source`/`published`/`summary` 字段 | PRD §2.2 | |
| B6 | 每个源最多取 `MAX_CANDIDATES_PER_SOURCE`（20）篇 | `config.py` | |

### C. GitHub Trending 抓取

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| C1 | 正确抓取 GitHub Trending 当日数据 | PRD §2.1 | |
| C2 | 筛选 AI 相关仓库（基于 description/topics/language 判断） | PRD §2.3-P5 | |
| C3 | 输出格式包含 `title`/`url`/`source`/`stars_today`/`description` | 数据模型 | |

### D. Hacker News 抓取（可选）

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| D1 | 使用 HN Firebase API (`hacker-news.firebaseio.com/v0`) | PRD §2.1 | |
| D2 | 基于 title 关键词筛选 AI 相关内容，min_score 门槛过滤 | PRD §2.1 | |
| D3 | 抓取失败不阻塞主流程（非致命错误） | PRD §2.2 | |

### E. 去重 & 过滤

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| E1 | 标题相似度去重（阈值 0.8），同事件多源报道合并 | PRD §2.2 | |
| E2 | 合并时保留 `merged_sources` 字段，供 LLM 排序时权重上调 | PRD §2.3 | |
| E3 | AI 关键词预过滤器正确实现，关键词列表覆盖大模型/芯片/投资等核心词 | PRD §2.2 | |
| E4 | GitHub Trending 数据源的数据跳过关键词过滤器（已在抓取时筛选） | PRD §2.2 | |
| E5 | 过滤后候选不足 5 篇时，回退到去重后全量 | `main.py` | |

### F. LLM 排序模块（核心）

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| F1 | 使用 OpenAI 兼容客户端（支持任意 `api_base` 切换模型） | PRD §4.1 | |
| F2 | Prompt 包含投研视角排序权重（P0-P5），LLM 理解并遵循 | PRD §2.3 | |
| F3 | Prompt 要求 LLM 输出严格 JSON（不含代码块标记） | `ranker.py` | |
| F4 | LLM 返回 JSON 解析失败时有重试机制（至少 1 次） | `ranker.py` | |
| F5 | 正确将候选文章格式化为 Prompt 中的编号列表 | `ranker.py` | |
| F6 | `select_top5()` 正确根据 LLM 输出的 `source_article_index` 从候选池取出对应文章 | `ranker.py` | |
| F7 | LLM 调用异常有明确的错误处理和日志 | PRD §6 | |

### G. LLM 翻译模块

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| G1 | 翻译 Prompt 包含术语表（LLM → 大语言模型 等），LLM 遵守术语规范 | PRD §2.4 | |
| G2 | 输出要求：标题 ≤ 50 字 + 摘要目标 100–200 字（容错 50–500 字并记录 warning）+ 保留原文链接 | PRD §2.4 | |
| G3 | 保留关键英文专有名词（公司名、产品名、股票代码）不翻译 | PRD §2.4 | |
| G4 | 翻译结果为简体中文 | PRD §2.4 | |
| G5 | 翻译失败有重试机制 | PRD §6 | |

### H. Server酱 Turbo 推送

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| H1 | API 调用格式正确：`POST https://sctapi.ftqq.com/{sendkey}.send` | PRD §2.5-A | |
| H2 | `title` 包含日期标识（如 "🤖 AI 每日 5 件事 | 2026-07-01"） | PRD §2.5-A | |
| H3 | `desp` 为 Markdown 格式，5 条消息排版清晰可读 | PRD §2.5-A | |
| H4 | `sendkey` 未配置时跳过推送（warning 日志）而非报错崩溃 | PRD §2.5-A | |
| H5 | API 返回 `code=0` 时确认为成功，非 0 时记录错误日志 | `serverchan.py` | |
| H6 | 推送失败不影响流水线其他步骤（非阻断错误） | `main.py` | |

### I. JSON 输出

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| I1 | **对外 JSON**（`data/daily-5-things.json`）：Schema 严格遵循投研日历 PRD §2.6：`project`/`exportedAt`/`items[]`，每条仅含 5 字段（`date`/`title`/`summary`/`url`/`source`） | PRD §2.5-B, §3.1 | |
| I2 | **归档 JSON**（`data/archive/YYYY-MM-DD.json`）：保留完整内部字段（含 `rank`/`tags`/`dailyTheme`） | PRD §3.2 | |
| I3 | **网页 JSON**（`web/data.json`）：保留完整内部字段，供 `app.js` 渲染 | PRD §3.2, §3.3 | |
| I4 | 归档文件按日期命名，不覆盖历史 | PRD §7 | |
| I5 | 维护 `data/history.json` 索引（dates 数组去重） | PRD §7 | |

### J. 主入口 & 编排

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| J1 | `main.py` 按正确顺序编排流水线：并行抓取所有源（RSS + GitHub Trending + HN）→ 去重 → 过滤 → 排序 → 翻译 → 输出 | PRD §2.2 | |
| J2 | `--dry-run` 模式下不推送微信、不写文件，但仍执行抓取+排序+翻译 | `main.py` | |
| J3 | 每步有清晰的日志输出和耗时信息 | 工程规范 | |
| J4 | 候选池不足 5 篇时明确报错退出（exit code 1） | `main.py` | |
| J5 | LLM API Key 未配置时明确报错退出（exit code 1），而非静默跳过 | `main.py` | |
| J6 | 整体超时控制合理（GitHub Actions timeout-minutes: 15） | PRD §2.6 | |

### K. GitHub Actions 定时工作流

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| K1 | Workflow 文件位于 `.github/workflows/daily.yml`，`permissions: contents: write` | PRD §4.3 | |
| K2 | cron 表达式 `0 0 * * *` (UTC) = 北京时间 8:00 | PRD §2.6 | |
| K3 | 支持 `workflow_dispatch` 手动触发 | PRD §2.6 | |
| K4 | 通过 GitHub Secrets 注入 `SERVERCHAN_SENDKEY`、`LLM_API_KEY`、`LLM_API_BASE`、`LLM_MODEL` | PRD §4.1 | |
| K5 | 运行成功后自动 `git commit` + `git push` 数据文件（只 add 实际存在的文件） | PRD §2.2 | |
| K6 | Python 版本指定为 3.12 | PRD §4.1 | |
| K7 | `timeout-minutes` 设为 15 | `.github/workflows/daily.yml` | |

### L. 网页浏览

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| L1 | `web/index.html` 为纯静态页面，需从项目根目录起 HTTP 服务（`python -m http.server 8080`），不支持 `file://` 直接打开 | PRD §2.5-C | |
| L2 | 页面加载当天数据：`fetch('data.json')`（从 `web/` 目录相对路径） | PRD §2.5-C | |
| L3 | 历史数据加载：`fetch('../data/archive/YYYY-MM-DD.json')`（从 `web/` 目录相对路径） | PRD §2.5-C | |
| L4 | 历史日期无数据时显示空状态提示，不应 fallback 显示当天数据 | PRD §2.5-C | |
| L5 | 支持通过日期控件或翻页按钮切换到历史日期 | PRD §2.5-C | |
| L6 | 每条消息显示：排序数字、中文标题、来源标签、标签、摘要、原文链接 | PRD §2.5-C | |
| L7 | 响应式布局，手机和桌面均可正常浏览 | PRD §2.5-C | |

---

### Review 记录

| 日期 | 版本 | Review 人 | 通过率 | 主要问题 | Codex 修复状态 |
|---|---|---|---|---|---|
| — | — | — | — | — | — |
