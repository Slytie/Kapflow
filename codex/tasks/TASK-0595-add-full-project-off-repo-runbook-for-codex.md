---
id: TASK-0595
epic: EPIC-148
title: "Add full-project off-repo runbook for Codex"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["qa"]
reviewers: ["platform", "architect"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-148.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `TP-TASK-007` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Tell Codex how to mount/process full corpora without committing data.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-148.md`
- `codex/context/EPIC-148.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: fixture-manifest validation; no-raw-data scan; cross-project invariant checks
- Acceptance gate: `TP-G01..TP-G12 as applicable`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Add full-project off-repo runbook for Codex
- Review focus covered: test data governance; no raw corpus leakage; no project-specific hardcoding
- Refactor focus covered: keep fixture/test utilities reusable across K12, K3, and blind validation
- Docs requirement covered: update three-project testing strategy and runbook
- Rollback/recovery posture recorded: remove fixture release; keep raw data quarantined; record waiver if gate cannot pass

## Source row mapping
- Source task ID: `TP-TASK-007`
- Source phase: `P14A Three-project testing ladder and blind validation readiness`
- Source priority: `P0`
- Source area: `testing/EPIC-148`
- Original depends_on: `P0 blockers; fixture governance; no-raw-data policy`
- Source-only dependency notes: `P0 blockers; fixture governance; no-raw-data policy`
- Recommended source branch: `capex-fixture/* or lab/capex-agent-tasks for agent-only work`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `docs/planning/capex_three_project_validation/OFF_REPO_FULL_CORPUS_RUNBOOK.yaml` as planning evidence for `TP-TASK-007`.
- The runbook records repo-clean preflight, operator-owned quarantine, read-only raw-corpus mount, sanitized output directory, aggregate-only reports, leak scan before repo copy, reviewed repo copy, teardown, and rollback/remediation controls.
- The runbook records capacity and restore placeholders as `blocked_pending_evidence`, maps `TP-G01`, `TP-G10`, `TP-G11`, `TP-G12`, `PROD-PRE-G06`, and `PROD-PRE-G07`, and does not claim full-corpus execution or gate closure.
- Added contract coverage in `tests/contract/test_capex_real_project_acceptance.py` for workflow steps, capacity/restore placeholders, raw-data boundary, gate refs, and non-activation posture.
- Closeout posture: planning evidence only. No full-corpus run, raw corpus import, fixture release approval, `TP-G10` pass claim, public route, workflow pack activation, CAPEX runtime activation, CAPEX product activation, pilot readiness, or production-preflight approval is added.
