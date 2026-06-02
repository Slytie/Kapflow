---
id: TASK-0247
epic: EPIC-139
title: "Weekly seed materialization hardening"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0238", "TASK-0239", "TASK-0246"]
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR014` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Weekly published artifact -> seven file-backed seed manifests/artifacts with created events, provenance, EdgeExecution.

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
- Source required tests: CR-008 plus regression tests
- Acceptance gate: `Seven seed artifacts created once; no inmem authoritative seed; EdgeExecution validated.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Seven seed artifacts created once; no inmem authoritative seed; EdgeExecution validated.
- Review focus covered: CR-008
- Refactor focus covered: RF-010
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR014`
- Source phase: `P2 Logistics/domain production hardening`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR013;PR005;PR006`
- Recommended source branch: `production/logistics-hardening`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Weekly seed materialization now creates one canonical generated seed manifest artifact per service date through `persist_generated_artifact_effects`.
- Full-week materialization creates seven file-backed `planning.daily_dispatch_seed.workbook` artifacts with byte sizes, content digests, `artifact.version.created` events, parent/provenance links, and matching EdgeExecution rows.
- Seed artifact content excludes volatile materialization idempotency keys, so logical retries reuse the same seed artifact without digest conflicts or duplicate seed events.
- Focused verification passed on 2026-06-02: `tests/unit/test_runtime_effect_helpers.py` and `tests/runtime/test_logistics_handoff_runtime.py`.
