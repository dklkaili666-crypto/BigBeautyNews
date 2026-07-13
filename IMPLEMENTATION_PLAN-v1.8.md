# BigBeautyNews v1.8 Implementation Plan

- Based on PRD version: v1.8
- Status: Approved — implementation in progress
- Created: 2026-07-13
- Implementation authorization: Approved by user on 2026-07-13

## Delivery strategy

Fix observable correctness and delivery risks first, then make two small behavior-preserving extractions from `run_pipeline()`. Do not disable Pages, change Touyanrili, add sources, add LLM calls, or redesign the pipeline.

## Tasks

| Task | Requirement IDs | Exact change scope | Dependencies | Verification and expected evidence | Status |
|---|---|---|---|---|---|
| T8-001 Geopolitics lexical coverage | FR-014; NFR-011 | Add failing tests for plural event terms, `US`/`U.S.` and lowercase `us` negative cases in `tests/test_geopolitics_pipeline.py`. Update only the matching representation and helpers in `src/pipeline/geopolitics.py`; keep the lightweight dictionary approach and existing classification flow. | Approved PRD v1.8 | Targeted geopolitics tests plus existing pipeline tests pass; explicit four acceptance examples pass; no new dependency. | Completed — 12 targeted tests passed |
| T8-002 Reproducible runtime and test dependencies | NFR-008; NFR-011 | Add a fully pinned `constraints.txt` for the resolved production/test toolchain and `requirements-dev.txt` declaring Pytest, Ruff and Mypy in addition to runtime requirements. Update install commands in workflows and README to use the same constraints. Do not upgrade unrelated application dependencies beyond the versions selected for this lock. | T8-001 | Create a temporary clean virtual environment, install with constraints, import runtime dependencies, run the full suite, and record exact versions. | Completed — clean install/import/pip check; 60 tests passed |
| T8-003 Side-effect-free CI and production preflight | FR-015; NFR-011 | Add `.github/workflows/ci.yml` for push/PR using Python 3.12, dependency cache, compileall, Pytest, Ruff and Mypy. Add a test step in `.github/workflows/daily.yml` after dependency installation and before `Run BigBeautyNews`, guarded by the same full-run condition. Extend `tests/test_workflow.py` to assert ordering, conditions, CI triggers and absence of production Secrets/commands in CI. | T8-002 | Workflow tests pass; CI has read-only contents permission, no live feed/LLM/ServerChan command, and daily preflight precedes production. | Completed — workflow tests passed |
| T8-004 Upgrade GitHub Actions runtime versions | FR-016; NFR-011 | Update checkout to `actions/checkout@v7` and Python setup to `actions/setup-python@v6` in both workflows. Add static version assertions and preserve removal of all Pages actions/permissions. | T8-003 | Workflow tests pass; both workflows use approved versions; no `checkout@v4`, `setup-python@v5`, Pages action or Pages permission remains. | Completed — approved versions statically verified |
| T8-005 Extract source fetching and candidate preparation | NFR-010; NFR-011 | In `src/main.py`, extract only the existing source-pool fetch and AI/政经 candidate preparation stages into named functions with explicit inputs/outputs. Preserve logging, warnings, source errors, history windows, classification and counts. Add direct tests for extracted stage boundaries where existing end-to-end tests are insufficient. | T8-001 | Main/pipeline tests pass before and after; candidate counts and failure reasons match existing fixtures; no unused abstraction or new class. | Completed — stage boundary tests passed |
| T8-006 Extract ranking/translation and output stages | NFR-010; NFR-011 | Extract the existing rank/translate/cross-board resolution and digest persistence/push stages into small named functions. Keep `run_pipeline()` as top-level sequencing and status finalization. Preserve exact LLM call count, schemas, one ServerChan POST, idempotency and failure semantics. | T8-005 | Full main/output/LLM tests pass; call-count assertions remain; `run_pipeline()` reads as stage orchestration rather than embedded implementation. | Completed — 16 stage/output tests; four-call assertion passed |
| T8-007 Consolidate current-state PRD and acceptance docs | NFR-009; NFR-011 | Archive the complete pre-cleanup v1.7/v1.8 history under `docs/archive/`; rewrite root `PRD.md` as concise current v1.8 truth with stable FR/NFR IDs, current architecture, actual Pages exception and revision links. Update `TRACEABILITY.md`, README and CHANGELOG so FR-012 is an accepted exception rather than a false claim that Pages is disabled. Do not modify Pages settings. | T8-001–T8-006 | Requirement-ID coverage script finds all current requirements and acceptance criteria; conflict search finds no stale “next target” or “Pages stopped” claims; archive exists and is readable. | Completed — 27/27 requirements covered; archive/readback passed |
| T8-008 Full regression, remote CI, and delivery evidence | FR-014–FR-016; NFR-008–NFR-011 | Run clean-environment install, compileall, full Pytest, Ruff, Mypy and diff check; update `TRACEABILITY-v1.8.md` with actual evidence. After all local checks pass, commit and push the approved changes to `master` so the new side-effect-free CI runs; monitor CI to success. Do not manually run the production daily workflow or send ServerChan. | T8-001–T8-007 | All local checks pass; all v1.8 requirements are `通过`; pushed commit has a successful CI run; repository remains synced and Pages setting is untouched. | In progress — local checks passed; remote CI pending |

## Planned implementation order

1. T8-001 correctness tests and rule fix.
2. T8-002 dependency lock.
3. T8-003 CI and daily preflight.
4. T8-004 action upgrades.
5. T8-005 fetch/prepare extraction.
6. T8-006 rank/output extraction.
7. T8-007 PRD/archive/trace cleanup.
8. T8-008 local and remote acceptance.

Every task is verified before the next dependent task. Any behavior change outside PRD v1.8 requires a new change request.

## Coverage check

- Unplanned v1.8 requirements: None.
- Tasks without approved requirements: None.
- Pages disable/delete/migration work: None.
- Touyanrili changes: None.
- New external service or LLM call: None.
- Implementation code modified before plan approval: None.
