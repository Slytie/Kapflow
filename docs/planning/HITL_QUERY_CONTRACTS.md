# HITL_QUERY_CONTRACTS.md

This document defines the first stable read contracts for future human-in-the-loop board/Kanban work.

These contracts are:
- read/query surfaces only,
- derived convenience views over canonical tables,
- intentionally narrow and machine-parseable.

Authoritative state remains:
- canonical current-state rows in runtime tables,
- authoritative timeline events in `timeline_events`.

## Contract source
Current source-of-truth read boundaries are:
- runtime CLI JSON outputs under `python3 -m onetruth.cli --db-url <db_url> ...`
- runtime HTTP JSON outputs under `/api/v1/*` (thin adapter over the same canonical runtime/query handlers)

HTTP contract details now live in:
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`

## 1) Human task queue rows
Command:
- `tasks list --workflow-run-id <id> --json`

Response envelope:
- `{"status":"ok","command":"tasks.list","tasks":[...]}`

Row shape (`tasks[]`):
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

## 2) Approval queue rows
Command:
- `approvals list --workflow-run-id <id> --json`

Response envelope:
- `{"status":"ok","command":"approvals.list","approvals":[...]}`

Row shape (`approvals[]`):
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

## 3) Exception/flag queue rows
Command:
- `flags list --workflow-run-id <id> --json`

Response envelope:
- `{"status":"ok","command":"flags.list","flags":[...]}`

Row shape (`flags[]`):
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

## 4) Artifact version summary rows
Command:
- `artifacts list --workflow-run-id <id> --json`

Response envelope:
- `{"status":"ok","command":"artifacts.list","artifact_versions":[...]}`

Row shape (`artifact_versions[]`):
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
- `links[]` (subject linkage rows for `workflow_run`, `human_task`, `approval`, `flag`)

Subject-linked artifact reads:
- `artifacts list-linked --workflow-run-id <id> --subject-kind <kind> --subject-id <id> --json`
- `GET /api/v1/human-tasks/{human_task_id}/artifacts`
- `GET /api/v1/approvals/{approval_id}/artifacts`
- `GET /api/v1/flags/{flag_id}/artifacts`
- `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts`

Attachment download surfaces:
- `artifacts download --artifact-version-id <id> --output-path <path> --json`
- `GET /api/v1/artifacts/{artifact_version_id}/download`

## 5) Pointer/current-official summary rows
Command:
- `pointers list --workflow-run-id <id> --json`

Response envelope:
- `{"status":"ok","command":"pointers.list","pointers":[...]}`

Row shape (`pointers[]`):
- `workflow_run_id`
- `pointer_key`
- `scope_kind`
- `scope_ref`
- `artifact_kind`
- `artifact_version_id`
- `promotion_reason`
- `promoted_by_task_run_id`
- `approved_by_approval_id`
- `generation`
- `updated_at`

## 6) Workflow run summary rows
Command:
- `runs list --json [--workflow-id <id>] [--tenant-id <id>] [--domain-id <id>] [--state <state>]`

Response envelope:
- `{"status":"ok","command":"runs.list","workflow_runs":[...]}`

Row shape (`workflow_runs[]`):
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

## 7) Timeline/event rows (HTTP)
Endpoint:
- `GET /api/v1/timeline-events`

Filters:
- `workflow_run_id`, `event_type`, `since_sequence_no`, `limit`, `offset`

Response envelope:
- `{"status":"ok","command":"api.timeline_events.list","events":[...],"page":...}`

Row shape (`events[]`):
- `sequence_no`
- `event_id`
- `event_type`
- `schema_version`
- `occurred_at`
- `recorded_at`
- `tenant_id`
- `domain_id`
- `actor`
- `links`
- `payload`
- optional: `correlation_id`, `causation_id`, `idempotency_key`, `integrity`

## 8) Workflow workspace projection rows (HTTP)
Endpoint:
- `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`

Response envelope:
- `{"status":"ok","command":"api.workflow_runs.workspace","workflow_run":{...},"graph":{...},"user_work":[...],"blocking_work":[...],"official_outputs":{...},"timeline_excerpt":{...},"freshness":{...}}`

Graph projection shape (`graph`):
- `nodes[]`
- `edges[]`
- `summary`
- `latest_event_sequence`
- `warnings[]`

Workspace action item shape (`user_work[]`, `blocking_work[]`):
- `id`
- `subject_kind`
- `subject_id`
- `canonical_state`
- `available_actions[]`
- `blocking_requirements[]`
- `linked_artifact_count`
- `missing_required_inputs[]`
- `can_complete`
- `can_upload_attachment`
- `can_run_stage06_agent_review`
- `metadata`

## Notes for parallel UI work
- UI/board work can consume these contracts through either CLI or HTTP surfaces.
- These contracts intentionally mirror canonical table fields and avoid derived semantics that could create a second truth path.
- HTTP adapter implementation now exists and preserves this canonical field set while adding board-specific aggregates and timeline feed endpoints for drawer/run-detail views.

Contract stability tests now exist in:
- `tests/runtime/contracts/test_hitl_query_contracts_stage06.py`
- `tests/runtime/contracts/test_hitl_query_contracts_stage07.py`

## Backend-owned frontend snapshots
Snapshot fixtures for parallel frontend work are exported from real scenario-backed runtime states:
- `fixtures/frontend_contracts/stage06_publish_ready_board_state.json`
- `fixtures/frontend_contracts/stage06_needs_information_state.json`
- `fixtures/frontend_contracts/stage07_major_replan_board_state.json`
- `fixtures/frontend_contracts/stage07_exception_branch_state.json`
- `fixtures/frontend_contracts/approval_queue_state.json`
- `fixtures/frontend_contracts/run_detail_state.json`
- `fixtures/frontend_contracts/timeline_state.json`
- `fixtures/frontend_contracts/official_outputs_pointers_state.json`

Refresh command:
- `make frontend-snapshots`

Drift check command:
- `PYTHONPATH=src python3 scripts/export_frontend_snapshots.py --check`

Snapshot contract test:
- `tests/runtime/contracts/test_frontend_snapshot_fixtures.py`

Example corpus seeding and ingress:
- corpus manifest: `fixtures/example_document_corpus/manifest.yaml`
- corpus loader/service: `src/onetruth/application/services/example_document_corpus.py`
- canonical seed command: `artifacts seed-corpus --json`
- canonical ingress command: `artifacts ingest --json`
