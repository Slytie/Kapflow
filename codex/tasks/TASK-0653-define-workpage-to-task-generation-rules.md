---
id: TASK-0653
epic: EPIC-144
title: "Define workpage-to-task generation rules"
status: TODO
owners: ["frontend", "capex-architecture"]
reviewers: ["backend", "qa", "capex-sme"]
depends_on: ["TASK-0567"]
risk: high
context_packs: ["codex/context/EPIC-144.md"]
patterns: ["SME-RP acceptance conditions", "workpage projection boundary"]
---

# TASK-0653 - Define Workpage-To-Task Generation Rules

## Why

CAPEX workpages may expose blockers and command surfaces, but they cannot become official state stores. Missing evidence, responsibility, revision, cost, safety, and contradiction cases need canonical task routing.

## Scope

Define workpage-to-task generation rules for real-project blocker cases.

- Route blocker handling through canonical tasks, flags, approvals, artifacts, and events.
- State explicitly that workpages never set official project status.
- Bind activation to `SME-RP-G005`.

## Out of scope

- Public CAPEX workpage API implementation.
- Frontend route implementation.
- Generic status commands.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-144 and `SME-RP-G005`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Workpage commands create canonical work where needed.
- Workpage projections cannot set closure, evidence sufficiency, commercial status, or official project status.
- Stale command guards remain required before any mutation.

## Source row mapping

- Source task ID: `TASK-0630`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G005`
- Source conditions: `7-A2;7-A3`
