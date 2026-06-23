---
id: TASK-0290
epic: EPIC-151
title: "Risk and CEO Transparency workflow"
status: DONE
completed_at: 2026-06-23T00:00:00Z
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0277", "TASK-0289"]
risk: high
context_packs:
  - "codex/context/EPIC-151.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `WFLOW-008` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Produce deterministic risk and CEO action snapshot with forecastability discipline.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-151.md`
- `codex/context/EPIC-151.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: not forecastable tests; CEO drilldown
- Acceptance gate: `AT-BRIDGE-008; NU-010`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: risk_state_snapshot; ceo_transparency_snapshot
- Review focus covered: no stochastic precision before validity
- Refactor focus covered: risk mapper
- Docs requirement covered: risk/CEO docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `WFLOW-008`
- Source phase: `P9 Risk`
- Source priority: `P0`
- Source area: `workflow/risk`
- Original depends_on: `WFLOW-007; ART-002`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed with planning-only workflow catalog/helper evidence:
  `docs/planning/capex_workflow_catalog/risk_ceo_transparency_workflow.yaml`
  and `onetruth.capex_platform.risk_ceo_transparency_workflow`.
- The helper requires `capex.project_state_snapshot.workflow_outputs.v1` basis, enforces same tenant/domain/project, known project-state SourceRefs, known project-state component refs, duplicate-risk prevention, deterministic severity/forecastability mapping, CEO drilldown refs, stale/missing/conflict/AI-draft propagation, and waiver caveats.
- This closeout supplied the prerequisite for later `TASK-0299` and `TASK-0659` planning closeouts, but it does not activate authored workflows, RiskSignal runtime, CEO cockpit/workpages, public routes, frontend routes, migrations, event-registry changes, official pointers, closure snapshots, external-system behavior, or CAPEX product/runtime behavior. `TASK-0539` and `TASK-0540` remain open.
