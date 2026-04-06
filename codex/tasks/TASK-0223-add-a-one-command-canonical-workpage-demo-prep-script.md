---
id: TASK-0223
epic: EPIC-134
title: "Add a one-command canonical workpage demo-prep script"
status: DONE
owners: ["backend"]
reviewers: ["pm", "qa"]
depends_on: ["TASK-0221", "TASK-0222"]
risk: medium
context_packs:
  - "codex/context/EPIC-134.md"
  - "codex/context/WORKPAGE_DEMO_GAP_FINDINGS_2026-04-06.md"
patterns: ["one-truth", "idempotency"]
---

## Why
Today the demo-ready workpage state is assembled implicitly by a smoke test. We need one user-facing prep command that yields canonical truth objects and prints the canonical workpage URLs.

From first principles, the prep operator should construct `S_demo` without introducing a second truth system:

`S_demo = T_demo(S_seed)`

where `T_demo` only uses existing canonical handlers, services, and commands.

## Scope
- add a new script, e.g. `scripts/run_logistics_workpage_demo_prep.py`
- reuse the existing weekly-first scaffold seed as the starting point
- materialize the minimum canonical weekly inputs needed for the workpages
- build the Stage04 outputs through the deterministic schedule-control path
- optionally create a driver-preferences snapshot (default: yes)
- emit a stable JSON summary containing canonical URLs, artifact IDs, and workflow run IDs
- keep the script idempotent for the same db/run identifiers
- keep the default path deterministic and not dependent on OpenAI

## Required output shape
The script output should include at least:
- `recommended_story_url`
- `weekly_run_id`
- `reporting_run_id`
- `weekly_workspace_url`
- `schedule_workpage_url`
- `schedule_artifact_url`
- `route_demand_workpage_url`
- `route_demand_artifact_url`
- `driver_preferences_workpage_url`
- `driver_preferences_artifact_url` if created
- `eod_workpage_url`
- `output_json_path` when requested

## Preferred implementation notes
- prefer deterministic Stage04 build for demo prep rather than a live OpenAI dependency
- do not import test-only helpers from `tests/`
- do not add a new public API just for the demo
- if helpful, factor a tiny service module under `src/onetruth/application/services/` and keep the script thin

## Out of scope
- multi-week accepted-history seeding
- route-demand drift auto-seeding
- live-dispatch or reporting completion beyond what is needed for the demo shell context
- frontend changes beyond what is needed to consume the printed URLs/documentation

## Likely touch points
- `scripts/run_logistics_local_demo.py`
- `scripts/run_logistics_workpage_demo_prep.py` (new)
- `src/onetruth/application/services/logistics_local_demo.py`
- a small new service file if needed
- existing Stage04 deterministic build handlers/services

## Verification
- run the new script end to end against a fresh sqlite db
- verify returned URLs resolve via runtime API/frontend once services are started
- `PYTHONPATH=src pytest -q tests/runtime/api/test_logistics_workpage_demo_prep.py` (new)

## Outcome
An operator can prepare demo-ready workpage state with one command and immediately open the canonical routes.
