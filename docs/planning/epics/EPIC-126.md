# EPIC-126 - Workpages v1 hardening and closeout

## Summary
After the first operational cadence demo is running and a real local user demo has produced feedback, harden the weekly/daily operator lane and explicitly close the first version of Workpages.

## Status
Proposed. Deferred until EPIC-125 reaches the first local demo and real feedback exists. Do not start this epic while EPIC-125 is still establishing the first running operator loop.

## Scope
### In scope
- feedback-driven UX corrections from the first local demo
- stronger regression coverage for weekly planning, manual daily replan, and daily reporting loops
- clearer operator language around draft, response, official output, delta, lineage, and stale state
- local/prod demo runbook tightening
- route/alias cleanup once canonical operator paths are proven
- explicit Workpages v1 boundary and acceptance proof

### Out of scope
- new workflow-family scope
- algorithmic live-dispatch candidate generation
- Stage06/Stage07 schedule workpage widening beyond the agreed v1 boundary
- generic email ingestion or generic spreadsheet-runtime ambitions
- broader topology changes unrelated to the first-user lane

## Dependencies
- EPIC-125 (running operator loop plus first local-demo feedback)
- EPIC-124 (stage-linked workpage route/CTA foundation)
- EPIC-100 (production-lane posture and runbook discipline)

## Recommended pattern cards (read cards first)
- `PATTERN-007`
- `PATTERN-009`

Context pack: `codex/context/EPIC-126.md`

## Current repo posture
- EPIC-125 is now active, but the local-demo milestone and continuous cadence milestone are not yet implemented.
- Hardening should consume observed operator feedback, not imagined polish work.
- This epic exists to tighten truth, regressions, language, observability, and route posture after the first real operator loop is demonstrated.

## Tasks
- TASK-0158 - TODO
- TASK-0159 - TODO
- TASK-0160 - TODO

## Key decision
Do not harden hypothetical flows. Hardening begins only after the first local operator demo and the initial production-shaped cadence milestone are real.

## Red-team question
Are we actually closing the first version of Workpages with explicit boundaries and stronger operator confidence, or are we using hardening as a way to continue widening product scope without declaring what v1 means?
