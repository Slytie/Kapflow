# Prompt for TASK-0081 — Split public artifact upload from local seeding via ingress descriptors

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Split public artifact upload from local seeding using explicit ingress descriptors so public HTTP stops accepting server-owned path controls.

## Prerequisites
- Depends on TASK-0077. Do not start coding if that dependency is incomplete or semantically unresolved.
- Depends on TASK-0078. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[public\ provenance = f(request\ bytes),\ \text{not}\ f(server\ path)\]

## Non-negotiable constraints
- Public/shared HTTP accepts inline bytes only for now (`content_base64`).
- Local seeding remains available only through non-HTTP/internal adapters.
- Storage-root selection stays server-owned on shared HTTP.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0081`: **Split public artifact upload from local seeding via ingress descriptors**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0081-public-artifact-upload-vs-local-seeding-split.md
- docs/planning/epics/EPIC-030.md
- codex/context/EPIC-030.md
- codex/context/EPIC-010.md
- `docs/patterns/cards/PATTERN-003.md`
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/artifacts/storage.py`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`

### What to figure out before coding
- Design the ingress descriptors needed to separate shared/public upload from internal local seeding.
- Identify every HTTP adapter that still accepts `source_path` or caller-chosen `storage_root`.
- Plan how CLI/scenario seeding stays available without leaking server-native storage decisions back through public APIs.

### Red-team checks
- Do not break local CLI/scenario seed flows just because public HTTP is being hardened.
- Do not leave `file://` or similar backend-native storage details exposed in shared API responses unless you can re-justify them explicitly.
- Do not turn this into an object-store migration.

### Output required from Ask mode
- A short diagnosis of the current state of this task surface.
- A proposed change set in dependency order.
- The boundary/profile split you are going to encode and the trust assumptions on each side.
- Exact files to change and why.
- The smallest tests that should fail first and then pass.
- Red-team risks and how you will avoid them.
- A smallness check explaining why this still fits one bounded Codex task.

### Stop conditions
- If the task is larger than one bounded tranche, split the follow-on work explicitly instead of silently expanding scope.
- If semantics are still ambiguous, propose the minimal docs/tests-as-spec change needed before any handler/runtime edits.
- If you find a dependency is not actually complete, say so and stop rather than coding on sand.

## Code mode prompt

Use this section only **after** the Ask-mode plan for `TASK-0081` has been reviewed and approved.

You are resuming `TASK-0081` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0081-public-artifact-upload-vs-local-seeding-split.md
- docs/planning/epics/EPIC-030.md
- codex/context/EPIC-030.md
- codex/context/EPIC-010.md
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/artifacts/storage.py`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/artifacts/storage.py`
- `tests/runtime/api/test_artifact_upload_profiles.py` (new)
- `tests/runtime/test_artifact_ingress_cli.py` (new or extend existing)
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-030.md`
- `codex/tasks/TASK-0081-public-artifact-upload-vs-local-seeding-split.md`

### Verification to run
- `PYTHONPATH=src pytest tests/runtime/api/test_artifact_upload_profiles.py -q`
- `PYTHONPATH=src pytest tests/runtime -k artifact -q`
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
