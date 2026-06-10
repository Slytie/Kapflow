# P03 — Work Queue / Inbox

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Global |
| Primary role | All role clusters |
| Primary user question | Which bounded decisions or evidence tasks are assigned to me? |
| Page archetype | task worklist + evidence side panel |
| MVP band | MVP |
| Primary state objects | tasks, approvals, waivers, promotion_requests |
| Evidence pattern | Task row shows bound object, artifact version, policy result, evidence completeness |
| Mobile behavior | Primary mobile surface |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- Global top bar: Home, Approvals, Projects, Reports, Admin, global search, role context.
- Primary surface: cockpit, list, report catalog, or administrative table depending on page.
- Right drawer: selected row/task/evidence/policy/audit detail.
- Persistent feedback: command receipts, background sync, notification status, and permission warnings.
- Page-specific sections: Assigned task filters; Task list; Evidence side panel; Decision/action footer; Command receipt stream.

## 4. Primary sections

- Assigned task filters
- Task list
- Evidence side panel
- Decision/action footer
- Command receipt stream

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `task` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `type` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `bound_object` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `artifact_version` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `policy_result` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `evidence_completeness` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `priority` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `due_at` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `stale_token` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Decision summary | Shows decision summary for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Target artifact version | Shows target artifact version for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence basis | Shows evidence basis for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Policy checks | Shows policy checks for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Downstream effects | Shows downstream effects for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Decision actions | Shows decision actions for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit trail | Shows audit trail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `approve` | Approver role, current generation, policy checks visible, evidence basis available. | Approval response event; does not promote pointer unless explicit promotion command follows. |
| `reject_or_request_changes` | Reason provided; target version current. | Rejection/request-changes event and task update. |
| `request_evidence` | Bound object and evidence gap reason identified. | Evidence request task/flag created. |
| `comment` | User has comment permission. | Comment event attached to bound object. |
| `promote_pointer_when_task_bound` | Explicit promotion task, approval/policy pass, current generation. | Official pointer generation created. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- bulk_approve_without_evidence
- approve_stale_generation
- approve_and_promote_hidden

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
- Mobile: Primary mobile surface
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
| P03-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P03-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P03-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P03-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P03-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |
| P03-T06 | approval_promotion_separation | Approve eligible task. | Approval event is written; official pointer changes only after explicit promotion command/policy receipt. |


## 14. Design notes

Tasks handle decisions; workpages handle broad review.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
