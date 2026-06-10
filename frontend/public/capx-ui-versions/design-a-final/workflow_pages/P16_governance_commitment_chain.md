# P16 — Governance / Commitment Chain

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | Procurement, PM |
| Primary user question | What was decided, quoted, ordered, revised, caveated, or settled? |
| Page archetype | timeline/table hybrid + revision drawer |
| MVP band | MVP |
| Primary state objects | commitment_chain, quote_order_revisions, scope_deltas, caveats |
| Evidence pattern | Revision comparison and affected rows panel |
| Mobile behavior | Read-only chain; decision tasks only |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Commitment timeline; Quote/order/revision table; Revision comparison; Scope/exclusion/caveat register; Affected assumptions and interfaces.

## 4. Primary sections

- Commitment timeline
- Quote/order/revision table
- Revision comparison
- Scope/exclusion/caveat register
- Affected assumptions and interfaces

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `event` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `document` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `counterparty` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `commitment_type` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `scope_delta` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `responsibility_shift` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `caveat` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `amount_or_date` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `basis` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `affected_rows` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `review_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Document/event detail | Shows document/event detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Before/after comparison | Shows before/after comparison for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Affected assumptions/interfaces | Shows affected assumptions/interfaces for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Policy blockers | Shows policy blockers for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Promotion readiness | Shows promotion readiness for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit | Shows audit for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `mark_reviewed` | Reviewer role; evidence inspected; generation current. | Review event recorded. |
| `promote_commitment_chain` | Commitment chain reviewed/approved; source refs resolved. | Official commitment baseline pointer. |
| `request_supplier_clarification` | Counterparty/contact/scope selected. | Clarification task and evidence request. |
| `create_revision_re_review_task` | Revision delta affects reviewed/official state. | Re-review tasks for affected rows. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- latest_order_equals_official
- ignore_order_revision_delta
- settlement_equals_technical_proof

Blocked-state copy should name the reason, the affected basis/evidence, and the next safe action.

## 9. Evidence requirements

| Evidence object | Basis required | Unresolved behavior |
|---|---|---|
| `basis_version_or_pointer` | Show the artifact/snapshot/basis generation supporting the visible state. | If unresolved, show unresolved-source warning and block truth-changing commands. |
| `freshness_or_stale_reason` | Show generated/reviewed timestamp and stale trigger count. | If stale, allow read-only drilldown and re-review task creation only. |
| `quote_order_revision_documents` | Link each commitment to exact document version and delta. | Revision deltas create affected-row stale/re-review tasks. |


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
- Mobile: Read-only chain; decision tasks only
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
| P16-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P16-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P16-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P16-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P16-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

K12 MVP-critical workflow.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
