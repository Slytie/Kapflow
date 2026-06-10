# P18 — Interface Resolution

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | PM, engineering, site owner |
| Primary user question | Do required and actual conditions match across owner/supplier/site/process boundaries? |
| Page archetype | required-vs-actual table |
| MVP band | MVP |
| Primary state objects | interface_register, site_evidence, supplier_requirements |
| Evidence pattern | Mismatch panels show required/actual/evidence/owner |
| Mobile behavior | Task cards and read-only detail |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Interface register; Required-vs-actual table; Evidence/mismatch comparison; Owner assignment; Readiness and risk effects.

## 4. Primary sections

- Interface register
- Required-vs-actual table
- Evidence/mismatch comparison
- Owner assignment
- Readiness and risk effects

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `interface` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `type` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `required_condition` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `actual_condition` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `evidence` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `mismatch_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `closure_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `risk_effect` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `readiness_effect` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `stale_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Interface detail | Shows interface detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Required condition evidence | Shows required condition evidence for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Actual/site condition evidence | Shows actual/site condition evidence for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Mismatch analysis | Shows mismatch analysis for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Owner/supplier responsibility | Shows owner/supplier responsibility for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Close/escalate actions | Shows close/escalate actions for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `assign_owner` | Bound object selected; owner eligible. | Owner assignment event. |
| `request_site_measurement` | Site/interface gap selected. | Measurement/evidence task created. |
| `close_interface` | Required and actual conditions match or authorized waiver exists; no stale basis. | Interface closure event. |
| `escalate_mismatch` | Mismatch unresolved and escalation route exists. | Escalation task. |
| `request_supplier_clarification` | Counterparty/contact/scope selected. | Clarification task and evidence request. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- supplier_requirement_as_owner_capability
- close_interface_with_unresolved_mismatch
- procurement_ready_with_critical_interface_open

Blocked-state copy should name the reason, the affected basis/evidence, and the next safe action.

## 9. Evidence requirements

| Evidence object | Basis required | Unresolved behavior |
|---|---|---|
| `basis_version_or_pointer` | Show the artifact/snapshot/basis generation supporting the visible state. | If unresolved, show unresolved-source warning and block truth-changing commands. |
| `freshness_or_stale_reason` | Show generated/reviewed timestamp and stale trigger count. | If stale, allow read-only drilldown and re-review task creation only. |
| `required_actual_evidence` | Show supplier/owner required condition and actual/site condition evidence separately. | Supplier requirement cannot be shown as owner capability. |


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
- Mobile: Task cards and read-only detail
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
| P18-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P18-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P18-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P18-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P18-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

K12 site-condition/interface archetype.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
