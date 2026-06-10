# P09 — Corpus Baseline

## 1. Page contract summary

| Field | Contract |
|---|---|
| Surface family | Core project |
| Primary role | PM, evidence reviewer |
| Primary user question | What evidence exists, what role does it play, and what is unresolved? |
| Page archetype | dense evidence table + packet review drawer |
| MVP band | MVP |
| Primary state objects | source_inventory, source_occurrence_register, artifact_role_assignments, artifact_packets |
| Evidence pattern | Document card exposes version, uploader, extraction, resolved-source state |
| Mobile behavior | Read-only artifact cards; task links |

## 2. Purpose

This page exists to answer the primary user question without allowing the user to confuse displayed state with official truth. It is a governed projection over CAPEX project state, evidence, tasks, approvals, and audit history.

Source anchors: SD-1, SD-2, SYS-1, INT-1, P1.

## 3. Layout zones

- ProjectStateBanner: project name, lifecycle context, forecastability, official snapshot version, stale/blocked indicators, open tasks/approvals.
- Secondary project navigation: Overview, Corpus, Lifecycle, Feasibility, Concept, Requirements, Budget, Commitments, Assumptions, Interfaces, Risk, Tasks, Handover, Evidence, Audit.
- Primary work area: dense table, matrix, cockpit, form, or timeline according to the page contract.
- Right-side detail drawer: selected row, evidence, policy checks, allowed/blocked commands, audit events.
- Footer/status area: last generated/reviewed time, saved view, export/report status, sync state when applicable.
- Page-specific sections: Source inventory; Source occurrence register; Duplicate groups; Artifact role assignments; Artifact packets; Unresolved/quarantined items.

## 4. Primary sections

- Source inventory
- Source occurrence register
- Duplicate groups
- Artifact role assignments
- Artifact packets
- Unresolved/quarantined items

## 5. Primary row/card model

| Column / field | Purpose | Evidence/state behavior |
|---|---|---|
| `artifact` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `occurrence` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `folder_context` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `inferred_role` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `reviewed_role` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `packet` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `version` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `extraction_status` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `resolved_source` | Supports the page question and table scanning. | Must link to evidence/basis where value affects decision. |
| `sensitivity` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |
| `last_action` | Supports the page question and table scanning. | Shows state label or opens drawer when decision-relevant. |


## 6. Detail drawer model

| Drawer section | Contents | Notes |
|---|---|---|
| Document preview | Shows document preview for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Occurrence context | Shows occurrence context for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Extracted claims | Shows extracted claims for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Version comparison | Shows version comparison for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Packet membership | Shows packet membership for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Role confirmation | Shows role confirmation for the selected object. | Preserve workpage context; deep comparison can route to a full page. |
| Audit | Shows audit for the selected object. | Preserve workpage context; deep comparison can route to a full page. |


## 7. Allowed commands

| Command | Preconditions | Write effects / result |
|---|---|---|
| `confirm_role` | Artifact occurrence selected; reviewer has evidence role permission. | Artifact role assignment reviewed event. |
| `merge_packet` | Packets selected; merge preview reviewed. | Packet grouping update draft/review event. |
| `split_packet` | Packet selected; split preview reviewed. | Packet grouping update draft/review event. |
| `quarantine` | Reason provided; user permitted. | Artifact quarantine state and audit event. |
| `request_extraction` | Artifact not quarantined; extraction allowed. | Extraction job created. |
| `mark_irrelevant` | Reason provided. | Occurrence/project relevance state updated. |


## 8. Blocked shortcuts

These shortcuts must be visibly blocked in the UI and rejected by backend command policy:

- treat_file_as_truth
- ignore_duplicate_context
- extract_from_quarantined_file

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
- Mobile: Read-only artifact cards; task links
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
| P09-T01 | basis_visibility | Open page with seeded data. | All primary items show basis and freshness; items with unresolved refs are visually marked. |
| P09-T02 | drawer_evidence | Select a representative row. | Drawer opens without losing table context and includes evidence, policy checks, command panel, audit events. |
| P09-T03 | blocked_shortcut | Attempt shortcut via UI/API test harness. | UI explains blocker; backend command receipt rejects state mutation. |
| P09-T04 | stale_behavior | Inject stale trigger for page basis. | Page shows stale reason banner, disables/gates commands, and offers re-review task path. |
| P09-T05 | mobile_behavior | Open narrow viewport. | Mobile layout shows task/read-only drilldown according to contract; no required desktop-only command is hidden without route. |


## 14. Design notes

Foundation for all downstream workflows.

This page must not become a standalone source of truth. It is a workflow surface that submits governed commands and displays receipts, evidence, policy, state labels, and audit paths.
