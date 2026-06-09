---
id: TASK-0656
epic: EPIC-143
title: "Add Safety and Work Permit Readiness workflow"
status: TODO
owners: ["capex-product", "capex-architecture"]
reviewers: ["ehs", "backend", "qa", "capex-sme"]
depends_on: ["TASK-0566"]
risk: high
context_packs: ["codex/context/EPIC-143.md"]
patterns: ["SME-RP acceptance conditions", "safety readiness"]
---

# TASK-0656 - Add Safety And Work Permit Readiness Workflow

## Why

Safety readiness is a standard CAPEX work-release concern, not a fixture-only concern. Missing safety evidence must block or route work through canonical tasks.

## Scope

Specify Safety and Work Permit Readiness as an MVP / early real-project workflow.

- Cover contractor readiness, safety briefing, work release, and escalation basics.
- Keep safety readiness distinct from technical closure and commercial status.
- Bind the workflow to `SME-RP-G012`.

## Out of scope

- Full EHS system replacement.
- Runtime connector implementation.
- Public frontend route implementation.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-143.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Missing safety briefing or permit evidence blocks work release or creates escalation work.
- Safety readiness is not treated as K3-only.
- Safety state remains canonical task/evidence/approval truth, not workpage-only state.

## Source row mapping

- Source task ID: `TASK-0633`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G012`
- Fixture refs: `K12-T8`
- Source conditions: `TOP-05;8-A3;12-A2`
