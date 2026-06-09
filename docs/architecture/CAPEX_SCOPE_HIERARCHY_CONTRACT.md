# CAPEX Scope Hierarchy Contract

## Status
Accepted planning contract for `TASK-0649` and `SME-RP-G003`.

## Purpose
CAPEX real-project status must remain separable by scope. This contract defines
the minimum logical `capex_scope` hierarchy required before scope-sensitive
workflows, workpages, closure checks, or executive views can claim readiness.

This is a planning contract only. It does not add runtime state, migrations,
APIs, public routes, frontend behavior, or CAPEX product activation.

## Logical scope hierarchy
The minimum logical scope hierarchy is exactly:

1. `project`
2. `module_workstream`
3. `package`
4. `discipline`
5. `source_occurrence`
6. `artifact`
7. `task`
8. `approval`
9. `flag`
10. `external_binding`

`capex_projects.project_id` remains the durable project root. `workflow_run_id`
is execution identity only; it is not project identity and is not scope identity.

## Boundary rules
- Scope rows never cross tenant, domain, or project boundaries.
- Parent and child scope refs must stay inside the same `project_id`.
- A scope child may narrow responsibility or evidence, but it must not override
  the project root or create a second project identity.
- One closed scope cannot imply overall closure.
- A workflow may claim overall closure only when the relevant scope dimensions
  have explicit closure evidence, residual handling, or approved waiver state.
- Workpage projections, external statuses, file presence, PR/PO/invoice state,
  handover notes, and supplier statements cannot set scope closure by
  themselves.

## False-closure fixture
`K12-T1` is the motivating fixture case for this contract: one scope may appear
closed while another scope remains in budget build-up or review. The expected
behavior is to show the scope statuses separately and prevent false overall
closure.

`K12-T1` is a fixture-case ID only. It is not a product namespace, gate
namespace, or runtime scope kind.

## Acceptance rule
Any future runtime schema, workflow, workpage, projection, executive snapshot,
or external-observation surface that uses `capex_scope` must preserve the
logical hierarchy and boundary rules in this contract before claiming SME-RP
readiness.
