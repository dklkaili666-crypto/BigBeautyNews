# BigBeautyNews v2.0 PRD：DeepSeek Flash 迁移与结构化输出修复

- 状态：Approved
- 批准人：项目所有者
- 批准证据：2026-08-23 明确回复“批准 PRD v2.0”
- 基线：已批准并交付的 PRD v1.9
- 提出日期：2026-08-23
- 目标用户：项目所有者
- 决策依据：2026-08-23 确认保留现有 API Base/Key、改用 Flash、关闭思考模式、失败后不回退 Pro

## 目标与成功标准

将生产 LLM 从 `deepseek-v4-pro` 切换为 `deepseek-v4-flash`，并让 AI 与政经两套排序/翻译调用显式使用非思考 JSON 输出，恢复每天 07:45 主任务和 08:15 兜底任务的稳定生成与微信推送。

成功标准：

- 生产配置使用 `deepseek-v4-flash`，现有 `LLM_API_BASE` 与 `LLM_API_KEY` 保持不变。
- 一次真实、非强制的手动运行完成 AI 5 条与全球政经 5 条生成，并成功发送一条 Server酱消息。
- 四处 LLM 调用都显式关闭思考模式并请求 JSON 对象，不再因只返回 `reasoning_content` 或空 `content` 而直接出现无上下文的 JSON 解析错误。
- 主任务连续两次 LLM 尝试失败时不推送、不写入成功推送日期；08:15 兜底仍可按现有机制重新尝试。
- 既有调度、新闻源、筛选规则、双榜单内容、对外 JSON、历史归档和幂等行为保持不变。

## 用户与场景

### 场景 S-001：每日自动推送

项目所有者无需开启本地电脑。07:45 主任务使用 Flash 完成两套排序和翻译，生成 AI 5 条与全球政经 5 条，并通过 Server酱发送一条微信消息。

### 场景 S-002：主任务失败后的兜底

如果 07:45 主任务的 LLM 调用在两次尝试后仍失败，系统不得推送不完整内容或标记当天已推送；08:15 兜底任务按现有幂等机制重新运行 Flash 流水线。

### 场景 S-003：故障诊断

如果 Flash 返回空内容或非法 JSON，运行日志应能区分空 `content`、非法 JSON和其他调用异常，同时不记录模型原文、思考内容或凭证。

## 范围

### 范围内

- 将 GitHub Actions Secret `LLM_MODEL` 从 `deepseek-v4-pro` 更新为 `deepseek-v4-flash`。
- 在 AI 排序、政经排序、AI 翻译和政经翻译四处 Chat Completions 调用中：
  - 显式设置 `extra_body={"thinking": {"type": "disabled"}}`；
  - 显式设置 `response_format={"type": "json_object"}`；
  - 保持现有提示词包含 JSON 输出要求和现有 `max_tokens=4096`。
- 为模型返回空内容、非法 JSON和正常 JSON补充针对性测试与不泄密诊断。
- 更新生产模型 Secret 后执行一次真实端到端验收。

### 范围外

- 不更换 `LLM_API_BASE` 或 `LLM_API_KEY`，不新增 API 供应商或凭证。
- 不自动回退到 Pro、其他模型或代码规则排序。
- 不修改新闻源、筛选规则、去重逻辑、排序标准、翻译提示词、摘要长度规则或榜单数量。
- 不修改 07:45/08:15 外部调度、Server酱渠道、推送幂等、网页、归档和投研日历 JSON Schema。
- 不合并尚未批准的 CR-001 Server酱 `readkey` 脱敏。
- 不通过简单扩大 `max_tokens` 规避思考模式兼容问题。

## 功能需求

### FR-018：生产模型切换为 Flash

生产环境必须将 `LLM_MODEL` 配置为 `deepseek-v4-flash`，并继续使用当前 `LLM_API_BASE` 与 `LLM_API_KEY`。

验收标准：

- GitHub Actions 中只有 `LLM_MODEL` Secret 在本次配置迁移中被更新。
- 真实运行状态或安全日志显示实际模型标识为 `deepseek-v4-flash`。
- 日志和仓库均不包含 API Key 或 Secret 原值。

### FR-019：四处调用使用非思考 JSON 输出

AI 排序、政经排序、AI 翻译和政经翻译必须显式关闭 DeepSeek 思考模式，并请求 JSON 对象响应。

验收标准：

- 四处调用均传入 `extra_body={"thinking": {"type": "disabled"}}`。
- 四处调用均传入 `response_format={"type": "json_object"}`。
- 单元测试逐一验证四处调用参数，而不是只覆盖其中一个模块。
- 合法 JSON 响应继续通过现有数量、索引、标题、摘要和质量校验。

### FR-020：空内容与非法 JSON处理

模型返回空 `content`、空白 `content` 或非法 JSON时，系统必须按现有上限最多尝试两次；两次均失败后终止本次流水线。

验收标准：

- 空或空白 `content` 被识别为明确的“LLM 返回空内容”错误，不直接暴露底层 `json.loads` 的模糊错误。
- 非空但非法 JSON 被识别为 JSON 格式错误。
- 失败日志只记录模型标识、尝试序号、异常类别，以及响应可用时的 `finish_reason`、`content` 长度、`reasoning_content` 长度和令牌用量；不得记录响应原文或思考内容。
- 两次失败后，程序退出码为 1，不执行翻译后续步骤、持久化成功结果或 Server酱推送。

### FR-021：保留主任务与兜底语义

LLM 失败不得被记录为成功推送；08:15 兜底应继续依据 `push-history.json` 判断是否重试。

验收标准：

- 07:45 失败时不新增当天 `push-history.json` 日期。
- 当天未成功推送时，08:15 兜底不会被幂等检查错误跳过。
- 任一运行成功推送后，同日后续非强制外部运行仍按现有逻辑跳过，避免重复微信消息。

### FR-022：真实端到端恢复验收

配置和代码完成后，必须使用现有工作流执行一次非强制手动生产运行。

验收标准：

- 工作流在现有 15 分钟超时内成功完成。
- 产出 AI 5 条与全球政经 5 条，既有内部/外部 Schema 校验通过。
- Server酱只发送一次且返回 HTTP 200、业务 `code=0`。
- 数据提交成功，运行状态记录 `generated=true`、`pushed=true`、`committed=true`、`schemaValid=true`。

## 非功能需求

### NFR-013：凭证与模型响应安全

API Base/Key 和 Server酱 SendKey 必须继续仅由 GitHub Secrets 注入；新增诊断不得泄露凭证、原始模型回答或 `reasoning_content`。

验收标准：

- 仓库差异中不存在 Secret 值。
- 自动化日志继续对 Secrets 掩码。
- 新增测试验证诊断信息只包含长度、状态和用量等元数据。

### NFR-014：既有行为兼容

除模型选择、思考模式、JSON 输出请求和错误诊断外，现有产品行为不得改变。

验收标准：

- 现有测试全部通过。
- 07:45/08:15 调度配置、新闻源、筛选/去重规则、提示词文本、输出 Schema 和 Server酱格式没有无需求关联的改动。
- 代码审查不存在未关联本 PRD 需求的实现改动或重构。

### NFR-015：可验证交付

本次交付必须通过单元、静态和真实场景验证。

验收标准：

- `pytest`、Ruff、Mypy、`compileall` 和 `git diff --check` 全部通过。
- 验收记录逐条覆盖 FR-018 至 FR-022、NFR-013 至 NFR-015，并附可复现证据。

## 假设与依赖

- 当前 API 服务继续支持 OpenAI Chat Completions 兼容接口以及模型标识 `deepseek-v4-flash`。
- 当前 API 服务支持 DeepSeek 的 `thinking` 开关和 `json_object` 响应格式；如果真实预检显示不支持，必须暂停并提交变更请求，不得静默删除参数。
- 当前 `LLM_API_BASE`、`LLM_API_KEY` 和 `SERVERCHAN_SENDKEY` 仍有效且余额/权限充足。
- 生产验收当天若尚未成功推送，非强制手动运行会发送一条真实微信消息；若当天已经成功推送，应使用下一业务日或经用户另行批准的强制推送方式验收。

## 风险

- DeepSeek 官方说明 JSON 输出仍可能偶发空 `content`；本版本依靠明确错误、两次尝试和08:15兜底降低影响，不承诺上游服务绝不失败。
- Flash 与 Pro 的排序和摘要质量可能不同；本版本不调整提示词或质量门槛，实际内容质量需在恢复运行后持续观察。
- 如果当前 API Base 是兼容网关而非官方直连，其对 `thinking` 或 `response_format` 的支持可能与官方接口不同；真实预检失败时需要新的产品决策。

## 未决决策

无。已确认：

- D1：保留当前 API Base/Key，只切换模型。
- D2：Flash 显式关闭思考模式并要求 JSON 对象。
- D3：两次失败后停止，不自动回退 Pro；08:15 继续使用 Flash 兜底。

## PRD 完整性检查

- S-001 由 FR-018、FR-019、FR-022 覆盖。
- S-002 由 FR-020、FR-021 覆盖。
- S-003 由 FR-020、NFR-013 覆盖。
- 每项功能和非功能需求均有可观察验收标准。
- 范围与非目标无冲突；无隐藏未决产品决策。

## 修订记录

| 版本 | 日期 | 状态 | 摘要 |
|---|---|---|---|
| v2.0-draft | 2026-08-23 | Draft | 切换 DeepSeek Flash，显式关闭思考模式并使用 JSON 输出；保留两次尝试和 08:15 兜底，不回退 Pro。 |
| v2.0 | 2026-08-23 | Approved | 项目所有者批准全部需求、范围和验收标准。 |
