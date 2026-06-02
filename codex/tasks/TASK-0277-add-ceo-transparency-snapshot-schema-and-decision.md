---
id: TASK-0277
epic: EPIC-151
title: "Add ceo_transparency_snapshot schema and decision"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0276"]
risk: high
context_packs:
  - "codex/context/EPIC-151.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ART-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
CEO-facing snapshot distinct from internal risk_state_snapshot.

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
- Source required tests: forecastability/no false precision tests
- Acceptance gate: `AT-CEO-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: capex.ceo_transparency_snapshot.v1.json
- Review focus covered: CEO output source refs; not raw AI
- Refactor focus covered: risk output mapper
- Docs requirement covered: CEO transparency docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `ART-002`
- Source phase: `P6/P9 Risk`
- Source priority: `P0`
- Source area: `schemas/risk`
- Original depends_on: `ART-001`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
