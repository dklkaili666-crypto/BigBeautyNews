# BigBeautyNews v2.0 实施计划

- 基于 PRD：v2.0（2026-08-23 Approved）
- 状态：Approved
- 批准人：项目所有者
- 批准证据：2026-08-23 明确回复“批准实施计划 v2.0”
- 目标：切换 `deepseek-v4-flash`，修复非思考结构化输出兼容性，并以真实微信推送完成验收

## 实施前提

- 开始编码前，将当前本地 `master` 快进到 `origin/master`，保留已批准 PRD 和本实施计划，不覆盖远端自动生成的数据提交。
- 不处理未批准的 CR-001，不修改本计划未列出的产品行为。
- GitHub Secrets 和真实工作流只在本计划获批、代码验证通过后变更或触发。

## 任务计划

| 任务 | 需求编号 | 改动范围 | 依赖 | 验证方式与预期证据 | 状态 |
|---|---|---|---|---|---|
| T20-001 非思考 JSON 请求契约 | FR-019；NFR-014 | 精准修改 `src/pipeline/ranker.py`、`src/pipeline/geopolitics_ranker.py`、`src/pipeline/translator.py` 的四处 Chat Completions 调用，加入 `thinking=disabled` 和 `json_object`；不改提示词、温度、输出额度或质量规则。扩展 `tests/test_llm_pipeline.py`、`tests/test_geopolitics_llm.py` 捕获并断言四处请求参数。 | 已批准 PRD | `python -m pytest -q tests/test_llm_pipeline.py tests/test_geopolitics_llm.py`：9 passed；四处参数均有独立断言。 | Completed |
| T20-002 空响应与非法 JSON 诊断 | FR-020；NFR-013 | 在上述三个 pipeline 文件中加入最小的响应校验：空/空白 `content` 使用明确异常；非法 JSON 保留独立错误类别；日志仅记录模型、尝试次数及可用的 `finish_reason`、内容/思考长度和 token 用量，不记录原文或思考文本。扩展对应单元测试覆盖空内容、非法 JSON、两次尝试及日志脱敏。 | T20-001 | `python -m pytest -q tests/test_llm_pipeline.py tests/test_geopolitics_llm.py`：13 passed；空内容、非法 JSON、两次尝试及日志脱敏断言通过。 | Completed |
| T20-003 流水线失败与兜底语义回归 | FR-020；FR-021；NFR-014 | 在 `tests/test_main.py` 增加排序失败集成测试，证明失败发生在持久化和 Server酱之前，状态为失败且 `pushed=false`；复用 `tests/test_external_scheduler.py` 与 `tests/test_push_state.py` 验证当天未写成功日期时兜底仍运行、成功后同日运行跳过。现有 `src/main.py` 预期无需修改。 | T20-002 | `python -m pytest -q tests/test_main.py tests/test_external_scheduler.py tests/test_push_state.py`：11 passed；失败不持久化、不推送、不写成功日期。 | Completed |
| T20-004 全量回归、范围审查与发布实现 | FR-019；FR-020；FR-021；NFR-013；NFR-014；NFR-015 | 运行完整测试和静态检查，检查差异只包含获批范围；将代码、测试、已批准 PRD 和已批准计划提交并推送到现有 `master`，使生产工作流加载新实现。 | T20-001～T20-003 | `pytest -q`、Ruff、Mypy、`compileall`、`git diff --check` 全部通过；差异审查无提示词/调度/Schema/新闻规则等孤儿改动；远端 `master` 包含交付提交。 | In Progress |
| T20-005 生产模型切换与真实验收 | FR-018；FR-022；NFR-013；NFR-015 | 只将 GitHub Actions Secret `LLM_MODEL` 更新为 `deepseek-v4-flash`，不改 Base/Key；随后以 `trigger_source=manual`、`force_push=false` 触发一次真实工作流并等待完成。若 API 不支持批准的参数，停止并提交变更请求。 | T20-004；当天尚未成功推送，或等待下一业务日 | Secret 元数据仅显示 `LLM_MODEL` 本次更新；真实运行在15分钟内成功；运行状态为 Flash、AI/政经各5条、Schema 全通过、Server酱 HTTP 200/code 0、只推送一次、数据提交成功。 | Pending |
| T20-006 逐项验收与交付记录 | FR-018～FR-022；NFR-013～NFR-015 | 新增 `TRACEABILITY-v2.0.md`，更新 `CHANGELOG.md` 和必要的 PRD/计划状态；记录测试命令、提交、workflow URL 和安全的运行证据，不记录凭证或模型原文。完成孤儿任务/改动检查后提交并推送验收文档。 | T20-005 | 验收表每项需求均有实际证据并标记通过；无未关联任务或实现改动；仓库与远端同步。 | Pending |

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

真实生产验收使用现有 `daily.yml`，输入固定为：

```text
trigger_source=manual
schedule_slot=
force_push=false
push_test=false
```

## 覆盖检查

| 需求 | 覆盖任务 |
|---|---|
| FR-018 | T20-005、T20-006 |
| FR-019 | T20-001、T20-004、T20-006 |
| FR-020 | T20-002、T20-003、T20-004、T20-006 |
| FR-021 | T20-003、T20-004、T20-006 |
| FR-022 | T20-005、T20-006 |
| NFR-013 | T20-002、T20-004、T20-005、T20-006 |
| NFR-014 | T20-001、T20-003、T20-004、T20-006 |
| NFR-015 | T20-004、T20-005、T20-006 |

- 未规划需求：无。
- 无需求关联任务：无。
- 计划外实现文件：无。

## 停止条件

- 当前 API 服务拒绝 `deepseek-v4-flash`、`thinking` 或 `response_format` 参数。
- 真实运行当天已有成功推送，导致非强制验收无法发送真实消息。
- 实施中发现必须修改提示词、调度、Schema、API Base/Key、回退策略或其他范围外行为。

命中停止条件时，记录证据并提交变更请求，不静默扩大范围。
