# EPIC-125 - Operational cadence demo (weekly planning + minimal daily replan + daily reporting first-user lane)

## Summary
Build the first production-shaped logistics operator lane so the repo can run a continuous weekly planning + minimal daily manual replan + daily reporting loop with real tasks, authoritative artifacts, workpage review, and official workbook outputs.

This epic is intentionally bounded to:
- `weekly_schedule_planning.v1`
- `live_dispatch.v1` (manual delta lane only)
- `dispatch_reporting.v1`

## Status
Active on 2026-03-29. `TASK-0151` is complete and freezes the operator-loop contract, authoritative-input posture, and milestone boundaries. `TASK-0152` is now complete and lands the weekly Friday intake -> Stage04 build -> review -> publish loop. `TASK-0153` is now complete and lands the daily EOS intake -> deterministic draft build -> EOD review -> finalize -> planning feedback loop. `TASK-0155` is now complete and lands the weekly-first local demo seed, runbook, and entry surface. `TASK-0156` is now complete and lands the external cadence tick plus single-node continuous operator runbook. The remaining cadence backlog is `TASK-0154` and `TASK-0157`, but EPIC-131 is now the next selected workpages priority.

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
6. Hardening remains deferred to EPIC-126.

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
- The existing weekly Stage04 build/review lane is already the lowest-risk weekly operator path; the immediate gap is truthful weekly intake and official weekly publish wiring.
- The existing dispatch-reporting artifact-backed EOD lane is already the right review surface for daily actual-routes truth.
- The existing weekly-to-live handoff and live-dispatch delta authority model already provide the smallest bounded day-of schedule-change seam.
- `TASK-0151` now freezes the first running-operator posture so later EPIC-125 tasks do not drift into raw-email parser scope, live-dispatch algorithmics, embedded scheduling, or early EPIC-126 hardening.

## Tasks
- TASK-0151 - DONE
- TASK-0152 - DONE
- TASK-0153 - DONE
- TASK-0154 - TODO
- TASK-0155 - DONE
- TASK-0156 - DONE
- TASK-0157 - TODO

## Local demo milestone
The first serious local UI/operator demo is now available after `TASK-0155`.
The repo now supports a complete single-machine weekly + daily walkthrough even though the external cadence tick is not yet wired.

## Continuous production-shaped milestone
The first continuously running environment is now supported after `TASK-0156`.
That milestone lands the external cadence invocation and single-node operator runbook posture.

## Red-team question
Are we still reusing the repo’s existing workflow/artifact/handoff/workpage model with the smallest truthful additions, or are we quietly reintroducing parser scope, live-dispatch algorithmics, or broader schedule-control ambitions before the first local operator demo has even happened?
