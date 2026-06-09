---
id: TASK-0651
epic: EPIC-142
title: "Harden evidence status vocabulary and transition rules"
status: DONE
completed_at: "2026-06-09T09:31:48Z"
owners: ["capex-architecture", "qa"]
reviewers: ["backend", "capex-sme", "security"]
depends_on: ["TASK-0565"]
risk: high
context_packs: ["codex/context/EPIC-142.md"]
patterns: ["SME-RP acceptance conditions", "evidence status model"]
---

# TASK-0651 - Harden Evidence Status Vocabulary And Transition Rules

## Why

Evidence presence is not evidence sufficiency. CAPEX needs general evidence-link status vocabulary before evidence-driven modules, workpages, or closure flows can activate.

## Scope

Define evidence-link statuses and transition rules for real-project evidence binding.

- Cover proposed, under review, valid, partly valid, contradictory, obsolete, invalid, insufficient, and accepted-with-residual-risk states.
- Bind the vocabulary to source occurrence and closure semantics.
- Mark `SME-RP-G004` as the approval gate.

## Out of scope

- Runtime evidence-binding implementation.
- Search/retrieval index implementation.
- Treating extracted text, AI output, or raw file presence as reviewed evidence.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-142 and `SME-RP-G004`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Evidence statuses are general CAPEX vocabulary, not fixture-specific labels.
- Contradictory, obsolete, invalid, and insufficient evidence cannot satisfy closure.
- Residual-risk acceptance remains explicit and reviewable.

## Source row mapping

- Source task ID: `TASK-0628`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G004`
- Source conditions: `TOP-08;6-A1`

## Closeout evidence

- Added `docs/architecture/CAPEX_EVIDENCE_STATUS_TRANSITION_CONTRACT.md` as the accepted planning contract for `SME-RP-G004`.
- Defined the exact evidence-link status vocabulary, closure eligibility rules, and allowed transition rules.
- Added machine-readable `evidence_status_vocabulary` entries to `SME_RP_ACCEPTANCE_REGISTER.yaml`, including transition rules and presence-is-not-sufficiency guardrails.
- Updated Annex A to reference the authoritative evidence status transition contract.
- Added contract coverage proving contradictory, obsolete, invalid, insufficient, proposed, under-review, and partly-valid evidence cannot satisfy closure by themselves, and residual-risk acceptance requires explicit acceptance or waiver.
- No evidence-binding runtime, search/retrieval index, migration, route, frontend behavior, raw corpus import, or CAPEX product activation was introduced.
