# HITL_HTTP_API_CONTRACTS.md

Stable HTTP contracts for the thin HITL adapter over canonical runtime/query surfaces.

These contracts are:
- server-authoritative projections over canonical runtime truth,
- machine-parseable JSON for board/list/detail UIs,
- intentionally narrow to avoid a duplicate semantics layer.

## 1) Base path and request context headers
Base path:
- `/api/v1`

Required request headers:
- `x-onetruth-tenant-id`
- `x-onetruth-domain-id`
- `x-onetruth-actor-id`
- `x-onetruth-actor-type` (`human|agent|service|system`)
- `x-onetruth-actor-roles` (comma-separated)

Scope enforcement:
- every request is filtered/validated by `(tenant_id, domain_id)` from headers,
- cross-scope detail/mutation attempts fail closed,
- there is no global/unscoped fallback.

## 2) Response envelopes
Success:
- `{"status":"ok", ...}`

Error:
- `{"status":"error","error":{"code":"...","message":"...","details":{...}}}`

## 3) Read endpoint contracts
### 3.1 Human task queue
Endpoint:
- `GET /api/v1/human-tasks`

Filters:
- `workflow_run_id`, `state`, `stage_id`, `task_kind`, `assignee_actor_id`, `owner_role`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.human_tasks.list","human_tasks":[...],"page":{"limit":100,"offset":0}}`

Human-task row shape (`human_tasks[]`):
- `human_task_id`
- `workflow_run_id`
- `task_run_id`
- `task_kind`
- `state`
- `candidate_roles`
- `owner_role`
- `assignee_actor_id`
- `assignee_actor_type`
- `due_at`
- `escalation_at`
- `lease_version`
- `claimed_at`
- `claimed_until`
- `linked_approval_id`
- `reopen_count`
- `generation`
- `created_at`
- `updated_at`
- `task_run_state`
- `stage_id`
- `blocked_on_kind`
- `blocked_on_ref`
- `spawned_from_flag_id`

### 3.2 Approval queue
Endpoint:
- `GET /api/v1/approvals`

Filters:
- `workflow_run_id`, `state`, `approval_kind`, `required_role`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.approvals.list","approvals":[...],"page":...}`

Approval row shape (`approvals[]`):
- `approval_id`
- `workflow_run_id`
- `task_run_id`
- `approval_kind`
- `scope_kind`
- `scope_ref`
- `state`
- `requested_by_task_run_id`
- `candidate_roles`
- `required_role`
- `requested_at`
- `responded_at`
- `response_kind`
- `response_reason`
- `decided_by_actor_id`
- `decided_by_actor_type`
- `generation`
- `created_at`
- `updated_at`

### 3.3 Flag/issue queue
Endpoint:
- `GET /api/v1/flags`

Filters:
- `workflow_run_id`, `state`, `kind`, `severity`, `assigned_group`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.flags.list","flags":[...],"page":...}`

Flag row shape (`flags[]`):
- `flag_id`
- `workflow_run_id`
- `tenant_id`
- `domain_id`
- `workflow_id`
- `partition_key`
- `kind`
- `severity`
- `state`
- `summary`
- `details_json`
- `assigned_group`
- `created_at`
- `closed_at`
- `created_by_actor_id`
- `created_by_actor_type`
- `source_event_id`
- `dedupe_key`
- `updated_at`

### 3.4 Workflow run summaries
Endpoint:
- `GET /api/v1/workflow-runs`

Filters:
- `workflow_id`, `tenant_id`, `domain_id`, `state`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.workflow_runs.list","workflow_runs":[...],"page":...}`

Workflow run summary row shape:
- `workflow_run_id`
- `workflow_id`
- `workflow_version`
- `tenant_id`
- `domain_id`
- `partition_key`
- `logical_date`
- `activation_key`
- `state`
- `created_at`
- `updated_at`
- `active_issue_count`

### 3.5 Workflow run detail
Endpoint:
- `GET /api/v1/workflow-runs/{workflow_run_id}`

Response:
- `{"status":"ok","command":"api.workflow_runs.detail","workflow_run":{...},"human_tasks":[...],"approvals":[...],"artifact_versions":[...],"pointers":[...],"flags":[...],"summary":{...}}`

### 3.6 Workflow run workspace (single-run)
Endpoint:
- `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`

Query:
- `timeline_limit` (optional, default `25`, max `200`)

Response:
- `{"status":"ok","command":"api.workflow_runs.workspace","workflow_run":{...},"graph":{...},"user_work":[...],"blocking_work":[...],"official_outputs":{...},"timeline_excerpt":{...},"freshness":{...}}`

Workspace response shape:
- `workflow_run` (canonical run summary row)
- `graph`
  - `nodes[]`
  - `edges[]`
  - `summary`
  - `latest_event_sequence`
  - `warnings[]`
- `user_work[]` (actionable items relevant to current actor)
- `blocking_work[]` (run-blocking open tasks/approvals/flags)
- `official_outputs` (current pointers + linked official artifact rows)
- `timeline_excerpt` (`events[]`, `event_count`)
- `freshness` (`latest_event_sequence`, `latest_event_recorded_at`, `workflow_run_updated_at`, `generated_at`)

Workspace item shape (`user_work[]`, `blocking_work[]`):
- `id` (stable item id)
- `subject_kind` (`human_task|approval|flag`)
- `subject_id`
- `canonical_state`
- `available_actions[]` (server-computed)
- `workpage_actions[]` (optional, additive, server-computed stage-linked workpage actions)
- `blocking_requirements[]` (server-computed)
- `linked_artifact_count`
- `missing_required_inputs[]`
- `can_complete`
- `can_upload_attachment`
- `can_run_stage06_agent_review`
- `metadata` (subject-specific rendering keys)

Stage-linked workpage action shape (`workpage_actions[]`, frozen in `TASK-0146`):
- lives only on workspace work items (`user_work[]`, `blocking_work[]`)
- does not live on `graph.nodes[]`
- does not add a separate top-level action map
- preserves existing `available_actions[]` for non-workpage inline mutations
- shape:
  - `action_id`
  - `workpage_kind`
  - `label`
  - `presentation` (`open_route|create_draft_then_open`)
  - `state` (`available|unavailable`)
  - `route` (canonical frontend route or `null`)
  - `create_path` (canonical API create path or `null`)
  - `subject_context` (`subject_kind`, `subject_id`, `workflow_run_id`)
  - `link_policy` (`create_relation_kind`, `submit_relation_kind`)
  - `disabled_reason`

Example:

```json
{
  "action_id": "workpage.schedule-v0.open_latest_draft",
  "workpage_kind": "schedule-v0",
  "label": "Open schedule draft",
  "presentation": "open_route",
  "state": "available",
  "route": "/runs/wr-123/workpages/schedule-v0/artifacts/av-456",
  "create_path": null,
  "subject_context": {
    "subject_kind": "human_task",
    "subject_id": "ht-123",
    "workflow_run_id": "wr-123"
  },
  "link_policy": {
    "create_relation_kind": null,
    "submit_relation_kind": "response"
  },
  "disabled_reason": null
}
```

Supported surface matrix (frozen in `TASK-0146`):

| Workflow | Surface | Supported subject | Action target | Presentation | Notes |
|---|---|---|---|---|---|
| `weekly_schedule_planning.v1` | `/runs/:workflowRunId/workspace` work items | human task `Stage04/work_item` | latest canonical schedule artifact route | `open_route` | Bounded Stage04 draft-edit lane. No create route exists. |
| `weekly_schedule_planning.v1` | `/runs/:workflowRunId/workspace` work items | human task `Stage05/information_request` | latest canonical schedule artifact route | `open_route` | Access is for draft review/edit context only. |
| `weekly_schedule_planning.v1` | `/runs/:workflowRunId/workspace` work items | human task `Stage05/final_review` | latest canonical schedule artifact route | `open_route` | Review access only, not publish or finalization. |
| `weekly_schedule_planning.v1` | `/runs/:workflowRunId/workspace` work items | approval `scope_ref=Stage06` | latest canonical schedule artifact route | `open_route` | Approval access stays distinct from approval response. |
| `dispatch_reporting.v1` | `/runs/:workflowRunId/workspace` work items | approval `scope_ref=Stage04` | latest canonical EOD artifact route if present, else canonical EOD create route | `open_route` or `create_draft_then_open` | Approval access only, no implicit approval response. |

Subject-link semantics (frozen in `TASK-0146`):
- `attachment` keeps existing upload/evidence semantics
- `draft` is reserved for in-progress workpage draft association and never satisfies required uploads, required reviews, approval response, or completion/finalization truth
- `response` is reserved for the new artifact version created by workpage submit and is the only workpage-linked relation kind that later tasks may allow to satisfy supported requirements
- `open_route` actions create no link by themselves
- weekly schedule actions freeze to `create_relation_kind=null` and `submit_relation_kind=response`
- dispatch-reporting approval actions freeze to `create_relation_kind=draft` and `submit_relation_kind=response`
- opening or submitting a workpage does not call `POST /api/v1/approvals/{id}/respond`
- `TASK-0146` does not add workpage actions to graph nodes, `/board`, `/my-work`, `/approvals`, `/runs/:workflowRunId` detail tabs, `/demo/logistics` story work items, `live_dispatch.v1`, Stage06 publish editing, Stage07 seed editing, or EOD finalization

### 3.7 Timeline feed
Endpoint:
- `GET /api/v1/timeline-events`

Filters:
- `workflow_run_id`, `event_type`, `since_sequence_no`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.timeline_events.list","events":[...],"page":...}`

Timeline row shape (`events[]`):
- `sequence_no`
- `event_id`
- `event_type`
- `occurred_at`
- `recorded_at`
- `tenant_id`
- `domain_id`
- `actor`
- `links`
- `payload`

### 3.8 Pointer/current-official summaries
Endpoint:
- `GET /api/v1/pointers`

Filters:
- canonical-first: `pointer_id`, `dataset_key`, `partition_kind`, `partition_key`, `stream_key`, `registry_kind`
- compatibility: `workflow_run_id`
- additional narrowing: `pointer_key`, `scope_kind`, `scope_ref`, `artifact_kind`
- pagination: `limit`, `offset`

Response:
- `{"status":"ok","command":"api.pointers.list","pointers":[...],"page":...}`

Pointer row shape:
- `pointer_id`
- `workflow_run_id`
- `pointer_key`
- `tenant_id`
- `domain_id`
- `dataset_key`
- `partition_kind`
- `partition_key`
- `stream_key`
- `registry_kind`
- `scope_kind`
- `scope_ref`
- `artifact_kind`
- `artifact_version_id`
- `promotion_reason`
- `promoted_by_task_run_id`
- `approved_by_approval_id`
- `generation`
- `updated_at`

### 3.9 Schedule-planning board aggregate
Endpoint:
- `GET /api/v1/board/schedule-planning`

Surface classification:
- legacy/internal regression surface for schedule-only flows
- primary logistics demo/product surface remains `GET /api/v1/stories/logistics-three-workflow` and frontend route `/demo/logistics`

Common filters:
- `workflow_run_id`, `workflow_id`, `workflow_state`
- task filters: `stage_id`, `task_kind`, `task_state`, `assignee_actor_id`, `owner_role`
- approval filters: `approval_state`, `approval_kind`, `required_role`
- pointer filters: `scope_kind`, `scope_ref`, `artifact_kind`
- pagination: `limit`, `offset`

Response:
- `{"status":"ok","command":"api.board.schedule_planning","board":{...}}`

Board object shape:
- `board_id`
- `filters`
- `lanes[]` (`lane`, `label`, `position`, `card_count`)
- `cards[]` (`card_type`: `human_task|approval`)
- `page`
- `workflow_runs[]`
- `pointers[]`
- `summary`

### 3.10 Workpage surfaces
Route-family decision:
- implemented today:
  - `GET /api/v1/workpages/demo/{workpage_id}`
  - `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0`
  - `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0`
  - `POST /api/v1/workpages/demo/eod-v0/drafts`
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`
  - `GET /api/v1/workpages/artifacts/{artifact_version_id}`
  - `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`

The `demo` subfamily is implemented today. After EPIC-122 it remains a compatibility-alias family, not the primary or long-term canonical access model. The canonical frontend run-backed pages now live under `/runs/:workflowRunId/workpages/*`. After EPIC-123, the implemented artifact-backed family now covers both EOD (`reporting.upd_draft.workbook`) and the bounded Stage04 schedule draft lane (`planning.draft_weekly_schedule.workbook`), while Stage06 publish, Stage07 seeds, and live-dispatch remain out of scope.

`TASK-0146` does not add any new workpage routes. Stage-linked workpage access remains an additive workspace projection over these existing canonical families rather than a second route family or second shell.

`TASK-0147` keeps the write-boundary seam on these same routes. Supported stage-linked create/submit flows may now accept one optional `subject_link` object; callers do not supply raw `links[]` or `relation_kind`, and the server derives relation-kind semantics from the specific workpage flow.

Current planned demo workpage ids:
- `schedule-v0`
- `eod-v0`

Demo query response:
- `{"status":"ok","command":"api.workpages.demo","workpage":{...},"source":{...},"freshness":{...}}`

Workflow-run-backed query response (implemented today for `schedule-v0` and `eod-v0`):
- `{"status":"ok","command":"api.workpages.workflow_run","workpage":{...},"source":{...},"freshness":{...},"run_context":{...},"draft_resolution":null|{...}}`

Artifact-backed read response:
- `{"status":"ok","command":"api.workpages.artifact","workpage":{...},"source":{...},"freshness":{...},"artifact_context":{...}}`

Workpage object shape (`workpage`):
- `workpage_id`
- `version`
- `title`
- `mode`
- `workflow_id`
- `dataset_key`
- `source_artifact_version_id`
- `source_examples`
- `summary`
- `sections`
- `validation`

Source metadata shape (`source`):
- `mode` (`demo|artifact_projection|run_projection`)
- `primary_dataset_key`
- `source_dataset_keys[]`
- `source_artifact_version_id`
- `source_refs[]`

Freshness metadata shape (`freshness`):
- `generated_at`
- `source_kind`
- `source_version`

Run context shape (`run_context`, run-backed surfaces only):
- `workflow_run_id`
- `workflow_id`
- `workflow_version`
- `partition_key`
- `logical_date`
- `activation_key`
- `state`

Artifact context shape (`artifact_context`):
- `artifact_version_id`
- `workflow_run_id`
- `artifact_kind`
- `supersedes_artifact_version_id`
- `superseded_by_artifact_version_id`
- `latest_in_chain_artifact_version_id`
- `download_path`

Draft resolution shape (`draft_resolution`, run-backed EOD landing only):
- `state` (`no_draft|latest_draft_available`)
- `latest_artifact_version_id`
- `artifact_route`

Notes:
- The schedule page is composite and may set `primary_dataset_key` to `null` while populating `source_dataset_keys[]`.
- The EOD page should remain aligned to `reporting.upd_draft.workbook`, not final-packet semantics.
- The artifact-backed workpage family now supports both the EOD workbook lane and the bounded Stage04 schedule draft workbook lane.
- Run-backed schedule responses should set `run_context` and leave `draft_resolution=null`.
- The implemented run-backed schedule route currently lives at `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0`.
- The implemented run-backed schedule route uses `source.mode=run_projection`, keeps `source_artifact_version_id=null`, and uses `freshness.source_kind=workflow_run_projection` plus `freshness.source_version=bundle.bundle_id`.
- If a weekly run does not yet have the required Stage04 input artifacts, the run-backed schedule route should fail cleanly with `409 workpage_projection_unavailable` and explicit missing dataset keys rather than falling back to demo defaults.
- The implemented schedule artifact-backed slice is anchored to `planning.draft_weekly_schedule.workbook` on canonical frontend route `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`, reusing the existing generic artifact-backed `GET /api/v1/workpages/artifacts/{artifact_version_id}` and `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit` family.
- Do **not** add `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/drafts`; Stage04 already materializes the initial draft workbook.
- In the implemented schedule slice, `planning.manager_review.doc` remains evidence only, while `planning.published_weekly_schedule.workbook` and `planning.daily_dispatch_seed.*` remain outside the edit surface.
- Run-backed EOD landing responses should set `run_context` plus `draft_resolution`, but must not pretend to be artifact projections.
- The implemented run-backed EOD landing route currently lives at `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0`.
- The implemented run-backed EOD landing route intentionally reuses the validated read-only EOD landing body, sets `source.mode=run_projection`, keeps `source.source_artifact_version_id=null`, and uses `freshness.source_kind=workflow_run_projection` plus `freshness.source_version=<latest_compatible_draft_artifact_version_id|workflow_run_id>`.
- The implemented run-backed EOD landing route resolves `draft_resolution` from the newest compatible `reporting.upd_draft.workbook` artifact in the supplied workflow run and leaves `artifact_context` absent.
- `artifact_context` is reserved for `source.mode=artifact_projection`; do not overload it on run-backed landing pages.
- `TASK-0137` intentionally freezes a narrow `draft_resolution` field instead of a generic `actions` blob.
- Artifact-backed EOD reads must remain projections over canonical workbook artifacts; the workpage is derived and the workbook artifact version remains authoritative truth.
- Artifact-backed EOD drafts must be anchored to canonical `dispatch_reporting.v1` workflow runs. No runless demo artifact store is allowed.
- The implemented EOD route is intentionally built from an intentionally partial example family, so its authoritative demo-query summary values are source-derived partial totals with explicit formula-integrity warnings rather than fixture-only full-day numbers.
- Demo workpage routes must be backend-built from authoritative example/source inputs, not by serving the human-authored workpage YAML fixtures verbatim.
- Backend-generated workpage route snapshots belong under `fixtures/frontend_contracts/`; human-authored workpage planning fixtures remain under `fixtures/logistics/workpages/`.

### 3.11 Artifact/document rows and downloads
Endpoints:
- `GET /api/v1/artifacts`
- `GET /api/v1/artifacts/{artifact_version_id}`
- `GET /api/v1/artifacts/{artifact_version_id}/download`

Subject-linked read endpoints:
- `GET /api/v1/human-tasks/{human_task_id}/artifacts`
- `GET /api/v1/approvals/{approval_id}/artifacts`
- `GET /api/v1/flags/{flag_id}/artifacts`
- `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts`

List filters (`GET /api/v1/artifacts`):
- `workflow_run_id`, `subject_kind`, `subject_id`, `artifact_kind`, `limit`, `offset`

Artifact row shape (`artifact_versions[]`):
- `artifact_version_id`
- `workflow_run_id`
- `task_run_id`
- `artifact_kind`
- `artifact_role`
- `media_type`
- `storage_uri`
- `content_digest`
- `byte_size`
- `metadata_json`
- `parent_artifact_version_id`
- `supersedes_artifact_version_id`
- `lineage_note`
- `created_at`
- `links[]` (`artifact_version_id`, `workflow_run_id`, `subject_kind`, `subject_id`, `relation_kind`, `created_at`, `created_by_actor_id`, `created_by_actor_type`)

Download response:
- `{"status":"ok","command":"api.artifacts.download","artifact_version":{...},"content_base64":"...","byte_size":123}`

Notes:
- downloads are artifact-backed (no alternate file subsystem),
- subject endpoints are convenience views over canonical `artifact_links`.

## 4) Mutation endpoint contracts
### 4.1 Claim human task
Endpoint:
- `POST /api/v1/human-tasks/{human_task_id}/claim`

Body:
- `lease_seconds`
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.human_tasks.claim","human_task_id":"...","result":{...}}`

### 4.2 Complete human task
Endpoint:
- `POST /api/v1/human-tasks/{human_task_id}/complete`

Body:
- `outcome`
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.human_tasks.complete","human_task_id":"...","result":{...}}`

### 4.3 Respond approval
Endpoint:
- `POST /api/v1/approvals/{approval_id}/respond`

Body:
- `response_kind`
- `response_reason`
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.approvals.respond","approval_id":"...","approval":{...}}`

### 4.4 Upload artifact/document attachment
Endpoints:
- `POST /api/v1/artifacts/ingest`
- `POST /api/v1/human-tasks/{human_task_id}/artifacts/upload`
- `POST /api/v1/approvals/{approval_id}/artifacts/upload`
- `POST /api/v1/flags/{flag_id}/artifacts/upload`
- `POST /api/v1/workflow-runs/{workflow_run_id}/artifacts/upload`

Body (subject upload):
- `artifact_kind`
- `artifact_role`
- `file_name`
- `media_type` (optional)
- `content_base64`
- `metadata_json` (optional)
- `relation_kind` (optional, default `attachment`)
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.<subject>.artifacts.upload","subject_kind":"...","subject_id":"...","artifact_version":{...},"ingress":{...}}`

Rules:
- upload creates canonical immutable artifact versions and emits authoritative events,
- no mutable/secondary attachment store is allowed,
- shared HTTP ingress accepts request bytes only; `source_path` and caller-selected `storage_root` are invalid on these endpoints,
- storage-root selection is server-owned on shared HTTP,
- scope checks apply to subject and workflow ownership before upload.

### 4.5 Create artifact-backed EOD draft
Endpoint:
- current implemented alias:
  - `POST /api/v1/workpages/demo/eod-v0/drafts`
- implemented canonical EPIC-122 route:
  - `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`

Body:
- `idempotency_key`
- `subject_link` (optional on the canonical run-backed route only; object with `subject_kind` and `subject_id`)

Response:
- current implemented alias response:
  - `{"status":"ok","command":"api.workpages.eod_drafts.create","draft":{"workflow_run_id":"...","artifact_version_id":"...","route":"/demo/logistics/workpages/eod-v0/artifacts/{artifact_version_id}"}}`
- implemented canonical EPIC-122 response:
  - `{"status":"ok","command":"api.workpages.eod_drafts.create","draft":{"workflow_run_id":"...","artifact_version_id":"...","route":"/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}"}}`

Rules:
- resolve or create the canonical demo `dispatch_reporting.v1` run for the known example slice,
- the run-backed EPIC-122 create route must resolve drafts only inside the supplied canonical workflow run,
- instantiate a new `reporting.upd_draft.workbook` artifact version from the reporting template pack,
- do not create runless demo artifacts,
- keep the demo create route as a compatibility alias until the canonical run-backed surfaces are proven,
- keep create semantics explicit and idempotent,
- the demo alias rejects `subject_link` with `invalid_workpage_subject_link`,
- the canonical run-backed create route accepts `subject_link` only for supported `dispatch_reporting.v1` Stage04 approval surfaces,
- callers do not supply `relation_kind`; the server derives `draft`,
- same-run subject validation still fails closed as `cross_workflow_link_reference`.

### 4.6 Submit artifact-backed workpage draft
Endpoint:
- `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`

Body:
- workpage edit fields:
  - `form_values` + `checklist_values[]` for EOD
  - `rows` + `reserve_rows` for schedule
- `subject_link` (optional; object with `subject_kind` and `subject_id` on supported surfaces only)
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.workpages.artifact.submit","submitted":{"workflow_run_id":"...","artifact_version_id":"...","supersedes_artifact_version_id":"...","route":"/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}"}}`

Conflict error:
- `{"status":"error","error":{"code":"workpage_artifact_conflict","message":"...","details":{"artifact_version_id":"...","latest_artifact_version_id":"...","workflow_run_id":"...","route":"/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}"}}}`

Rules:
- submit creates a **new immutable** workbook artifact version,
- the new version must set `supersedes_artifact_version_id` to the submitted base artifact version,
- explicit submit/save only; no per-keystroke artifact writes,
- the returned `route` now points at `/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}` so stale/conflict reopen and submit success stay inside the canonical nested workpage family,
- if the base artifact version has already been superseded in the same draft chain, fail closed with `workpage_artifact_conflict`,
- the shared submit route now covers both the implemented EOD draft lane and the bounded Stage04 schedule draft lane,
- supported `subject_link` surfaces stay frozen to the `TASK-0146` matrix; invalid or unsupported surfaces fail closed as `invalid_workpage_subject_link`,
- callers do not supply `relation_kind`; the server derives `response`,
- same-run subject validation still fails closed as `cross_workflow_link_reference`,
- final-packet approval/pointer semantics remain out of scope for this epic.

### 4.7 Run bounded Stage06 OpenAI review sandbox
Endpoint:
- `POST /api/v1/human-tasks/{human_task_id}/stage06-agent-review`

Body:
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.human_tasks.stage06_agent_review","human_task_id":"...","result":{...}}`

Result shape (`result`):
- `classification` (`outcome`, `rationale_summary`, `evidence_refs`, `suggested_follow_on_task_kind`)
- `model_metadata` (`response_id`, `request_id`, `model`, `usage`, `attempts`, `requested_at`, `completed_at`)
- `input_artifacts` (canonical input artifact refs used for model context)
- `evidence_artifact` (canonical artifact-version row for captured model evidence)
- `completion_result` (canonical `tasks.complete` result including spawned children)

Rules:
- this endpoint is intentionally narrow to Stage06 `review_packet` tasks,
- model output is schema-constrained and used only to select existing canonical completion outcome values,
- follow-on workflow truth is emitted only via existing completion/spawn handlers (no API-side workflow semantics).

## 5) Semantic rule
These HTTP contracts expose canonical state and transitions. They do not create a second semantics layer, and they do not make client-side workflow logic authoritative.
