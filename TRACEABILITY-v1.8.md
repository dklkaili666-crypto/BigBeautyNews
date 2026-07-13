# BigBeautyNews v1.8 Traceability and Acceptance

- PRD version: v1.8
- Implementation plan: Approved on 2026-07-13
- Verification date: 2026-07-13

| Requirement | Planned tasks | Implementation evidence | Verification evidence | Result | Notes |
|---|---|---|---|---|---|
| FR-014 | T8-001, T8-008 | Plural event terms and case-sensitive `US` handling in `src/pipeline/geopolitics.py`; acceptance examples in `tests/test_geopolitics_pipeline.py` | `python -m pytest tests/test_geopolitics_pipeline.py tests/test_geopolitics_llm.py -q` → 12 passed | 部分通过 | T8-001 complete; final regression pending |
| FR-015 | T8-003, T8-008 | Side-effect-free `.github/workflows/ci.yml`; conditioned preflight before production in `daily.yml`; static workflow coverage | `python -m pytest tests/test_workflow.py -q` → 6 passed | 部分通过 | Remote CI evidence pending |
| FR-016 | T8-004, T8-008 | Both workflows use `checkout@v7` and `setup-python@v6`; tests reject old/Pages actions | Workflow version and Pages assertions passed | 部分通过 | Remote CI evidence pending |
| NFR-008 | T8-002, T8-008 | Fully pinned `constraints.txt`; explicit `requirements-dev.txt`; constrained README install commands | Clean `.venv-v1.8`: install and runtime imports succeeded; `pip check` clean; full suite 60 passed | 部分通过 | Python 3.12 remote CI evidence pending |
| NFR-009 | T8-007, T8-008 | Current-state `PRD.md`; complete history under `docs/archive/`; corrected README/CHANGELOG/FR-012 exception | Coverage script: 27 unique requirements, 27 acceptance sections, no missing IDs; archives readable; stale-claim search clean | 通过 | Pages exception is explicit and settings untouched |
| NFR-010 | T8-005, T8-006, T8-008 | Named fetch, prepare, rank, translate, persist and push functions in `src/main.py`; `run_pipeline()` retains orchestration/failure status | 16 main/output tests passed; direct stage boundaries and four-call LLM assertion; Ruff/Mypy passed | 部分通过 | Final full regression pending |
| NFR-011 | T8-001–T8-008 | Requirement-scoped rule, workflow, dependency, refactor, test and documentation changes only | 66 tests passed; Ruff, Mypy, compileall and `git diff --check` passed | 部分通过 | Remote CI and final orphan check pending |

Allowed final results: `通过`, `部分通过`, `未通过`, `阻塞`.

## Orphan check

- Tasks without approved requirements: None.
- Material changes without approved requirements: None.

## Accepted exception

| Baseline requirement | Actual state | Acceptance |
|---|---|---|
| FR-012 Pages boundary | Daily workflow has no Pages actions/permissions, but repository Pages remains public/built | User explicitly accepted this exception and excluded Pages changes from v1.8 |
