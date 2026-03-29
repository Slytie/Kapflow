---
id: TASK-0155
epic: EPIC-125
title: "Add the local FE/BE demo runbook, seeded operator smoke path, and demo entrypoints for the first user test"
status: TODO
owners: ["frontend", "docs"]
reviewers: ["qa"]
depends_on: ["TASK-0152", "TASK-0153", "TASK-0154"]
risk: medium
context_packs: ["codex/context/EPIC-125.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Why
The first serious local FE/BE demo should happen before cadence automation and before hardening. This task creates the runbook and operator path for that demo.

## Scope
- document how to run backend and frontend locally for the operational lane
- add or update seeded demo data / demo entrypoints needed to walk the weekly + daily loop locally
- document the exact click path and required uploads for the first operator demo
- add a compact smoke path proving the local loop is runnable by a human tester
- explicitly mark this as the start point for UI/user feedback collection

## Out of scope
- external cadence automation
- production deployment wiring
- broad UX hardening

## Acceptance signals
- a developer or SME can bring FE and BE up locally and walk the intended operator flow
- the runbook clearly says when local demoing should start
- feedback capture is expected and explicit
