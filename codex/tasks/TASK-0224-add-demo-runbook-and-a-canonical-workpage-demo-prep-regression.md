---
id: TASK-0224
epic: EPIC-134
title: "Add the demo runbook and a canonical workpage demo-prep regression"
status: TODO
owners: ["architect", "qa"]
reviewers: ["pm"]
depends_on: ["TASK-0223"]
risk: low
context_packs:
  - "codex/context/EPIC-134.md"
  - "codex/context/WORKPAGE_DEMO_GAP_FINDINGS_2026-04-06.md"
patterns: ["docs-as-truth"]
---

## Why
A prep script without a documented startup and walkthrough still leaves too much room for operator error. The repo needs one short runbook and one regression that proves the prep contract stays honest.

## Scope
- add a concise runbook describing:
  - required toolchain versions
  - backend startup
  - frontend startup
  - scaffold seed vs workpage demo-prep distinction
  - exact prep command
  - exact canonical URLs to validate
  - what is intentionally not pre-seeded, for example multi-week accepted history
- add a regression test that executes the new prep script or service and verifies the resulting canonical workpage routes return expected contracts
- keep the validation route-focused and lightweight; do not build a large frontend automation layer for this tranche

## Suggested runbook structure
1. clone / install / doctor
2. init db
3. run `scripts/run_logistics_local_demo.py` or let the prep script do it implicitly
4. run `scripts/run_logistics_workpage_demo_prep.py`
5. start backend
6. start frontend
7. open the canonical URLs from the output JSON
8. recommended walkthrough order:
   - schedule landing
   - schedule draft artifact
   - route-demand landing/artifact
   - driver-preferences landing/artifact
   - reporting EOD landing

## Out of scope
- turning the story shell into the primary validation surface
- adding demo-only UI affordances
- broad documentation cleanup unrelated to the demo path

## Verification
- `PYTHONPATH=src pytest -q tests/runtime/api/test_logistics_workpage_demo_prep.py`
- `python scripts/run_logistics_workpage_demo_prep.py --help`
- `rg -n "run_logistics_workpage_demo_prep|schedule_workpage_url|route_demand_workpage_url|driver_preferences_workpage_url" docs scripts tests`

## Outcome
The repo contains one short, production-shaped, low-friction demo path that validates the canonical workpages and stays covered by regression tests.
