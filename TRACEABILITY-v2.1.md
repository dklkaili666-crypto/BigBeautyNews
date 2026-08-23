# BigBeautyNews v2.0 / v2.1 验收记录

- PRD 版本：v2.0、v2.1
- PRD 批准：项目所有者于 2026-08-23 分别批准 v2.0、CR-v2.0-001 和 v2.1
- 实施计划批准：项目所有者于 2026-08-23 分别批准 v2.0、v2.1
- 验证日期：2026-08-23
- 交付状态：Delivered（代码、真实工作流、微信接口和数据提交均已验证）

## 需求追踪

| 需求 | 计划任务 | 实现证据 | 验证证据 | 结果 | 备注 |
|---|---|---|---|---|---|
| FR-018 生产模型切换为 Flash | T20-005、T21-003 | GitHub Secret `LLM_MODEL` 于 2026-08-23 更新；`LLM_API_BASE`、`LLM_API_KEY` 的更新时间仍为 2026-07-02。 | `data/run-status.json` 记录 `llmModel=deepseek-v4-flash`；成功 workflow 32640356597。 | 通过 | Secret 值未写入文档或日志。 |
| FR-019 四处非思考 JSON 输出 | T20-001、T20-004 | `src/pipeline/ranker.py`、`src/pipeline/geopolitics_ranker.py`、`src/pipeline/translator.py` 四处调用均设置 `thinking=disabled` 与 `json_object`；提交 `38fef4e`。 | 四处请求参数有独立单元测试；真实运行返回 HTTP 200，安全诊断中 `reasoning_length=0`。 | 通过 | 未删除或降级结构化输出参数。 |
| FR-020 可诊断重试与失败 | T20-002、T20-003、T21-001 | 空内容、非法 JSON和长度违规均有独立安全错误；每个阶段仍最多两次；提交 `38fef4e`、`583f481`。 | 空响应/非法 JSON/两次失败/日志脱敏测试通过；失败 workflow 32640092208、32640230193 均在持久化和推送前退出。 | 通过 | 失败运行没有写成功推送日期。 |
| FR-021 主任务与兜底语义 | T20-003、T21-004 | 未修改外部调度与 `push-history.json` 幂等逻辑。 | `tests/test_main.py`、`tests/test_external_scheduler.py`、`tests/test_push_state.py` 共 11 项通过；成功后 `push-history.json` 仅新增一次 2026-08-23。 | 通过 | 07:45/08:15 配置未改。 |
| FR-022 真实端到端恢复 | T20-005、T21-003 | 最终实现提交 `067c70a`；数据提交 `db76b4f`。 | [workflow 32640356597](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/32640356597) 约 61 秒成功；AI/政经各 5 条；HTTP 200、业务 code 0；日志仅 1 条 Server酱成功；状态四个布尔值均为 true。 | 通过 | `errors=[]`，运行未使用 `force_push`。 |
| FR-023 翻译长度纠偏重试 | T21-001～T21-003 | 共享长度违规元数据、完整 5 条重生成、字段定向纠偏；提交 `583f481`、`535528d`、`067c70a`。 | 16 项定向测试通过；真实成功运行中 AI 首次标题长度 60，第二次纠偏后通过，随后政经翻译、推送和提交均成功。 | 通过 | 第二次请求不含第一轮模型文本或思考内容。 |
| NFR-013 凭证与模型响应安全 | T20-002、T21-001～T21-004 | 日志只记录长度、状态、用量和违规字段；测试用唯一敏感标记验证隔离。 | 全量 74 项测试通过；Actions 对四个 Secret 均显示掩码；成功运行的思考长度为 0。 | 通过 | 既有 Server酱 `readkey` 风险仍按批准范围留在 CR-001，不属于本次实现。 |
| NFR-014 既有行为兼容 | T20-004、T21-002～T21-004 | 只修改三个 LLM 模块、对应测试及批准文档；v2.1 只修改翻译纠偏。 | 74 项测试、Ruff、Mypy、`compileall`、`git diff --check` 通过；归档和网页各 5+5，对外 JSON 仍为 AI 5 条五字段。 | 通过 | 基础提示词、代码阈值、调度、新闻源、Schema、推送格式和回退策略未改。 |
| NFR-015 可验证交付 | T20-004、T21-002～T21-004 | PRD、CR、计划、实现、测试与本追踪记录均进入 Git。 | 本表覆盖 FR-018～FR-023、NFR-013～NFR-015；本地静态检查与真实生产证据齐全。 | 通过 | 无孤儿任务或实现改动。 |

## 验证汇总

| 验证 | 结果 |
|---|---|
| `python -m pytest -q tests/test_llm_pipeline.py tests/test_geopolitics_llm.py` | 16 passed |
| `python -m pytest -q tests/test_main.py tests/test_external_scheduler.py tests/test_push_state.py` | 11 passed |
| `python -m pytest -q` | 74 passed |
| `python -m ruff check src tests` | 通过 |
| `python -m mypy src --ignore-missing-imports --check-untyped-defs` | 20 个源文件通过 |
| `python -m compileall -q src` | 通过 |
| `git diff --check` | 通过 |

## 真实运行证据

- [32639343904](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/32639343904)：v2.0 首次 Flash 验证；非思考 JSON 与两套排序成功，翻译长度失败，按规则未推送。
- [32640092208](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/32640092208)：v2.1 首次纠偏验证；第 3 条标题 53 字符，第二次仍为 53，未推送。
- [32640230193](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/32640230193)：明确字符计数后，标题从 60 降至 53，仍未达到上限，未推送。
- [32640356597](https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/32640356597)：字段定向短标题纠偏后成功；AI 与政经各 5 条、Schema、单次 Server酱推送和数据提交全部通过。

最终 `data/run-status.json`：模型为 `deepseek-v4-flash`，`generated/pushed/committed/schemaValid=true`，`pushHttpStatus=200`，`pushResponseCode=0`，`errors=[]`。`data/archive/2026-08-23.json` 与 `web/data.json` 各含 AI 5 条、政经 5 条；`data/daily-5-things.json` 仍只有 AI 5 条，每条字段严格为 `date/title/summary/url/source`。

## 孤儿检查

- 未关联需求的任务：无。
- 未关联需求的实现改动：无。
- 未批准的模型/API 回退、第三次尝试、代码截断或阈值放宽：无。
- 新闻源、筛选/去重、调度、Schema、Server酱格式和网页实现改动：无。

## 已知范围外事项

`data/run-status.json` 仍会保存既有 Server酱成功响应摘要中的 `readkey`。它不是 SendKey，但公开仓库下应按潜在敏感值处理；本次按用户批准的 v2.0/v2.1 范围明确不处理，继续由 `CHANGE_REQUEST-v1.9-001.md` 跟踪。
