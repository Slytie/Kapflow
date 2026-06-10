# P12 — Concept Engineering / Options

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | PM, engineering |
| Primary user question | What solution paths exist and what does each imply? |
| Page archetype | option comparison workspace |
| MVP band | Near-MVP |
| Primary state objects | concept_options, option_assumptions, option_interfaces, supplier_candidates |
| Evidence pattern | Each option card/table row shows assumptions, interfaces, risk basis |
| Mobile behavior | Read-only option summaries |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Concept option cards; Option comparison table; Option assumptions; Option interfaces; Supplier candidates and quotes; Option readiness.

## 4. Primary sections

- Concept option cards
- Option comparison table
- Option assumptions
- Option interfaces
- Supplier candidates and quotes
- Option readiness

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `option` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `description` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `supplier_candidates` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `rough_cost` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `schedule_estimate` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `key_assumptions` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `open_interfaces` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `risk_profile` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `evidence_basis` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `readiness` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Option detail | Shows option detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Layouts/drawings/quotes | Shows layouts/drawings/quotes for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Assumptions inherited | Shows assumptions inherited for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Interface map | Shows interface map for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Risk per option | Shows risk per option for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Send to decision matrix | Shows send to decision matrix for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `create_option` | Project has feasibility context; user has engineering role. | Concept option draft created. |
| `attach_quote` | Quote artifact passed source checks. | Quote linked to concept option. |
| `compare_options` | At least two options selected. | Comparison projection generated. |
| `send_to_decision_matrix` | Option has required comparison fields or declared gaps. | Decision-matrix draft created/updated. |
| `request_option_review` | Option draft selected. | Option review task created. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- select_option_without_review
- hide_option_risk
- treat_budgetary_quote_as_order

Blocked-state copy should name the reason, the affected basis/evidence, and the next safe action.

## 9. Evidence requirements

| Evidence object | Basis required | Unresolved behavior |
|---|---|---|
| `basis_version_or_pointer` | Show the artifact/snapshot/basis generation supporting the visible state. | If unresolved, show unresolved-source warning and block truth-changing commands. |
| `freshness_or_stale_reason` | Show generated/reviewed timestamp and stale trigger count. | If stale, allow read-only drilldown and re-review task creation only. |
| `decision_basis` | Show roughness/confidence/evidence gap/assumption inheritance for early-stage decisions. | Rough feasibility cannot be promoted as final scope. |


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
- Mobile: Read-only option summaries
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
| P12-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P12-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P12-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P12-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P12-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Concept engineering creates variants, interfaces, supplier preselection.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
