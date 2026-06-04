---
id: TASK-0645
epic: EPIC-139
title: EPIC-139 redo final supported-environment acceptance
status: DONE
completed_at: "2026-06-04T11:37:57Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0643", "TASK-0644"]
risk: high
context_packs: ["codex/context/EPIC-139.md", "codex/context/EPIC-150.md"]
patterns: ["EPIC-139 redo final acceptance", "supported environment gate"]
---

# TASK-0645 - EPIC-139 Redo: Final Supported-Environment Acceptance

## Why

The EPIC-139 redo package required one final acceptance pass after the neutral-default repair and downstream interlock/doc correction. This task records the supported Python 3.11 / Node 20 evidence needed before EPIC-139 can return to green.

## Scope

Run the final acceptance gate for TASK-0643 and TASK-0644, classify the repaired source state, and update the CAPEX progress/control plane only if the gate passes.

## Out of scope

- Additional runtime refactors beyond failures uncovered by the gate.
- New public HTTP routes, schemas, or plugin framework shape.
- Rewriting historical EPIC-139 task closeouts.
- Activating CAPEX runtime/product behavior.

## Verification

- `python3.11 --version`
- `node --version`
- `python3.11 -m pytest -q tests/unit/test_approval_response_hooks.py`
- `python3.11 -m pytest -q tests/unit/test_workpage_descriptor_registry.py tests/unit/test_workpage_domain_registry.py`
- `python3.11 -m pytest -q tests/runtime/api/test_weekly_publish_loop_api.py::test_weekly_publish_approval_auto_publishes_reviewed_latest_draft tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py::test_dispatch_reporting_happy_path_builds_review_finalizes_and_handoffs`
- `python3.11 scripts/run_capex_invariant_audit.py --output-root /private/tmp/kapflow-epic139-task0645-audit --json`
- `python3.11 -m pytest -q tests/contract/test_capex_invariant_audit.py`
- `python3.11 scripts/validate_capex_epic_progress_data.py frontend/src/data/capexEpicProgressData.json`
- `python3.11 -m pytest -q tests/contract/test_capex_epic_progress_data.py`
- `python3.11 scripts/validate_repo.py`
- `npm ci` from `frontend/`
- `npm run test:run -- src/pages/capexEpicProgressPage.test.tsx` from `frontend/`
- `git diff --check`

## Acceptance criteria

- Source state is classified as accepted/repaired after the original State B finding: platform defaults are neutral and logistics activation is explicit.
- Approval default hooks are empty, and non-logistics approval responses have no logistics effects.
- Workpage default registries are empty, and default lookup cannot resolve logistics workpages or actions.
- Explicit logistics activation still publishes weekly schedules and finalizes dispatch reporting.
- CAPEX invariant audit passes current source and has contract coverage for old bad patterns.
- EPIC-139 progress/control-plane truth is green/done, while historical EPIC-139 closeouts remain represented.
- EPIC-150 dependency wording remains corrected.
- Final validation runs under Python 3.11 and Node 20.

## Source row mapping

- Source task ID: `E139-REDO-007`
- Source priority: `P1`
- Source area: `final-acceptance`

## Closeout evidence

- Source-state classification: State C / repaired and accepted after the redo package's State B finding.
- Environment evidence: Python 3.11.14 and Node v20.20.0.
- Approval neutrality evidence: default approval hooks are empty; explicit logistics approval activation remains covered by regression tests.
- Workpage neutrality evidence: default descriptor/action registries are empty; logistics workpages/actions resolve only through explicit logistics registries.
- Logistics regression evidence: weekly publish and dispatch reporting finalize flows pass through explicit activation.
- Invariant audit evidence: `/private/tmp/kapflow-epic139-task0645-audit` reports 12 hard gates passed, 0 hard-gate failures, and 3 known gaps.
- Control-plane evidence: TASK-0643, TASK-0644, and TASK-0645 are done; EPIC-139 is no longer held RED by redo-specific overrides; TASK-0576 remains historical/reconciled evidence.
- Waivers: none.
