---
id: TASK-0378
epic: EPIC-145
title: "Fixture quarantine utility"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-145.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `RF-010` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Create utility/checks for sanitized fixture manifests and raw-data leakage scans.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-145.md`
- `codex/context/EPIC-145.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-145` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
adapter boundary creation PR + tests + docs

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: As required by quality gates: QG-06;QG-07;QG-08
- Acceptance gate: `QG-06;QG-07;QG-08`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: adapter boundary creation PR + tests + docs
- Review focus covered: primary + specialist; gates=QG-06;QG-07;QG-08
- Refactor focus covered: Use conservative refactor policy; separate pure refactor unless local/tiny/justified.
- Docs requirement covered: Update docs/templates/registers as applicable; see QUALITY_OVERLAY.
- Rollback/recovery posture recorded: Required for Tier 3+ or phase closeout; otherwise document not applicable.

## Source row mapping
- Source task ID: `RF-010`
- Source phase: `P4/P4A`
- Source priority: `P0`
- Source area: `refactoring/adapter boundary creation`
- Original depends_on: `phase preflight and safety net`
- Converted repo dependencies: none
- Source dependency notes still to satisfy: phase preflight and safety net
- Recommended source branch: `feature/capex-rf-010`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
