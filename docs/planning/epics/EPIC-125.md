# EPIC-125 - Operational cadence demo (weekly planning + minimal daily replan + daily reporting first-user lane)

## Summary
Build the first production-shaped logistics operator lane so the repo can run a continuous weekly planning + minimal daily manual replan + daily reporting loop with real tasks, authoritative artifacts, workpage review, and official workbook outputs.

This epic is intentionally bounded to:
- `weekly_schedule_planning.v1`
- `live_dispatch.v1` (manual delta lane only)
- `dispatch_reporting.v1`

## Status
Completed on 2026-04-06. `TASK-0151` through `TASK-0157` are now complete. `TASK-0154` is reconciled to `DONE` from existing live-dispatch runtime truth rather than newly implemented during the closeout pass, and `TASK-0157` closes the epic by aligning repo memory plus recording the first-demo feedback handoff.

Closeout note:
- EPIC-125 is now completed history rather than an active implementation epic.
- The downstream feedback-consuming work is already reflected in completed EPIC-126 cleanup history plus the landed EPIC-131, EPIC-132, EPIC-133, and EPIC-134 tranches.
- First-demo feedback themes are frozen in `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_EPIC125_CLOSEOUT_AND_FEEDBACK_NOTE.md`.

## Key goal
Prove the following operator loop end to end:

\[
I^{weekly}_{stage04-ready} \to B^{stage04}_{schedule} \to R^{manager}_{schedule} \to O^{weekly}_{published}
\]

\[
S_d \oplus \Delta^{manual}_d \to O^{dispatch}_d
\]

\[
I^{daily}_{eos} \to B^{reporting}_{draft} \to R^{manager}_{eod} \to O^{daily}_{final} \to H_{daily \to weekly}
\]

## Scope
### In scope
- bounded weekly Friday intake over Stage04-ready structured inputs
- existing Stage04 planner/agent execution path as the weekly build engine
- schedule review/edit via the existing artifact-backed schedule workpage
- bounded publish of the reviewed weekly schedule workbook
- minimal manual live-dispatch route-delta lane using existing seed activation and official delta semantics
- workflow-native daily EOS intake -> draft-reporting build -> review workpage -> finalize path
- reuse of the existing reporting->planning actual-hours feedback lane
- local FE/BE demo runbook and smoke path
- external cadence tick and single-node production-shaped deploy/runbook

### Out of scope
- algorithmic live-dispatch candidate generation or ranking
- live-dispatch workpage productization unless it becomes truly trivial
- raw route-email parsing as authoritative truth
- Stage06/Stage07 schedule workpage widening
- broad workspace modernization beyond already-landed stage-linked workpage actions
- multi-node orchestration or embedded schedulers

## High-level decisions
1. Weekly Friday machine truth is **Stage04-ready workbook input**, not the raw route email.
2. Raw route email/doc remains evidence and may be stored, but is not parser-owned truth in this epic.
3. Daily actual-routes truth remains in `dispatch_reporting.v1` through `reporting.eos_raw.workbook`.
4. The daily schedule can change through a **manual live-dispatch delta lane**, not through widened weekly schedule editing.
5. The first local demo happens **before** the continuous cadence/deploy milestone.
6. At planning time, hardening was deferred until after first-demo feedback; that follow-on path is now completed history.

## Dependencies
- EPIC-124 (stage-linked workpages and requirement-aware artifact linkage)
- EPIC-121, EPIC-122, EPIC-123 (existing workpage lanes)
- EPIC-030, EPIC-040, EPIC-100 (artifact, runtime, production-lane primitives)

## Recommended pattern cards (read cards first)
- `PATTERN-007`
- `PATTERN-009`

Context pack: `codex/context/EPIC-125.md`

## Current repo status / rationale
- EPIC-124 is complete, so the repo already has run-backed/artifact-backed workpage route truth plus bounded stage-linked CTA integration on supported workspace surfaces.
- The weekly Stage04 build/review/publish lane is now landed as the truthful weekly operator path.
- The dispatch-reporting artifact-backed EOD lane is now landed as the daily actual-routes review/finalize surface.
- The weekly-to-live handoff and live-dispatch delta authority model are now landed as the bounded day-of schedule-change seam; `TASK-0154` is reconciled to `DONE` from this existing runtime truth.
- Later feedback-consuming work is already reflected in completed EPIC-126 cleanup history plus the landed EPIC-131, EPIC-132, EPIC-133, and EPIC-134 tranches.

## Tasks
- TASK-0151 - DONE
- TASK-0152 - DONE
- TASK-0153 - DONE
- TASK-0154 - DONE
- TASK-0155 - DONE
- TASK-0156 - DONE
- TASK-0157 - DONE

## Local demo milestone
The first serious local UI/operator demo is now available after `TASK-0155`.
The repo now supports a complete single-machine weekly + daily walkthrough, including the bounded live replan lane.

## Continuous production-shaped milestone
The first continuously running environment is now supported after `TASK-0156`.
That milestone lands the external cadence invocation and single-node operator runbook posture.

## Red-team question
Are we still reusing the repo’s existing workflow/artifact/handoff/workpage model with the smallest truthful additions, or are we quietly reintroducing parser scope, live-dispatch algorithmics, or broader schedule-control ambitions before the first local operator demo has even happened?
