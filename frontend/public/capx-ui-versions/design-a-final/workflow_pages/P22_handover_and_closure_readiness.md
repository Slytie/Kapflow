# P22 — Handover & Closure Readiness

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | PM, operations, quality |
| Primary user question | Which kind of closure is achieved, blocked, or only partial? |
| Page archetype | closure vector + open-point table |
| MVP band | Near-MVP/Post-MVP partial |
| Primary state objects | handover_state, closure_vector, open_points, lifecycle_obligations |
| Evidence pattern | Closure vector with separate states and evidence |
| Mobile behavior | Read-only closure summary + approval tasks |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Closure vector; Handover packet state; Open-point table; Documentation/training/commercial/technical/effectiveness dimensions; Lifecycle obligations.

## 4. Primary sections

- Closure vector
- Handover packet state
- Open-point table
- Documentation/training/commercial/technical/effectiveness dimensions
- Lifecycle obligations

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `closure_dimension` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `evidence_required` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `evidence_available` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `open_points` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `due_at` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `residual_risk` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `acceptance_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `basis` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Closure dimension detail | Shows closure dimension detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence and handover documents | Shows evidence and handover documents for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Open-point ownership | Shows open-point ownership for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Residual risk | Shows residual risk for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Acceptance/closure commands | Shows acceptance/closure commands for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit | Shows audit for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `accept_handover_with_open_points` | Open points, owners, deadlines and residual risks explicit; authority present. | Handover acceptance event; closure dimensions remain separate. |
| `close_defect` | Defect evidence and verification complete. | Local defect closure event. |
| `request_effectiveness_evidence` | Effectiveness gap selected. | Evidence/test task created. |
| `accept_residual_risk` | Impact/consequence visible; authorized route. | Residual-risk acceptance event. |
| `promote_closure_snapshot` | Closure vector reviewed/approved where required. | Official closure snapshot pointer. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- handover_equals_closure
- settlement_equals_technical_proof
- local_defect_equals_system_effectiveness

Blocked-state copy should name the reason, the affected basis/evidence, and the next safe action.

## 9. Evidence requirements

| Evidence object | Basis required | Unresolved behavior |
|---|---|---|
| `basis_version_or_pointer` | Show the artifact/snapshot/basis generation supporting the visible state. | If unresolved, show unresolved-source warning and block truth-changing commands. |
| `freshness_or_stale_reason` | Show generated/reviewed timestamp and stale trigger count. | If stale, allow read-only drilldown and re-review task creation only. |
| `closure_dimension_evidence` | Show evidence by closure dimension: handover, formal, technical, commercial, defect, effectiveness, documentation, lifecycle. | One closure dimension cannot close another. |


## 10. State handling

| State | Required behavior |
|---|---|
| empty | No records match this view yet. Clear filters, upload evidence, create a draft, or open a related task depending on page purpose. |
| loading | Loading governed projection and basis vector. Show skeleton rows and preserve filters; do not show stale prior data as current without a freshness badge. |
| error | The projection could not be loaded or validated. Show technical cause where safe: stale generation, missing evidence, unresolved source, policy mismatch, sync failure, or permission problem. |
| stale | This view is based on a generation that has been invalidated by newer evidence or configuration. Block truth-changing commands; allow read-only inspection and create/request re-review. |
| permission | You can view this context only partially or cannot perform the selected command. Explain required role or separation-of-duties rule without leaking restricted content. |


## 11. Mobile and responsive behavior

- Desktop: full workbench behavior with filters, dense rows, drawer, evidence/audit and command panels.
- Tablet: summary/detail where space allows; otherwise route to row detail.
- Mobile: Read-only closure summary + approval tasks
- Truth-changing mobile actions require online revalidation, evidence summary, policy result, and command receipt.

## 12. Accessibility and performance

- Use native table semantics when read-only; use interactive grid semantics only where editing is essential.
- Keep filters visible, stable, and resettable.
- Announce save/validate/queued/synced/error states as status messages.
- Preserve focus after drawers and confirmations.
- Server-side filtering/sorting and virtualization are required for large workpages.
- Error messages must identify the basis of the error: stale generation, missing evidence, unresolved source, policy mismatch, permission, or sync failure.

## 13. Acceptance tests

| Test ID | Category | Given | Expected |
|---|---|---|---|
| P22-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P22-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P22-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P22-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P22-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |
| P22-T06 | closure_vector | Mark production handover accepted. | Technical/effectiveness/commercial/formal closure dimensions remain open unless separately evidenced and commanded. |


## 14. Design notes

K12 closure decomposition is non-negotiable.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
