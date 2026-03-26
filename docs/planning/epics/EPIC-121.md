# EPIC-121 - First artifact-backed workpage slice (EOD draft/review on immutable workbook artifacts)

## Summary
Build the first artifact-backed workpage vertical slice so the repo can prove the original promise behind workpages:
- a workpage can be tied to a concrete spreadsheet artifact version,
- the page can save meaningful edits back into a **new immutable workbook artifact version**,
- and the workbook remains downloadable through the normal artifact path.

This epic is intentionally narrow:
- **page:** EOD workpage only
- **workflow:** `dispatch_reporting.v1`
- **artifact family:** `reporting.upd_draft.workbook`
- **surface:** logistics demo shell first

It is intentionally **not** the generic artifact-editor epic and **not** the schedule write-path epic.

## Status
Completed on 2026-03-25 through `TASK-0136`. The first bounded artifact-backed EOD slice now exists end to end in the logistics demo shell and repo-memory is synchronized to that visible truth.

## Scope
### In scope
- repo-native artifact-path brief/plan and context pack
- bounded multi-workflow template-registry support for reporting templates
- a minimal `dispatch_reporting.v1` template pack for `reporting.upd_draft.workbook`
- a bounded workbook adapter/materializer contract for the EOD slice
- artifact-backed EOD draft creation, projection, and submit routes
- backend-generated contract snapshots for those routes
- frontend migration of the EOD page to an artifact-backed route with submit/conflict/download/version-lineage UX
- demo-shell entrypoints and doc/status sync

### Out of scope
- schedule artifact-backed write path
- generic workpage runtime for every artifact family
- final-packet approval/pointer promotion flow
- human-task/workspace integration unless a bounded existing lane already supports it cleanly
- per-keystroke autosave to artifact versions
- spreadsheet-clone UX or formula-engine emulation

## Dependencies
- EPIC-120 (query-backed workpages already validated and complete through `TASK-0131`)
- EPIC-030 (artifact store + supersedes lineage already exist)
- EPIC-080 (logistics demo shell and frontend route posture already exist)

## Recommended pattern cards (read cards first)
- `PATTERN-007`
- `PATTERN-009`

Context pack: `codex/context/EPIC-121.md`

## Current repo status / rationale
- Query-backed workpage routes are complete through `TASK-0131`.
- `TASK-0132` has now frozen the first artifact-backed EOD route family, canonical run anchoring, and save/conflict boundaries in repo-native docs.
- The existing `/demo/logistics/workpages/eod-v0` page remains the query-backed landing page; the artifact-backed page is a sibling route keyed by `artifact_version_id`.
- The repo already has canonical artifact version lineage via `supersedes_artifact_version_id`.
- The repo now has a bounded `dispatch_reporting.v1` template pack, multi-workflow template-registry support, and a first Stage03 workbook adapter/materializer seam through `TASK-0133`.
- `TASK-0134` through `TASK-0136` are complete: backend artifact draft/create/read/submit, frontend artifact-backed EOD editing, demo-shell entrypoints, and recent draft history are all implemented.
- `/demo/logistics` now exposes direct `Open EOD preview` and `Create editable EOD draft` entrypoints in the backend-demo-workpages header group.
- The artifact-backed EOD page now reads recent draft history from `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts`, filtered to the bounded `reporting.upd_draft.workbook` chain.
- The schedule page is still composite and remains query-backed in this epic.
- EPIC-121 is now closed as the first bounded artifact-backed workpage slice; the next move should be chosen as a new epic rather than by silently widening this one.

## Tasks
- TASK-0132 - DONE
- TASK-0133 - DONE
- TASK-0134 - DONE
- TASK-0135 - DONE
- TASK-0136 - DONE

## Red-team question
Are we still proving one bounded artifact-backed EOD path inside the canonical run/artifact model, or are we quietly broadening into a generic editor, schedule writes, or approval/final-packet semantics before the first immutable-write slice is stable?
