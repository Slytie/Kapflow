# P20 — Tasks and Approvals

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | All role clusters |
| Primary user question | What decisions are pending for this project and what evidence supports them? |
| Page archetype | project-scoped queue + decision drawer |
| MVP band | MVP |
| Primary state objects | tasks, approvals, waivers, promotion_requests, command_receipts |
| Evidence pattern | Decision view includes target version, policy result, downstream effects |
| Mobile behavior | Primary mobile flow |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Project task filters; Approval route stages; Promotion requests; Waivers and residual-risk decisions; Command receipts.

## 4. Primary sections

- Project task filters
- Approval route stages
- Promotion requests
- Waivers and residual-risk decisions
- Command receipts

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `item` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `decision_type` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `bound_object` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `target_version` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `policy_result` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `evidence_status` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `route_stage` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `due_at` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `stale_token` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `receipt_status` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Task/approval detail | Shows task/approval detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Target artifact version | Shows target artifact version for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Policy checks | Shows policy checks for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence basis | Shows evidence basis for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Downstream effects | Shows downstream effects for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Decision actions | Shows decision actions for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Command receipt | Shows command receipt for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `approve` | Approver role, current generation, policy checks visible, evidence basis available. | Approval response event; does not promote pointer unless explicit promotion command follows. |
| `reject_or_request_changes` | Reason provided; target version current. | Rejection/request-changes event and task update. |
| `request_changes` | Decision task selected; reasons provided. | Changes requested event. |
| `promote_pointer` | Approval when required; policy pass; stale token valid; references resolved. | Official pointer generation. |
| `comment` | User has comment permission. | Comment event attached to bound object. |
| `delegate_if_policy_allows` | Delegation permitted; substitute eligible. | Delegation event. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- approve_and_promote_in_one_hidden_step
- approve_stale_artifact
- skip_policy_explanation

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
- Mobile: Primary mobile flow
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
| P20-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P20-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P20-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P20-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P20-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |
| P20-T06 | approval_promotion_separation | Approve eligible task. | Approval event is written; official pointer changes only after explicit promotion command/policy receipt. |


## 14. Design notes

Approval does not equal official.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
