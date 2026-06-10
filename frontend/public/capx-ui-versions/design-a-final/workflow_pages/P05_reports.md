# P05 — Reports

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Global |
| Primary role | Finance, executive, PM lead |
| Primary user question | What governed report can be produced from current snapshots? |
| Page archetype | report catalog + generation drawer |
| MVP band | Near-MVP |
| Primary state objects | snapshot_pointers, report_templates, audit_events |
| Evidence pattern | Report header includes basis versions and unresolved-source warnings |
| Mobile behavior | Read-only PDF/report consumption |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- Global top bar: Home, Approvals, Projects, Reports, Admin, global search, role context.
- Primary surface: cockpit, list, report catalog, or administrative table depending on page.
- Right drawer: selected row/task/evidence/policy/audit detail.
- Persistent feedback: command receipts, background sync, notification status, and permission warnings.
- Page-specific sections: Report catalog; Template filters; Basis selector; Generation drawer; Export history.

## 4. Primary sections

- Report catalog
- Template filters
- Basis selector
- Generation drawer
- Export history

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `report_template` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `scope` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `basis_snapshot` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `freshness` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `unresolved_warnings` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `last_generated` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `available_formats` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Report purpose | Shows report purpose for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Required basis | Shows required basis for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Warnings that will be included | Shows warnings that will be included for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Export policy | Shows export policy for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Generation history | Shows generation history for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `generate_report` | Template scope selected; basis versions resolved. | Report job with basis manifest. |
| `export_snapshot_report` | Report generated from governed snapshot. | Export event audited. |
| `schedule_report` | User has scheduling permission. | Scheduled report config created. |
| `open_basis` | Basis object accessible. | No mutation; opens basis panel. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- export_raw_ai_summary
- omit_basis_from_report
- remove_unresolved_source_warning

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
- Mobile: Read-only PDF/report consumption
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
| P05-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P05-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P05-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P05-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P05-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Reports derive from governed snapshots.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
