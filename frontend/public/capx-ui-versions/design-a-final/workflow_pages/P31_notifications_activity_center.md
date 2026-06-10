# P31 — Notifications / Activity Center

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Support |
| Primary role | All role clusters |
| Primary user question | What changed that I should notice but may not need to decide? |
| Page archetype | activity feed + persistent alerts |
| MVP band | Near-MVP |
| Primary state objects | notifications, stale_events, task_assignments, sync_events |
| Evidence pattern | Important actions route to queue, not toast only |
| Mobile behavior | Mobile alert entry |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- Context header: scope selector, project/global filter, current basis where relevant.
- Primary utility surface: evidence library, audit timeline, integration status, or notification feed.
- Right drawer: entity detail with evidence/audit/policy links.
- Status area: filter state, sync/freshness, export status, permission explanation.
- Page-specific sections: Activity feed; Persistent alerts; Task assignments; Stale events; Sync notifications; User preferences.

## 4. Primary sections

- Activity feed
- Persistent alerts
- Task assignments
- Stale events
- Sync notifications
- User preferences

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `notification` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `type` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `priority` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `bound_object` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `freshness` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `requires_action` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `created_at` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `route_to` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Notification detail | Shows notification detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Why shown | Shows why shown for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Bound evidence/task | Shows bound evidence/task for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Available route | Shows available route for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Dismiss/mute policy | Shows dismiss/mute policy for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit | Shows audit for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `open_notification` | Notification accessible. | Opens bound object or detail. |
| `mute_low_priority` | Notification is not critical/task-bound. | Preference/event. |
| `convert_to_task` | Notification has actionable bound object. | Task created. |
| `open_bound_object` | Bound object accessible. | Navigation only. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- notification_only_approval
- dismiss_critical_task_without_action
- hide_stale_alert

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
- Mobile: Mobile alert entry
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
| P31-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P31-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P31-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P31-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P31-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Notifications reduce surprise, not replace tasks.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
