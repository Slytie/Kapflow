---
id: TASK-0287
epic: EPIC-143
title: "Assumption Closure workflow"
status: DONE
completed_at: 2026-06-23T00:00:00Z
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0284", "TASK-0286"]
risk: high
context_packs:
  - "codex/context/EPIC-143.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `WFLOW-005` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Extract supplier/counterparty assumptions and closure states with evidence or waiver.

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
- Source required tests: missing evidence; waiver; contradicted tests
- Acceptance gate: `AT-007; NEG-CLOSE-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: counterparty_assumption_register; assumption_closure_matrix; flags
- Review focus covered: AI not close; evidence-specific closure
- Refactor focus covered: closure row state machine
- Docs requirement covered: assumption docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `WFLOW-005`
- Source phase: `P7 Workflows`
- Source priority: `P0`
- Source area: `workflow/assumptions`
- Original depends_on: `WFLOW-002; WFLOW-004`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `docs/planning/capex_workflow_catalog/assumption_closure_workflow.yaml` for the `WFLOW-005` Assumption Closure workflow planning contract.
- Added `onetruth.capex_platform.assumption_closure_workflow` to produce deterministic `counterparty_assumption_register`, `assumption_closure_matrix`, and `assumption_flags` outputs from sanitized assumption observations, Corpus Baseline refs, and Governance / Commitment Chain basis.
- Evidence: Assumption Closure workflow unit tests and CAPEX workflow catalog contract tests passed on 2026-06-23.
- Closeout posture: `WFLOW-005` closes planning/internal output-shape evidence only; authored workflow pack activation, public routes, Assumption Closure workpages, physical closure snapshots, stale/reopen policy, owner-interface resolution, reviewed baseline truth, official pointer creation, and CAPEX runtime/product activation remain later gated work.
