# BigBeautyNews PRD

> 版本：v1.5 | 日期：2026-07-05 | 状态：v0.6 开发就绪 | 变更：明确 v0.6 实施边界、验收口径、事件 ID 规则、评分规则、运行状态语义和非目标范围

---

## 1. 产品概述

### 1.1 核心定位

**BigBeautyNews** — 面向 AI 投资者的每日 5 件事简报系统。目标形态是每天自动从官方一手源、专业行业源、北美主流科技媒体、GitHub Trending / Hacker News 等来源抓取 AI 领域最重要的 5 条事件，翻译为简体中文，推送到微信和本地网页，同时以标准化 JSON 接口输出给 AI 投研日历项目。

产品定位不是“AI 新闻翻译器”，而是“AI 投研信息雷达”：优先捕捉对公司、产业链、Capex、芯片、云服务、模型竞争和监管环境有影响的事件，并保留足够的内部字段，方便后续复盘、检索和投研日历联动。

### 1.2 目标用户

- 用户自己（个人使用，无需多用户/权限）
- 投研日历项目的 L2 数据订阅方

### 1.3 使用场景

| 场景 | 描述 |
|---|---|
| **晨间阅读** | 每天早上 7:45，微信收到 5 条 AI 大事件推送 |
| **本地浏览** | 打开本地网页，按日期浏览历史所有日期的 5 件事 |
| **日历联动** | 投研日历自动导入今日 5 件事，在日历上以 L2 蓝色事件条展示 |
| **深度阅读** | 点击任意消息跳转原文 |

### 1.4 项目名称

- 英文名：**BigBeautyNews**
- 中文描述：每日 AI 五件事

### 1.5 当前基线与本轮实施范围

为避免把长期愿景和本轮开发混在一起，PRD 将能力分为三层：

| 层级 | 范围 | 状态 |
|---|---|---|
| 已实现基线 | Tier 2 媒体 RSS、GitHub Trending、Hacker News、跨日 URL / 近似标题去重、48/72 小时时效窗口、微信推送、对外 5 字段 JSON、网页归档、7:45 + 8:15 调度兜底 | 已具备，后续改动不得破坏 |
| v0.6 本轮实施 | 来源分层字段、AI 投研实体词典、确定性规则预评分、最小可用 `eventId`、GitHub repo 冷却、运行状态文件、失败日志、PRD / Checklist 对齐 | 下一步开发目标 |
| 后续增强 | 大规模 Tier 0 / Tier 1 一手源覆盖、SEC / 财报 transcript 深度解析、embedding 聚类、RAG 历史问答、自动股票代码映射、邮件 / Telegram / 企业微信多通道告警 | 暂不作为 v0.6 验收条件 |

v0.6 的原则：优先把“数据质量、防重复、可观测性、验收口径”打牢；不为了追求完整投研平台而一次性重构全系统。

---

## 2. 功能需求

### 2.1 数据源

#### 信息源优先级

系统按来源质量分层处理信息。当前已接入 Tier 2 / Tier 3；v0.6 必须在数据模型中支持所有层级，并至少为后续接入 Tier 0 / Tier 1 留出配置入口。完整覆盖 Tier 0 / Tier 1 属于后续增强，不作为 v0.6 阻塞项。

| 层级 | 来源类型 | 示例 | 用途 |
|---|---|---|
| **Tier 0** | 官方 / 一手源 | OpenAI Blog、Anthropic News、Google DeepMind Blog、Meta AI Blog、NVIDIA Blog、Microsoft Azure Blog、AWS Blog、SEC 8-K/10-Q/10-K、公司 IR、业绩会 transcript | 确认重大事件，提升信息质量上限 |
| **Tier 1** | 专业行业源 | SemiAnalysis、ServeTheHome、Hugging Face Blog、arXiv、Papers with Code、The Decoder | 判断产业趋势、技术演进和供给瓶颈 |
| **Tier 2** | 主流科技媒体 | The Verge、TechCrunch、Ars Technica、MIT Technology Review、Wired | 传播热度与二次验证 |
| **Tier 3** | 社区趋势 | GitHub Trending、Hacker News | 捕捉早期开发者趋势 |

#### 当前已接入来源

| 来源 | 层级 | 方式 | 说明 |
|---|---|---|---|
| **The Verge** | Tier 2 | RSS (`theverge.com/rss/ai-artificial-intelligence/index.xml`) | AI 专版 |
| **TechCrunch** | Tier 2 | RSS (`techcrunch.com/category/artificial-intelligence/feed/`) | AI 板块 |
| **Ars Technica** | Tier 2 | RSS (`feeds.arstechnica.com/arstechnica/technology-lab`) | Technology Lab（含 AI 内容） |
| **MIT Technology Review** | Tier 2 | RSS (`www.technologyreview.com/feed/`) | 科技前沿 |
| **Wired** | Tier 2 | RSS (`www.wired.com/feed/tag/ai/latest/rss`) | AI 标签 |
| **GitHub Trending** | Tier 3 | 优先网页爬取；失败时 fallback 到 GitHub Search API | AI 相关仓库，按投研视角筛选 |
| **Hacker News** | Tier 3 | HN API (`hacker-news.firebaseio.com`) | 可选补充，AI 相关热门讨论 |

> **注意**：RSS 源 URL 可能随时间变化，抓取模块应以实际 HTTP 200 为准，404 的源自动跳过不阻塞整体流程。
> **GitHub Trending 注意**：GitHub Trending 没有稳定官方 API。优先网页爬取真实 Trending；失败时 fallback 到 GitHub Search API，使用 `topic:ai OR topic:llm OR topic:machine-learning`，按近 7 日新增 stars / pushed 时间排序。

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
│              │  当日去重 + 事件级合并        │                             │
│              │  跨日 eventId/URL/repo 冷却  │                             │
│              │  预过滤：AI 投研实体词典       │                             │
│              └────────────┬────────────┘                             │
│                           ▼                                           │
│              ┌─────────────────────────┐                             │
│              │  规则预评分 + LLM 复核 Top 5 │                             │
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

### 2.3 排序策略（核心）

每天候选池约 50–80 篇文章。系统不应完全依赖 LLM 主观排序，而应采用“规则预评分 + LLM 复核排序”：

1. 抓取层为每条候选内容补充来源层级、发布时间、原始来源、实体词等结构化字段；
2. 规则层用确定性逻辑计算投研价值分数，形成可解释的初始排序；
3. LLM 基于候选内容和结构化分数做最终 Top 5 选择、解释和微调；
4. 最终入选原因、分数和 warning 写入内部归档，方便复盘。

#### 2.3.1 投研权重

| 权重优先级 | 类别 | 示例 |
|---|---|---|
| **P0（最高）** | 大厂战略动态 | 英伟达/谷歌/Meta/微软/亚马逊/苹果/特斯拉的 AI 策略调整、并购、重大发布 |
| **P1** | 竞争格局变化 | 新模型开源（如 Llama 4）、竞品关系变化、芯片供应链变动 |
| **P2** | 产品/服务发布 | 新 AI 产品上线、新功能推出、API 开放 |
| **P3** | 融资/估值事件 | AI 独角兽融资、IPO 动向、估值变化 |
| **P4** | 学术/技术突破 | 架构创新、训练方法突破、benchmark 刷新 |
| **P5（最低）** | 社区趋势 | GitHub Trending 热门仓库、HN 热门讨论 |

#### 2.3.2 规则预评分字段

每条候选新闻先生成结构化评分，分值范围 0–5：

| 字段 | 含义 |
|---|---|
| `sourceCredibilityScore` | 来源权威性，官方/SEC/IR 最高，社区传闻最低 |
| `marketImpactScore` | 对股票、产业链、Capex、竞争格局的潜在影响 |
| `noveltyScore` | 是否是新增信息，而不是重复报道 |
| `timelinessScore` | 信息新鲜度 |
| `entityImportanceScore` | 涉及公司、人物、模型、产业链节点的重要性 |
| `confidenceScore` | 信息是否可交叉验证；不进入默认总分，但用于风险提示和人工复盘 |

默认总分：

```text
totalScore =
  marketImpactScore * 0.35
+ sourceCredibilityScore * 0.20
+ noveltyScore * 0.20
+ entityImportanceScore * 0.15
+ timelinessScore * 0.10
```

LLM 可以基于上下文微调顺序，但必须在 `selectionReason` 中解释为什么高分候选被放弃或低分候选被选入。

v0.6 不允许为预评分额外增加 LLM 调用；预评分必须可本地复现。LLM 调用仍保持“排序 1 次 + 必要时重排 1 次 + 翻译 1 次”的成本边界。

**排序原则：**
- 同一事件的多家媒体报道合并为一条，保留 `relatedUrls` / `mergedSources` / `primarySource`
- 最近 7 天已经推送过的 URL 不得再次进入候选池；近似相同标题按同事件排除
- GitHub Trending 仓库 URL 默认冷却 14 天，避免同一个 repo 连续多日进入 Top 5
- 同一事件的 `eventId` 默认冷却 7 天；官方重大事件允许作为“后续进展”再次入选，但必须标注新信息点
- 默认只使用最近 48 小时的文章；不足 5 条时扩大到 72 小时，再不足时可放宽时效，但不得放宽跨日去重
- 优先"对 AI 投资决策有实质影响"的事件，而不是"有趣但无关"
- 来源多样性是强偏好，不是绝对失败条件：候选池质量充足时 Top 5 尽量覆盖至少 3 个来源、单一来源尽量不超过 2 条；首次结果过度集中时自动要求 LLM 重排；重试后仍集中则继续产出，但写入 warning
- 例外：`marketImpactScore >= 4.5` 且 `sourceTier = "tier0"` 的官方重大事件，不因来源多样性被剔除
- LLM 用结构化 JSON 输出，便于后续自动化处理

### 2.4 事件级去重

系统不应仅靠 URL 或标题相似度去重，而应逐步升级为事件级去重。每个事件生成稳定 `eventId`，用于跨日冷却、同事件合并和历史复盘。

```typescript
interface NewsEvent {
  eventId: string;
  canonicalTitle: string;
  entities: string[];
  eventType: string;
  firstSeenAt: string;
  lastSeenAt: string;
  sourceUrls: string[];
  primarySource: string;
}
```

事件聚类依据：

| 方法 | 用途 |
|---|---|
| URL 标准化 | 去掉 UTM / tracking 参数，统一 redirect 后真实链接 |
| 标题相似度 / SimHash / embedding | 判断近似标题 |
| 实体抽取 | 识别 OpenAI、NVIDIA、Microsoft、Llama、CUDA、CoWoS 等关键实体 |
| 时间窗口 | 48/72 小时内高度相关事件合并 |
| 事件类型 | 产品发布、模型发布、财报、融资、监管、并购、开源、论文、供应链 |

v0.6 的最小实现规则：

1. `canonicalUrl`：移除 fragment、常见 tracking 参数（如 `utm_*`、`fbclid`、`gclid`），标准化 host 大小写和尾部 `/`。
2. `entities`：先用 AI 投研实体词典做规则抽取；未识别到实体时允许为空数组。
3. `eventType`：先用关键词规则分类；无法识别时使用 `unknown`。
4. `eventId`：优先使用 `eventType + sorted(top entities) + normalized title fingerprint` 生成 SHA-1；若实体为空，则退化为 `canonicalUrl` 的 SHA-1。
5. 跨日去重优先级：`canonicalUrl` 精确匹配 > `eventId` 匹配 > 标题相似度阈值匹配。
6. 同一事件再次入选时，必须在 `selectionReason` 或 `warnings` 中标注“后续进展”，否则按重复内容排除。

### 2.5 AI 投研实体词典

预过滤不应只依赖标题或正文是否出现 “AI”。系统应维护 AI 投研实体词典，覆盖这些类别：

| 类别 | 示例 |
|---|---|
| 大模型 | LLM、foundation model、reasoning model、agent、inference |
| 云厂商 | Microsoft Azure、AWS、Google Cloud、Meta、Oracle Cloud |
| 芯片 | GPU、ASIC、TPU、accelerator、HBM、CoWoS、CUDA |
| 数据中心 | capex、data center、power、cooling、networking |
| 光通信 | optics、transceiver、800G、1.6T、CPO、silicon photonics |
| 模型平台 | Hugging Face、OpenRouter、vLLM、TensorRT、PyTorch |
| 产业事件 | order、guidance、supply constraint、capacity、partnership |

### 2.6 翻译要求

- **必须翻译为简体中文**，不发送英文原文
- 每条消息结构：**中文标题 + 中文摘要（目标 100–200 字）+ 原文链接（附在末尾）**
- 长度容错：摘要在 **50–500 字**内仍可产出，但记录 warning；超出该范围才重试或失败，避免 LLM 轻微偏离目标导致整条流水线中断
- 翻译质量：投研用语的准确翻译（如 "LLM → 大语言模型"、"benchmark → 基准测试"、"open source → 开源"）
- 保留关键英文专有名词（如公司名、产品名、股票代码）

### 2.7 推送渠道

#### A. 微信推送（Server酱 Turbo）

- **方式**：Server酱 Turbo API，HTTP POST
- **API**：`https://sctapi.ftqq.com/<SENDKEY>.send`
- **注册**：[sct.ftqq.com](https://sct.ftqq.com) 微信扫码登录 → 获取 SendKey
- **时间**：每天早上 7:45（北京时间）
- **格式**：Markdown，`title` 为日期标题，`desp` 为 5 条消息的 Markdown 正文
- **免费额度**：每天 5 条（每次推送算 1 条，刚好够）
- **注意**：Server酱 Turbo 和 Server酱³ 是不同的产品，SendKey 不通用
- **幂等保护**：成功推送日期写入 `data/push-history.json`；同一天重跑默认只刷新数据、不重复推送。人工确需重发时使用 `--force-push`
- `push-history.json` 只记录微信推送成功；完整运行状态写入 `run-history.json` / `run-status.json`

#### B. 投研日历 JSON 输出

- **输出路径**：`data/daily-5-things.json`
- **Schema** 严格按照外部投研日历项目 PRD §2.6 的要求：

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

### 2.8 定时执行

- **引擎**：GitHub Actions `schedule` cron
- **时间**：主触发 `cron: '45 23 * * *'`（UTC），即北京时间次日早上 7:45；并在 8:15、8:35、8:55、9:20（北京时间）设置多时点冗余触发
- **兜底幂等**：每个冗余触发点运行前检查当天推送状态，已成功则跳过，未成功则重试完整流水线
- **业务日期**：所有面向用户和归档的 `date` 均使用北京时间业务日期，即 `datetime.now(ZoneInfo("Asia/Shanghai")).date()`；`exportedAt` 可继续使用 UTC ISO 时间
- **无需本地电脑开机**：所有抓取、处理、推送均在 GitHub 云服务器上完成
- **手动触发**：支持 `workflow_dispatch`，手动运行一次；同时支持手机端新建 `manual-push` issue 或评论 `/push` / `/push-force` 触发推送
- **注意事项**：
  - GitHub Actions 延迟：免费用户排队约 0–40 分钟
  - 仓库 60 天无提交会自动停用 schedule，需定期 commit 保持活跃

---

## 3. 数据模型

### 3.1 对外 Schema（投研日历 L2 导入格式）

> 遵循外部投研日历项目 PRD §2.6 的约定。**这是写给投研日历的接口契约，只包含投研日历需要的 5 个字段。**

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
  eventId: string;               // 事件级 ID，用于跨日去重和复盘
  date: string;                  // 日期 ISO 8601 (YYYY-MM-DD)
  title: string;                 // 中文标题（≤ 50 字，概括核心信息）
  summary: string;               // 中文摘要（目标 100–200 字，容错 50–500 字）
  url: string;                   // 原文链接
  canonicalUrl: string;          // 标准化后的原文链接
  source: string;                // 来源名称（如 "TechCrunch" / "GitHub Trending"）
  sourceTier: "tier0" | "tier1" | "tier2" | "tier3";
  isPrimarySource: boolean;      // 是否一手源
  tags: string[];                // 标签（如 ["大模型", "OpenAI", "融资"]）
  rank: number;                  // 当日排序 1–5
  eventType: string;             // product_launch/model_release/earnings/regulation/funding/open_source 等
  entities: string[];            // 公司、产品、模型、人物、产业链节点
  tickers: string[];             // 相关股票代码，如 NVDA/MSFT/GOOGL
  sourceCredibilityScore: number;
  marketImpactScore: number;
  noveltyScore: number;
  timelinessScore: number;
  entityImportanceScore: number;
  confidenceScore: number;
  totalScore: number;
  whyItMatters: string;          // 为什么重要，中文 1–2 句话
  investmentImplication: string; // 对投资研究的含义
  riskNote: string;              // 风险或不确定性
  originalTitle?: string;        // 原文标题（保留，用于溯源）
  published?: string;            // 原文发布时间 ISO 8601
  mergedSources: string[];       // 同事件合并的媒体来源
  relatedUrls: string[];         // 同事件其他报道
  primarySource: string;         // 同事件首选来源
  selectionReason: string;       // LLM 给出的入选原因
  promptVersion: string;         // Prompt 版本，方便复盘
  modelUsed: string;             // 使用模型
  rawPayloadHash: string;        // 原始数据哈希
  warnings: string[];            // 非阻断 warning
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

interface RunStatus {
  date: string;                  // 北京时间业务日期
  status: "success" | "failed" | "partial";
  startedAt: string;             // UTC ISO
  finishedAt: string;            // UTC ISO
  candidateCount: number;
  selectedCount: number;
  sourcesAvailable: number;
  llmModel: string;
  generated: boolean;
  pushed: boolean;
  committed: boolean;
  schemaValid: boolean;
  warnings: string[];
  errors: string[];
}
```

运行状态语义：

| 字段 | 含义 |
|---|---|
| `generated` | 已完成 Top 5 生成、翻译、Schema 校验和本地 JSON 写出 |
| `pushed` | Server酱返回成功，且已写入 `push-history.json` |
| `committed` | 数据文件、状态文件、归档文件已提交到 Git 仓库 |
| `schemaValid` | 对外 JSON 与内部归档 JSON 均通过本地 schema 校验 |
| `status=success` | `generated=true`、`pushed=true`、`committed=true`、`schemaValid=true` |
| `status=partial` | 数据已生成但推送或提交失败；工作流仍应最终返回失败，方便 8:15 兜底重试 |
| `status=failed` | 未能生成可用 Top 5，或 schema 校验失败 |

推送失败时，不得写入 `push-history.json`；8:15 兜底只以 `push-history.json` 判断是否需要重试，不以 `run-status.json` 的 `generated` 判断。

### 3.3 数据产出总结

| 产出文件 | Schema | 用途 |
|---|---|---|
| `data/daily-5-things.json` | 对外 5 字段（§3.1） | 投研日历导入 |
| `data/archive/YYYY-MM-DD.json` | 内部完整字段（§3.2） | 网页历史浏览 |
| `web/data.json` | 内部完整字段（§3.2） | 网页当日加载 |
| `data/run-status.json` | 最近一次运行状态（§3.2） | 故障排查 |
| `data/run-history.json` | 历史运行状态列表 | 判断连续失败 |
| `data/error-log/YYYY-MM-DD.json` | 当天失败详情 | 保留候选池、错误和 warning |

### 3.4 内部与外部的字段映射

| 内部字段 | 对外字段 | 规则 |
|---|---|---|
| `date` | `date` | 原样输出，格式 `YYYY-MM-DD` |
| `title` | `title` | 中文标题 |
| `summary` | `summary` | 中文摘要 |
| `url` | `url` | 原文 HTTP(S) 链接 |
| `source` | `source` | 来源名称 |
| `id/eventId/tags/rank/originalTitle/published/sourceTier/*Score/entities/tickers/mergedSources/relatedUrls/selectionReason/warnings/createdAt` | — | 仅内部、网页与归档使用，不写入对外 JSON |
| `dailyTheme` | — | 日报级内部字段，不写入对外 JSON |

---

## 4. 技术方案

### 4.1 技术选型

| 维度 | 选择 | 理由 |
|---|---|---|
| **语言** | Python 3.12+ | RSS 解析、HTTP 请求生态成熟（`feedparser`/`requests`/`beautifulsoup4`） |
| **调度** | GitHub Actions | 免费、无需服务器、与 GitHub 生态深度整合 |
| **LLM** | Claude API / OpenAI API / 免费 LLM API | 排序 1 次 + 必要时重排 1 次 + 翻译 1 次；规则预评分不额外调用 LLM |
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
│   │   ├── filter.py            # 预过滤（AI 投研实体词典）
│   │   ├── ranker.py            # LLM 排序（Top 5）
│   │   └── translator.py        # LLM 翻译
│   ├── outputs/                 # 输出模块
│   │   ├── __init__.py
│   │   ├── serverchan.py        # Server酱推送
│   │   ├── push_state.py        # 推送成功状态与幂等保护
│   │   ├── json_writer.py       # 写出投研日历 JSON
│   │   └── web_builder.py       # 更新静态网页
│   └── config.py                # 配置（RSS 源列表、Key 等）
├── data/                        # 产出数据（Git 追踪）
│   ├── daily-5-things.json      # 今日 5 件事（投研日历导入格式，5 字段）
│   ├── history.json             # 历史索引
│   ├── push-history.json        # 已成功推送日期（防重复推送）
│   ├── run-status.json          # 最近一次运行状态
│   ├── run-history.json         # 历史运行状态
│   ├── error-log/               # 失败日志与候选池快照
│   │   └── 2026-07-01.json
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
GitHub Actions 触发（每天 UTC 23:45 = 北京次日 07:45）
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
│     ├─ URL / 标题 / eventId 去重    │
│     ├─ 合并同事件多源报道           │
│     └─ AI 投研实体词典预过滤         │
│                                    │
│  3. 规则预评分 + LLM 排序 Top 5     │
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
| **v0.5** | 优化：推送幂等、来源多样性、真实样本去重调优、翻译质量与网页美化 | 稳定运行版本 |
| **v0.6** | 投研增强：来源分层、事件级去重、规则预评分、运行状态监控 | 更接近投研信息雷达 |

### 5.1 v0.6 明确非目标

以下内容允许在设计上预留字段或接口，但不得作为 v0.6 的阻塞验收项：

- 不做完整 SEC / 10-K / 10-Q / 8-K 解析系统；
- 不做财报电话会 transcript 自动摘要；
- 不引入 embedding 向量库或 RAG 历史问答；
- 不强制自动识别所有股票代码，`tickers` 可先为空数组或规则命中；
- 不做多用户权限、后台管理、订阅管理；
- 不新增邮件 / Telegram / 企业微信等第二推送通道；
- 不改变投研日历对外 5 字段 JSON 契约。

---

## 6. 关键风险 & 对策

| 风险 | 对策 |
|---|---|
| **Server酱免费额度 5 条/天** | 每天只推 1 条消息（内含 5 则，用 Markdown 排版），刚好在免费额度内 |
| **GitHub Actions 延迟或漏调度** | 7:45 主触发 + 8:15/8:35/8:55/9:20 多时点冗余；当天已成功时不重复生成或推送；仍未触发时可用手机 issue 手动推送 |
| **LLM API 成本** | 正常每天调用 2 次（排序 + 翻译），格式错误或来源集中时最多额外重试 / 重排 1 次；规则预评分不调用 LLM |
| **RSS 源不可用** | 多源冗余（5 个媒体源），一个挂了不影响整体；后续可加 web scraping 备用方案 |
| **新闻重复或过旧** | 读取最近 7 天归档做跨日去重；默认 48 小时时效窗口，候选不足时逐级放宽 |
| **翻译质量不稳定** | Prompt 中锁定翻译风格 + 术语表，减少 LLM 随意发挥 |
| **信息源偏媒体化** | 增加 Tier 0 官方 / 监管 / IR 一手源和 Tier 1 专业行业源，媒体源降为传播热度验证 |
| **LLM 排序不可解释** | 先做规则预评分，再让 LLM 复核排序；内部归档保留分数、原因和 warning |
| **来源多样性误伤重大事件** | 多样性作为强偏好；官方重大高分事件允许突破来源上限，但记录 warning |
| **运行失败不可见** | 输出 `run-status.json`、`run-history.json`、`error-log/YYYY-MM-DD.json`；连续失败时单独告警 |
| **北京时间与 UTC 日期错位** | 所有用户可见日期和归档日期使用 Asia/Shanghai 业务日期；`exportedAt` 使用 UTC |

---

## 7. 与投研日历的协作约定

| 约定项 | 约定 |
|---|---|
| **数据格式** | 严格遵循外部投研日历项目 PRD §2.6 的 JSON Schema |
| **文件路径** | `data/daily-5-things.json`（固定路径） |
| **推送方式（阶段一）** | 投研日历手动导入 JSON 文件 |
| **推送方式（阶段二）** | 投研日历 GitHub Actions 直接 `curl` 拉取 BigBeautyNews 仓库的 raw JSON URL |
| **文件名** | 固定文件名 `daily-5-things.json`，每次运行覆盖最新内容 |
| **历史归档** | `data/archive/YYYY-MM-DD.json` 保留每天历史，不覆盖 |

---

## 8. v0.6 验收 Checklist

| # | 验收项 | 通过标准 |
|---|---|---|
| 1 | 不破坏已实现基线 | 现有每日推送、对外 JSON、网页归档、7:45 / 8:15 调度兜底、推送幂等测试继续通过 |
| 2 | 来源分层 | 每条候选和归档新闻都有 `sourceTier`，取值统一为 `tier0` / `tier1` / `tier2` / `tier3` |
| 3 | AI 投研实体词典 | 关键词覆盖大模型、云厂商、芯片、数据中心、光通信、模型平台、产业事件；重要 AI Capex / 芯片 / 数据中心新闻不因标题没有 “AI” 被误杀 |
| 4 | URL 标准化 | `canonicalUrl` 移除常见 tracking 参数；同一 URL 的不同 UTM 版本不会重复入选 |
| 5 | 最小可用 `eventId` | 能基于 `eventType + entities + title fingerprint` 生成稳定事件 ID；实体为空时退化为 canonical URL hash |
| 6 | 跨日去重 | 最近 7 天内相同 `canonicalUrl` / `eventId` / 近似标题不得重复入选；GitHub repo URL 默认 14 天冷却 |
| 7 | 后续进展例外 | 同一事件再次入选时，必须在 `selectionReason` 或 `warnings` 标注“后续进展”及新信息点 |
| 8 | 规则预评分 | 每条内部候选和入选项都有 0–5 的 `sourceCredibilityScore` / `marketImpactScore` / `noveltyScore` / `timelinessScore` / `entityImportanceScore` / `confidenceScore` / `totalScore` |
| 9 | LLM 成本边界 | 规则预评分不额外调用 LLM；正常运行仍为排序 1 次 + 翻译 1 次，只有来源集中或格式错误时允许重试 / 重排 |
| 10 | 来源多样性 | 候选充足时先要求 LLM 重排；重排后仍集中则成功产出并记录 warning，不直接中断 |
| 11 | 状态文件 | 每次运行写入 `data/run-status.json`；追加或更新 `data/run-history.json`；失败时写入 `data/error-log/YYYY-MM-DD.json` |
| 12 | 状态语义 | `generated` / `pushed` / `committed` / `schemaValid` 各自独立；推送失败不得写入 `push-history.json` |
| 13 | Schema 校验 | 对外 5 字段 JSON 和内部归档 JSON 均有本地校验；schema 失败时不得推送 |
| 14 | 北京时间业务日期 | 用户可见日期、归档文件名、`push-history.json` 日期均使用 Asia/Shanghai；`exportedAt` 使用 UTC ISO |
| 15 | GitHub Trending fallback | 网页爬取失败时 fallback 到 GitHub Search API；fallback 结果必须标注来源和 warning |
| 16 | 文档同步 | README / CHANGELOG / Code Review Checklist 与 PRD v1.5 的验收口径一致 |

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v1.0 | 2026-07-01 | 初稿，基于与用户的完整需求讨论 |
| v1.1 | 2026-07-01 | 新增 Code Review Checklist（附录） |
| v1.2 | 2026-07-01 | 骨架校对修正：Server酱改为 Turbo、Schema 分层（对外 5 字段 vs 内部完整）、LLM 调用次数修正为 2 次、网页方案明确（项目根起 HTTP 服务）、Ars Technica RSS URL 修正、目录结构注释更新、Checklist 细化和迭代 |
| v1.3 | 2026-07-05 | 内容质量修正：最近 7 天跨日去重、48/72 小时时效窗口、来源多样性硬约束、归档溯源字段；同步记录 7:45 主触发与 8:15 兜底调度 |
| v1.4 | 2026-07-05 | 投研增强版：增加一手源优先级、规则预评分、事件级去重、AI 投研实体词典、运行状态监控、北京时间业务日期规则；来源多样性从硬失败改为强偏好 + warning |
| v1.5 | 2026-07-05 | PRD 加固：拆分已实现基线 / v0.6 本轮实施 / 后续增强，明确非目标、最小 eventId 规则、运行状态语义、LLM 成本边界和 v0.6 验收清单 |

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
| B1 | 正确抓取 5 个北美媒体 RSS 源：The Verge / TechCrunch / Ars Technica / MIT Tech Review / Wired，并标注为 Tier 2 | PRD §2.1 | |
| B2 | 使用 `feedparser` 解析 RSS，正确处理 `entries` 中的 `title`/`link`/`published`/`summary` | PRD §4.1 | |
| B3 | 并行抓取（`ThreadPoolExecutor` 或 `asyncio`），单源超时 ≤ 15s | PRD §2.2 | |
| B4 | 单一源失败不阻塞整体流程，记录错误日志后继续 | PRD §2.2 | |
| B5 | 每篇文章输出包含：`title`/`url`/`source`/`published`/`summary` 字段 | PRD §2.2 | |
| B6 | 每个源最多取 `MAX_CANDIDATES_PER_SOURCE`（20）篇 | `config.py` | |

### C. GitHub Trending 抓取

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| C1 | 正确抓取 GitHub Trending 当日数据；网页爬取失败时 fallback 到 GitHub Search API | PRD §2.1 | |
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
| E1 | 当日标题相似度去重：跨来源阈值 0.65、同来源阈值 0.95；同事件多源报道合并 | PRD §2.2 | |
| E2 | 合并时保留 `merged_sources` 字段，供 LLM 排序时权重上调 | PRD §2.3 | |
| E3 | AI 投研实体词典正确实现，覆盖大模型、云厂商、芯片、数据中心、光通信、模型平台和产业事件 | PRD §2.5 | |
| E4 | GitHub Trending 数据源的数据跳过关键词过滤器（已在抓取时筛选） | PRD §2.2 | |
| E5 | 最近 7 天已推送 URL 硬排除，近似相同标题按 0.85 阈值排除 | PRD §2.3 | |
| E6 | 默认使用 48 小时内文章；不足 5 条扩大到 72 小时，再不足才放宽时效 | PRD §2.3 | |
| E7 | 时效回退不得重新引入最近 7 天已推送内容 | PRD §2.3 | |
| E8 | 生成并使用 `eventId` 做事件级去重；同事件保留 `relatedUrls` / `mergedSources` / `primarySource` | PRD §2.4 | |
| E9 | GitHub repo URL 默认 14 天冷却，避免同一 repo 连续多日入选 | PRD §2.3 | |

### F. LLM 排序模块（核心）

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| F1 | 使用 OpenAI 兼容客户端（支持任意 `api_base` 切换模型） | PRD §4.1 | |
| F2 | Prompt 包含投研视角排序权重（P0-P5）和规则预评分字段，LLM 理解并遵循 | PRD §2.3 | |
| F3 | Prompt 要求 LLM 输出严格 JSON（不含代码块标记） | `ranker.py` | |
| F4 | LLM 返回 JSON 解析失败时有重试机制（至少 1 次） | `ranker.py` | |
| F5 | 正确将候选文章格式化为 Prompt 中的编号列表 | `ranker.py` | |
| F6 | `select_top5()` 正确根据 LLM 输出的 `source_article_index` 从候选池取出对应文章 | `ranker.py` | |
| F7 | LLM 调用异常有明确的错误处理和日志 | PRD §6 | |
| F8 | 候选池来源充足时，Top 5 强偏好覆盖至少 3 个来源且单一来源尽量最多 2 条；重排后仍集中则记录 warning 但不直接失败 | PRD §2.3 | |
| F9 | 官方一手源高分重大事件（`marketImpactScore >= 4.5` 且 `sourceTier = tier0`）不因来源多样性被剔除 | PRD §2.3 | |

### G. LLM 翻译模块

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| G1 | 翻译 Prompt 包含术语表（LLM → 大语言模型 等），LLM 遵守术语规范 | PRD §2.6 | |
| G2 | 输出要求：标题 ≤ 50 字 + 摘要目标 100–200 字（容错 50–500 字并记录 warning）+ 保留原文链接 | PRD §2.6 | |
| G3 | 保留关键英文专有名词（公司名、产品名、股票代码）不翻译 | PRD §2.6 | |
| G4 | 翻译结果为简体中文 | PRD §2.6 | |
| G5 | 翻译失败有重试机制 | PRD §6 | |

### H. Server酱 Turbo 推送

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| H1 | API 调用格式正确：`POST https://sctapi.ftqq.com/{sendkey}.send` | PRD §2.7-A | |
| H2 | `title` 包含日期标识（如 "🤖 AI 每日 5 件事 | 2026-07-01"） | PRD §2.7-A | |
| H3 | `desp` 为 Markdown 格式，5 条消息排版清晰可读 | PRD §2.7-A | |
| H4 | `sendkey` 未配置时记录明确错误并使流水线失败 | PRD §2.7-A | |
| H5 | API 返回 `code=0` 时确认为成功，非 0 时记录错误日志 | `serverchan.py` | |
| H6 | 推送失败时流水线返回失败，不写入成功推送状态，允许兜底任务重试 | `main.py` | |
| H7 | 推送成功后写入 `data/push-history.json`；同日重跑不重复推送，`--force-push` 可显式重发 | `main.py` | |

### I. JSON 输出

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| I1 | **对外 JSON**（`data/daily-5-things.json`）：Schema 严格遵循外部投研日历项目 PRD §2.6：`project`/`exportedAt`/`items[]`，每条仅含 5 字段（`date`/`title`/`summary`/`url`/`source`） | PRD §2.7-B, §3.1 | |
| I2 | **归档 JSON**（`data/archive/YYYY-MM-DD.json`）：保留完整内部字段（含 `eventId`/`sourceTier`/`*Score`/`entities`/`rank`/`tags`/`published`/`mergedSources`/`selectionReason`/`dailyTheme`） | PRD §3.2 | |
| I3 | **网页 JSON**（`web/data.json`）：保留完整内部字段，供 `app.js` 渲染 | PRD §3.2, §3.3 | |
| I4 | 归档文件按日期命名，不覆盖历史 | PRD §7 | |
| I5 | 维护 `data/history.json` 索引（dates 数组去重） | PRD §7 | |
| I6 | 维护 `data/run-status.json`、`data/run-history.json`；失败时写入 `data/error-log/YYYY-MM-DD.json` | PRD §3.3 | |

### J. 主入口 & 编排

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| J1 | `main.py` 按正确顺序编排流水线：并行抓取 → 当日去重 → 跨日去重 → AI 过滤 → 时效过滤 → 排序 → 翻译 → 输出 | PRD §2.2 | |
| J2 | `--dry-run` 模式下不推送微信、不写文件，但仍执行抓取+排序+翻译 | `main.py` | |
| J3 | 每步有清晰的日志输出和耗时信息 | 工程规范 | |
| J4 | 候选池不足 5 篇时明确报错退出（exit code 1） | `main.py` | |
| J5 | LLM API Key 未配置时明确报错退出（exit code 1），而非静默跳过 | `main.py` | |
| J6 | 整体超时控制合理（GitHub Actions timeout-minutes: 15） | PRD §2.8 | |
| J7 | `--force-push` 只绕过推送幂等保护，不影响其他流水线步骤 | `main.py` | |
| J8 | 用户可见日期、归档日期、推送幂等日期均使用 `Asia/Shanghai` 业务日期；`exportedAt` 使用 UTC ISO | PRD §2.8 | |
| J9 | 运行状态区分 `generated` / `pushed` / `committed` / `schemaValid`，避免把数据生成成功误判为推送成功 | PRD §3.2 | |

### K. GitHub Actions 定时工作流

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| K1 | Workflow 文件位于 `.github/workflows/daily.yml`，`permissions: contents: write` | PRD §4.3 | |
| K2 | 主 cron `45 23 * * *` = 北京时间 7:45；兜底 cron 覆盖 8:15、8:35、8:55、9:20，且当天成功后跳过兜底 | PRD §2.8 | |
| K3 | 支持 `workflow_dispatch` 手动触发，也支持手机端 issue / comment 触发 `/push` 或 `/push-force` | PRD §2.8 | |
| K4 | 通过 GitHub Secrets 注入 `SERVERCHAN_SENDKEY`、`LLM_API_KEY`、`LLM_API_BASE`、`LLM_MODEL` | PRD §4.1 | |
| K5 | 生成可用数据后自动 `git commit` + `git push` 数据文件和状态文件；若推送失败，状态仍需记录并让工作流最终失败 | PRD §3.2 | |
| K6 | Python 版本指定为 3.12 | PRD §4.1 | |
| K7 | `timeout-minutes` 设为 15 | `.github/workflows/daily.yml` | |

### L. 网页浏览

| # | 检查项 | 对应用户需求 | 结果 |
|---|---|---|---|
| L1 | `web/index.html` 为纯静态页面，需从项目根目录起 HTTP 服务（`python -m http.server 8080`），不支持 `file://` 直接打开 | PRD §2.7-C | |
| L2 | 页面加载当天数据：`fetch('data.json')`（从 `web/` 目录相对路径） | PRD §2.7-C | |
| L3 | 历史数据加载：`fetch('../data/archive/YYYY-MM-DD.json')`（从 `web/` 目录相对路径） | PRD §2.7-C | |
| L4 | 历史日期无数据时显示空状态提示，不应 fallback 显示当天数据 | PRD §2.7-C | |
| L5 | 支持通过日期控件或翻页按钮切换到历史日期 | PRD §2.7-C | |
| L6 | 每条消息显示：排序数字、中文标题、来源标签、标签、摘要、原文链接 | PRD §2.7-C | |
| L7 | 响应式布局，手机和桌面均可正常浏览 | PRD §2.7-C | |

---

### Review 记录

| 日期 | 版本 | Review 人 | 通过率 | 主要问题 | Codex 修复状态 |
|---|---|---|---|---|---|
| — | — | — | — | — | — |
