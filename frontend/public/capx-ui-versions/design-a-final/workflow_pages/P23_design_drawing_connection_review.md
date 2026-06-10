# P23 — Design / Drawing / Connection Review

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Expansion |
| Primary role | Engineering, PM |
| Primary user question | Do drawings/connections match requirements and interfaces? |
| Page archetype | drawing evidence workpage |
| MVP band | Post-MVP |
| Primary state objects | drawing_reviews, connection_points, requirement_links |
| Evidence pattern | Preview/annotation/evidence bindings |
| Mobile behavior | Read-only snapshots |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Drawing package table; Connection-point review; Requirement links; Markup/comments; Mismatch flags.

## 4. Primary sections

- Drawing package table
- Connection-point review
- Requirement links
- Markup/comments
- Mismatch flags

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `drawing` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `version` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `system_area` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `connection_point` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `linked_requirement` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `review_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `mismatch` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `evidence_region` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `next_action` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Drawing preview | Shows drawing preview for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Version comparison | Shows version comparison for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Connection details | Shows connection details for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Requirement/interface links | Shows requirement/interface links for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Review comments | Shows review comments for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Flag actions | Shows flag actions for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `review_drawing` | Drawing version current; reviewer role. | Drawing review event. |
| `flag_connection_mismatch` | Connection point and mismatch evidence selected. | Mismatch flag/task. |
| `link_requirement` | Requirement accessible; link scope selected. | Requirement link event. |
| `request_supplier_revision` | Supplier artifact/mismatch selected. | Revision request task. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- claim_drawing_sufficiency_without_review
- use_unapproved_drawing_as_baseline

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
- Mobile: Read-only snapshots
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
| P23-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P23-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P23-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P23-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P23-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Reserved by K12/K3 post-MVP expansion.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
