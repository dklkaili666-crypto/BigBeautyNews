# Changelog

## [Unreleased]

### v0.6.6 外部准时调度
- 按 PRD OPS-01 将正式定时源从 GitHub `schedule` 改为 cron-job.org，固定 `Asia/Shanghai` 7:45 主触发和 8:15 幂等兜底
- 外部触发通过 `workflow_dispatch` 携带 `trigger_source` / `schedule_slot`，运行状态可区分主触发、兜底和人工触发
- 增加最小权限配置器、两条任务幂等创建与回读校验，以及自动清理的一次性外部触发冒烟测试

### v0.6.5 调度收敛
- 按运行策略收敛自动调度：只保留北京时间 7:45 主触发和 8:15 兜底触发
- 9:10 临时验证不写入长期 cron，改用一次性强制触发，避免后续每天重复推送

### v0.6.4 推送链路可观测性修复
- 增加 `workflow_dispatch push_test=true` 的 Server酱独立冒烟测试模式
- `run-status.json` 记录 trigger、workflowRunId、digestHash、sendkeyPresent、pushAttempted、Server酱 HTTP/code/message/响应摘要等诊断字段
- GitHub Actions checkout 后先拉取最新 `master`，避免排队任务基于旧 `push-history.json` 重复推送

### v0.6.3 推送触发可靠性修复
- 增加 8:35、8:55、9:20 北京时间冗余触发点，降低 GitHub Actions schedule 漏触发导致整天不推送的概率
- 增加手机端手动触发方式：新建 `manual-push` issue 或评论 `/push` / `/push-force`
- 更新 PRD，明确自动推送不依赖本地电脑开机；GitHub 云端漏调度时使用多时点冗余和手机手动兜底

### v0.6.2 P2 质量修复
- 扩展高频 AI 实体词典，覆盖 Midjourney、Strix、Mistral AI、xAI、CoreWeave、阿里/百度/腾讯/华为等实体
- 修正 `committed` 状态语义：主流程默认写入 `false`，GitHub Actions 在提交数据前标记为 `true` 并随数据一起提交

### v0.6.1 P1 质量修复
- 收紧泛政策/监管/禁令关键词：仅有 `policy`、`ban`、`regulation` 或正文中顺带出现一次泛化 `AI` 时，不再进入 AI 候选池
- Top 5 排序新增社区源上限：`GitHub Trending` / `Hacker News` 默认最多 1 条，超限会触发一次重排；重排后仍超限则记录 warning

### v0.6 投研增强
- 增加来源分层、URL 标准化、最小可用 `eventId` 和 GitHub repo 冷却
- 增加 AI 投研实体词典，覆盖 Capex、芯片、数据中心、光通信等非字面 AI 新闻
- 增加确定性规则预评分字段，LLM 排序前可解释
- 内部归档保留 `sourceTier`、`canonicalUrl`、`eventId`、实体、评分和 warning
- 增加对外 JSON / 内部归档 schema 校验
- 增加 `run-status.json`、`run-history.json` 和失败 `error-log`
- GitHub Trending 页面失败时 fallback 到 GitHub Search API

### v0.5 优化
- 将定时任务调整为北京时间 7:45，避开 GitHub Actions 整点调度高峰
- 增加按日期持久化的微信推送幂等保护和 `--force-push`
- LLM Top 5 增加来源多样性软约束与一次重排
- 基于真实跨源标题样本将去重阈值从 0.8 调整为 0.65
- 同来源使用 0.95 阈值，避免相似但不同事件被误合并
- RSS 标题解码 HTML 实体，提升去重准确率
