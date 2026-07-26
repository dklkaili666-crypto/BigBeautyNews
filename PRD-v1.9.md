# BigBeautyNews v1.9 修复 PRD

- 状态：Approved
- 批准人：项目所有者
- 批准证据：2026-07-26 明确确认 PRD，并选择 `deepseek-v4-pro`
- 基线：PRD v1.8
- 变更原因：2026-07-25 起，LLM 服务拒绝现有 `LLM_MODEL`，导致 07:45 主任务和 08:15 兜底均在 AI 排序阶段以 HTTP 400 失败。

## 目标与成功标准

恢复自动日报的 LLM 排序、翻译和 Server酱推送能力，同时保持既有 07:45 / 08:15 外部调度、5+5 内容、幂等、手机手动入口和新闻筛选逻辑不变。

成功标准：将 GitHub Actions 的 `LLM_MODEL` Secret 更新为所选、且服务商明确支持的模型后，当前业务日的一次非强制手动 workflow dispatch 完成 5+5 生成并成功发送一条 Server酱消息；运行状态不再出现“unsupported API model names”错误。

## 用户与场景

- 用户：项目所有者。
- 场景：服务商淘汰旧模型名后，自动日报仍应在无需本地电脑开机的情况下恢复。

## 范围

### 范围内

- 在 GitHub Actions Secret 中仅更新 `LLM_MODEL` 的值。
- 手动触发一次既有日报 workflow 验证真实 LLM 调用与 Server酱推送。
- 记录运行 URL、模型兼容性结果和验收证据。

### 范围外

- 不修改新闻筛选、排序提示词、来源、LLM 调用次数、Server酱渠道、cron-job.org 任务或 GitHub workflow 代码。
- 不新增供应商、密钥、模型回退逻辑或付费服务。

## 功能需求

### FR-017：LLM 模型兼容性恢复

将 `LLM_MODEL` 配置为用户批准、且服务商当前支持的 `deepseek-v4-pro`。

验收：在更新 Secret 后，非强制手动 workflow dispatch 的 AI 排序和翻译不再返回模型名 `invalid_request_error`；当天尚无成功推送时，流水线完成 5+5 并只发送一次 Server酱 POST。

## 非功能需求

### NFR-012：配置变更安全与范围控制

Secret 只能在 GitHub Actions 的 Secret 存储中更新，不得进入仓库、日志或验收文档；代码、新闻筛选逻辑和定时任务配置不得改动。

验收：`git diff` 不含源代码、workflow 或新闻规则改动；GitHub 日志继续掩码 Secret；验收记录只引用模型标识和 workflow URL，不包含凭证。

## 假设、依赖与风险

- 依赖：当前 `LLM_API_BASE` / `LLM_API_KEY` 仍有效；服务商错误消息列出的两个模型可用。
- 风险：`flash` 与 `pro` 的质量、延迟和成本不同；本次不增加自动回退，以避免扩大范围。
- 可逆性：如所选模型仍被服务商拒绝，可仅替换同一 Secret 为另一个已批准模型名，无需代码改动。

## 未决决策

| 决策 | 选项 | 影响 |
|---|---|---|
| D1：目标模型 | `deepseek-v4-pro`（已批准） | 侧重输出质量；作为本次唯一模型配置变更。 |

## 修订记录

| 版本 | 日期 | 摘要 |
|---|---|---|
| v1.9-draft | 2026-07-26 | 针对服务商模型名兼容性变更的最小生产配置修复。 |
| v1.9 | 2026-07-26 | 用户批准使用 `deepseek-v4-pro`。 |
