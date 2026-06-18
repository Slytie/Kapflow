---
id: TASK-0605
epic: EPIC-152
title: "Verify semantic MR, CODEOWNERS, review-tier, and CI gates are active"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform", "sre"]
reviewers: ["security", "qa"]
depends_on: ["TASK-0589", "TASK-0590", "TASK-0591", "TASK-0592", "TASK-0593", "TASK-0594", "TASK-0595", "TASK-0596", "TASK-0597", "TASK-0598"]
risk: high
context_packs:
  - "codex/context/EPIC-152.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `PP-TASK-007` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Confirm P0/P1/P2 branch and review controls prevent unsafe CAPEX runtime changes.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-152.md`
- `codex/context/EPIC-152.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: preflight checklist; regression evidence; CI gate evidence; data leak scan; restore rehearsal as applicable
- Acceptance gate: `PROD-PRE-G09`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Verify semantic MR, CODEOWNERS, review-tier, and CI gates are active
- Review focus covered: evidence completeness; no waiver without owner/reason/expiry; no production activation from draft artifacts
- Refactor focus covered: none; preflight is evidence review, not broad implementation refactor
- Docs requirement covered: MASTER_Production_Preflight_Review.md; go/no-go memo
- Rollback/recovery posture recorded: no-go or conditional go; deactivate feature gates; preserve evidence and waiver trail

## Source row mapping
- Source task ID: `PP-TASK-007`
- Source phase: `P15 Capacity, backup/restore, and controlled pilot readiness`
- Source priority: `P0`
- Source area: `production-preflight`
- Original depends_on: `TP-TASK-001..TP-TASK-010; P0 blocker remediation; release/migration/activation governance`
- Source-only dependency notes: `P0 blocker remediation; release/migration/activation governance`
- Recommended source branch: `release-candidate/* or activation/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `docs/planning/capex_production_preflight/SEMANTIC_REVIEW_CI_GATE_REVIEW.yaml` as no-go / blocked review evidence for `PP-TASK-007` and `PROD-PRE-G09`.
- The review covers repo CODEOWNERS entries, `make capex-semantic-tests`, the GitHub Actions CAPEX semantic lane, the CAPEX invariant audit, semantic-review planning evidence, documented CI expectations, and review-tier expectations.
- Hosted branch-protection proof, required-check enforcement evidence, semantic MR gate logs, review-tier enforcement proof, CAPEX runtime-change CI pass records, and explicit gate waiver evidence remain missing and blocking.
- Updated the master production-preflight review so `PROD-PRE-G09` is reviewed but remains `no_go_blocked_pending_evidence`.
- Closeout posture: review evidence only. No hosted CI enforcement claim, branch-protection claim, review-tier approval, waiver approval, production-preflight pass, pilot readiness, public route, workflow pack activation, CAPEX runtime activation, or CAPEX product activation is added.
