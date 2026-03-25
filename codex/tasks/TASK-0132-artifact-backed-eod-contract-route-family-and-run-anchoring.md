---
id: TASK-0132
epic: EPIC-121
title: "Freeze the artifact-backed EOD workpage contract, route family, and canonical run anchoring"
status: DONE
owners: ["backend", "frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0131"]
risk: medium
context_packs: ["codex/context/EPIC-121.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0131`, the active schedule and EOD pages exist as server-authoritative query-backed routes.

The next batch needs one explicit contract freeze for the first artifact-backed write path before template-pack, route, or frontend implementation work starts.

## Objective
Freeze the first artifact-backed workpage contract and route family for the EOD slice, including:
- the canonical run/artifact anchoring rule,
- the write boundaries,
- the frontend route posture,
- and the explicit stop line for this epic.

## Non-goals
- No route implementation yet.
- No workbook template pack implementation yet.
- No frontend page migration yet.
- No schedule write-path design.
- No human-task/workspace integration unless it is already a trivial bounded reuse.

## Source files changed
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-121.md`
- `codex/context/EPIC-121.md`
- `docs/planning/LOGISTICS_WORKPAGES_ARTIFACT_PATH_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_ARTIFACT_PATH_BRIEF.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0133-dispatch-reporting-template-pack-registry-and-eod-workbook-adapter.md`
- `codex/tasks/TASK-0134-backend-eod-artifact-draft-projection-submit-routes-and-snapshots.md`
- `codex/tasks/TASK-0135-frontend-eod-artifact-workpage-route-migration.md`
- `codex/tasks/TASK-0136-demo-entrypoints-version-history-and-doc-sync-for-artifact-backed-eod.md`
- the task file itself

## Plan
1. Freeze the artifact-backed route family for EOD.
2. Make the canonical run-anchoring rule explicit.
3. Freeze the initial submit semantics, conflict rule, and stop line.
4. Record which parts remain demo-shell only versus later workflow/task integration.

## Verification
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The repo has one explicit contract/route-family decision for the first artifact-backed EOD path.
- The contract does not invent runless demo artifacts.
- The contract keeps schedule out of the write path.
- The task leaves `TASK-0133`..`TASK-0136` unblocked.

## Notes / decisions
Keep this task doc/contract-only. The first artifact-backed route family should leave room for future artifact-backed pages without pretending every current page already has a stable artifact identity.

## Outcome
- Added repo-native EPIC-121 planning/context memory and the artifact-path brief/plan.
- Froze the first artifact-backed EOD route family in `HITL_HTTP_API_CONTRACTS.md`:
  - `POST /api/v1/workpages/demo/eod-v0/drafts`
  - `GET /api/v1/workpages/artifacts/{artifact_version_id}`
  - `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`
- Made canonical run anchoring explicit: the first artifact-backed EOD drafts must live inside a canonical `dispatch_reporting.v1` workflow run; no runless demo artifact lane is allowed.
- Froze explicit create/submit conflict semantics while keeping schedule query-backed and composite in this epic.
- Queued `TASK-0133` as the next implementation tranche for the reporting template pack, multi-workflow template registry support, and workbook adapter tests.
