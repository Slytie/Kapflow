---
id: TASK-0650
epic: EPIC-140
title: "Draft RACI and role-permission matrix"
status: DONE
completed_at: "2026-06-09T09:31:48Z"
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

## Closeout evidence

- Added `docs/architecture/CAPEX_RACI_ROLE_PERMISSION_MATRIX.md` as the accepted planning contract for `SME-RP-G002`.
- Defined the exact RACI role set and governed action set for role-sensitive CAPEX modules.
- Added machine-readable `raci_role_permission_matrix` entries to `SME_RP_ACCEPTANCE_REGISTER.yaml`, including minimum project-role posture and permission-source guardrails.
- Updated Annex A to reference the authoritative RACI contract.
- Added contract coverage proving RACI is a business-responsibility overlay and cannot be derived from generated material, workpage state, AI output, or external status.
- No runtime authorization implementation, migration, route, frontend behavior, raw corpus import, or CAPEX product activation was introduced.
