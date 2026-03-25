---
id: TASK-0133
epic: EPIC-121
title: "Add dispatch-reporting template-pack/registry support and EOD workbook adapter round-trip tests"
status: TODO
owners: ["backend"]
reviewers: ["frontend", "qa"]
depends_on: ["TASK-0132"]
risk: high
context_packs: ["codex/context/EPIC-121.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
The first artifact-backed EOD path cannot exist truthfully unless the repo can instantiate a real `reporting.upd_draft.workbook` template and round-trip bounded edits back into workbook bytes.

Today the repo has authored `dispatch_reporting.v1` workflow/artifact contracts but no reporting template pack, and the template-registry service is still too schedule-centric.

## Objective
Add the bounded template-pack/registry/workbook-adapter foundation required for the first artifact-backed EOD slice.

## Non-goals
- No backend workpage routes yet.
- No frontend route migration yet.
- No final-packet template pack.
- No generic workbook runtime for every workflow family.
- No schedule workbook adaptation in this task.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/LOGISTICS_WORKPAGES_ARTIFACT_PATH_PLAN.md`
- `docs/workflows/dispatch_reporting/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/OPERATING_MODEL.md`
- `docs/workflows/dispatch_reporting/v1/examples/*`
- `fixtures/workflows/schedule_planning/template_registry.v1.yaml`
- `src/onetruth/application/services/template_registry.py`
- `src/onetruth/api/routes/templates.py`
- `src/onetruth/api/route_specs/templates.py`

## Source files to change
- new `fixtures/workflows/dispatch_reporting/template_pack/` files (bounded Stage03 pack)
- new `fixtures/workflows/dispatch_reporting/template_registry.v1.yaml`
- `src/onetruth/application/services/template_registry.py`
- template route/tests if needed for multi-workflow registry lookup
- new workbook adapter/materializer module(s) and tests
- docs/task-memory touched by the new template-pack truth
- the task file itself with outcomes and follow-ups

## Plan
1. Add a minimal Stage03 `reporting.upd_draft.workbook` template pack that matches the bounded workpage contract.
2. Add bounded multi-workflow registry support so reporting templates are discoverable.
3. Implement the first EOD workbook adapter/materializer seam.
4. Add round-trip tests that prove immutable workbook write safety for the bounded tables.

## Verification
- targeted template-registry tests
- targeted workbook adapter/materializer tests
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The repo can resolve a real `dispatch_reporting.v1` template for `reporting.upd_draft.workbook`.
- The first EOD workbook adapter/materializer round-trips bounded edits to workbook bytes.
- The task does not broaden into route implementation yet.

## Notes / decisions
Prefer a bounded semantic workbook over trying to mirror the raw EOS workbook. This epic is proving the artifact-backed editing loop, not spreadsheet fidelity for every legacy column/formula.
