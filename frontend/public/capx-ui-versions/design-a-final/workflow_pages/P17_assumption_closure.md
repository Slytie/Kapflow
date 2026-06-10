# P17 — Assumption Closure

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | PM, engineering, procurement |
| Primary user question | Which assumptions are open, closed, contradicted, waived, or stale? |
| Page archetype | matrix/table + closure drawer |
| MVP band | MVP |
| Primary state objects | counterparty_assumption_register, assumption_closure_matrix, evidence_links |
| Evidence pattern | Each row has source, counterparty, required evidence, closure basis |
| Mobile behavior | Task-focused; no dense matrix editing |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Assumption closure matrix; Evidence sufficiency filters; Waiver/residual risk panel; Stale assumption triggers; Closure commands.

## 4. Primary sections

- Assumption closure matrix
- Evidence sufficiency filters
- Waiver/residual risk panel
- Stale assumption triggers
- Closure commands

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `assumption` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `counterparty_or_owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `source` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `impact` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `evidence_required` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `evidence_available` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `closure_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `waiver_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `residual_risk` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `stale_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Assumption detail | Shows assumption detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Source evidence | Shows source evidence for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Closure options | Shows closure options for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Contradictions | Shows contradictions for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Waiver/residual risk policy | Shows waiver/residual risk policy for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit | Shows audit for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `close_assumption_with_evidence` | Sufficient linked evidence; no stale basis; reviewer role. | Assumption closure event/updated matrix. |
| `request_evidence` | Bound object and evidence gap reason identified. | Evidence request task/flag created. |
| `waive_assumption` | Authority, scope, reason, residual risk, expiry where applicable. | Waiver event and residual-risk visibility. |
| `accept_residual_risk` | Impact/consequence visible; authorized route. | Residual-risk acceptance event. |
| `create_re_review_task` | Stale or changed basis selected. | Re-review task created. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- close_because_no_contradiction_found
- close_without_evidence
- close_stale_assumption

Blocked-state copy should name the reason, the affected basis/evidence, and the next safe action.

## 9. Evidence requirements

| Evidence object | Basis required | Unresolved behavior |
|---|---|---|
| `basis_version_or_pointer` | Show the artifact/snapshot/basis generation supporting the visible state. | If unresolved, show unresolved-source warning and block truth-changing commands. |
| `freshness_or_stale_reason` | Show generated/reviewed timestamp and stale trigger count. | If stale, allow read-only drilldown and re-review task creation only. |
| `closure_evidence` | Show evidence required, evidence available, sufficiency, contradiction, waiver and residual-risk state. | No evidence/no waiver means closure command is blocked. |
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
- Mobile: Task-focused; no dense matrix editing
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
| P17-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P17-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P17-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P17-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P17-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |
| P17-T06 | closure_vector | Mark production handover accepted. | Technical/effectiveness/commercial/formal closure dimensions remain open unless separately evidenced and commanded. |


## 14. Design notes

Human-reviewed closure is mandatory.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
