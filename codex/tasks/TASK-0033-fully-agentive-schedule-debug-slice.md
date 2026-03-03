---
id: TASK-0033
epic: EPIC-005
title: "Specify the fully-agentive Schedule Planning debug slice"
status: DONE
owners:
- platform
- ops
reviewers:
- security
- qa
depends_on:
- TASK-0016
- TASK-0018
- TASK-0021
risk: high
context_packs: []
patterns:
- PATTERN-001
- PATTERN-003
---

## Context
Stage 4 has pivoted to Schedule Planning as the primary runtime/debug wedge. The team wants an end-to-end debug path where agents do the work for every in-scope stage, but that must not create a second agent-only authority path.

## Objective
Define the fully-agentive Schedule Planning slice so agent-owned work, approvals, and artifact promotions still travel through the canonical workflow/task/approval/event substrate.

## Non-goals
- Do not remove support for human execution.
- Do not loosen approval or pointer rules.
- Do not invent a transcript-centric state machine.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/STAGE4_PLAN.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml`
- `docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/planning/TEST_MATRIX.md`

## Context packs / patterns to consult
- `PATTERN-001`
- `PATTERN-003`

## Source files to change
- `docs/planning/STAGE4_PLAN.md`
- `docs/planning/TEST_STRATEGY.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `docs/workflows/schedule_planning/v1/OPERATING_MODEL.md` if role/approval notes need to be sharpened
- architecture docs only if canonical runtime semantics must change

## Generated / downstream artifacts impacted
- Schedule Planning golden traces
- approval packets / live ops packets
- generated runbook packs
- generated CompanyOS IR

## Plan
1. Define what "agents do the work for every task" means at the level of task ownership, approvals, and official state transitions.
2. Specify how designated agent principals map onto existing Schedule Planning roles.
3. Ensure the acceptance/test docs prove the fully-agentive path without creating agent-only authoritative state.
4. Record any authority-chain implications before implementation planning proceeds.

## Verification
- Planning docs and Schedule Planning acceptance criteria agree on the fully-agentive objective.
- No updated document implies a second approval model or second event system.
- Reviewers can trace how Stage06/Stage07 approvals still behave under the debug slice.

## Acceptance criteria
- the fully-agentive Schedule Planning debug slice is explicit, bounded, and testable
- designated agent principals are described in terms of the existing canonical task/approval model
- no source doc implies agent-only authoritative state

## Notes / decisions
The target is not "humans removed". The target is "whole flow debuggable without bypassing the one-truth system."


## Completion notes
- Completed in the repo-native semantic-closure tranche on 2026-03-02.
