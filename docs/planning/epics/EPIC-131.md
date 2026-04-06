# EPIC-131 - Schedule recalculation, route-demand separation, accepted navigation, and soft preferences

## Summary
Extend the weekly logistics workpage layer without collapsing distinct truths into one ambiguous editor.

This epic froze and implemented the v1 boundaries:
- `schedule-v0` = driver reassignment/on-call edits plus server recalculation only
- `route-demand-v0` = route-demand truth editor
- `driver-preferences-v0` = soft/advisory weekly snapshot
- accepted history stays separate from draft lineage

## Status
Completed on 2026-04-05.

## Delivered scope
- descriptor-backed backend workpage registry and canonical run/kind-scoped routing
- schedule preview/save with pinned dependency baselines and calculation evidence
- separate accepted-series and draft-lineage navigation for schedule artifacts
- `route-demand-v0` public run/artifact editor with schedule drift propagation
- `driver-preferences-v0` public run/artifact snapshot editor with soft advisory schedule cues
- canonical-route cutover and regression closeout

## Explicitly deferred beyond v1
- date-specific driver exception modeling
- automatic agentic rescheduling after route-demand changes
- broader feedback-driven hardening beyond the implemented v1 operator surfaces

## Dependencies
- EPIC-123
- EPIC-124
- EPIC-125
- EPIC-030

Context pack: `codex/context/EPIC-131.md`

## Tasks
- TASK-0201 - DONE
- TASK-0202 - DONE
- TASK-0203 - DONE
- TASK-0204 - DONE
- TASK-0205 - DONE
- TASK-0206 - DONE
- TASK-0207 - DONE

## Key decision
Keep schedule reassignment, route-demand truth, advisory preferences, accepted history, and draft lineage explicit and separate even when they appear in one operator module.
