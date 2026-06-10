# P06 — Admin / Settings

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Global |
| Primary role | Admin, system owner |
| Primary user question | How are roles, routes, policies, integrations, and terminology configured? |
| Page archetype | admin tables + policy drawers |
| MVP band | Post-MVP foundation |
| Primary state objects | rbac, approval_routes, policy_rules, integration_config |
| Evidence pattern | Every policy change audited and versioned |
| Mobile behavior | Read-only status; no full admin on mobile |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- Global top bar: Home, Approvals, Projects, Reports, Admin, global search, role context.
- Primary surface: cockpit, list, report catalog, or administrative table depending on page.
- Right drawer: selected row/task/evidence/policy/audit detail.
- Persistent feedback: command receipts, background sync, notification status, and permission warnings.
- Page-specific sections: Role and permission tables; Approval route configuration; Policy rule editor; Integration settings; Terminology settings; Audit of config changes.

## 4. Primary sections

- Role and permission tables
- Approval route configuration
- Policy rule editor
- Integration settings
- Terminology settings
- Audit of config changes

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `setting` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `scope` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `current_value` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `policy_version` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `last_changed_by` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `last_changed_at` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `risk_level` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Setting detail | Shows setting detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Policy effect | Shows policy effect for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Separation-of-duties impact | Shows separation-of-duties impact for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Change preview | Shows change preview for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit trail | Shows audit trail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `manage_roles` | Admin role; separation-of-duties policy allows change. | Role assignment proposal or policy event. |
| `configure_routes` | Admin role; route validation passes. | Approval route config draft/version. |
| `set_terms` | Admin role; terminology scope selected. | Terminology config version. |
| `submit_policy_change` | Policy change draft validates. | Policy review/approval task created. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- self_approve_permission
- disable_audit
- bypass_separation_of_duties

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
- Mobile: Read-only status; no full admin on mobile
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
| P06-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P06-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P06-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P06-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P06-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

RBAC and separation-of-duties must be visible.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
