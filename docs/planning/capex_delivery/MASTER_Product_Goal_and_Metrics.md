# CAPEX Product Goal And Metrics

## Status
- Status: `AUTHORITATIVE_SOURCE`
- Owner tasks: `TASK-0582`, `TASK-0583`
- Acceptance gates: `SD-GATE-001`, `SD-GATE-002`
- Activation posture: `planning_only_no_capex_activation`

This planning source records the CAPEX Product Goal, metric stack, and
vertical-slice delivery posture. It does not activate CAPEX runtime behavior,
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
and exit gates. The ladder is not a roadmap commitment, dependency register,
or risk milestone overlay; that follow-on work remains `TASK-0584`.

## Non-Activation Boundary
Closing `TASK-0582` and `TASK-0583` records planning-governance evidence only.
CAPEX activation remains blocked by source-governance, workflow/workpage,
fixture, release/capacity, restore/preflight, and production readiness gates
until those gates close or receive explicit waivers.
