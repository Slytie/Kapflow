---
id: TASK-0079
epic: EPIC-060
title: "Introduce capability-decision primitives for read-side actionability"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security"]
depends_on: ["TASK-0077", "TASK-0078"]
risk: high
context_packs: ["codex/context/EPIC-060.md", "codex/context/EPIC-050.md", "codex/context/EPIC-010.md"]
patterns: ["PATTERN-002", "PATTERN-005"]
---

## Context
Read-side actionability currently computes available actions from local logic that does not yet share a single capability vocabulary with the planned write-side enforcement. The truth-alignment tranche needs a small reusable decision layer before mutating handlers.

## Objective
Introduce small shared capability-decision primitives on the read side so actionability projections use one runtime vocabulary with structured reason codes.

## Non-goals
- No write-path behavior changes in this task.
- No giant cross-cutting authz package.
- No API response redesign beyond what the frozen semantics require.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-060.md`
- `codex/context/EPIC-060.md`
- `codex/context/EPIC-050.md`
- `codex/context/EPIC-010.md`
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/flag_model.md`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `tests/runtime/api/test_workspace_actionability.py`

## Context packs / patterns to consult
- `codex/context/EPIC-060.md`
- `codex/context/EPIC-050.md`
- `codex/context/EPIC-010.md`
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-005.md`

## Source files to change
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/services/capabilities/*.py`
- `tests/runtime/api/test_workspace_actionability.py`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-060.md`
- `codex/tasks/TASK-0079-capability-decision-primitives-for-read-side-actionability.md`

## Generated / downstream artifacts impacted
- Read-side actionability payloads and reason-code coverage.

## Plan
1. Define a tiny shared principal/capability-decision vocabulary.
2. Keep capability logic close to aggregate semantics rather than centralizing everything into one hotspot.
3. Migrate workspace actionability to use shared decisions with stable response shapes where possible.
4. Add structured reason-code tests before later write-path parity work.

## Verification
- `PYTHONPATH=src pytest tests/runtime/api/test_workspace_actionability.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Read-side actionability consumes shared capability decisions.
- Reason codes are structured and reusable by later write-path checks.
- Behavior remains aligned with the semantics frozen in `TASK-0077`.
- No write-side enforcement lands yet.

## Notes / decisions
- Keep the new seam intentionally small so it does not become the next god module.

## Source Files Changed
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/services/capabilities/__init__.py`
- `src/onetruth/application/services/capabilities/shared.py`
- `src/onetruth/application/services/capabilities/tasks.py`
- `src/onetruth/application/services/capabilities/approvals.py`
- `src/onetruth/application/services/capabilities/flags.py`
- `src/onetruth/application/services/capabilities/artifacts.py`
- `tests/unit/test_capability_decisions.py`
- `tests/runtime/api/test_workspace_actionability.py`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-060.md`
- `codex/tasks/TASK-0079-capability-decision-primitives-for-read-side-actionability.md`

## Verification Run
- `PYTHONPATH=src pytest tests/unit/test_capability_decisions.py -q`
- `PYTHONPATH=src pytest tests/contract/test_capability_matrix.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_workspace_actionability.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_logistics_three_workflow_story_endpoint.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Completion Notes
- Read-side actionability now projects shared per-aggregate capability decisions instead of embedding all role, assignee, policy, and upload logic in one stringly adapter.
- `task_requirements.py` now emits structured blocker entries alongside the legacy `blocking_reason_codes`, and `task_actionability.py` preserves the existing HTTP payload shape by projecting those structured reasons back to the legacy codes.
- Write-path enforcement is still intentionally deferred to `TASK-0080`, upload-boundary cleanup remains in `TASK-0081`, and broader read-model cleanup remains in `TASK-0083`.
