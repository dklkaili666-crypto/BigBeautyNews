# OPS-01 外部准时调度最终验收

- PRD 基线：v1.6 OPS-01，当前归并于 v1.8 FR-011
- 验收区间：2026-07-11～2026-07-13
- 时区：`Asia/Shanghai`
- 最终状态：通过

## 三日运行证据

下表时间均为北京时间。`createdAt` 来自 GitHub Actions，`pushAttemptedAt` 来自仓库运行状态；Server酱成功要求 HTTP 200 且响应 `code=0`。

| 日期 | 计划任务 | GitHub createdAt | pushAttemptedAt | Server酱 | Workflow | 结果 |
|---|---:|---:|---:|---|---|---|
| 2026-07-11 | 07:45 primary | 07:45:17 | 07:46:01 | HTTP 200 / code 0 / pushId 45137579 | [29131086121](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/29131086121) | 准时推送 |
| 2026-07-11 | 08:15 fallback | 08:15:18 | — | 未调用，`already_pushed` | [29132217911](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/29132217911) | 幂等跳过 |
| 2026-07-12 | 07:45 primary | 07:45:19 | 07:45:56 | HTTP 200 / code 0 / pushId 45265070 | [29172621010](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/29172621010) | 准时推送 |
| 2026-07-12 | 08:15 fallback | 08:15:17 | — | 未调用，`already_pushed` | [29173423940](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/29173423940) | 幂等跳过 |
| 2026-07-13 | 07:45 primary | 07:45:16 | 07:45:51 | HTTP 200 / code 0 / pushId 45391597 | [29213965574](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/29213965574) | 准时推送 |
| 2026-07-13 | 08:15 fallback | 08:15:17 | — | 未调用，`already_pushed` | [29214965185](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/29214965185) | 幂等跳过 |

三天 primary 的 GitHub 创建时间分别偏离计划 17、19、16 秒，均在 7:45±5 分钟内。三天自动链路均只有 primary 发起一次 Server酱 POST，fallback 未重复推送。

2026-07-13 11:09 的 [workflow 29221045872](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/29221045872) 由仓库所有者以 `trigger_source=manual`、`force_push=true` 显式运行，并执行 `--force-push`。这是 PRD 保留的人工强制重发能力，不属于自动调度重复推送。

## 最终验收表

| 需求 | 验收标准 | 实现与证据 | 结果 |
|---|---|---|---|
| OPS-01-1 外部调度 | cron-job.org 使用 `Asia/Shanghai`，07:45 primary、08:15 fallback | 已部署 job 8059160 / 8059161；三日运行证据如上 | 通过 |
| OPS-01-2 执行边界 | GitHub Actions 只作为执行器，不用 GitHub `schedule` 作为正式定时源 | `daily.yml` 仅保留外部 `workflow_dispatch` 与人工入口；静态 workflow 测试通过 | 通过 |
| OPS-01-3 兜底幂等 | 外部请求携带来源与时段；已推送则跳过，主任务失败才补推 | 三天 fallback 均记录 `external_scheduler` / `fallback` / `already_pushed`，且未调用 Server酱 | 通过 |
| OPS-01-4 权限最小化 | 外部服务只持有单仓库 Actions 写权限；凭证不入库或日志 | 细粒度令牌完成真实调度；仓库与运行证据无令牌/API Key | 通过 |
| OPS-01-5 可观测性 | 区分主、兜底和人工触发，保留计划时间、运行时间和推送结果 | `run-history.json` 含 trigger、scheduleSlot、workflowRunId、pushAttemptedAt、HTTP/code/pushId；workflow URL 可追溯 | 通过 |
| 连续三日准时性 | 连续 3 天 07:45±5 分钟推送；失败最迟 08:15 补推 | 07:45:16～07:45:19 创建，07:45:51～07:46:01 完成推送 | 通过 |
| 自动推送单日幂等 | 正常自动链路同日最多一次推送 | 每日 primary 一次成功、fallback 一次跳过；显式 `force_push` 例外已单独标明 | 通过 |
| 手机手动恢复 | 保留 `/push`、`/push-force` 和 Actions 手动运行 | workflow 输入和 issue/comment 入口保留；相关测试通过 | 通过 |
| 回归质量 | 测试、构建、lint、类型检查通过 | `66 passed`；compileall、Ruff、Mypy、`git diff --check` 通过 | 通过 |
| 范围控制 | 不实现 PRD 外功能，不修改新闻筛选逻辑 | 本次最终验收仅更新 PRD 状态和验收记录 | 通过 |

## 最终结论

OPS-01 的五个需求编号和全部验收标准均已通过。自动推送不依赖本地电脑开机；cron-job.org 负责准时触发，GitHub Actions 执行流水线，8:15 负责幂等兜底，手机人工恢复入口继续可用。
