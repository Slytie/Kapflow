---
id: TASK-0566
epic: EPIC-143
title: "Implement workflow handoff manifest contract"
status: DONE
completed_at: 2026-06-08T00:00:00Z
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-143.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `NU-CB-P0-006` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Define handoff manifest with artifact versions, pointer generations, validation summaries, basis freshness.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-143.md`
- `codex/context/EPIC-143.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CB2-T010; handoff stale-basis tests
- Acceptance gate: `NU-GATE-006`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: HandoffManifest schema; handoff validation guard; task/workpage handoff bindings
- Review focus covered: No silent workflow state handoff; exact basis required
- Refactor focus covered: Additive schema and validation helper
- Docs requirement covered: Update workflow family docs
- Rollback/recovery posture recorded: Block downstream workflow activation on missing handoff manifest

## Source row mapping
- Source task ID: `NU-CB-P0-006`
- Source phase: `P6/P7 workflow substrate`
- Source priority: `P0`
- Source area: `capex/workflow`
- Original depends_on: `W2/W4/W5; sourceRef resolver`
- Source-only dependency notes: `W2/W4/W5; sourceRef resolver`
- Recommended source branch: `capex/handoff-manifest`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `schemas/runtime/capex_workflow_handoff_manifest.schema.json` and internal service `onetruth.capex_platform.workflow_handoffs` with `HandoffManifest`, validation results, and fail-closed `require_valid_handoff_manifest(...)`.
- Handoff validation now requires exact source workflow scope, artifact version basis, pointer generation basis, meaningful `source_occurrence:*` refs, validation summaries, closure evaluation refs, current closure snapshot refs, and task/workpage handoff bindings.
- Missing manifests, pointer generation drift, unresolved SourceRefs, stale closure snapshots, failed closure basis, missing validation summaries, and scope mismatches are rejected before downstream handoff trust.
- No CAPEX workflow runtime activation, HTTP routes, frontend routes, physical handoff table, or raw K12/K3/blind corpus material was introduced.
- Evidence: `PYTHONPATH=src python3.11 -m pytest -q tests/unit/test_capex_workflow_handoff_manifest.py tests/contract/test_capex_workflow_handoff_manifest_schema.py` passed on 2026-06-08.
