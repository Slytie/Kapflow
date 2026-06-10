# P04 — Global Search

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Global |
| Primary role | PM, procurement, finance |
| Primary user question | Where is this project, supplier, artifact, task, or claim? |
| Page archetype | search results + entity filters |
| MVP band | Near-MVP |
| Primary state objects | project_index, artifact_index, task_index, supplier_index |
| Evidence pattern | Results display entity type, authority level, freshness, and scope |
| Mobile behavior | Lightweight search and read-only detail |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- Global top bar: Home, Approvals, Projects, Reports, Admin, global search, role context.
- Primary surface: cockpit, list, report catalog, or administrative table depending on page.
- Right drawer: selected row/task/evidence/policy/audit detail.
- Persistent feedback: command receipts, background sync, notification status, and permission warnings.
- Page-specific sections: Search box with scope; Entity-type filters; Results grouped by entity; Authority/freshness chips; Recent searches.

## 4. Primary sections

- Search box with scope
- Entity-type filters
- Results grouped by entity
- Authority/freshness chips
- Recent searches

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `result` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `entity_type` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `project_scope` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `authority_level` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `freshness` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `matched_field` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `basis` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `last_updated` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Result context | Shows result context for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Why matched | Shows why matched for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence links | Shows evidence links for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Authority level explanation | Shows authority level explanation for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Open related actions | Shows open related actions for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `search` | Search scope permitted. | Projection results only. |
| `filter` | Data projection loaded. | Projection state changes only. |
| `open_entity` | Entity access permitted. | No mutation; opens entity. |
| `save_search` | User authenticated. | Saved search preference. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- treat_search_result_as_evidence
- open_unpermitted_entity
- promote_from_search

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
- Mobile: Lightweight search and read-only detail
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
| P04-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P04-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P04-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P04-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P04-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Search complements structured workpages, not a truth surface.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
