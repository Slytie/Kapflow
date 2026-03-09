# STAGE4_PLAN.md - Vertical Slice MVP

## Stage goal
Ship one end-to-end Schedule Planning vertical slice that proves:
- durable orchestration semantics
- fully-agentive execution across every in-scope stage so the whole flow can be debugged end-to-end
- explicit conditional follow-on task spawning for dynamic review/rework/info loops
- immutable artifact versions + promotion pointers + lineage
- additive schedule-delta semantics for live-day replans
- complete audit timeline with strong links
- basic operability
- minimum sandbox posture for any automation/tool execution

At the same time, preserve Payroll as a secondary reference workflow for:
- linear approval-heavy semantics
- lock/finalize governance
- cross-checking that the shared one-truth substrate does not become Schedule-only
- keeping the full authored workflow surface complete even when it is not the primary runtime focus

And freeze the one-truth merger so the repo does not split into separate contract and agentic source systems.

## Authoritative design stance
Stage 4 treats the following as the complete hand-authored semantics surface per workflow:
- workflow contract
- artifact map
- acceptance criteria
- operating model
- decision catalog
- execution profile

Shared schema and vocabulary contracts that now gate this surface:
- governance vocabulary
- permissions vocabulary
- tool-class registry
- workflow-pack schemas
- runtime object schemas
- event payload schemas

CompanyOS IR, runbook packs, tool matrices, approval logs, and future execution specs are downstream of that surface.

## Primary workflow: Schedule Planning
- Partition key: `ScheduleDateID`
- Scope: `(tenant_id, domain_id)`
- Primary runtime/debug wedge
- Temporal posture: service interval + logical date + service timezone are pinned, not inferred loosely from a date string

In-scope end-to-end stages:
- Stage03 Demand Forecast & Coverage
- Stage04 Capacity Plan
- Stage05 Draft Schedule & Constraint Triage
- Stage06 Supervisor Review & Publish
- Stage07 Intraday Exception Control

### Stage 4 debug objective for the primary workflow
In designated debug tenants, Stage 4 should be able to exercise the entire in-scope Schedule Planning path with agents doing the work for every task. This means:
- each in-scope stage can be driven by agent-owned task work,
- approvals still use the canonical approval object model,
- designated agent principals may respond within the same approval pathway when the debug scenario requires it,
- official state still changes only through canonical events, artifact versions, and pointer promotions.

This objective exists so the team can debug the whole orchestration path without waiting on humans. It is not permission to create a second agent-only runtime model.

## Secondary workflow: Payroll
- Partition key: `PayPeriodID`
- Scope: `(tenant_id, domain_id)`
- Secondary reference workflow for linear approvals and lock/finalize semantics
- Payroll traces are still placeholder-only; do not treat Payroll as the default replay wedge for runtime work

## Current repo state
The repo now includes:
- a canonical governance vocabulary
- full workflow-pack validation
- explicit Schedule Planning temporal and activation semantics
- tightened human-task and control-plane semantics
- runtime object schemas
- event payload schemas
- Schedule Planning golden traces covering happy path, fully-agentive flow, drift, lease expiry, degraded mode, and cross-scope denial
- a concrete runtime bootstrap (`docs/planning/RUNTIME_BOOTSTRAP.md`)
- an ordered first implementation slice (`docs/planning/FIRST_RUNTIME_SLICE.md`)
- a planned step-run scenario harness for agent-executed flows (`docs/planning/STEP_RUN_SCENARIO_HARNESS.md`)
- an accepted runtime-architecture ADR (`docs/adr/ADR-003-stage4-runtime-architecture.md`)

## Runtime architecture now chosen
Stage 4 will be instantiated as:
- a Python modular monolith under `src/onetruth/`
- PostgreSQL for canonical current-state rows plus append-only `timeline_events`
- a pluggable object-store adapter for immutable artifact contents
- background workers for decider/reconciliation, lease expiry, projections, exports, and later generator work

Important constraint:
- `timeline_events` is the canonical event substrate and also the relay surface for derived consumers
- do **not** add an external workflow engine or second durable workflow history for Stage 4

## Historical build order (milestones now landed through TASK-0032)
1. Map the typed event registry to runtime emission points and tests (`TASK-0029`)
2. Design the step-run scenario harness for agent-executed flows and conditional task spawning (`TASK-0039`)
3. Translate promotion semantics and schedule delta rules into artifact-store design (`TASK-0030`)
4. Design and land the projection coherence harness (`TASK-0031`) - completed
5. Prototype generator for runbook packs and CompanyOS IR (`TASK-0032`)
6. Then proceed with runtime implementation work in this order:
   - repo scaffold under `src/onetruth/`, `tests/runtime/`, and `alembic/`
   - canonical event store and core current-state tables
   - Schedule Planning Stage03 -> Stage06 path through approval, conditional follow-on review/info loops, and base-pointer promotion
   - step-run scenario harness where an agent executes each step and spawned children are asserted via timeline evidence
   - Schedule Planning Stage07 issue loop with flags, lease recovery, bounded child-task spawning, and delta promotion
   - execution session / tool policy gate wiring
   - projection coherence worker and generated derivative prototype

## Exit criteria for implementation-bootstrap readiness
- A fresh agent can tell that Schedule Planning is the primary runtime/debug wedge and Payroll is the secondary reference workflow.
- The fully-agentive debug objective is explicit and does not imply a second truth system.
- The chosen runtime stack, package layout, persistence model, and first code slice are explicit.
- Workflow packs, schemas, traces, and planning docs validate for cross-file drift.
- Runtime work can start without inventing actor vocab, approval outcomes, time-window semantics, control-plane behavior, code locations, or event/pointer semantics.

## Red-team deltas that remain mandatory
- fail-open means exports / projections may degrade, not truth persistence
- promotion drift must remain visible
- claim / lease semantics must prevent silent stalls
- background consumers and derived stores must enforce scope
- Schedule Planning replans must remain additive deltas
- generated artifacts must never outrank their source files
- the fully-agentive debug slice must still use the canonical task / approval / event / pointer path
