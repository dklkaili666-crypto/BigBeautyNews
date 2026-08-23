# BigBeautyNews v2.1 实施计划

- 基于 PRD：v2.1（2026-08-23 Approved）
- 状态：Approved
- 批准人：项目所有者
- 批准证据：2026-08-23 明确回复“批准实施计划 v2.1”
- 变更来源：已批准 CR-v2.0-001
- 目标：在不放宽质量标准的前提下，让 Flash 第二次翻译尝试针对长度违规完成纠偏

## 实施前提

- v2.0 的 T20-001～T20-004 已完成，提交 `38fef4e` 已在远端 `master`。
- 生产 `LLM_MODEL` 已是 `deepseek-v4-flash`；API Base/Key 未变。
- v2.0 真实运行只阻塞在 AI 翻译长度校验，非思考 JSON 请求和两套排序均已通过生产验证。
- 本计划不处理 CR-001，不修改本计划未列出的产品行为。

## 任务计划

| 任务 | 需求编号 | 改动范围 | 依赖 | 验证方式与预期证据 | 状态 |
|---|---|---|---|---|---|
| T21-001 翻译长度纠偏实现 | FR-023；FR-020；NFR-013；NFR-014 | 精准修改 `src/pipeline/translator.py`：复用一套安全长度校验生成 rank/字段/实际长度/允许范围；AI与政经第一次长度不合格时，仅为第二次请求追加纠偏说明并要求返回完整5条 JSON。不得包含第一轮标题、摘要、响应或思考内容；不得改基础提示词、长度阈值或两次上限。扩展 `tests/test_llm_pipeline.py`、`tests/test_geopolitics_llm.py`。 | 已批准 PRD v2.1 | 16 项定向测试通过；AI/政经纠偏成功、完整5条要求、安全长度元数据和敏感标记隔离均有断言；AI两次长度不合格仍失败。 | Completed |
| T21-002 全量回归、范围审查与重新发布 | FR-023；FR-020；NFR-013；NFR-014 | 运行定向和全量检查；审查差异只涉及翻译纠偏和对应测试；更新 v2.0/v2.1 计划状态，将实现、批准文档和 CR 提交并推送到现有 `master`。 | T21-001 | 定向测试、`pytest -q`、Ruff、Mypy、`compileall`、`git diff --check` 全部通过；基础提示词、阈值、排序、调度、Schema、新闻规则和回退策略无改动；远端包含新提交。 | Pending |
| T21-003 Flash 真实端到端验收 | FR-022；FR-023；NFR-013；NFR-014 | 使用现有 `daily.yml`，以 `trigger_source=manual`、`force_push=false` 触发一次真实运行并等待完成；检查四次 LLM 阶段、5+5输出、Schema、Server酱和数据提交。 | T21-002；当天尚未成功推送 | 工作流15分钟内成功；模型为 Flash；AI/政经各5条；Server酱 HTTP 200/code 0且只发送一次；状态 `generated/pushed/committed/schemaValid` 全为 true。 | Pending |
| T21-004 逐项验收与交付记录 | FR-018～FR-023；NFR-013～NFR-015 | 新增 `TRACEABILITY-v2.1.md`，更新 `CHANGELOG.md`、`PRD.md`、v2.0/v2.1计划状态；记录测试、提交、workflow URL和安全运行证据，完成孤儿任务/改动检查后提交并推送。 | T21-003 | v2.0与v2.1全部需求逐条通过；无未关联任务或实现改动；仓库与远端同步。 | Pending |

## 验证命令

```powershell
python -m pytest -q tests/test_llm_pipeline.py tests/test_geopolitics_llm.py
python -m pytest -q tests/test_main.py tests/test_external_scheduler.py tests/test_push_state.py
python -m pytest -q
python -m ruff check src tests
python -m mypy src --ignore-missing-imports --check-untyped-defs
python -m compileall -q src
git diff --check
```

真实生产验收输入保持：

```text
trigger_source=manual
schedule_slot=
force_push=false
push_test=false
```

## 覆盖检查

| 需求 | 覆盖任务 |
|---|---|
| FR-023 | T21-001、T21-002、T21-003、T21-004 |
| FR-020（v2.1修订） | T21-001、T21-002、T21-004 |
| FR-022（v2.1续验） | T21-003、T21-004 |
| NFR-013（v2.1续验） | T21-001～T21-004 |
| NFR-014（v2.1续验） | T21-001～T21-004 |
| v2.0其他未变需求 | T21-002～T21-004回归与最终验收 |

- 未规划需求：无。
- 无需求关联任务：无。
- 计划外实现文件：无。

## 停止条件

- 实现需要放宽标题/摘要阈值、修改基础提示词或增加第三次尝试。
- 真实运行再次因非长度类 Flash/API 不兼容失败。
- 真实运行当天已经成功推送，导致非强制验收不能发送真实消息。

命中停止条件时提交新的变更请求，不静默扩大范围。
