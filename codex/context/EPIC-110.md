# EPIC-110 Context Pack — Workflow Lab (thin, non-authoritative candidate-evaluation lane)

**Purpose (why you might open this):**
- You are planning or implementing the thin Workflow Lab lane for candidate workflow/process/task evaluation.
- You need to know what the lab may compare, what it must never become, and which current repo outputs should be normalized first.
- You are deciding whether a candidate change is an execution variant or a semantic/versioned change.

## Non-negotiable invariants to keep in mind
- Workflow Lab is **non-authoritative**: it produces evidence about kernel behavior, not production truth.
- The healthy promotion relationship is `lab -> gate -> prod`, not direct mutation from lab into production.
- Early Workflow Lab should focus on **execution variants under fixed semantics**.
- Semantic changes belong to workflow/version/release evolution until explicit coexistence support is proven.
- Prod and lab must be separate environments with separate state; tenant/domain separation inside one deployment is not enough.
- Keep Workflow Lab off the public/UI critical path at first.

## Contracts / docs to treat as authoritative
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- `docs/planning/epics/EPIC-110.md`
- `docs/workflow_lab/README.md`
- `docs/workflow_lab/AUTHORITY_BOUNDARY.md`
- `docs/workflow_lab/PHASED_PLAN.md`
- `docs/workflow_lab/SCHEMA_PACK.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
- `docs/workflows/logistics_ops_family/v1/README.md`
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `src/onetruth/infrastructure/definitions/control_layer.py`
- `src/onetruth/application/services/logistics_weekly_agent_pilot.py`
- `src/onetruth/application/services/realistic_schedule_planning_pilot.py`
- `src/onetruth/application/services/current_capability_certification.py`
- `src/onetruth/application/services/execution_evidence.py`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-003.md`
- `docs/patterns/cards/PATTERN-005.md`

## Required test coverage (tests-as-spec)
- doc contract coverage for Workflow Lab Phase 0 boundary language
- schema validation for Workflow Lab report/freshness contracts
- normalization tests over existing Stage04 / scheduling / certification outputs
- readiness-gate checks and release-mediated promotion docs/tests where applicable
- later, freshness-guard and adapter tests only after G1 is met

## Current Repo Status (2026-03-18 implementation pass)
- `docs/workflow_lab/` now exists as a thin Phase 0 doc tree.
- The thin Workflow Lab core schema pack now exists under `schemas/workflow_lab/`.
- There is still no `src/onetruth/workflow_lab/` package, which keeps Workflow Lab off the runtime surface for now.
- The repo already emits rich raw material for Phase 1 normalization:
  - Stage04 inspection packets and pilot summaries
  - realistic scheduling pilot outputs
  - current capability certification outputs
  - runtime workspace/export bundles
- The next queued gap is TASK-0119 normalization over those outputs; heavy Workflow Lab execution/comparison work remains gated on G1/G2.

## Planned task order inside this epic
1. `TASK-0117`
2. `TASK-0118`
3. `TASK-0119`
4. `TASK-0120`
5. `TASK-0121` (gated on G1)
6. `TASK-0122` (gated on G2)

## Red-team questions for future runs
- Are we creating a second semantics compiler by convenience?
- Are we comparing semantic changes as if they were merely execution variants?
- Are we trying to build a public Workflow Lab surface before internal normalization and release gating prove useful?
- Are we materializing worlds directly from production state instead of through a redaction/materialization step?
