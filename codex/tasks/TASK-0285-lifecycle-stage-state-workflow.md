---
id: TASK-0285
epic: EPIC-143
title: "Lifecycle Stage State workflow"
status: DONE
completed_at: "2026-06-23T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0284"]
risk: medium
context_packs:
  - "codex/context/EPIC-143.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `WFLOW-003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Map project to CAPEX lifecycle navigation without waterfall truth.

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
- Source required tests: stage navigation tests
- Acceptance gate: `NU-003`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: lifecycle_stage_state; optional stage_readiness_matrix
- Review focus covered: stage not truth; derived only
- Refactor focus covered: separate navigation projection
- Docs requirement covered: lifecycle docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `WFLOW-003`
- Source phase: `P7 Workflows`
- Source priority: `P1`
- Source area: `workflow/navigation`
- Original depends_on: `WFLOW-002`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `docs/planning/capex_workflow_catalog/lifecycle_stage_state_workflow.yaml` for the `WFLOW-003` Lifecycle Stage State workflow planning contract.
- Added `onetruth.capex_platform.lifecycle_stage_state_workflow` to produce deterministic `lifecycle_stage_state`, `stage_readiness_matrix`, and `lifecycle_navigation_flags` outputs from Corpus Baseline source refs and sanitized stage observations.
- The helper treats lifecycle stages as derived navigation only: stage rows are not official truth, AI drafts cannot make a stage ready, missing evidence fails open, and conflicting evidence produces non-authoritative flags.
- Added focused lifecycle workflow unit coverage in `tests/unit/test_capex_lifecycle_stage_state_workflow.py`, plus workflow catalog contract coverage and raw-corpus marker bans.
- Closeout posture: this task closes planning/internal output-shape evidence only. It adds no authored workflow pack, workpage, public route, frontend route, closure snapshot, reviewed baseline creation, official pointer creation, waterfall gate authority, production approval, or CAPEX runtime/product activation.
