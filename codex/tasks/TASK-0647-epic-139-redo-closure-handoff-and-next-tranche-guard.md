---
id: TASK-0647
epic: EPIC-139
title: EPIC-139 redo closure handoff and next-tranche guard
status: DONE
completed_at: "2026-06-04T12:08:56Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0646"]
risk: medium
context_packs: ["codex/context/EPIC-139.md", "codex/context/EPIC-140.md"]
patterns: ["EPIC-139 redo closure handoff", "CAPEX next-tranche guard"]
---

# TASK-0647 - EPIC-139 Redo: Closure Handoff And Next-Tranche Guard

## Why

The EPIC-139 redo package is complete after TASK-0643 through TASK-0646. This follow-up records the closure handoff so future CAPEX task selection does not reopen EPIC-139 cleanup or mistake the accepted domain-neutrality gate for CAPEX runtime activation.

## Scope

Add a repo-native closure handoff note and contract guard proving EPIC-139 stays closed as State C / repaired, while the next CAPEX planning tranche points to EPIC-140 gated project/access work.

## Out of scope

- Runtime behavior changes.
- New public HTTP routes, schemas, approval behavior, workpage behavior, or logistics activation changes.
- Rewriting old EPIC-139 task closeouts.
- Adding TASK-0647 to the TASK-0643 through TASK-0646 package reclose matrix.
- Activating CAPEX runtime/product behavior.

## Verification

- `python3.11 -m pytest -q tests/contract/test_epic139_redo_closure_handoff.py tests/contract/test_epic139_redo_reclose_matrix.py`
- `python3.11 -m pytest -q tests/contract/test_capex_epic_progress_data.py tests/contract/test_capex_v5_reconciliation.py`
- `python3.11 -m pytest -q tests/unit/test_approval_response_hooks.py tests/unit/test_workpage_descriptor_registry.py tests/unit/test_workpage_domain_registry.py`
- `python3.11 scripts/run_capex_invariant_audit.py --output-root /private/tmp/kapflow-epic139-task0647-audit --json`
- `python3.11 scripts/validate_capex_epic_progress_data.py frontend/src/data/capexEpicProgressData.json`
- `npm run test:run -- src/pages/capexEpicProgressPage.test.tsx` from `frontend/`
- `python3.11 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- EPIC-139 remains done and does not return to RED or needs-review posture.
- TASK-0643 through TASK-0647 are represented as done in the CAPEX progress surface.
- TASK-0576 remains represented as historical/reconciled evidence.
- The reclose matrix remains bounded to the package/source rows and redo package tasks TASK-0643 through TASK-0646.
- The closure handoff names EPIC-140 as the next gated CAPEX tranche and preserves the CAPEX runtime activation blocker.
- EPIC-150 dependency wording remains corrected.

## Source row mapping

- Source task ID: `E139-REDO-HANDOFF`
- Source priority: `P1`
- Source area: `closure-handoff`

## Closeout evidence

- Added `docs/planning/EPIC139_REDO_CLOSURE_HANDOFF.md` as the post-package closure handoff note.
- Added contract coverage for EPIC-139 done posture, TASK-0643 through TASK-0647 representation, TASK-0576 alias preservation, reclose-matrix bounds, EPIC-140 next-tranche posture, and EPIC-150 wording correction.
- Regenerated CAPEX progress data so TASK-0647 is represented under EPIC-139 while EPIC-139 remains done.
- Waivers: none.
