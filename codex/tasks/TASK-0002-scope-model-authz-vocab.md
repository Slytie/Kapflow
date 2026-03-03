---
id: TASK-0002
epic: EPIC-010
title: "Define scope model + authz vocabulary + isolation test plan"
status: DONE
owners: ["security", "platform"]
reviewers: ["sre", "qa"]
depends_on: ["TASK-0001"]
risk: high
---

## Context
Tenant+domain isolation is non-negotiable and must apply to APIs and background consumers.

## Objective
- Finalize `docs/architecture/scope_model.md`
- Finalize `schemas/policy/permissions.yaml`
- Draft isolation test plan outline (what endpoints/consumers must be tested)

## Non-goals
- Do not build a full RBAC UI.

## Plan
1) Define which objects are tenant-global vs domain-scoped.
2) Define minimal actions/roles needed for payroll slice.
3) Enumerate isolation tests:
   - API read/write
   - list endpoints
   - exporters/indexers/workers

## Files to read
- `docs/architecture/invariants.md`
- `docs/workflows/payroll/v1/WORKFLOW_CONTRACT.yaml`
- `docs/planning/epics/EPIC-010.md`

## Files to change
- `docs/architecture/scope_model.md`
- `schemas/policy/permissions.yaml`
- (optional) `docs/planning/checklists/SECURITY_SIGNOFF.md`

## Acceptance criteria
- [ ] Security signs off on scope model.
- [ ] Isolation plan is CI-gate ready (even if tests are implemented later).

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
