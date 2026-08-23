# BigBeautyNews 产品需求文档

> 当前批准基线：v2.1 | 状态：Delivered | 批准日期：2026-08-23 | 生产验收：2026-08-23

## 1. 目标、用户与成功标准

BigBeautyNews 是个人投研新闻工具。它每天生成 AI Top 5 与全球地缘政经 Top 5（中国、美国优先），翻译为简体中文，并在一条 Server酱消息中推送。项目保留本地网页和内部历史数据；投研日历继续从固定公开 raw URL 拉取仅含 AI Top 5 的五字段 JSON。

- 用户：项目所有者，个人投研使用。
- 自动日报：北京时间 7:45 主触发，8:15 幂等兜底。
- 手动恢复：GitHub Actions 或手机 issue/comment 触发，可选择强制重发。
- 成功标准：每日完整 5+5；四个 LLM 阶段各最多尝试两次，成功日报只执行 1 次 Server酱 POST；不用付费新闻 API；既有调度、幂等、网页和投研日历契约兼容。

## 2. 当前流程与范围

```text
免费 RSS / GitHub Trending / Hacker News
  → AI 与政经独立候选池
  → 本地过滤、去重、时效与主板块分类
  → 两次 LLM 排序 + 两次 LLM 翻译
  → 完整性与 schema 校验
  → 内部 5+5 归档、本地网页、外部 AI 五字段 JSON
  → 一次 Server酱双板块推送
```

范围内：现有新闻源、规则、双榜单、LLM 排序翻译、数据输出、Server酱、外部调度、CI 和文档。
范围外：新增新闻源或渠道、修改 Touyanrili、改变仓库 Public 状态、关闭或迁移 GitHub Pages、为单阶段增加第三次 LLM 尝试、抓取文章全文。

## 3. 功能需求

### FR-001：免费政经来源池

使用已批准的 8 个公开免费 RSS，不需要新闻 API Key。
验收：配置包含 SCMP、NPR、BBC、Guardian 的批准来源；抓取器按源隔离错误；无付费新闻 API 配置。

### FR-002：独立政经预过滤

政经候选池与 AI 候选池分离，候选必须同时包含地域主体和政经事件信号。
验收：中美及全球重要事件正例保留；娱乐、生活和泛评论负例排除；预过滤不调用 LLM。

### FR-003：政经 Top 5 与地域优先

排序优先重要性、市场影响、时效、来源质量及中美相关性，地域配额为质量优先的软约束。
验收：结果严格为 5 条唯一事件；不满足质量约束时最多重排一次并记录 warning。

### FR-004：榜单内及跨榜单去重

使用规范 URL、eventId 和标题相似度去重；交叉事件只进入主要影响板块并确定性补位。
验收：同事件不跨榜重复；补位后仍为 5+5；历史去重在板块移动后重新应用。

### FR-005：复用现有 LLM 服务

政经排序和翻译复用现有 OpenAI 兼容配置。
验收：不新增供应商配置；政经排序和翻译各调用一次；输出为符合 schema 的简体中文内容。

### FR-006：单次双板块微信推送

一条 Server酱消息先展示 AI Top 5，再展示政经 Top 5。
验收：两个标题、两组 1–5、10 个原文链接；正常运行只发送一次 POST；保留大小限制与结果诊断。

### FR-007：双榜单完整性门槛

任一榜单不足 5 条时不得持久化或推送残缺日报。
验收：失败状态指出对应数量；不写成功推送标记，兜底仍可重试。

### FR-008：内部数据与历史归档

内部数据保存 AI/政经各 5 条、各自主题及投研增强字段，并兼容旧 AI-only 归档。
验收：内部 schema 严格校验 5+5；历史读取可处理缺少政经字段的旧文件。

### FR-009：投研日历契约不变

`data/daily-5-things.json` 继续只输出 AI 5 条，每条仅 `date/title/summary/url/source`。
验收：固定路径、项目标识、条数和字段集合不变；政经字段不得进入该文件。

### FR-010：本地网页双榜单

本地网页按日期展示 AI 在上、政经在下；旧归档只展示 AI。
验收：新数据显示 10 张卡片和两个板块；日期导航及安全链接继续工作；旧数据无错误空板块。

### FR-011：调度与手动触发不变

保留 7:45 主触发、8:15 幂等兜底、Actions 手动触发及手机 issue/comment 触发。
验收：参数验证、当天成功跳过、`force_push`、`push_test` 和状态记录继续通过测试；自动调度连续 3 个自然日于 7:45±5 分钟内完成推送，8:15 兜底在主任务成功后幂等跳过。显式 `force_push` 是用户主动重发，不计入自动调度单日一次限制。

### FR-012：Pages 发布边界

日报 workflow 不包含 Pages 部署 action 或 Pages/id-token 权限。GitHub Pages 仓库设置当前仍为公开 built 状态，用户已接受并要求 v1.8 不处理。
验收：workflow 无 Pages 部署步骤或权限；不修改 Pages 设置；公开例外在 README 和验收记录中可见。

### FR-013：双榜单运行状态

运行状态分别记录 AI/政经候选数、入选数和板块相关失败，同时保留原有状态字段。
验收：成功、失败、部分成功和外部兜底跳过场景均有可读状态证据。

### FR-014：政经词形与美国缩写

规则支持 `sanction(s)`、`tariff(s)`、`election(s)`、`missile(s)`、`regulation(s)`，识别 `US`/`U.S.`，但不把代词 `us` 当作美国。
验收：批准的三个正例保留、一个小写 `us` 负例排除；既有分类测试通过；不新增 NLP 依赖。

### FR-015：无副作用 CI 与生产前门槛

push/PR CI 使用 Python 3.12 执行 compileall、Pytest、Ruff、Mypy；日报在正式流水线前执行快速测试。
验收：CI 权限只读且无生产 Secrets、实时抓取、LLM、Server酱或写库命令；日报测试失败时不进入 `python src/main.py`。

### FR-016：GitHub Actions 运行时升级

CI 与日报统一使用批准的 `actions/checkout@v7`、`actions/setup-python@v6`，不引入 Pages actions。
验收：静态测试拒绝旧版本；远程 CI 至少成功运行一次。

### FR-017：LLM 模型兼容性基线

生产环境必须使用服务商当前支持的模型标识；不支持的模型应明确失败，不能推送或写成功日期。当前具体模型与请求契约由 FR-018～FR-023 定义。
验收：不存在模型名 `invalid_request_error`；失败运行不持久化成功结果或推送。

### FR-018：生产模型使用 DeepSeek Flash

GitHub Actions 的 `LLM_MODEL` 使用 `deepseek-v4-flash`，现有 API Base/Key 保持不变。
验收：安全运行状态显示 Flash；Secret 原值不进入仓库或日志。

### FR-019：四处非思考 JSON 输出

AI/政经排序与翻译四处调用均显式关闭思考模式并请求 JSON 对象。
验收：四处参数均有单元测试；真实请求返回 JSON 且 `reasoning_length=0`。

### FR-020：可诊断的两次尝试

空内容、非法 JSON和翻译长度违规均使用安全元数据诊断；单阶段最多尝试两次，仍失败则终止流水线。
验收：错误类别明确，日志不含响应原文或思考内容，失败时不持久化或推送。

### FR-021：主任务与兜底语义

LLM 失败不得写成功推送日期；08:15 兜底继续依据 `push-history.json` 决定重试或幂等跳过。
验收：失败后兜底可运行；成功后同日非强制外部任务跳过。

### FR-022：Flash 真实端到端运行

一次现有非强制生产 workflow 必须在 15 分钟内生成 AI 5 条与政经 5 条，完成 Schema 校验、单次 Server酱推送和数据提交。
验收：运行状态 `generated/pushed/committed/schemaValid` 全为 true，Server酱 HTTP 200、业务 code 0。

### FR-023：翻译长度纠偏

AI 或政经翻译首次长度违规时，第二次请求只追加 rank、字段、实际长度、允许范围和不含模型原文的字段定向纠偏，重新生成完整 5 条 JSON。
验收：第二次请求不含首轮标题、摘要、原始响应或思考内容；合格时保留原文章元数据；仍不合格时安全失败。

## 4. 非功能需求

### NFR-001：新闻数据零费用

新闻抓取只使用免费公开来源；验收：无付费新闻 API 或新闻 API Key。

### NFR-002：向后兼容

保留 CLI、环境变量、外部 JSON、调度、幂等和旧网页数据兼容；验收：全量回归通过。

### NFR-003：精准改动

改动必须绑定批准需求，不做邻近重构；验收：无孤儿任务或无需求代码。

### NFR-004：可靠性

来源错误隔离、榜单完整性严格、失败可重试；验收：失败与重试测试通过，不静默降级成功。

### NFR-005：性能与调用边界

并行抓取，四个 LLM 阶段各最多尝试两次，workflow 最长 15 分钟；验收：尝试上限与 timeout 测试通过。

### NFR-006：内容使用边界

仅处理 RSS 提供的标题、摘要、来源和链接，不抓取文章全文；验收：无全文抓取器。

### NFR-007：安全与隐私透明

Secrets 只来自环境变量；仓库、raw JSON 和 Pages 公开例外明确；验收：无凭证入库，权限测试与文档一致。

### NFR-008：依赖可复现

直接依赖保持可读，生产与开发工具使用同一精确约束文件。
验收：解析依赖版本固定；干净环境可安装、导入并运行全量测试；本地与 Actions 均使用 `constraints.txt`。

### NFR-009：PRD 表达当前状态

根 PRD 只描述当前 v2.1，历史长文独立归档。
验收：无过期“下一步”或 Pages 已关闭表述；完整历史可读；每项当前需求有验收标准。

### NFR-010：小步拆分主流水线

`run_pipeline()` 保留顶层编排，抓取、候选准备、排序、翻译、持久化和推送为单一职责函数。
验收：不引入框架、类或无调用者抽象；公开行为不变；阶段边界有测试。

### NFR-011：行为与成本回归保护

AI 5 + 政经 5、单次 POST、调度、幂等、外部 JSON 和四个 LLM 阶段保持不变；单阶段不得超过两次尝试。
验收：compileall、全量 Pytest、Ruff、Mypy、diff check 和远程 CI 通过；不修改 Pages 设置或 Touyanrili。

### NFR-012：模型配置安全与范围控制

LLM 模型、API Base/Key 和 Server酱 SendKey 继续通过 GitHub Secrets 注入；模型迁移不得修改新闻筛选、workflow、cron-job.org 或无关 Secret。
验收：日志和验收记录不包含 LLM API Key、Server酱 SendKey 或模型 Secret 原值；配置变更有可审计元数据。

### NFR-013：凭证与模型响应安全

诊断与纠偏不得泄露 Secret、原始模型回答或 `reasoning_content`。
验收：测试用唯一敏感标记证明日志和第二次请求均不含模型文本；Actions 继续掩码 Secrets。

### NFR-014：范围兼容

除 Flash 请求契约和翻译长度纠偏外，既有产品行为保持不变。
验收：全量测试通过；基础提示词、代码阈值、调度、新闻源、筛选/去重、Schema、Server酱格式和回退策略无孤儿改动。

### NFR-015：可验证交付

模型迁移必须通过单元、静态和真实场景验证，并逐项追踪批准需求。
验收：Pytest、Ruff、Mypy、`compileall`、diff check 和非强制生产 workflow 均通过；追踪表覆盖 FR-018～FR-023、NFR-013～NFR-015。

## 5. 依赖、风险与例外

- 依赖：公开 RSS、GitHub Actions、cron-job.org、支持 `deepseek-v4-flash` 非思考 JSON 请求的现有 LLM API、Server酱、公开 GitHub raw URL。
- 风险：免费 RSS 可用性变化；依赖锁需兼容 Python 3.12；轻量词典仍可能漏掉未批准的新词形。
- 对策：逐源隔离错误、严格完整性门槛、CI 与生产前测试、需求驱动扩词。
- 已知例外：GitHub Pages 当前公开且 built；用户明确选择 v1.8 不处理。它不影响投研日历 raw JSON，但构成额外公开入口。
- 未决产品决策：[CR-001](CHANGE_REQUEST-v1.9-001.md) 提议脱敏 Server酱响应中的 `readkey`；该既有字段的权限未在官方公开文档中说明，等待用户决定是否纳入下一轮范围。

## 6. 文档与版本记录

- [完整 v1.0–v1.8 清理前历史](docs/archive/PRD-v1.0-v1.8-full.md)
- [v1.7 实施计划](docs/archive/IMPLEMENTATION_PLAN-v1.7.md)与[验收记录](docs/archive/TRACEABILITY-v1.7.md)
- [v1.8 实施计划](IMPLEMENTATION_PLAN-v1.8.md)与[验收记录](TRACEABILITY-v1.8.md)
- [v1.9 修复 PRD](PRD-v1.9.md)、[实施计划](IMPLEMENTATION_PLAN-v1.9.md)与[验收记录](TRACEABILITY-v1.9.md)
- [v1.9 CR-001：Server酱响应 readkey 脱敏](CHANGE_REQUEST-v1.9-001.md)
- [v2.0 Flash 迁移 PRD](PRD-v2.0.md)与[实施计划](IMPLEMENTATION_PLAN-v2.0.md)
- [v2.1 长度纠偏 PRD](PRD-v2.1.md)、[变更请求](CHANGE_REQUEST-v2.0-001.md)、[实施计划](IMPLEMENTATION_PLAN-v2.1.md)与[验收记录](TRACEABILITY-v2.1.md)
- [OPS-01 外部准时调度最终验收](docs/archive/TRACEABILITY-OPS-01.md)

| 版本 | 日期 | 摘要 |
|---|---|---|
| v1.0–v1.6 | 2026-07-01～2026-07-10 | AI 日报、投研增强、状态与外部准时调度 |
| v1.7 | 2026-07-13 | 免费 RSS 政经 Top 5、单消息双榜单、内部网页与归档兼容 |
| v1.8 | 2026-07-13 | 词形修复、CI/生产门槛、Actions 升级、依赖锁、PRD 整理、流水线拆分 |
| v1.9 | 2026-07-26 | LLM 服务商模型名兼容性修复，采用 `deepseek-v4-pro`，不修改新闻筛选逻辑。 |
| v2.0 | 2026-08-23 | 迁移 `deepseek-v4-flash`，四处显式使用非思考 JSON 输出并增加安全响应诊断。 |
| v2.1 | 2026-08-23 | 增加翻译长度纠偏重试；真实 5+5、单次微信推送与数据提交通过。 |
