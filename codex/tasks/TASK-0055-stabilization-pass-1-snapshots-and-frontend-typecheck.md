---
id: TASK-0055
epic: EPIC-080
title: "Stabilization pass 1: frontend typecheck and deterministic snapshot checks"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0047", "TASK-0048", "TASK-0051"]
risk: medium
context_packs: ["codex/context/EPIC-080.md", "codex/context/EPIC-090.md"]
patterns: []
---

## Objective
Stabilize the current red checks by fixing:
1. frontend TypeScript typechecking failure
2. backend-owned frontend snapshot determinism failure in `scripts/export_frontend_snapshots.py --check`

## Failing Commands (Target)
- `cd frontend && npm run typecheck`
- `PYTHONPATH=src python3 scripts/export_frontend_snapshots.py --check`

## Non-goals
- No new product/runtime/frontend features.
- No contract expansions.
- No workflow behavior changes beyond deterministic metadata sanitation needed for stable snapshot exports.

## Source Files To Change
- `frontend/src/lib/repositories/artifactAttachments.ts`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `tests/runtime/test_example_document_corpus_ingress.py`
- `tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `fixtures/frontend_contracts/*.json`
- `Makefile`
- `README.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/DECISIONS_SINCE_LAST.md` (stabilization decision note)

## Verification Commands
- `make schema-validate`
- `make contract`
- `make runtime-api` (if target exists)
- `make frontend-snapshots`
- `make frontend-snapshots-check`
- `PYTHONPATH=src python3 scripts/export_frontend_snapshots.py --check`
- `PYTHONPATH=src pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `PYTHONPATH=src pytest -q tests/runtime/test_example_document_corpus_ingress.py`
- `cd frontend && npm run typecheck`

## Acceptance Criteria
- `uploadAttachmentForSubject` uses a valid TypeScript object-parameter signature and frontend exports remain unchanged.
- `ingress_source_path` metadata is stable and never stores local absolute machine paths in snapshot exports.
- Fixture-ingested source metadata paths use `fixtures/...` when available; non-fixture paths fall back to basename.
- Backend-owned frontend snapshots are regenerated and no longer contain local absolute paths.
- `scripts/export_frontend_snapshots.py --check` passes after regeneration.
- Regression tests cover source-path sanitation and snapshot path determinism.
- Repo docs/task index are updated and not stale.

## Notes
- In this execution environment, Node/npm is not installed, so direct local execution of `npm run typecheck` is blocked. The code change still targets the typecheck root cause directly.
