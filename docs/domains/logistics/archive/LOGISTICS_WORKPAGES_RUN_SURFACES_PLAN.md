> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# Logistics workpages run surfaces - repo-grounded implementation plan

## Why this exists
After the first workpage tranche and the first artifact-backed EOD slice, the repo now has:
- query-backed workpage pages under `/demo/logistics/workpages/*`,
- an artifact-backed EOD draft/create/read/submit loop,
- and bounded recent-version/history affordances around that EOD slice.

This document now records the implemented workflow-native access model that graduated workpages beyond demo-only discovery.

## Repo-grounded constraints that shape this epic
### 1) Demo workpages are not the final access model
The current workpage surfaces are discovered from the logistics demo shell. That is useful for curation and demos, but it is not the final workflow-native surface.

Implication:
- keep `/demo/logistics/workpages/*` as compatibility aliases,
- but use canonical workflow-run-backed routes for real workpage access.

### 2) Schedule is composite
The schedule page is still a composite projection over weekly-planning inputs and selected-day preview state.

Implication:
- do not force schedule into one-artifact or write-path semantics in this epic,
- implement a run-backed **read/query** schedule route instead.

### 3) EOD already has the first artifact-backed write path
The repo already has:
- `POST /api/v1/workpages/demo/eod-v0/drafts`
- `GET /api/v1/workpages/artifacts/{artifact_version_id}`
- `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`

Implication:
- the next EOD work is not to deepen artifact writes,
- it is to add a canonical **run-backed landing/latest-draft-resolution** surface around the existing artifact route.

### 4) Legacy workspace/task surfaces are still not the right entry seam
The repo still contains legacy schedule/workspace assumptions and should not absorb a broad workpage integration project in the same epic.

Implication:
- prefer workflow-run-backed routes over broad workspace/human-task integration in this epic.

## Frozen route posture from TASK-0137
### Backend canonical route family
- `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}`
- `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`

Keep the existing artifact-backed EOD routes unchanged:
- `GET /api/v1/workpages/artifacts/{artifact_version_id}`
- `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`

### Frontend canonical route family
- `/runs/:workflowRunId/workpages/schedule-v0`
- `/runs/:workflowRunId/workpages/eod-v0`
- `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`

Keep the current demo routes as compatibility aliases while the canonical run-backed surfaces are introduced and proven.

Implemented in `TASK-0140`:
- the frontend now serves `/runs/:workflowRunId/workpages/schedule-v0`
- the frontend now serves `/runs/:workflowRunId/workpages/eod-v0`
- the frontend now serves `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`
- `/demo/logistics/workpages/*` remains in place as a compatibility alias family
- artifact-backed submit/conflict handoff routes now point at canonical nested `/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}` pages

Implemented in `TASK-0141`:
- `/demo/logistics` now exposes canonical run-backed workpage links as the primary discoverable header actions
- weekly-planning and dispatch-reporting family-node drilldowns now expose run-specific canonical workpage CTAs
- `/demo/logistics/workpages/*` remains a clearly labeled compatibility-alias family rather than the primary access model

## Contract freeze from TASK-0137
The existing `WorkpageContract` remains the right inner contract for the page body. EPIC-122 freezes only the smallest additions needed for canonical run-backed usage:
- add optional `run_context` for run-backed surfaces,
- add EOD-only `draft_resolution` on the run-backed landing response,
- do **not** add a generic `actions` blob in this task,
- do **not** overload `artifact_context` on a run-backed landing page if the page is not itself an artifact projection.

### Run-backed schedule route
Build from a real `weekly_schedule_planning.v1` workflow run and the run's canonical weekly-planning source material / derived bundle state.

Implemented in `TASK-0138`:
- `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0`
- backend-generated snapshot `fixtures/frontend_contracts/workpage_schedule_v0_run_state.json`

Important guardrails:
- do not serve the human-authored workpage fixture verbatim,
- do not treat the logistics story board summary as the only truth,
- do not let selected-day preview semantics drift into live-dispatch ownership.

### Run-backed EOD landing route
Build from a real `dispatch_reporting.v1` workflow run and expose:
- the current landing/review contract,
- whether a draft workbook already exists for that run,
- the latest editable artifact version if it exists,
- and the canonical artifact-backed route needed to reopen that draft.

Implemented in `TASK-0139`:
- `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0`
- `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`
- backend-generated snapshots `fixtures/frontend_contracts/workpage_eod_v0_run_state.json` and `fixtures/frontend_contracts/workpage_eod_v0_run_artifact_create_response.json`

Important guardrails:
- keep actual editing on the existing artifact-backed route,
- do not quietly switch to final-packet semantics,
- do not invent runless or detached artifact discovery.

## Snapshot policy
Backend-generated snapshots should cover:
- the run-backed schedule workpage route,
- the run-backed EOD landing/draft-resolution route,
- and any new response shapes needed for frontend migration.

These belong under `fixtures/frontend_contracts/` because they are backend-generated API fixtures. Human-authored planning/oracle workpage fixtures remain under `fixtures/logistics/workpages/`.

## Epic task order
1. `TASK-0137` - DONE
2. `TASK-0138` - DONE
3. `TASK-0139` - DONE
4. `TASK-0140` - DONE
5. `TASK-0141` - DONE

## Explicit non-goals
- no schedule write/materialize path
- no generic artifact editor expansion
- no final-packet approval or pointer-promotion flow
- no live-dispatch operational page
- no broad legacy workspace/task modernization

## Documentation maintenance rules for this epic
Every task in this epic must update repo-native memory in the same change set when visible route truth changes.

Minimum docs to review/update when touched:
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- the matching `codex/tasks/TASK-....md` file

Update these too when the change affects them:
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`

## Red-team guardrails
- Do not start schedule write-path work in this epic.
- Do not broaden into final-packet/approval semantics for EOD.
- Do not collapse run-backed landing and artifact-backed editing into one ambiguous route.
- Do not route this epic through the legacy workspace/task surfaces unless a bounded seam is already truly ready.
- Do not let demo aliases disappear before canonical run-backed routes are proven.
- Do not blur human-authored workpage fixtures with backend-generated frontend contract snapshots.
