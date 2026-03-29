---
id: TASK-0153
epic: EPIC-125
title: "Wire the daily EOS intake, draft-reporting review workpage, finalize flow, and planning feedback handoff"
status: TODO
owners: ["backend", "frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0151"]
risk: high
context_packs: ["codex/context/EPIC-125.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Why
The daily reporting lane is the authoritative source of actual-routes truth and must drive both the review workpage and future compliance inputs.

## Scope
- make the daily EOS upload task the authoritative intake for `reporting.eos_raw.workbook`
- add or expose the bounded workflow-native build from EOS raw input to `reporting.upd_draft.workbook`
- ensure the generated draft artifact opens in the existing EOD artifact-backed workpage
- add the bounded finalization path to `reporting.final_packet.workbook`
- ensure the existing reporting->planning handoff updates future actual-hours truth for compliance

## Out of scope
- finalization UX beyond the bounded operator lane
- new reporting document packet scope if workbook-first output is sufficient

## Acceptance signals
- an uploaded EOS workbook leads to a generated draft reporting artifact
- that artifact opens in the review workpage
- finalization produces the official workbook output and the planning feedback artifact
