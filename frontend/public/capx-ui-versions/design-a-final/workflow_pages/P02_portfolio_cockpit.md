# P02 — Portfolio Cockpit

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Global |
| Primary role | Finance manager, executive, PM lead |
| Primary user question | Which projects have exposure, stale state, or decision needs? |
| Page archetype | deterministic dashboard + drilldown grid |
| MVP band | Near-MVP |
| Primary state objects | portfolio_projection, project_state_snapshots, risk_snapshots |
| Evidence pattern | Every KPI points to snapshot version and source module |
| Mobile behavior | Read-only drilldown; decision links only |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- Global top bar: Home, Approvals, Projects, Reports, Admin, global search, role context.
- Primary surface: cockpit, list, report catalog, or administrative table depending on page.
- Right drawer: selected row/task/evidence/policy/audit detail.
- Persistent feedback: command receipts, background sync, notification status, and permission warnings.
- Page-specific sections: Portfolio KPI strip; Exposure and forecastability charts; Project drilldown grid; Decision-needed queue; Snapshot freshness panel.

## 4. Primary sections

- Portfolio KPI strip
- Exposure and forecastability charts
- Project drilldown grid
- Decision-needed queue
- Snapshot freshness panel

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `project` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `site` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `business_driver` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `current_stage` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `exposure` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `forecastability` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `top_blocker` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `stale_count` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `open_decisions` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `basis_snapshot` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `last_reviewed` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Project summary | Shows project summary for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Exposure basis | Shows exposure basis for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Top blockers | Shows top blockers for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Freshness and unresolved sources | Shows freshness and unresolved sources for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Open management decisions | Shows open management decisions for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `drill_to_project` | User has project access. | No mutation; opens project projection. |
| `open_escalation_task` | Escalation task exists or user may create one. | Opens or creates bounded escalation task. |
| `filter_portfolio` | Portfolio projection loaded. | Projection state changes only. |
| `generate_portfolio_report` | Required snapshots available. | Report generation job created with basis manifest. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- edit_project_truth_from_portfolio
- hide_unknown_state
- rank_projects_without_basis

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
- Mobile: Read-only drilldown; decision links only
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
| P02-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P02-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P02-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P02-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P02-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |
| P02-T06 | not_forecastable | Remove critical risk evidence. | Forecast/risk precision is replaced by not-forecastable reason and next action. |


## 14. Design notes

Dashboard is not truth; it summarizes governed snapshots.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
