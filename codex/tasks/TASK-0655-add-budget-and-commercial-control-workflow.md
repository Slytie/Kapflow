---
id: TASK-0655
epic: EPIC-143
title: "Add Budget and Commercial Control workflow"
status: TODO
owners: ["capex-product", "capex-architecture"]
reviewers: ["backend", "procurement", "controlling", "capex-sme"]
depends_on: ["TASK-0566"]
risk: high
context_packs: ["codex/context/EPIC-143.md"]
patterns: ["SME-RP acceptance conditions", "commercial observation boundary"]
---

# TASK-0655 - Add Budget And Commercial Control Workflow

## Why

Commercial evidence must be visible and reconcilable without becoming ERP truth or technical closure. CAPEX needs a general workflow for budget and commercial observation.

## Scope

Specify Budget and Commercial Control as an MVP / early workflow.

- Model commercial control as observation and reconciliation.
- Preserve separation between commercial settlement and technical effectiveness.
- Bind the workflow to `SME-RP-G006` and `SME-RP-G012`.

## Out of scope

- ERP/accounting ledger replacement.
- Runtime connector implementation.
- Numeric threshold invention.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-143.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- PR, PO, invoice, forecast, and controlling data are treated as observed/reconciled evidence.
- Commercial settlement cannot close technical, effectiveness, handover, or assumption dimensions.
- Missing or deviating commercial fields can route canonical clarification work.

## Source row mapping

- Source task ID: `TASK-0632`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G006;SME-RP-G012`
- Fixture refs: `K12-T4;K12-T10`
- Source conditions: `TOP-04;8-A2;9-A2`
