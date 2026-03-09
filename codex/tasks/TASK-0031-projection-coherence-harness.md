---
id: TASK-0031
epic: EPIC-060
title: Design the projection coherence harness for approval-critical packets
status: DONE
owners:
- platform
- security
reviewers:
- ops
- qa
depends_on:
- TASK-0012
- TASK-0024
- TASK-0028
risk: high
context_packs:
- codex/context/EPIC-060.md
patterns:
- PATTERN-002
- PATTERN-005
- PATTERN-008
---

## Context
Approval packets and live ops packets are explicitly projections, not authoritative state. The missing piece is the coherence harness that says which canonical fields must match authoritative evidence, when projection drift is visible, and when an approval-critical packet must block rather than render misleadingly.

## Objective
Define the projection coherence harness for Stage 4 approval-critical packets and live operations views.

## Non-goals
- Do not turn projections into a second source of truth.
- Do not design a full UI framework.
- Do not hide coherence problems in logs only.

## Source files to read first
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml`
- `docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `schemas/runtime/projection.schema.json`
- `schemas/runtime/approval.schema.json`

## Context packs / patterns to consult
- `codex/context/EPIC-060.md`
- `PATTERN-002`
- `PATTERN-005`
- `PATTERN-008`

## Source files to change
- `docs/planning/PROJECTION_COHERENCE_HARNESS.md` (new)
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
- `docs/architecture/approval_model.md` if packet-blocking rules need to become architectural
- `schemas/runtime/projection.schema.json` if new coherence enums/statuses are required

## Generated / downstream artifacts impacted
- Stage06 publish packet
- Stage07 replan packet
- Stage07 live ops packet
- approval review exports and decision logs

## Plan
1. Enumerate projection kinds that matter in Stage 4.
2. Define canonical fields each projection must preserve from authoritative source.
3. Define coherence-check execution, visible failure modes, and block/allow rules.
4. Tie the design to tests and emitted events (`projection.rendered`, `projection.coherence_failed`).

## Verification
- every approval-critical packet has an explicit canonical-field checklist
- coherence failure behavior is explicit (block, warn, or degrade visible)
- the design preserves the rule that projections are regenerable and non-authoritative
- tests are named for drifted packet, stale packet, and missing-source scenarios

## Acceptance criteria
- projection coherence rules are concrete enough for implementation
- approval-critical packet blocking rules are explicit
- required events, tests, and source lineage fields are named
- no projection becomes the place where official business state is decided

## Notes / decisions
The harness should make it obvious when a packet is stale or incoherent, not merely “best effort.”

## Completion Notes (2026-03-08)
- Authored `docs/planning/PROJECTION_COHERENCE_HARNESS.md` with canonical field checklists, block-vs-warn policy, and required `projection.coherence_failed` evidence behavior.
- Implemented runtime coherence behavior and coverage in `tests/runtime/test_projection_coherence.py`.
- Landed visible coherence handling for:
  - `workspace_official_outputs`
  - `workspace_export_bundle`
  - `handoff_operator_view`
