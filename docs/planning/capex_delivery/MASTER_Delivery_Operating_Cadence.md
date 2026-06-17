# CAPEX Delivery Operating Cadence

## Status
- Status: `AUTHORITATIVE_SOURCE`
- Owner task: `TASK-0586`
- Acceptance gate: `SD-GATE-005`
- Activation posture: `planning_only_no_capex_activation`

This planning source defines the lightweight operating cadence for CAPEX
delivery governance. It does not activate CAPEX runtime behavior, public
routes, frontend workpages, workflow packs, raw corpus import, pilot readiness,
production readiness, or product use.

## Cadence Principles
- Lean governance first: every meeting must produce a repo-native decision
  record, task update, dependency update, or explicit no-change note.
- No meeting bloat: a duplicate meeting is invalid unless it replaces an
  existing rhythm with a recorded owner and sunset reason.
- Cadence decisions must preserve the one authoritative backlog hierarchy from
  `Backlog_Taxonomy_and_Decomposition_Guide.md`.
- Cadence output is planning evidence only; it cannot approve runtime,
  product, public route, workflow pack, raw corpus, pilot, or production
  activation.

## Cadence Rhythm Register
| Rhythm | Frequency | Owner | Inputs | Outputs | Decision record |
|---|---|---|---|---|---|
| weekly refinement | Weekly while CAPEX planning work is active | platform | Product goal metrics, open task briefs, dependency register, slice ladder | Ready near-term story candidates, unresolved blockers, updated task evidence notes | Update task files or `docs/status/DECISIONS_SINCE_LAST.md` when scope or sequencing changes |
| three-amigos | Weekly for near-term stories only | platform + architect + QA | Backlog template, metric refs, slice refs, source/evidence refs, acceptance scenarios | Vertical and testable story shape, missing evidence list, test approach | Story/task closeout evidence or explicit test-gap note |
| monthly dependency/risk review | Monthly while dependency rows remain open or blocked | platform | `MASTER_Dependency_Register.csv`, `Risk_Based_Milestone_Model.csv`, open CAPEX risks | Owner/needed-by/mitigation changes, blocked milestone review, escalation candidates | Dependency register patch or no-change note |
| demo/review | At slice exit or material planning milestone | product + platform | Completed slice evidence, semantic test output, invariant/audit status | Review verdict, learning notes, next blocker or MMF candidate | Delivery-governance note in intake/status docs |
| 8-12 week outcome roadmap refresh | Every 8-12 weeks of active CAPEX planning or after material blocker change | product | Product goal, metric stack, first-90-days overlay, dependency/risk state | Outcome roadmap adjustment without false date precision | Roadmap overlay update or explicit no-change note |

## Acceptance Guardrails
- Refinement must not create a second backlog system.
- Three-amigos review must not accept demo-only success criteria.
- Dependency/risk review must keep production-ready blocked while restore,
  capacity, release, storage, raw-corpus, and production-preflight gates are
  unresolved.
- Demo/review must inspect repo-native evidence, not screenshots or raw corpus
  material.
- Outcome roadmap refresh must use ranges and confidence notes, not exact
  delivery dates without evidence.

## Non-Activation Boundary
Closing `TASK-0586` records cadence planning evidence only. It is not CAPEX
runtime activation, product activation, public route approval, workflow pack
activation, raw corpus import approval, pilot approval, production approval, or
delivery readiness approval.
