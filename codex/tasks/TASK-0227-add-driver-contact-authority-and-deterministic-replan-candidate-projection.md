---
id: TASK-0227
epic: EPIC-135
title: "Add driver-contact authority and deterministic replan candidate/compliance projection"
status: TODO
owners: ["backend"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0225"]
risk: high
context_packs:
  - "codex/context/EPIC-135.md"
  - "codex/context/UNIFIED_REPLAN_ARCHITECTURE_FINDINGS_2026-04-25.md"
patterns: []
---

## Why
The popup needs ranked replacements, all other eligible drivers, blocked candidates, phone numbers, and compliance context. The repo already has deterministic schedule-control logic, but it has no canonical contact authority and no popup-ready candidate projection.

## Objective
Add a separate contact authority and extend deterministic schedule-control output so the popup can show actionable candidate recommendations without browser-side ranking.

## Non-goals
- a contact-management UI
- turning preferences into hard constraints
- agent-runtime work
- official delta promotion

## Source files to read first
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/weekly_schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/live_dispatch/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `src/onetruth/application/services/schedule_control/candidate_generation.py`
- `src/onetruth/application/services/schedule_control/scoring.py`
- `src/onetruth/application/services/schedule_control/validation.py`
- `src/onetruth/application/services/schedule_control/workpage_calculations.py`
- `src/onetruth/application/services/logistics_workpages_shared.py`
- `docs/workflows/weekly_schedule_planning/v1/examples/driver_capabilities_actual_ops_lab_v4.yaml`

## Source files to change
- weekly/live workflow contracts, artifact maps, and execution-profile guidance
- schedule-control projection helpers
- artifact kind / dataset key registries and read-side contact helpers
- workpage contract builders
- demo fixtures/seeds and contract snapshots
- relevant backend tests

## Plan
1. Introduce mirrored canonical read-side contact workbooks:
   - `planning.driver_contact_directory.workbook`
   - `dispatch.driver_contact_directory.workbook`
2. Author those inputs in the weekly/live workflow contracts and artifact maps, and record in execution-profile guidance that contact truth is for operator contact projection only, not hard eligibility.
3. Seed and resolve those artifacts separately from driver capabilities and approved availability.
4. Extend deterministic replan projection to return:
   - top 3 hard-pass candidates
   - all remaining hard-pass candidates
   - blocked candidates with hard-filter reasons
   - projected checks and coverage impact
5. Include per-candidate metrics:
   - phone number
   - on-call posture
   - availability state
   - preference state
   - rolling-7 projected hours
   - remaining headroom
   - hard-filter reasons
6. Preserve the repo rule that on-call priority affects ranking only after hard-filter pass.

## Verification
- backend unit/contract tests for deterministic candidate grouping and phone-number projection
- tests proving contacts stay separate from driver capabilities truth
- demo/fixture regression showing candidate projection can render phone numbers and compliance metrics

## Acceptance criteria
- The repo has mirrored weekly/live contact bridge inputs for driver phone numbers.
- The popup contract can expose top candidates, other candidates, blocked candidates, and projected checks without browser-side ranking.
- Preferences remain advisory and do not become hard eligibility gates in this tranche.
