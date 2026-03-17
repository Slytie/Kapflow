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

## Current Repo Status (2026-03-14)
- Completed in this epic: `TASK-0013`, `TASK-0050`, `TASK-0052`, `TASK-0053`, `TASK-0065`, `TASK-0066`, `TASK-0069`, `TASK-0070`, `TASK-0088`, `TASK-0089`, and `TASK-0101`.
- Stage06 and weekly Stage04 now have a real attested shared-env principal seam and a bounded execution runtime, but execution command centrality still sits too close to the legacy orchestration hotspot.

## Planned next tranche in this epic
- `TASK-0105` will extract the execution/tool/policy command family so Stage06 and weekly Stage04 services stop importing execution semantics from `workflow_task_lifecycle.py`.

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
- TASK-0105
