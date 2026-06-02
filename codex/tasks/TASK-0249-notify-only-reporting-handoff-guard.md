---
id: TASK-0249
epic: EPIC-139
title: "Notify-only/reporting handoff guard"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0246", "TASK-0247"]
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR016` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
File-backed notify manifests; block late reporting from mutating published weekly truth; retain legacy behavior local_dev/test only if needed.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-139.md`
- `codex/context/EPIC-139.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-009 plus regression tests
- Acceptance gate: `Late reporting guard passes; replace-on-conflict disabled in shared_env production path.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Late reporting guard passes; replace-on-conflict disabled in shared_env production path.
- Review focus covered: CR-009
- Refactor focus covered: RF-011
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR016`
- Source phase: `P2 Logistics/domain production hardening`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR013;PR014`
- Recommended source branch: `production/logistics-hardening`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Notify-only target input artifacts now persist as file-backed generated JSON manifests through the canonical generated-artifact helper instead of authoritative `inmem://` handoff rows.
- Reporting-to-planning late feedback in the default/shared-env boundary profile now fails closed with `late_reporting_handoff_conflict` before replacing the existing `stage03.actual_hours_snapshot` input binding.
- Legacy merge-and-replace behavior remains available only when `ONETRUTH_API_BOUNDARY_PROFILE` is explicitly `local_dev` or `ci_test`.
- Focused verification: `PYTHONPYCACHEPREFIX=/private/tmp/kapflow-pyc pytest tests/runtime/test_logistics_handoff_runtime.py -q` passed.
- Closeout posture: `MP-PR016` is closed as notify-only/reporting handoff hardening only; it is not CAPEX production activation, deployment, or planning-cycle policy completion.
