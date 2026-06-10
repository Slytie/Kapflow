# P29 — Audit / History

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Support |
| Primary role | Auditor, PM, approver |
| Primary user question | Who did what, when, on which version, with what outcome? |
| Page archetype | immutable timeline + filters |
| MVP band | MVP foundation |
| Primary state objects | audit_events, command_receipts, policy_verdicts, pointer_events |
| Evidence pattern | Actor/time/action/outcome/entities/policy/evidence |
| Mobile behavior | Read-only timeline |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- Context header: scope selector, project/global filter, current basis where relevant.
- Primary utility surface: evidence library, audit timeline, integration status, or notification feed.
- Right drawer: entity detail with evidence/audit/policy links.
- Status area: filter state, sync/freshness, export status, permission explanation.
- Page-specific sections: Audit filters; Immutable event timeline; Command receipts; Policy verdicts; Pointer events; Export.

## 4. Primary sections

- Audit filters
- Immutable event timeline
- Command receipts
- Policy verdicts
- Pointer events
- Export

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `timestamp` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `actor` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `action` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `outcome` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `entity` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `version_or_generation` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `policy_verdict` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `source_context` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `receipt_id` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Event detail | Shows event detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Related entities | Shows related entities for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence and basis | Shows evidence and basis for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Policy/context | Shows policy/context for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Command receipt | Shows command receipt for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Export metadata | Shows export metadata for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `filter` | Data projection loaded. | Projection state changes only. |
| `export_audit` | Audit scope and permission valid. | Audit export event. |
| `open_related_entity` | Related entity accessible. | Navigation only. |
| `save_audit_view` | User authenticated. | Saved audit filter view. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- edit_audit_event
- delete_audit_event
- export_without_scope

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
- Mobile: Read-only timeline
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
| P29-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P29-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P29-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P29-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P29-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Audit drawer/tab supports trust and compliance.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
