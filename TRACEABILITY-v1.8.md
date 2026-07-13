# BigBeautyNews v1.8 Traceability and Acceptance

- PRD version: v1.8
- Implementation plan: Approved on 2026-07-13
- Verification date: 2026-07-13
- Delivery status: Implemented and verified; awaiting final user acceptance

| Requirement | Planned tasks | Implementation evidence | Verification evidence | Result | Notes |
|---|---|---|---|---|---|
| FR-014 | T8-001, T8-008 | Plural event terms and case-sensitive `US` handling in `src/pipeline/geopolitics.py`; acceptance examples in `tests/test_geopolitics_pipeline.py` | 12 targeted tests and 66-test full regression passed | 通过 | No NLP dependency added |
| FR-015 | T8-003, T8-008 | Side-effect-free `.github/workflows/ci.yml`; conditioned preflight before production in `daily.yml`; static workflow coverage | 6 workflow tests passed; remote CI run 29222735480 passed all checks | 通过 | CI contains no production secrets or commands |
| FR-016 | T8-004, T8-008 | Both workflows use `checkout@v7` and `setup-python@v6`; tests reject old/Pages actions | Version assertions passed; remote CI run 29222735480 succeeded | 通过 | No Pages action or permission introduced |
| NFR-008 | T8-002, T8-008 | Fully pinned `constraints.txt`; explicit `requirements-dev.txt`; constrained README/workflow installs | Clean install/import and `pip check` passed; Python 3.12 CI install and full checks passed | 通过 | Production and development resolve through one constraint file |
| NFR-009 | T8-007, T8-008 | Current-state `PRD.md`; complete history under `docs/archive/`; corrected README/CHANGELOG/FR-012 exception | Coverage script: 27 unique requirements, 27 acceptance sections, no missing IDs; archives readable; stale-claim search clean | 通过 | Pages exception is explicit and settings untouched |
| NFR-010 | T8-005, T8-006, T8-008 | Named fetch, prepare, rank, translate, persist and push functions in `src/main.py`; `run_pipeline()` retains orchestration/failure status | Direct stage tests, 66-test regression, Ruff and Mypy passed | 通过 | No framework, class or unused abstraction added |
| NFR-011 | T8-001–T8-008 | Requirement-scoped rule, workflow, dependency, refactor, test and documentation changes only | 66 tests, Ruff, Mypy, compileall, diff check and remote CI passed | 通过 | Four-call assertion passed; Daily/ServerChan not triggered; Pages/Touyanrili untouched |

Allowed final results: `通过`, `部分通过`, `未通过`, `阻塞`.

## Orphan check

- Tasks without approved requirements: None.
- Material changes without approved requirements: None.
- Changed files without a v1.8 or accepted baseline requirement: None.

## Accepted exception

| Baseline requirement | Actual state | Acceptance |
|---|---|---|
| FR-012 Pages boundary | Daily workflow has no Pages actions/permissions, but repository Pages remains public/built | User explicitly accepted this exception and excluded Pages changes from v1.8 |

## Remote evidence

- Commit: `3477c9431b172452dc19957b66c3f156e36efed4`
- CI: https://github.com/dklkaili666-crypto/BigBeautyNews/actions/runs/29222735480 — success, Python 3.12, all six steps passed.
- BigBeautyNews Daily workflow: not triggered by this delivery.
- ServerChan: no test or production message sent by this delivery.
