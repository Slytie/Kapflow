---
id: TASK-0081
epic: EPIC-030
title: "Split public artifact upload from local seeding via ingress descriptors"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security"]
depends_on: ["TASK-0077", "TASK-0078"]
risk: high
context_packs: ["codex/context/EPIC-030.md", "codex/context/EPIC-010.md"]
patterns: ["PATTERN-003"]
---

## Context
Public/shared HTTP and local/scenario seeding currently sit too close together in artifact ingress surfaces. The shared API needs a provenance-safe posture before write-boundary enforcement and route-boundary cleanup continue.

## Objective
Separate public artifact upload from local seeding by introducing explicit ingress descriptors so shared HTTP accepts inline request bytes only, while local/scenario seeding remains available through non-HTTP/internal paths.

## Non-goals
- No object-store migration.
- No removal of local CLI/scenario seed flows.
- No broad artifact-store redesign.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-030.md`
- `codex/context/EPIC-030.md`
- `codex/context/EPIC-010.md`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/artifacts/storage.py`

## Context packs / patterns to consult
- `codex/context/EPIC-030.md`
- `codex/context/EPIC-010.md`
- `docs/patterns/cards/PATTERN-003.md`

## Source files to change
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/artifacts/storage.py`
- `tests/runtime/api/test_artifact_attachment_api.py`
- `tests/runtime/api/test_artifact_upload_profiles.py`
- `tests/runtime/api/test_workspace_actionability.py`
- `tests/runtime/api/test_cross_scope_api_denial.py`
- `tests/runtime/test_example_document_corpus_ingress.py`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/architecture/human_task_semantics.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-030.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/status/CURRENT_FOCUS.md`
- `codex/tasks/TASK-0081-public-artifact-upload-vs-local-seeding-split.md`

## Generated / downstream artifacts impacted
- Artifact ingress/runtime API contract coverage.
- No new generated artifacts expected.

## Plan
1. Define ingress descriptors for shared/public upload versus internal/local seeding.
2. Remove caller-controlled `source_path` and storage-root selection from shared HTTP paths.
3. Preserve CLI/scenario seeding through internal adapters.
4. Add tests proving shared HTTP provenance is request-byte-owned while local seeding still works.

## Verification
- `PYTHONPATH=src pytest tests/runtime/api/test_artifact_attachment_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_artifact_upload_profiles.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_workspace_actionability.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_cross_scope_api_denial.py -q`
- `PYTHONPATH=src pytest tests/runtime/test_example_document_corpus_ingress.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Shared/public HTTP accepts inline bytes only for now.
- Local seeding remains available through non-HTTP/internal flows.
- Shared HTTP no longer exposes caller-selected server-native storage controls.
- Artifact ingress docs and tests distinguish the two paths clearly.

## Notes / decisions
- Keep any storage-root decision server-owned on shared HTTP.

## Source Files Changed
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/artifacts/storage.py`
- `tests/runtime/api/test_artifact_attachment_api.py`
- `tests/runtime/api/test_artifact_upload_profiles.py`
- `tests/runtime/api/test_workspace_actionability.py`
- `tests/runtime/api/test_cross_scope_api_denial.py`
- `tests/runtime/test_example_document_corpus_ingress.py`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/architecture/human_task_semantics.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-030.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/status/CURRENT_FOCUS.md`
- `codex/tasks/TASK-0081-public-artifact-upload-vs-local-seeding-split.md`

## Verification Run
- `PYTHONPATH=src pytest tests/runtime/api/test_artifact_attachment_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_artifact_upload_profiles.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_workspace_actionability.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_cross_scope_api_denial.py -q`
- `PYTHONPATH=src pytest tests/runtime/test_example_document_corpus_ingress.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Completion Notes
- Shared/public HTTP ingress now requires `content_base64` and rejects caller-controlled `source_path` / `storage_root`.
- CLI/scenario/internal local seeding remains on the same canonical artifact path and records normalized source-path provenance with `ingress_kind=local_source_path`.
- Shared HTTP request-byte ingress records `ingress_kind=request_bytes` and strips caller-supplied source-path provenance fields instead of persisting them.
