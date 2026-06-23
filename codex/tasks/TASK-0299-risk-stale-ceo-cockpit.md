---
id: TASK-0299
epic: EPIC-144
title: "Risk / Stale / CEO Cockpit"
status: DONE
completed_at: 2026-06-23T00:00:00Z
owners: ["frontend"]
reviewers: ["platform", "qa"]
depends_on: ["TASK-0290"]
risk: high
context_packs:
  - "codex/context/EPIC-144.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `WP-009` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
CEO-facing risk, blockers, forecastability, management actions with drill-down.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-144.md`
- `codex/context/EPIC-144.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: not forecastable; drilldown tests
- Acceptance gate: `AT-CEO-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: risk cockpit
- Review focus covered: no false precision; source refs visible
- Refactor focus covered: risk cards/components
- Docs requirement covered: CEO cockpit docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `WP-009`
- Source phase: `P9 Risk`
- Source priority: `P0`
- Source area: `frontend/workpage`
- Original depends_on: `WFLOW-008`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closeout evidence added `docs/planning/capex_workpage_catalog/risk_stale_ceo_cockpit_workpage.yaml` and `onetruth.capex_platform.risk_stale_ceo_cockpit_workpage` for a planning-only cockpit projection from `capex.risk_ceo_transparency.workflow_outputs.v1`.
- The helper produces deterministic risk cards, stale/blocker cards, CEO management-action cards, SourceRef drilldowns, forecastability display, canonical bytes/digests, and task-specific error codes while rejecting raw content, bad refs, duplicate card IDs, and false precision when not forecastable.
- This closeout does not activate public CAPEX routes, frontend routes, a CEO cockpit runtime, runtime risk engine, authored workflow packs, official pointers, closure snapshots, migrations, event-registry changes, raw corpus import, or CAPEX product/runtime behavior.
