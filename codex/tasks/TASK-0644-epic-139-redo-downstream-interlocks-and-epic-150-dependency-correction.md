---
id: TASK-0644
epic: EPIC-139
title: EPIC-139 redo downstream interlocks and EPIC-150 dependency correction
status: DONE
completed_at: "2026-06-04T11:21:06Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0643"]
risk: high
context_packs: ["codex/context/EPIC-139.md", "codex/context/EPIC-150.md"]
patterns: ["EPIC-139 redo control plane", "EPIC-150 dependency correction"]
---

# TASK-0644 - EPIC-139 Redo: Downstream Interlocks And EPIC-150 Wording

## Why

The EPIC-139 redo package found that downstream CAPEX epics could still look selectable while EPIC-139 was RED, and EPIC-150 mislabeled EPIC-139 as artifact/blob custody and auth-before-read.

## Scope

Add downstream progress interlocks for EPIC-143, EPIC-150, and EPIC-151 while EPIC-139 remains needs-review, and correct EPIC-150 dependency wording so EPIC-139 means domain-boundary cleanup and approval/workpage neutrality.

## Out of scope

- Runtime approval/workpage neutrality repairs already tracked by `TASK-0643`.
- Final clean Python 3.11 / Node 20 supported-environment acceptance.
- Rewriting old EPIC-139 task closeouts; they remain historical evidence.

## Verification

- `python3.11 scripts/validate_capex_epic_progress_data.py frontend/src/data/capexEpicProgressData.json`
- `python3.11 -m pytest -q tests/contract/test_capex_epic_progress_data.py`
- `npm run test:run -- src/pages/capexEpicProgressPage.test.tsx`
- `python3.11 scripts/run_capex_invariant_audit.py --output-root /private/tmp/kapflow-epic139-task0644-audit --json`
- `python3.11 scripts/validate_repo.py`

## Acceptance criteria

- EPIC-139 remains not-done while the redo review gate is active.
- `TASK-0643` remains present as the active needs-review marker.
- `TASK-0576` remains represented as historical/reconciled EPIC-139 evidence.
- EPIC-143, EPIC-150, and EPIC-151 display as blocked or needs-review while EPIC-139 is RED.
- EPIC-150 no longer describes EPIC-139 as artifact/blob custody and auth-before-read.

## Source row mapping

- Source task ID: `E139-REDO-005; E139-REDO-006`
- Source priority: `P1`
- Source area: `control-plane/docs`

## Closeout evidence

- Added downstream EPIC progress interlocks for EPIC-143, EPIC-150, and EPIC-151.
- Corrected EPIC-150 dependency and context wording to distinguish EPIC-139 domain-boundary neutrality from artifact/blob auth-before-read and EPIC-141 SourceRef work.
- Added contract coverage for the EPIC-139 RED control-plane state and forbidden EPIC-150 dependency wording.
