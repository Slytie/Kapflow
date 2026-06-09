# CAPEX RACI Role-Permission Matrix

## Status
Accepted planning contract for `TASK-0650` and `SME-RP-G002`.

## Purpose
CAPEX role-sensitive modules need explicit responsibility boundaries before
they can claim SME-RP readiness. This matrix defines the minimum RACI and
role-permission posture for real-project work.

This is a planning contract only. It does not add runtime authorization logic,
schemas, migrations, APIs, routes, frontend behavior, or CAPEX product
activation.

## Authority boundary
RACI is a business-responsibility overlay, not a runtime authorization source.

Runtime permission authority remains:
- `project_memberships`
- `capex_project_authorization`
- canonical approvals
- audited events
- immutable artifacts
- promotion pointers

Generated material, workpage state, AI output, external status, local folder
state, file presence, PR/PO/invoice state, supplier statements, and handover
notes are never permission sources.

## RACI roles
The RACI role set is exactly:

- Project Manager
- Engineering SME
- Maintenance
- Production / Operator
- EHS
- Procurement
- Controlling
- Plant Management
- Technical Director
- CEO / Sponsor
- Supplier

## Governed actions
The governed action set is exactly:

- `create_source_occurrence`
- `review_evidence_link`
- `approve_decision_package`
- `adopt_project_state`
- `close_closure_dimension`
- `reopen_closure_dimension`
- `waive_evidence_or_residual_risk`
- `escalate_to_ceo_sponsor`

## Minimum role-permission posture
Every governed action must name an accountable owner, at least one consulted or
reviewing role when source or closure truth changes, and the minimum project
membership posture required before runtime implementation may execute the
action.

Minimum posture by action:

| Action | Accountable role | Minimum project posture |
|---|---|---|
| `create_source_occurrence` | Project Manager | `project_contributor` |
| `review_evidence_link` | Engineering SME | `project_contributor` plus review assignment |
| `approve_decision_package` | Plant Management | `project_admin` or canonical approval responder |
| `adopt_project_state` | Project Manager | `project_admin` plus canonical approval evidence |
| `close_closure_dimension` | Project Manager | `project_admin` plus closure evidence |
| `reopen_closure_dimension` | Project Manager | `project_contributor` plus stale/reopen basis |
| `waive_evidence_or_residual_risk` | Technical Director | `project_admin` plus waiver evidence |
| `escalate_to_ceo_sponsor` | CEO / Sponsor | `project_contributor` plus escalation basis |

These postures are acceptance constraints for later implementation. They do not
grant permission by themselves.

## Activation rule
Role-sensitive workflow, workpage, projection, snapshot/export, and external
observation surfaces must not claim SME-RP readiness until they preserve this
matrix or record an explicit waiver.
