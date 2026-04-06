---
id: TASK-0154
epic: EPIC-125
title: "Add the minimal manual daily-replan lane through live dispatch seed activation and official delta promotion"
status: DONE
owners: ["backend"]
reviewers: ["qa"]
depends_on: ["TASK-0151"]
risk: high
context_packs: ["codex/context/EPIC-125.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Why
The first production use case must support day-of schedule change, but only in a bounded manual way. The repo already has a live-dispatch authority model that can support this without candidate-generation algorithmics.

## Scope
- activate or resolve the correct live-dispatch run for a service day from the weekly daily seed
- require `dispatch.route_delta_intake.workbook` as the authoritative manual day-of delta input
- bind an actual-hours snapshot using already-supported kinds rather than inventing a new handoff
- create the smallest truthful review/approval/promotion path that yields `dispatch.official_replan_delta.workbook`
- expose this lane in the operator/demo story without introducing a full live-dispatch workpage unless trivial

## Out of scope
- candidate generation and ranking
- a general live-dispatch workpage surface
- wider live-dispatch productization

## Acceptance signals
- an operator can manually change the day’s schedule through the live-dispatch delta lane
- the official delta is immutable and promoted truthfully
- the weekly schedule workpage remains bounded and does not absorb day-of control

## Closeout note
`TASK-0154` is reconciled to `DONE` in `TASK-0157` from existing repo truth rather than new runtime work in the closeout pass.
The bounded manual daily-replan lane is already present in the live-dispatch runtime handlers, the weekly-first local demo smoke, and the operator/demo runbooks.
