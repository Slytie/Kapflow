# CAPEX Product Goal And Metrics

## Status
- Status: `AUTHORITATIVE_SOURCE`
- Owner tasks: `TASK-0582`, `TASK-0583`, `TASK-0584`, `TASK-0585`, `TASK-0586`, `TASK-0587`, `TASK-0588`
- Acceptance gates: `SD-GATE-001`, `SD-GATE-002`, `SD-GATE-003`, `SD-GATE-004`, `SD-GATE-005`, `SD-GATE-006`, `SD-GATE-007`
- Activation posture: `planning_only_no_capex_activation`

This planning source records the CAPEX Product Goal, metric stack,
vertical-slice delivery posture, dependency register, risk milestone overlay,
backlog taxonomy, delivery cadence, first-90-days execution overlay, and
Definition of Ready / Done. It does not activate CAPEX runtime behavior,
public CAPEX routes, frontend CAPEX workpages, authored workflow packs, raw
corpus import, pilot readiness, production readiness, or product activation.

## Product Goal
Build a governed CAPEX evidence-to-decision workflow foundation that helps
teams identify real-project blockers, bind claims to reviewed source evidence,
route decisions through canonical tasks/approvals, and promote official
artifacts without false closure, raw-corpus leakage, or project-boundary
violations.

## Signoff Record
Repo planning acceptance for `SD-GATE-001` is recorded by this document,
`Product_Goal_Metric_Stack.csv`, the matching contract tests, and the
`TASK-0582` closeout evidence. This signoff is limited to repo planning
governance. It is not implementation approval, CAPEX runtime activation,
public route activation, migration approval, raw corpus import approval,
pilot approval, production approval, or product activation.

External business/product signoff remains required before any module can claim
market, pilot, production, or public workflow/workpage readiness.

## Metric Principles
- Optimize for governed truth, safety, and learning before throughput.
- Every flow metric must carry a truth, quality, safety, or operability
  guardrail.
- No metric may reward velocity alone.
- Metrics must distinguish observed source material, reviewed evidence,
  canonical decisions, immutable artifacts, audited pointers, and projection
  read models.
- Metrics must preserve tenant, domain, and project boundaries.
- Metrics must not depend on raw project corpus content being present in the
  repository.

## Metric Stack
The machine-readable metric stack is
`docs/planning/capex_delivery/Product_Goal_Metric_Stack.csv`.

Required categories are:

- `outcome`
- `learning`
- `flow`
- `quality`
- `operability`

## Vertical Slice Ladder
The machine-readable vertical-slice ladder is
`docs/planning/capex_delivery/Vertical_Slice_Ladder.csv`.

The first ladder spans `VS-00` through `VS-05` and is intentionally thin: each
slice must prove one end-to-end learning or safety claim with testable entry
and exit gates. The dependency register and risk milestone overlay now live in
`MASTER_Dependency_Register.csv` and `Risk_Based_Milestone_Model.csv`.

## Backlog Taxonomy
The backlog hierarchy and decomposition templates now live in
`Backlog_Taxonomy_and_Decomposition_Guide.md` and
`docs/planning/capex_delivery/templates/`. They define the one authoritative
planning hierarchy without creating a second backlog system.

## Delivery Cadence And Overlay
The delivery operating cadence now lives in
`MASTER_Delivery_Operating_Cadence.md`. The first-quarter planning overlay now
lives in `MASTER_First_90_Days_Execution_Overlay.md`. They provide lightweight
planning rhythm and range-based roadmap evidence without exact-date precision
or activation approval.

## Definition Of Ready And Done
The CAPEX task-class Definition of Ready / Done now lives in
`MASTER_Definition_of_Ready_Done.md`. The repository pull request template
contains the matching compact consistency checklist.

## Non-Activation Boundary
Closing `TASK-0582` through `TASK-0588` records planning-governance evidence
only. CAPEX activation remains blocked by source-governance, workflow/workpage,
fixture, release/capacity, storage, restore/preflight, raw-corpus, production
preflight, and production readiness gates until those gates close or receive
explicit waivers.
