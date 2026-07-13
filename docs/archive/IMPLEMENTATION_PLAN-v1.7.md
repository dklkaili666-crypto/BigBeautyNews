# BigBeautyNews v0.7 Implementation Plan

- Based on PRD version: v1.7
- Status: Complete
- Created: 2026-07-13
- Implementation authorization: User explicitly approved the implementation plan on 2026-07-13

## Delivery strategy

Implement the smallest independent second pipeline that reuses the existing RSS fetcher, LLM configuration, output conventions, scheduler, and push transport. Preserve the AI pipeline and the external `daily-5-things.json` contract. Add focused geopolitics modules rather than refactoring working AI modules.

## Tasks

| Task | Requirement IDs | Exact change scope | Dependencies | Verification and expected evidence | Status |
|---|---|---|---|---|---|
| T-001 Free geopolitics source ingestion | FR-001; NFR-001; NFR-004; NFR-006 | Add a separate geopolitics RSS source list in `src/config.py` for the eight approved feeds. Reuse `src/fetchers/rss_fetcher.py`; change it only if a verified feed format requires normalization already in scope. Add mocked feed/config tests in `tests/test_geopolitics_sources.py`. | Approved PRD v1.7 | `python -m pytest -q tests/test_geopolitics_sources.py tests/test_fetchers.py` → 6 passed. | Completed |
| T-002 Geopolitics filtering, classification, and duplicate foundation | FR-002; FR-004; NFR-003; NFR-005 | Add `src/pipeline/geopolitics.py` containing the minimum entity/event dictionaries, rule filter, China/US/global classification, primary-board classification for AI/政经 crossover events, and deterministic rule score used only for fallback ordering. Extend `src/pipeline/dedup.py` only with cross-board duplicate comparison/replacement helpers. Add positive, negative, regional, 48/72-hour, crossover, and duplicate tests in `tests/test_geopolitics_pipeline.py`. | T-001 | `python -m pytest -q tests/test_geopolitics_pipeline.py tests/test_pipeline.py` → 20 passed. | Completed |
| T-003 Geopolitics LLM ranking and translation | FR-003; FR-005; NFR-001; NFR-005; NFR-006 | Add `src/pipeline/geopolitics_ranker.py` with the approved ranking priorities, China/US soft quotas, source-diversity quality check, strict five-index validation, and one retry. Add `translate_geopolitics_top5` to `src/pipeline/translator.py` using the existing OpenAI-compatible client/config and政经-specific prompt; do not refactor the working AI prompt. Add mocked LLM tests in `tests/test_geopolitics_llm.py`. | T-002 | `python -m pytest -q tests/test_geopolitics_llm.py tests/test_llm_pipeline.py` → 9 passed. | Completed |
| T-004 Dual-board internal schema and stable external contract | FR-008; FR-009; NFR-002 | Extend `src/outputs/json_writer.py` so internal/current/archive digests require AI `items` + `dailyTheme` and政经 `geopoliticsItems` + `geopoliticsTheme`, each with five items. Keep `build_external_digest` and external validation AI-only and five-field. Make archive readers tolerate old files without geopolitics fields and expose category-specific history to callers. Update `tests/test_outputs.py`. | T-002 | `python -m pytest -q tests/test_outputs.py` → 10 passed. | Completed |
| T-005 End-to-end orchestration, completeness gate, and observability | FR-004; FR-007; FR-009; FR-011; FR-013; NFR-002; NFR-004; NFR-005 | Update `src/main.py` to fetch AI and政经 sources without mixing pools; run their independent filters/rankers/translators; apply primary-board classification, final cross-board dedup and deterministic next-candidate replacement; require 5+5 before successful persistence/push; preserve 7:45/8:15, manual triggers, idempotency, and external AI JSON. Extend `src/outputs/status.py` with per-board candidate/selected counts and board-specific errors without changing existing status flags. Update `tests/test_main.py`, `tests/test_workflow.py`, and status tests. | T-001–T-004 | `python -m pytest -q tests/test_main.py tests/test_workflow.py tests/test_push_state.py tests/test_outputs.py` → 16 passed. | Completed |
| T-006 One ServerChan post with two Top 5 sections | FR-006; FR-011; NFR-002 | Surgically extend `src/outputs/serverchan.py` to accept both boards/themes and render one Markdown body: AI first, geopolitics second, ranks 1–5 within each. Preserve endpoint, one POST, 64KB guard, result fields, idempotency caller semantics, and smoke-test behavior. Update `tests/test_outputs.py`. | T-004, T-005 | `python -m pytest -q tests/test_outputs.py tests/test_main.py` → 13 passed. | Completed |
| T-007 Local web dual-board display and legacy archive compatibility | FR-010; FR-008; NFR-002 | Update `web/app.js`, and only the necessary markup/style in `web/index.html` / `web/style.css`, to render AI first and geopolitics second for new data while rendering only AI for legacy archives. Add focused static/data tests under `tests/test_outputs.py` or a new `tests/test_web.py` matching the repository’s lightweight frontend convention. | T-004 | `python -m pytest -q tests/test_web.py tests/test_outputs.py` → 12 passed; browser evidence: new fixture 10 cards/two sections/two rank sets, legacy current data 5 cards/no empty state. | Completed |
| T-008 Stop BigBeautyNews Pages without breaking automation | FR-011; FR-012; NFR-002; NFR-007 | Edit `.github/workflows/daily.yml` only to remove the `github-pages` environment, Pages/id-token permissions, `_site` artifact preparation, configure/upload/deploy steps. Preserve checkout, dispatch inputs, push checks, secrets, pipeline execution, Git commit/push, and skipped-run handling. Extend `tests/test_workflow.py`. Do not change repository visibility or Touyanrili. | T-005 | `python -m pytest -q tests/test_workflow.py tests/test_external_scheduler.py` → 6 passed. | Completed |
| T-009 Documentation, full regression, and acceptance evidence | FR-001–FR-013; NFR-001–NFR-007 | Update `README.md` and `CHANGELOG.md` only for approved behavior, free source list, LLM call boundary, local web instructions, public raw JSON dependency, and stopped Pages deployment. Run full checks and populate `TRACEABILITY.md` with actual file/test evidence and one result per requirement. Remove only orphan additions introduced by this work. | T-001–T-008 | `compileall` passed; `pytest -q` → 58 passed; Ruff passed; Mypy with third-party import ignore passed; `git diff --check` passed; eight RSS feeds and raw URL returned HTTP 200. | Completed |

## Planned implementation order

1. T-001 source ingestion.
2. T-002 deterministic filtering/classification/dedup foundation.
3. T-003 geopolitics LLM ranking and translation.
4. T-004 internal/external data contracts.
5. T-005 complete pipeline orchestration and failure semantics.
6. T-006 final push presentation.
7. T-007 local web presentation.
8. T-008 workflow privacy reduction.
9. T-009 full regression and acceptance.

Each task is verified before starting the next dependent task. Ordinary implementation choices constrained by the PRD do not require additional approval. Any behavior that changes the approved product boundary requires a change request before implementation.

## Coverage check

- Unplanned functional requirements: None.
- Unplanned non-functional requirements: None.
- Tasks without approved requirements: None.
- Cross-project changes: None; Touyanrili remains read-only and out of implementation scope.
- Implementation code modified before approval: None.
- Final status: All planned tasks completed; no approved requirement is unimplemented.
