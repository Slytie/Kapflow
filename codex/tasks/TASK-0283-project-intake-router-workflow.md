---
id: TASK-0283
epic: EPIC-143
title: "Project Intake Router workflow"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0261", "TASK-0276"]
risk: high
context_packs:
  - "codex/context/EPIC-143.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `WFLOW-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Route new/mid-project/issue/CEO entry and create intake/module activation artifacts.

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
- Source required tests: entry mode tests; mid-project K12 test
- Acceptance gate: `AT-007; NU-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: project_intake_profile; module_activation_profile; handoff_manifest
- Review focus covered: human confirms; AI draft only
- Refactor focus covered: workflow output helper
- Docs requirement covered: intake workflow docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `WFLOW-001`
- Source phase: `P7 Workflows`
- Source priority: `P0`
- Source area: `workflow`
- Original depends_on: `PROJ-001; ART-001`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Completion evidence
- Added `docs/planning/capex_workflow_catalog/project_intake_router_workflow.yaml` as the planning-only `WFLOW-001` Project Intake Router contract.
- Added `onetruth.capex_platform.project_intake_router` to build deterministic `project_intake_profile`, `module_activation_profile`, and `handoff_manifest` payloads for new-project, mid-project, issue-escalation, and CEO/sponsor entry modes.
- Enforced human-confirmed / AI-draft-only posture and sanitized context refs for the mid-project K12 fixture path without raw corpus import or project-specific file hardcoding.
- Added unit and contract coverage for entry modes, mid-project K12 sanitized refs, human confirmation, raw-context rejection, and non-activation boundaries.
