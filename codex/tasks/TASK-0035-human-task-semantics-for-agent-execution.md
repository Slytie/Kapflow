---
id: TASK-0035
epic: EPIC-050
title: "Tighten human-task semantics for end-to-end agent execution"
status: DONE
owners:
- platform
reviewers:
- ops
- qa
- security
depends_on:
- TASK-0033
- TASK-0034
risk: high
context_packs:
- codex/context/EPIC-050.md
patterns:
- PATTERN-002
- PATTERN-007
- PATTERN-008
- PATTERN-009
---

## Context
The current human-task semantics are still too abstract for lease/concurrency implementation, and the new fully-agentive Schedule Planning objective increases the need to define how agent-owned work relates to claim, lease, escalation, and approval prep.

## Objective
Upgrade task semantics so claim/lease/escalation behavior is implementation-grade for both human-owned and agent-owned end-to-end execution.

## Non-goals
- Do not design a full workforce-management UI.
- Do not create a separate agent-task universe.
- Do not settle DB schemas here; that belongs to runtime-schema work.

## Source files to read first
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/orchestration_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `docs/planning/TEST_MATRIX.md`

## Context packs / patterns to consult
- `codex/context/EPIC-050.md`
- `PATTERN-002`
- `PATTERN-007`
- `PATTERN-008`
- `PATTERN-009`

## Source files to change
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/orchestration_semantics.md` if task transitions need clarification
- `docs/planning/TEST_MATRIX.md`

## Generated / downstream artifacts impacted
- schedule golden traces
- replay/acceptance tests
- generated runbook packs

## Plan
1. Define canonical task states and legal transitions.
2. Specify claim atomicity, idempotency, lease duration, heartbeat, and lease-expiry behavior.
3. Clarify how agent-owned task work coexists with approval prep/review tasks.
4. Add explicit event expectations for claim/lease/escalation paths.

## Verification
- One engineer can implement claim/lease logic from the doc alone.
- One QA engineer can derive concurrency tests from the doc alone.
- The fully-agentive slice still routes through canonical task objects and events.

## Acceptance criteria
- task states and transitions are explicit
- lease/heartbeat/escalation rules are implementable without guessing
- agent-owned work is defined as a mode of the same task system, not a peer runtime universe

## Notes / decisions
This task tightens behavior. Runtime schemas come later.


## Completion notes
- Completed in the repo-native semantic-closure tranche on 2026-03-02.
