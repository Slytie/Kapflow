---
id: TASK-0123
epic: EPIC-120
title: "Freeze logistics workpages v0 scope, product brief, and repo-native example fixtures"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: []
risk: medium
context_packs: ["codex/context/EPIC-120.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
Workpages were previously discussed as generic artifact-linked editors, but the safer first move is a frontend-first logistics slice grounded in existing normalized examples and the current `/demo/logistics` shell.

## Objective
Freeze the first workpage package in repo-native form so future Codex runs can start from current repo truth instead of scattered chat context or external attachments.

## Non-goals
- No FE implementation yet.
- No backend workpage API.
- No artifact projection/materialization code.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/FRONTEND_ARCHITECTURE.md`
- `docs/planning/FRONTEND_INTERACTION_RULES.md`
- `docs/workflows/weekly_schedule_planning/v1/examples/*`
- `docs/workflows/dispatch_reporting/v1/examples/*`

## Context packs / patterns to consult
- `codex/context/EPIC-120.md`
- `PATTERN-007`
- `PATTERN-009`

## Source files changed
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_V0_PLAN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_V0_PRODUCT_BRIEF.md`
- `docs/planning/epics/EPIC-120.md`
- `codex/context/EPIC-120.md`
- `fixtures/logistics/workpages/*`
- `docs/workflows/dispatch_reporting/v1/examples/*`
- routing/status/task-memory docs

## Verification
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- A fresh Codex run can explain what the first two workpages are and where FE work should start.
- The repo has explicit task and context routing for the workpage tranche.
- External source-material insight needed for v0 is distilled into repo-native planning docs.

## Notes / decisions
- Workpage fixtures are human-authored planning/test fixtures. They are intentionally distinct from backend-owned `fixtures/frontend_contracts/` snapshots.
