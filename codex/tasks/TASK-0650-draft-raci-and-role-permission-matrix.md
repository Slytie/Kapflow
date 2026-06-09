---
id: TASK-0650
epic: EPIC-140
title: "Draft RACI and role-permission matrix"
status: TODO
owners: ["capex-product", "capex-architecture"]
reviewers: ["engineering-pm", "backend", "capex-sme"]
depends_on: ["TASK-0262", "TASK-0648"]
risk: high
context_packs: ["codex/context/EPIC-140.md"]
patterns: ["SME-RP acceptance conditions", "role-sensitive activation"]
---

# TASK-0650 - Draft RACI And Role-Permission Matrix

## Why

Role-sensitive CAPEX modules need explicit responsibility and permission boundaries before activation. The RACI applies to CAPEX real-project work generally, not only to one fixture.

## Scope

Draft the RACI and role-permission matrix for create, review, approve, adopt, close, reopen, waive, and escalate actions.

- Align roles with project membership and future authorization projections.
- Mark `SME-RP-G002` as the activation gate for role-sensitive modules.
- Keep official state changes routed through the canonical object/event/pointer path.

## Out of scope

- Runtime authorization implementation beyond existing EPIC-140 foundation.
- Frontend-only permission filtering.
- New official-state shortcuts.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-140 and `SME-RP-G002`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- RACI draft covers create, review, approve, adopt, close, reopen, waive, and escalate.
- Role-sensitive activation remains blocked until the matrix is accepted or explicitly waived.
- No generated material or workpage state becomes a permission source.

## Source row mapping

- Source task ID: `TASK-0627`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G002`
- Source conditions: `TOP-10;5-A3;14-D8`
