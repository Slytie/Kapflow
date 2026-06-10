# P07 — Project Overview / State Snapshot

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | Project manager |
| Primary user question | What is the current governed state and what requires action? |
| Page archetype | state snapshot + exception summary |
| MVP band | MVP |
| Primary state objects | project_state_snapshot, risk_snapshot, flags, tasks, official_pointers |
| Evidence pattern | Top basis/version panel; stale reasons and drill paths |
| Mobile behavior | Summary cards and task list |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Basis/version banner; Exception summary cards; Lifecycle and closure summary; Open action list; Management-summary readiness.

## 4. Primary sections

- Basis/version banner
- Exception summary cards
- Lifecycle and closure summary
- Open action list
- Management-summary readiness

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `state_item` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `dimension` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `current_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `basis` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `freshness` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `blocker` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `next_action` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `linked_workpage` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| State explanation | Shows state explanation for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Basis vector | Shows basis vector for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence links | Shows evidence links for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Affected downstream items | Shows affected downstream items for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Available commands | Shows available commands for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit timeline | Shows audit timeline for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `open_workpage` | User has page access. | No mutation. |
| `open_task` | Task is visible to user or role. | No mutation; opens task drawer/full view. |
| `request_update` | Bound state item selected. | Task or rerun request created. |
| `create_summary_draft` | Governed snapshot exists. | Non-authoritative summary draft. |
| `open_evidence` | Evidence references resolved and accessible. | No mutation; opens drawer. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- mark_green_directly
- mark_project_closed_directly
- hide_not_forecastable

Blocked-state copy should name the reason, the affected basis/evidence, and the next safe action.

## 9. Evidence requirements

| Evidence object | Basis required | Unresolved behavior |
|---|---|---|
| `basis_version_or_pointer` | Show the artifact/snapshot/basis generation supporting the visible state. | If unresolved, show unresolved-source warning and block truth-changing commands. |
| `freshness_or_stale_reason` | Show generated/reviewed timestamp and stale trigger count. | If stale, allow read-only drilldown and re-review task creation only. |


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
- Mobile: Summary cards and task list
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
| P07-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P07-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P07-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P07-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P07-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Center of gravity for an in-flight project.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
