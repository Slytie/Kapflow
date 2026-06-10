# P19 — Risk / Stale Cockpit

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | PM, PMO, executive |
| Primary user question | What changed, what became stale, and what must be re-reviewed? |
| Page archetype | risk cockpit + stale trigger table |
| MVP band | MVP |
| Primary state objects | risk_state_snapshot, stale_reopen_register, flags |
| Evidence pattern | Every risk shows basis, trigger, uncertainty, owner, mitigation |
| Mobile behavior | Mobile alert and mitigation task |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Risk summary; Stale/reopen trigger table; Changed-variable feed; Mitigation ownership; Not-forecastable reasons; Escalations.

## 4. Primary sections

- Risk summary
- Stale/reopen trigger table
- Changed-variable feed
- Mitigation ownership
- Not-forecastable reasons
- Escalations

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `risk_or_stale_item` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `cause` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `affected_object` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `probability_or_unknown` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `impact` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `basis` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `trigger_source` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `mitigation` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `next_review` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `forecastability` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Risk detail | Shows risk detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Cause and consequence chain | Shows cause and consequence chain for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence basis | Shows evidence basis for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Changed-variable trigger | Shows changed-variable trigger for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Mitigation plan | Shows mitigation plan for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Re-review/promotion effects | Shows re-review/promotion effects for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `assign_mitigation` | Risk selected; owner and mitigation defined. | Mitigation task/update. |
| `request_re_review` | Stale/uncertain item selected. | Re-review task created. |
| `escalate` | Escalation reason and recipient role selected. | Escalation task/event. |
| `mark_not_forecastable_reason_reviewed` | Reason reviewed; no false precision substituted. | Reason review event. |
| `accept_residual_risk` | Impact/consequence visible; authorized route. | Residual-risk acceptance event. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- invent_precision
- suppress_not_forecastable
- close_risk_without_re_review_after_trigger

Blocked-state copy should name the reason, the affected basis/evidence, and the next safe action.

## 9. Evidence requirements

| Evidence object | Basis required | Unresolved behavior |
|---|---|---|
| `basis_version_or_pointer` | Show the artifact/snapshot/basis generation supporting the visible state. | If unresolved, show unresolved-source warning and block truth-changing commands. |
| `freshness_or_stale_reason` | Show generated/reviewed timestamp and stale trigger count. | If stale, allow read-only drilldown and re-review task creation only. |
| `risk_trigger_basis` | Show cause, consequence, trigger source, basis, uncertainty, and owner. | Unknown or stale inputs must show not forecastable rather than precise risk score. |


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
- Mobile: Mobile alert and mitigation task
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
| P19-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P19-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P19-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P19-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P19-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |
| P19-T06 | not_forecastable | Remove critical risk evidence. | Forecast/risk precision is replaced by not-forecastable reason and next action. |


## 14. Design notes

Risk is ongoing and re-evaluated.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
