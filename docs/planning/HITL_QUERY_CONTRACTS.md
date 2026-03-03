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

## 3) Artifact version summary rows
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

## 4) Pointer/current-official summary rows
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

## 5) Workflow run summary rows
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

## Notes for parallel UI work
- UI/board work can consume these contracts through either CLI or HTTP surfaces.
- These contracts intentionally mirror canonical table fields and avoid derived semantics that could create a second truth path.
- HTTP adapter implementation now exists and preserves this canonical field set while adding board-specific aggregates.

Contract stability tests now exist in:
- `tests/runtime/contracts/test_hitl_query_contracts_stage06.py`
