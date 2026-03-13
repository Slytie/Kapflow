---
id: TASK-0080
epic: EPIC-060
title: "Enforce capability decisions at the write boundary"
status: TODO
owners: ["platform"]
reviewers: ["qa", "security"]
depends_on: ["TASK-0079"]
risk: high
context_packs: ["codex/context/EPIC-060.md", "codex/context/EPIC-050.md", "codex/context/EPIC-030.md", "codex/context/EPIC-010.md"]
patterns: ["PATTERN-002", "PATTERN-005"]
---

## Context
Once read-side actionability speaks the frozen capability vocabulary, the write boundary needs to enforce the same decisions so denied actions do not mutate canonical state or append authoritative events.

## Objective
Apply the shared capability decisions at the write boundary for claim/complete/review, approval respond, flag transition, and artifact upload/attach paths, while keeping denial semantics explicit and side-effect free.

## Non-goals
- No hotspot extraction in this task.
- No capability-lattice redesign.
- No flattening of collaboration/upload semantics if they are intentionally broader than claim/execute.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-060.md`
- `codex/context/EPIC-060.md`
- `codex/context/EPIC-050.md`
- `codex/context/EPIC-030.md`
- `codex/context/EPIC-010.md`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/services/capabilities/*.py`
- `src/onetruth/api/errors.py`
- `tests/runtime/api/test_human_task_claim_via_api.py`
- `tests/runtime/api/test_approval_respond_via_api.py`
- `tests/runtime/api/test_workspace_actionability.py`

## Context packs / patterns to consult
- `codex/context/EPIC-060.md`
- `codex/context/EPIC-050.md`
- `codex/context/EPIC-030.md`
- `codex/context/EPIC-010.md`
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-005.md`

## Source files to change
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/api/errors.py`
- `src/onetruth/application/services/capabilities/*.py`
- `tests/runtime/api/test_human_task_claim_via_api.py`
- `tests/runtime/api/test_approval_respond_via_api.py`
- `tests/runtime/api/test_flag_transition_via_api.py`
- `tests/runtime/api/test_artifact_upload_profiles.py`
- `tests/security/test_write_path_capability_enforcement.py`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-060.md`
- `codex/tasks/TASK-0080-write-boundary-capability-enforcement.md`

## Generated / downstream artifacts impacted
- Mutation denial/error semantics and security coverage.

## Plan
1. Identify every mutation path that must consume shared capability decisions.
2. Make denied writes explicit and side-effect free.
3. Add focused runtime/security tests proving denied requests leave no canonical row or event changes behind.
4. Leave hotspot extraction for later once invariants are stable.

## Verification
- `PYTHONPATH=src pytest tests/runtime/api/test_human_task_claim_via_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_approval_respond_via_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_flag_transition_via_api.py -q`
- `PYTHONPATH=src pytest tests/security/test_write_path_capability_enforcement.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Read-side and write-side now speak the same capability vocabulary.
- Denied writes append no canonical events and mutate no current-state rows.
- Error categories are honest enough to distinguish forbidden from conflict paths.
- Hotspot extraction remains out of scope.

## Notes / decisions
- This task hardens enforcement only after `TASK-0077` and `TASK-0079` freeze semantics and shared decision primitives.
