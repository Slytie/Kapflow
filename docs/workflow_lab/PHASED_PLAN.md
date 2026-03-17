# Workflow Lab Phased Plan

This doc recaps the current thin-lab posture already established in planning.

## Phase 0 / B0
- docs only
- authority boundary
- concepts and anti-patterns
- phased plan and readiness gates
- no runtime package required unless it stays dependency-light

## Phase 1 / B1
Normalize evidence the repo already knows how to produce:
- weekly Stage04 inspection packets and pilot summaries
- realistic scheduling pilot outputs
- current capability certification outputs
- selected runtime workspace/export bundles when sanitized-world inputs are useful later

The next queued Workflow Lab tasks are:
- `TASK-0118`
- `TASK-0119`

## Later gated phases
- `TASK-0121` stays gated on `G1`
- `TASK-0122` stays gated on `G2`

### G1 recap
Do not start the first true execution-layer work until:
1. production is deployed through the official release path
2. frontend identity is server-derived in `shared_env`
3. `local_dev` non-loopback bind is blocked
4. prod and lab are separate environments with separate state
5. backup/restore/rollback have been rehearsed with real evidence
6. basic observability exists

### G2 recap
Do not start worlds/compare/semantic-version work until:
1. at least one user is stable in production
2. there have been one or two clean production release cycles
3. lab reports are already useful in practice
4. there is repeated demand for repeatable candidate comparison
5. there is an explicit workflow-version coexistence strategy if semantic promotion is going to be routine

## Ongoing guardrails
- keep Workflow Lab off the public/UI critical path at first
- keep the lab non-authoritative
- keep the default promotion model release-mediated
- treat execution variants and semantic/version changes as different classes of change
