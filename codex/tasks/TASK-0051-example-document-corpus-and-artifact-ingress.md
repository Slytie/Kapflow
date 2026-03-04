---
id: TASK-0051
epic: EPIC-030
title: "Promote example documents into executable fixture corpus with canonical artifact ingress"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0042", "TASK-0046", "TASK-0047", "TASK-0048", "TASK-0049"]
risk: high
context_packs: ["codex/context/EPIC-030.md", "codex/context/EPIC-080.md", "codex/context/EPIC-090.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
Canonical runtime substrate, Stage06/Stage07 business slices, and frontend real API integration are implemented.

The remaining gap was to turn template-pack completed examples into first-class executable fixture inputs and run them through the same artifact/attachment truth path used by runtime behavior.

## Objective
Implement a documented example-document corpus and integrate it through canonical artifact ingress, then expose real inline upload/download flows across CLI, API, and frontend surfaces.

This task also seeds stable fixture manifests/snapshots for downstream sandbox/agent tests.

## Non-goals
- No generalized execution-session framework.
- No new OpenAI end-to-end business flow in this task.
- No second attachment/file truth subsystem.
- No mutable/delete-first artifact semantics that conflict with immutable artifact history.
- No broad storage-backend hardening beyond a pragmatic dev adapter.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/FRONTEND_INTERACTION_RULES.md`
- `docs/planning/HITL_BOARD_ARCHITECTURE.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/promotion_semantics.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `fixtures/workflows/schedule_planning/template_pack/`

## Source files changed
- Runtime/storage/linkage:
  - `src/onetruth/infrastructure/artifacts/storage.py`
  - `src/onetruth/infrastructure/repositories/artifact_links.py`
  - `src/onetruth/infrastructure/db/models.py`
  - `alembic/versions/20260304_0005_artifact_links_for_document_ingress.py`
  - `src/onetruth/infrastructure/events/event_store.py`
  - `src/onetruth/application/handlers/workflow_task_lifecycle.py`
  - `src/onetruth/application/services/example_document_corpus.py`
  - `src/onetruth/cli/__main__.py`
- API adapter:
  - `src/onetruth/api/routes/artifacts.py`
  - `src/onetruth/api/main.py`
- Fixtures/snapshots:
  - `fixtures/example_document_corpus/manifest.yaml`
  - `fixtures/example_document_corpus/README.md`
  - `fixtures/frontend_contracts/*.json` (refreshed)
  - `scripts/export_frontend_snapshots.py`
- Runtime tests:
  - `tests/runtime/test_example_document_corpus_ingress.py`
  - `tests/runtime/api/test_artifact_attachment_api.py`
  - `tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
  - `tests/runtime/helpers/scenario_harness.py`
- Frontend inline attachment wiring:
  - `frontend/src/lib/api/onetruthApi.ts`
  - `frontend/src/lib/repositories/artifactAttachments.ts`
  - `frontend/src/lib/repositories/humanTasksRepository.ts`
  - `frontend/src/lib/repositories/approvalsRepository.ts`
  - `frontend/src/lib/repositories/flagsRepository.ts`
  - `frontend/src/lib/repositories/workflowRunsRepository.ts`
  - `frontend/src/components/AttachmentActions.tsx`
  - `frontend/src/components/ApprovalCard.tsx`
  - `frontend/src/components/FlagCard.tsx`
  - `frontend/src/pages/MyWorkPage.tsx`
  - `frontend/src/pages/BoardPage.tsx`
  - `frontend/src/pages/ApprovalsPage.tsx`
  - `frontend/src/pages/ExceptionsPage.tsx`
  - `frontend/src/components/attachmentActions.test.tsx`
- Documentation and memory:
  - `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
  - `README.md`
  - `docs/planning/HITL_HTTP_API_CONTRACTS.md`
  - `docs/planning/HITL_QUERY_CONTRACTS.md`
  - `docs/planning/FRONTEND_INTERACTION_RULES.md`
  - `docs/planning/FIRST_RUNTIME_SLICE.md`
  - `docs/planning/TEST_MATRIX.md`
  - `docs/status/DECISIONS_SINCE_LAST.md`
  - `docs/planning/TASK_INDEX.md`
  - `docs/status/CURRENT_FOCUS.md`

## Verification commands
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `make runtime-api`
- `pytest -q tests/runtime/test_example_document_corpus_ingress.py`
- `pytest -q tests/runtime/api/test_artifact_attachment_api.py`
- `pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `pytest -q`
- Frontend checks:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run test:run`
  - `cd frontend && npm run build`

## Acceptance criteria
- Example documents are promoted into a documented executable corpus with stable IDs and manifested seed sets.
- Corpus documents ingress through canonical artifact versioning + storage + event emission, not ad hoc fixture shortcuts.
- Artifact linkage supports human tasks, approvals, flags, and workflow-run attachment surfaces.
- CLI/API/frontend inline upload/download paths are wired to canonical artifact-backed operations.
- Frontend contract snapshots remain backend-owned and regenerated from real scenario states.
- Runtime/API tests cover ingress determinism, linkage coherence, digest/metadata round-trip, and cross-scope denial.
- Docs and repo memory are updated with no stale future-tense for implemented attachment/ingress behavior.

## Notes
- TASK-0048 is already allocated in this repository (`frontend-real-api-integration-and-board-hardening`), so this work uses the next free task ID (`TASK-0051`).
- This task is explicitly groundwork for the next sandbox/agent test slice consuming seeded corpus inputs through canonical artifact truth.
