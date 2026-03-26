# EPIC-122 - Workflow-run-backed workpages (canonical run-backed schedule review + EOD draft resolution)

## Summary
Build the next workpage layer so the repo can graduate from curated demo-only workpage entrypoints to canonical **workflow-run-backed** workpage surfaces.

This epic is intentionally asymmetric:
- **schedule** becomes a run-backed, composite, query/read-only review page
- **EOD** becomes a run-backed landing/latest-draft-resolution page around the already-proven artifact-backed edit route

This epic is intentionally **not** the schedule write-path epic and **not** the broad workspace/task integration epic.

## Status
Active as of 2026-03-26. `TASK-0137` and `TASK-0138` are now complete, so the route family, alias posture, and minimal run-context/draft-resolution contract are frozen in repo-native docs and the first canonical run-backed schedule route plus generated snapshot now exist. `TASK-0139` is the next bounded implementation tranche.

## Scope
### In scope
- repo-native run-surfaces brief/plan and context pack
- workflow-run-backed workpage route-family freeze
- backend run-backed schedule workpage query route + generated snapshot
- backend run-backed EOD landing/latest-draft-resolution route + generated snapshot
- frontend migration to canonical `/runs/:workflowRunId/workpages/*` routes while preserving artifact-backed EOD editing handoff
- demo/story drilldown entrypoints and doc/status sync

### Out of scope
- schedule artifact-backed write path
- EOD final-packet / approval / pointer-promotion flow
- generic workpage builder/runtime
- broad workspace/human-task integration unless a bounded existing seam is already trivial and truthful
- live-dispatch day-of editing console
- per-keystroke autosave into `artifact_versions`

## Dependencies
- EPIC-120 (query-backed workpage surfaces already validated)
- EPIC-121 (first artifact-backed EOD slice already validated)
- EPIC-080 (frontend shell, route posture, and backend-owned contract snapshots)
- EPIC-030 (artifact lineage model remains canonical for the EOD edit lane)

## Recommended pattern cards (read cards first)
- `PATTERN-007`
- `PATTERN-009`

Context pack: `codex/context/EPIC-122.md`

## Current repo status / rationale
- Query-backed schedule/EOD workpage surfaces already exist under `/demo/logistics/workpages/*`.
- The first artifact-backed EOD create/read/submit lane is complete through `TASK-0136`.
- The repo already has immutable artifact lineage, download, and conflict handling for artifact-backed EOD editing.
- `TASK-0137` is now complete: the canonical backend run-backed workpage family, the canonical frontend run-backed route posture, and the `run_context` / `draft_resolution` boundary are all frozen in repo-native docs.
- The schedule page remains composite and should not be forced into one-artifact semantics in this epic.
- The EOD page already has the first artifact-backed write path, so the next EOD work is run-backed landing/latest-draft resolution rather than deeper write semantics.
- `/demo/logistics/workpages/*` remains a curated alias/entrypoint family until the canonical run-backed surfaces are implemented and proven.
- Legacy workspace/task surfaces still contain old schedule-centric assumptions and should not absorb this epic.

## Tasks
- TASK-0137 - DONE
- TASK-0138 - DONE
- TASK-0139 - TODO
- TASK-0140 - TODO
- TASK-0141 - TODO

## Red-team question
Are we still promoting workpages from demo-only surfaces to canonical workflow-run-backed surfaces, or are we quietly broadening into schedule writes, EOD finalization, or legacy workspace/task modernization before the workflow-native access model is proven?
