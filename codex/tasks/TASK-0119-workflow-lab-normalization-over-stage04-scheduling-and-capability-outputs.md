---
id: TASK-0119
epic: EPIC-110
title: "Normalize Stage04, realistic scheduling, and capability outputs into Workflow Lab reports"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0118"]
risk: high
context_packs: ["codex/context/EPIC-110.md"]
patterns: ["PATTERN-003", "PATTERN-005"]
---

## Context
The repo already produces rich outputs that are ideal for Workflow Lab Phase 1: Stage04 inspection packets and pilot summaries, realistic scheduling pilot outputs, and current capability certification manifests. The smartest next move is to normalize those outputs before inventing a general experiment engine.

## Objective
Implement the first Workflow Lab normalizers and derived review packets over the outputs the repo already emits, producing stable machine-readable reports plus human review packets from the same truth.

## Non-goals
- No generalized experiment orchestration.
- No public Workflow Lab API/UI.
- No direct world execution engine yet.
- No semantic-version comparison machinery.

## Source files to read first
- Stage04 pilot services / outputs
- realistic scheduling pilot services / outputs
- current capability certification outputs
- `docs/workflow_lab/*` and `schemas/workflow_lab/*`

## Context packs / patterns to consult
- codex/context/EPIC-110.md
- PATTERN-003
- PATTERN-005

## Source files to change
- normalization modules/scripts
- report packet renderer(s)
- targeted tests and docs
- task-memory / epic/context updates

## Generated / downstream artifacts impacted
- normalized reports and review packets over existing outputs
- no changes to authoritative runtime truth

## Plan
1. Normalize weekly Stage04 outputs into `RunReport.core`.
2. Normalize realistic scheduling pilot outputs into the same contract.
3. Normalize current capability certification outputs as one normalized report per scenario row.
4. Render a derived review packet from the normalized truth and freeze behavior with tests.

## Verification
- targeted tests for normalizers/renderers
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The repo can already produce Workflow Lab reports from existing outputs.
- Both engineering-convenient (Stage04) and product-nearer (realistic scheduling/capability) outputs are covered.
- Workflow Lab becomes useful without adding a new execution platform.

## Notes / decisions
Prefer scripts or a thin package surface first; do not introduce a large `workflow_lab` runtime package unless task 0110 has already made dependency boundaries honest enough.

Implemented in TASK-0119:
- `src/onetruth/application/services/workflow_lab_normalization.py` now normalizes weekly Stage04 inspection packets, realistic schedule-planning inspection packets, and current capability certification scenarios into `workflow_lab_run_report.json`.
- The same module renders `workflow_lab_review_packet.md` from the normalized report only.
- Weekly Stage04 and realistic schedule-planning pilot suites now emit adjacent Workflow Lab artifacts per pilot and add their paths into each `pilot_runs[]` row.
- Current capability certification now emits one Workflow Lab report + review packet per scenario output directory and records those paths in `scenarios[]`.
- No `compare_report` generation, execution adapter, freshness guard, or public Workflow Lab API/UI was added.

Verification:
- `python3.11 -m pytest -q tests/runtime/contracts/test_workflow_lab_report_normalization.py`
- `python3.11 -m pytest -q tests/runtime/test_logistics_weekly_agent_pilot.py tests/runtime/test_realistic_schedule_planning_pilot.py tests/runtime/contracts/test_current_capability_certification_harness.py`
- `python3 scripts/validate_repo.py --schemas-only`
