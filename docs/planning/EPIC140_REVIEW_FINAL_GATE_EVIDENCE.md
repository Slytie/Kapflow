# EPIC-140+ Review Final Gate Evidence

Date: 2026-06-17

Scope: EPIC-140+ second-order review repair tasks 1-10 for foundation/readiness scope. This evidence does not authorize CAPEX runtime activation, product activation, public CAPEX routes, public workpage command dispatch, raw corpus import, migration approval beyond already-reviewed migrations, or production/pilot go-live.

## Gate Status

| Gate | Status | Reason code | Evidence |
| --- | --- | --- | --- |
| G-001 | PASS | FOUNDATION_SCOPE_ONLY | EPIC-140 remains closed as project/access foundation; activation blockers remain explicit. |
| G-002 | PASS | REVOCATION_EVENT_CONTRACT | `capex.project_membership.revoked` registry/payload/runtime-state contract exists. |
| G-003 | PASS | FAIL_CLOSED_AUTHORIZATION | Authorization reads require live active direct membership truth plus projection rows. |
| G-004 | PASS | MODULE_SPECIFIC_READINESS | `SME-RP-MODULE-READINESS-RULE.v1` is bound to `SME-RP-G002` and `SME-RP-G012` and blocks affected modules only. |
| G-005 | PASS | SQLITE_ALEMBIC_PARITY | CAPEX runtime table parity and bootstrap repair tests are in repo-native integration coverage. |
| G-006 | PASS | MALFORMED_BOOTSTRAP_FAIL_CLOSED | Empty malformed CAPEX shells are repaired; non-empty malformed shells fail closed. |
| G-007 | PASS | ARTIFACT_PROJECT_IDENTITY | Project-scoped artifact versions persist/require matching `project_id`; null identity fails CAPEX promotion. |
| G-008 | PASS | PROVENANCE_PROJECT_ISOLATION | Project-scoped provenance edges require same non-null project identity. |
| G-009 | PASS | SOURCEREF_PROJECT_GUARD | SourceRef resolver remains the active same-project guard; relation activation remains blocked. |
| G-010 | PASS | POINTER_PROMOTION_PROJECT_GUARD | Official pointer promotion requires artifact, workflow, approval/task, pointer scope, and event context project agreement. |
| G-011 | PASS | WORKPAGE_COMMAND_ACTIVATION_GUARD | Internal workpage command dispatch requires active `workpage_command_dispatch_v1` policy. |
| G-012 | PASS | WORKPAGE_COMMAND_IDEMPOTENCY | Workpage command envelopes replay exact command receipts and reject same-key/different-fingerprint attempts. |
| G-013 | PASS | DOWNSTREAM_ACTIVATION_BLOCKED | EPIC-150 and downstream activation gates remain blocked/open; no public CAPEX activation was added. |
| G-014 | PASS | FUTURE_RELATION_POLICY_BLOCKED | Source occurrence sharing/relation policy remains inactive until same tenant/domain/project enforcement is implemented. |
| G-015 | PASS | TASK_CONTROL_PLANE_CONSISTENT | `TASK-0202..TASK-0207` frontmatter now matches `TASK_INDEX.md`; DONE-on-open task dependency guard is enforced. `TASK-0299 -> TASK-0290` is safe because `TASK-0299` remains TODO/needs-review, not DONE. |
| G-016 | PASS | PROGRESS_DATA_REPO_OWNED | `frontend/src/data/capexEpicProgressData.json` is regenerated from repo source, validates `meta.codexRule`, `localOnly`, and freshness, and is checked by `capex-progress-check`. |
| G-017 | PASS | REDTEAM_PROBES_FIRST_CLASS | CAPEX invariant audit reports red-team project-security and workpage activation/idempotency hard gates. |
| G-018 | PARTIAL | FRONTEND_TESTS_FAILED | Python/backend/control-plane gates pass under Python 3.11.14. Node v20.20.0/npm 10.8.2 install, typecheck, isolated CAPEX progress page test, and build pass; `frontend-workpages-smoke` and `frontend-test` fail/hang in existing logistics/workspace UI suites. |
| G-019 | PASS | ROOT_DEBRIS_REMOVED | Review-identified zero-byte root debris files, including observed trailing-newline filename variants, are removed and narrowly forbidden by repo assurance. |
| G-020 | PASS | SCOPED_EVIDENCE_RECORDED | This file records scoped statuses/reason codes rather than blanket approval. |

## Verification Log

- `python3.11 --version`: `Python 3.11.14`
- `node --version`: `v20.20.0`
- `npm --version`: `10.8.2`
- `python3.11 scripts/validate_capex_epic_progress_data.py frontend/src/data/capexEpicProgressData.json`: PASS, 17 epics / 396 tasks.
- `python3.11 scripts/run_capex_invariant_audit.py --output-root .tmp/capex-invariant-audit --json`: PASS, 16 hard gates passed / 3 known gaps / 19 total.
- `python3.11 -m pytest tests/contract/test_capex_epic_progress_data.py tests/contract/test_task_control_plane_hygiene.py -q`: PASS, 12 tests.
- `python3.11 -m pytest tests/contract/test_repo_automation_truth.py -q`: PASS, 10 tests.
- `python3.11 -m pytest tests/contract/test_capex_invariant_audit.py -q`: PASS, 9 tests.
- `make PYTHON=python3.11 schema-validate`: PASS.
- `make PYTHON=python3.11 capex-semantic-tests`: PASS, progress check plus 66 CAPEX semantic tests.
- `cd frontend && npm ci`: PASS install; npm audit reported 9 vulnerabilities already present in the dependency tree.
- `make frontend-workpages-smoke`: FAIL, 2 failed / 1 passed test files, 15 failed / 11 passed tests; failures were timeout/loading-state failures in dispatch-report and logistics-schedule workpage UI tests.
- `make frontend-typecheck`: PASS.
- `make frontend-test`: FAIL/HUNG, broad frontend UI timeout failures across logistics/workpage/workspace/app-shell suites; process was terminated after reporting the failing groups.
- `cd frontend && npm run test:run -- src/pages/capexEpicProgressPage.test.tsx`: PASS, 6 tests after progress-data expectation refresh.
- `make frontend-build`: PASS.

## Activation Boundary

The final review repair closes the EPIC-140+ foundation review scope only. CAPEX runtime/product activation remains blocked by downstream source-governance, public workpage/API, artifact/provenance/pointer product-surface, release/capacity, real pilot storage or waiver, and production-preflight gates.
