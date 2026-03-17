---
id: TASK-0104
epic: EPIC-030
title: "Extract artifact-version and pointer-promotion mutation families"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0102"]
risk: high
context_packs: ["codex/context/EPIC-030.md", "codex/context/EPIC-040.md"]
patterns: ["PATTERN-001", "PATTERN-003"]
---

## Context
The artifact/pointer cluster is the largest remaining non-execution hotspot inside `workflow_task_lifecycle.py`. This cluster mixes:
- artifact creation and ingress
- pointer promotion
- lineage/canonical-scope helpers
- artifact download/read compatibility helpers

Because artifacts and pointers are the practical expression of one-truth officialness, this family should be explicit and isolated rather than hidden inside the legacy monolith.

## Objective
Extract artifact-version and pointer-promotion mutation families into dedicated handler modules, with shared lineage/canonical-scope helpers moved behind a narrow artifact seam.

## Non-goals
- No object-store migration.
- No transport v3 or streaming rewrite.
- No semantic changes to artifact officialness, pointer promotion, or lineage rules.
- No expansion of public ingress surface.

## Source files to read first
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/handlers/_shared/artifact_effects.py`
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/pointers.py`
- `src/onetruth/application/services/execution_evidence.py`
- `src/onetruth/infrastructure/artifacts/storage.py`
- `docs/architecture/promotion_semantics.md`
- `tests/runtime/api/test_binary_download_transport.py`

## Context packs / patterns to consult
- `codex/context/EPIC-030.md`
- `codex/context/EPIC-040.md`
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-003.md`

## Source files to change
- new `src/onetruth/application/handlers/artifacts.py`
- new `src/onetruth/application/handlers/pointers.py`
- one or more new shared artifact-lineage/canonical-scope helper modules if justified
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- direct call sites in services/routes/CLI that should consume the new modules
- import-boundary tests
- targeted artifact/pointer/runtime tests

## Generated / downstream artifacts impacted
- Task-memory and epic/context updates only.

## Plan
1. Identify the smallest coherent artifact mutation seam.
2. Move shared lineage/scope helpers out of `workflow_task_lifecycle.py`.
3. Extract pointer promotion into its own dedicated family.
4. Preserve import compatibility through thin wrappers only where required.
5. Add boundary tests so extracted artifact/pointer modules do not drift back into the legacy hotspot.

## Verification
- targeted pytest for artifact ingress/create/list/download + pointer promotion flows
- `PYTHONPATH=src pytest -q tests/contract/test_handler_import_boundaries.py`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Artifact and pointer mutation logic no longer lives primarily inside `workflow_task_lifecycle.py`.
- Shared artifact-lineage helpers have a neutral home.
- Pointer/officialness semantics remain unchanged.

## Notes / decisions
Keep the current transport model stable unless a helper move absolutely requires a small compatibility shim.
