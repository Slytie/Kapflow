# P25 — Issue / Hypothesis Evidence Review

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Expansion |
| Primary role | PM, engineering, quality |
| Primary user question | What issue occurred, what hypotheses explain it, and what evidence closes it? |
| Page archetype | issue evidence chain + effectiveness closure |
| MVP band | Post-MVP |
| Primary state objects | issues, hypotheses, evidence, corrective_actions, effectiveness_tests |
| Evidence pattern | Hypothesis/evidence graph with closure states |
| Mobile behavior | Task-focused triage |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Issue list; Hypothesis/evidence chain; Corrective actions; Local closure; System/effectiveness verification; Reopen history.

## 4. Primary sections

- Issue list
- Hypothesis/evidence chain
- Corrective actions
- Local closure
- System/effectiveness verification
- Reopen history

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `issue` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `severity` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `hypothesis` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `evidence_state` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `corrective_action` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `local_closure` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `effectiveness_state` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `owner` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `reopen_trigger` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `basis` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Issue detail | Shows issue detail for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Hypothesis graph | Shows hypothesis graph for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Evidence links | Shows evidence links for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Corrective action proof | Shows corrective action proof for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Closure dimension | Shows closure dimension for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Effectiveness tests | Shows effectiveness tests for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit | Shows audit for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `create_hypothesis` | Issue selected; hypothesis statement entered. | Hypothesis object created. |
| `link_evidence` | Evidence reference resolved. | Evidence link event. |
| `close_local_defect` | Local fix evidence verified. | Local defect closure event. |
| `verify_effectiveness` | Effectiveness test evidence sufficient. | System/effectiveness closure event. |
| `reopen_issue` | New evidence or failed effectiveness trigger selected. | Issue reopened event. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- local_fix_equals_effectiveness
- close_issue_without_root_cause_or_waiver

Blocked-state copy should name the reason, the affected basis/evidence, and the next safe action.

## 9. Evidence requirements

| Evidence object | Basis required | Unresolved behavior |
|---|---|---|
| `basis_version_or_pointer` | Show the artifact/snapshot/basis generation supporting the visible state. | If unresolved, show unresolved-source warning and block truth-changing commands. |
| `freshness_or_stale_reason` | Show generated/reviewed timestamp and stale trigger count. | If stale, allow read-only drilldown and re-review task creation only. |
| `source_occurrence` | Show path/folder context, version, uploader, extraction and resolution state. | Unresolved occurrences cannot be used as reviewed evidence. |


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
- Mobile: Task-focused triage
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
| P25-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P25-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P25-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P25-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P25-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

K12 issue-evidence archetype extension.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
