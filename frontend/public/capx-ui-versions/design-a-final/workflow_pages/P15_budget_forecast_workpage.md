# P15 — Budget / Forecast Workpage

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | Finance, PM |
| Primary user question | What is approved, committed, actual, remaining, and forecasted? |
| Page archetype | dense financial table + variance drilldown |
| MVP band | Near-MVP |
| Primary state objects | budget_lines, commitments, actuals, forecasts, variances |
| Evidence pattern | Sticky totals and basis/version panel; line evidence drawers |
| Mobile behavior | Mobile summary and approval task only |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Budget line grid; Approved/committed/actual/remaining footer; Variance drilldown; Cost center/vendor filters; Basis and ERP sync panel.

## 4. Primary sections

- Budget line grid
- Approved/committed/actual/remaining footer
- Variance drilldown
- Cost center/vendor filters
- Basis and ERP sync panel

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `line_item` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `package_or_wbs` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `cost_center` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `vendor` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `status` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `approved_budget` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `committed` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `actual` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `remaining` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `forecast` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `variance` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `currency` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `basis_version` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `sync_state` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Line detail | Shows line detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Commitment links | Shows commitment links for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Variance explanation | Shows variance explanation for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence and attachments | Shows evidence and attachments for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Policy checks | Shows policy checks for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| ERP sync history | Shows erp sync history for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `edit_budget_draft` | Budget line editable; not official mutation. | Budget draft update. |
| `submit_budget_review` | Budget draft validates. | Budget review/approval task. |
| `approve_budget_change` | Finance approver role; route/policy pass. | Budget approval event. |
| `request_variance_explanation` | Variance line selected. | Explanation task. |
| `retry_sync` | Current official state and handoff manifest exist. | Sync retry event/job. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- post_unapproved_budget
- hide_variance_basis
- sync_before_official_capex_state

Blocked-state copy should name the reason, the affected basis/evidence, and the next safe action.

## 9. Evidence requirements

| Evidence object | Basis required | Unresolved behavior |
|---|---|---|
| `basis_version_or_pointer` | Show the artifact/snapshot/basis generation supporting the visible state. | If unresolved, show unresolved-source warning and block truth-changing commands. |
| `freshness_or_stale_reason` | Show generated/reviewed timestamp and stale trigger count. | If stale, allow read-only drilldown and re-review task creation only. |
| `financial_basis_and_sync` | Show approved, committed, actual, remaining, forecast, variance, currency, cost center, ERP sync state. | Official CAPEX state must be separated from external posting/sync. |


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
- Mobile: Mobile summary and approval task only
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
| P15-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P15-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P15-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P15-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P15-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Desktop dense table; financial error prevention.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
