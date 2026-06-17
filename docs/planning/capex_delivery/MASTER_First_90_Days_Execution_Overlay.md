# CAPEX First 90 Days Execution Overlay

## Status
- Status: `AUTHORITATIVE_SOURCE`
- Owner task: `TASK-0587`
- Acceptance gate: `SD-GATE-006`
- Activation posture: `planning_only_no_capex_activation`

This planning source maps the first execution quarter after signoff into
ranges and evidence milestones. It provides no exact calendar dates and makes
no product, runtime, public route, workflow pack, raw corpus, pilot, or
production activation claim.

## No False Date Precision
The overlay uses relative windows instead of calendar commitments. Actual
timing must be refreshed through the 8-12 week outcome roadmap refresh rhythm
after real throughput and blocker evidence exist.

## Quarter Overlay
| Window | Planning focus | Metric refs | Slice refs | Dependency refs | Milestone refs | Evidence output |
|---|---|---|---|---|---|---|
| Window 1: align goal/metrics | goal/metrics signoff refresh and dependency board visibility | MG-OUT-001; MG-OUT-003; MG-OPS-002 | VS-00 | DEP-001; DEP-002; DEP-010 | stakeholder aligned | Product goal, metric stack, backlog, and dependency board remain aligned |
| Window 2: stabilize CI baseline | CI baseline and semantic lane confidence for the blocker-proof path | MG-QLT-001; MG-QLT-002; MG-OPS-001 | VS-00; VS-01 | DEP-003; DEP-006; DEP-010 | architecture proven | Semantic and invariant evidence remains green or records explicit blockers |
| Window 3: first slice demo | first slice demo proving blocker or learning value without demo-only success | MG-LRN-001; MG-FLW-001; MG-QLT-003 | VS-01; VS-02 | DEP-003; DEP-004; DEP-006 | architecture proven; system viable | Reviewed evidence shows what was learned and what remains blocked |
| Window 4: first MMF | first MMF candidate around procurement escalation without editable workpage status shortcuts | MG-OUT-002; MG-FLW-002; MG-LRN-001 | VS-03 | DEP-005; DEP-007; DEP-010 | system viable; business increment | Canonical task/approval routing proposal remains evidence-bound |
| Window 5: roadmap refresh | roadmap refresh across blockers, learning slices, first MMF, and validation holdout posture | MG-OUT-001; MG-LRN-002; MG-OPS-001 | VS-04; VS-05 | DEP-008; DEP-009; DEP-010 | business increment; production ready | Updated roadmap notes preserve blocked production-ready posture |

## Required Distinctions
- Blockers are explicit dependency, gate, or evidence gaps; they are not hidden
  as roadmap uncertainty.
- A learning slice answers a measured question and updates evidence; it is not
  a product-readiness claim.
- The first MMF is a planning candidate until canonical workflow/task/approval
  behavior and activation gates are separately approved.
- Roadmap refresh records ranges, confidence, and blockers; it does not create
  exact date promises.

## Non-Activation Boundary
Closing `TASK-0587` records first-quarter planning evidence only. It is not
CAPEX runtime activation, product activation, public route approval, workflow
pack activation, raw corpus import approval, pilot approval, production
approval, or production-ready evidence.
