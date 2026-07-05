# Changelog

## [Unreleased]

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
