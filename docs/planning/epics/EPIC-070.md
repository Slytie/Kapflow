# EPIC-070 - Automation sandbox baseline (tool execution gating)

## Summary
Define the minimum sandbox and tool-gating posture for Stage 4.

## Why this epic exists (risk retired)
Keeps agentic execution inside policy, scope, and approval constraints.

## Scope
### In scope
- tool-plane posture
- out-of-plan deny-by-default
- transcript-as-evidence rule
- approval-critical projection safety hooks

### Out of scope
- general self-modifying method runtime

## Dependencies
- EPIC-060
- EPIC-025

## Recommended pattern cards (read cards first)
- `PATTERN-005`
- `PATTERN-006`

Context pack: `codex/context/EPIC-070.md`

Also see `docs/patterns/PATTERN_INDEX.yaml` for the full tagged library.

## Tasks
- TASK-0013

## Current Repo Status (2026-03-17)
- Completed in this epic: `TASK-0013`, `TASK-0050`, `TASK-0052`, `TASK-0053`, `TASK-0065`, `TASK-0066`, `TASK-0069`, `TASK-0070`, `TASK-0088`, `TASK-0089`, `TASK-0101`, and `TASK-0105`.
- Stage06 and weekly Stage04 now have a dedicated execution-runtime handler seam in `src/onetruth/application/handlers/execution_runtime.py`.
- Execution/tool/policy mutation callers now import that runtime seam directly, while `workflow_task_lifecycle.py` stays import-compatible through thin wrappers.

## Latest completed tranche in this epic
- `TASK-0105` extracted the execution/tool/policy command family without reopening policy semantics, trust profiles, or Stage04/Stage06 runtime behavior.

## Queued Tasks
- TASK-0013
- TASK-0050
- TASK-0052
- TASK-0053
- TASK-0065
- TASK-0066
- TASK-0069
- TASK-0070
- TASK-0088
- TASK-0089
- TASK-0101
