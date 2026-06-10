# P21 — CEO / Management Transparency

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project/global |
| Primary role | Executive, PM lead |
| Primary user question | What needs management attention and what can be safely reported? |
| Page archetype | governed executive cockpit |
| MVP band | Near-MVP |
| Primary state objects | management_summary_snapshot, project_state_snapshot, risk_snapshot |
| Evidence pattern | Snapshot basis, forecastability, unknowns, blockers, decision needed |
| Mobile behavior | Mobile briefing cards |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- Global top bar: Home, Approvals, Projects, Reports, Admin, global search, role context.
- Primary surface: cockpit, list, report catalog, or administrative table depending on page.
- Right drawer: selected row/task/evidence/policy/audit detail.
- Persistent feedback: command receipts, background sync, notification status, and permission warnings.
- Page-specific sections: Executive summary cards; Forecastability and unknowns; Exposure/blocker grid; Decision-needed panel; Evidence drilldown; Published summary history.

## 4. Primary sections

- Executive summary cards
- Forecastability and unknowns
- Exposure/blocker grid
- Decision-needed panel
- Evidence drilldown
- Published summary history

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `project_or_decision` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `status_or_forecastability` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `exposure` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `top_blocker` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `unknown_reason` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `freshness` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `basis_snapshot` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `decision_needed` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Executive explanation | Shows executive explanation for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence basis | Shows evidence basis for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Unresolved/unknowns | Shows unresolved/unknowns for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Decision request | Shows decision request for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Publication readiness | Shows publication readiness for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit | Shows audit for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `publish_governed_summary` | Summary derived from governed snapshot; unresolved warnings included. | Published management summary event. |
| `request_decision` | Decision need and evidence basis identified. | Decision task created. |
| `drilldown` | Drill target accessible. | Navigation/projection only. |
| `create_escalation_task` | Bound object, evidence and urgency provided. | Escalation task. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- publish_raw_ai_summary
- hide_stale_state
- turn_unknown_into_green

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
- Mobile: Mobile briefing cards
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
| P21-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P21-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P21-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P21-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P21-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Dashboards derive from governed snapshots.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
