---
id: TASK-0028
epic: EPIC-040
title: Translate the runtime object model into an implementation plan
status: DONE
owners:
- platform
reviewers:
- security
- ops
- qa
depends_on:
- TASK-0023
- TASK-0036
risk: high
context_packs:
- codex/context/EPIC-040.md
patterns:
- PATTERN-001
- PATTERN-002
- PATTERN-003
- PATTERN-004
---

## Context
The runtime object model and schemas were in place, but a fresh coding agent still had to guess the implementation stack, repo layout, persistence strategy, and first code slice. That ambiguity was the last major blocker before real runtime work.

## Objective
Turn the runtime model and runtime schemas into concrete Stage 4 implementation guidance: chosen architecture, package layout, persistence model, state-machine boundaries, and first coding tranche.

## Non-goals
- Do not implement runtime services yet.
- Do not introduce an external workflow engine or a second durable workflow-definition system.
- Do not split into microservices before the canonical substrate and Schedule Planning wedge are proven.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/STAGE4_PLAN.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/architecture/orchestration_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/human_task_semantics.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `schemas/runtime/*.schema.json`

## Context packs / patterns to consult
- `codex/context/EPIC-040.md`
- `PATTERN-001`
- `PATTERN-002`
- `PATTERN-003`
- `PATTERN-004`

## Source files to change
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/adr/ADR-003-stage4-runtime-architecture.md`
- routing/status docs if the chosen runtime architecture becomes authoritative

## Generated / downstream artifacts impacted
- compiled `ExecutionSpec`
- generated runbook packs
- projection/render outputs
- future CompanyOS IR

## Plan
1. Choose the concrete Stage 4 runtime architecture that best preserves the one-truth authority model.
2. Map canonical runtime objects to tables, handlers, workers, and package boundaries.
3. Define the first coding slice so the first PR creates the right scaffold in the right places.
4. Record the decision in an ADR and update routing docs so fresh-session Codex runs start from the same plan.

## Verification
- `docs/planning/RUNTIME_BOOTSTRAP.md` explicitly names the stack, persistence model, and repo layout.
- `docs/planning/FIRST_RUNTIME_SLICE.md` explicitly tells a fresh agent what to write first and where it should live.
- No updated doc introduces a second event store, second approval system, or second workflow-definition surface.
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`

## Acceptance criteria
- one run model and one approval model remain intact in the proposed implementation
- the chosen runtime stack and repo layout are explicit
- tables, APIs/handlers, and state-machine boundaries are concrete enough that implementation can start without guessing
- the first implementation slice is explicit and Schedule Planning-first

## Notes / decisions
The chosen implementation is a Python modular monolith with PostgreSQL current-state tables plus append-only `timeline_events`, pluggable object storage for immutable artifacts, and background workers for decider/reconciliation/projections/export. `timeline_events` doubles as the outbox substrate for derived consumers.

## Completion notes
- Completed on 2026-03-03 by adding `docs/planning/RUNTIME_BOOTSTRAP.md`, `docs/planning/FIRST_RUNTIME_SLICE.md`, and `docs/adr/ADR-003-stage4-runtime-architecture.md`.
