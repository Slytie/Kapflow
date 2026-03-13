# EXECUTION_SESSION_RUNTIME_MODEL.md

## Purpose
This document defines the canonical execution-runtime slice introduced in TASK-0052.
It converts the bounded Stage06 OpenAI sandbox from an integration spike into first-class runtime truth.

## Canonical objects

### ExecutionSession
A canonical runtime row representing one bounded execution attempt attached to one workflow task.

Core identity and links:
- `execution_session_id`
- `workflow_run_id`
- `task_run_id`
- `execution_spec_id`

Lifecycle fields:
- `state`
- `owner_mode`
- `principal_actor`
- `budget`
- `tool_call_count`
- `created_at`, `updated_at`, `closed_at`

### ToolExecution
A canonical runtime row representing one concrete tool/model invocation inside an execution session.

Core identity and links:
- `tool_execution_id`
- `execution_session_id`

Lifecycle and audit fields:
- `tool_class`, `tool_name`
- `state`
- `idempotency_key`, `attempt_no`
- `policy_decision_id`
- `output_artifact_version_ids`
- `requested_at`, `completed_at`
- `error_code`

`tool_class` on `tool_executions` is the concrete runtime/executor identifier for the bounded attempt (for example an engine-specific OpenAI Responses runtime string). It is not the same vocabulary as authored `allowed_tool_classes` in `EXECUTION_PROFILE.yaml`, which remain capability-level control metadata. The mapping between the two belongs in the tool-class registry/runtime binding source, not in workflow authored allowlists.

### PolicyDecision
A canonical runtime row representing the explicit policy verdict for a guarded tool request.

Core fields:
- `policy_decision_id`
- `principal_actor`
- `decision` (`allow`, `deny`, `require_approval`)
- `reason_code`
- `required_approval_action`
- `tool_execution_id`
- `decided_at`

## Canonical linkage
- one `execution_session` belongs to exactly one `workflow_run` and `task_run`
- one `execution_session` may have many `tool_executions`
- one `tool_execution` has at most one `policy_decision`
- execution evidence may link directly to `execution_session`, `tool_execution`, and `policy_decision` via canonical `artifact_links`
- model evidence remains canonical artifact truth via immutable `artifact_versions`
- workflow truth remains canonical task/workflow rows and events (no side state in API/frontend/helpers)

## State transitions

### ExecutionSession
Allowed transitions used in this slice:
- `CREATED -> WAITING_POLICY`
- `WAITING_POLICY -> RUNNING` (explicit policy-allow transition)
- `RUNNING -> SUCCEEDED`
- `RUNNING -> FAILED`
- `RUNNING -> WAITING_APPROVAL`
- `WAITING_APPROVAL -> FAILED` (reconcile timeout fallback)

Terminal states:
- `SUCCEEDED`, `FAILED`, `CANCELED`

### ToolExecution
Allowed transitions used in this slice:
- `REQUESTED -> APPROVED`
- `REQUESTED -> DENIED`
- `APPROVED -> COMPLETED`
- `APPROVED -> FAILED`

Terminal states:
- `COMPLETED`, `FAILED`, `DENIED`, `CANCELED`

## Event emission rules
Canonical row changes emit authoritative timeline events in the same transaction:
- session create/transition:
  - `execution.session.created`
  - `execution.session.state_changed`
- tool request/decision/completion:
  - `tool.execution.requested`
  - `tool.execution.approved`
  - `tool.execution.denied`
  - `tool.execution.completed`

Runtime enforcement now validates event-type required-link semantics at append time using `schemas/events/event_type_registry.yaml`.
For execution events this means:
- `execution.session.created` must include `execution_spec` links,
- execution tool/policy events must include all required execution-facet links defined by registry.

No execution lifecycle truth is kept only in logs.

## Idempotency strategy
- command-level idempotency is explicit and required on mutation commands
- event idempotency keys remain the hard duplicate barrier
- Stage06 sandbox builds deterministic IDs from `(workflow_run_id, task_run_id, base_idempotency_key)` for:
  - `execution_session_id`
  - `tool_execution_id`
  - `policy_decision_id`
- replaying the same Stage06 idempotency key therefore fails closed (`duplicate_execution_request`) instead of duplicating canonical effects

## Session activation/completion rules (Stage06 bounded path)
1. create execution session (`WAITING_POLICY`)
2. request tool execution (`REQUESTED`)
3. evaluate policy decision (`allow`/`deny`/`require_approval`)
4. on `allow`, transition session to `RUNNING`
5. if allowed, execute bounded OpenAI classifier
6. persist evidence artifact version
7. complete tool execution (`COMPLETED` or `FAILED`)
8. complete workflow task through canonical task handler
9. transition execution session to `SUCCEEDED` (or `FAILED` on any mapped failure)

## Failure mapping
- policy deny/require-approval:
  - tool transitions to `DENIED`
  - session transitions to `FAILED` or `WAITING_APPROVAL`
- model/provider/config failure:
  - tool transitions to `FAILED` with `error_code`
  - session transitions to `FAILED`
- downstream workflow mutation failure after model success:
  - session transitions to `FAILED`
  - tool state remains canonical (`COMPLETED` if evidence persisted and tool step succeeded)

## Recovery / reconcile behavior
`maintenance reconcile-executions` provides first-pass recovery for stale open sessions.

Current behavior:
- detect stale sessions in non-terminal states
- fail open `tool_executions` (`REQUESTED`/`APPROVED`/`RUNNING`) with timeout error
- transition session to `FAILED`
- emit canonical failure events without duplicating already-terminal effects
- preserve already-completed tool/evidence effects (no duplicate `tool.execution.completed` or `artifact.version.created` on reconcile)

This is bounded and intentionally minimal for TASK-0052.

## Audit and evidence linkage
- policy decisions are persisted as canonical rows and linked to tool executions
- tool executions store output artifact IDs for evidence traceability
- evidence artifacts include execution IDs in metadata and can attach directly to execution facets:
  - `execution_session_id`
  - `tool_execution_id`
  - `policy_decision_id`
- pinned execution-semantics evidence is persisted as immutable artifacts:
  - `execution.compiled_spec.json`
  - `execution.compile_source_manifest.json`
- reusable helper surface for future agent traces lives in `src/onetruth/application/services/execution_evidence.py`
- Stage06 and weekly Stage04 now share the same helper surface for stable execution IDs, evidence-artifact persistence, and artifact-root resolution.
- Stage06 compiled execution semantics are now derived from the authored Stage06 execution profile plus a registry-backed runtime tool binding, while preserving the same bounded single-call sandbox behavior.
- local/dev/test artifact-root policy:
  - `ONETRUTH_ARTIFACT_ROOT` should point at a temp/output-specific local path when a run needs isolated evidence bytes,
  - default fallback `.onetruth_artifacts/` is local live evidence only and must never be treated as fixture/source authority,
  - if evidence should become a reusable fixture, copy/promote it explicitly into `fixtures/` instead of reading it back from the live artifact root.
- authoritative reconstruction uses runtime rows + timeline events + artifact versions

## Bounded OpenAI fit and explicit out-of-scope
In scope:
- one bounded Stage06 classifier tool call path through canonical execution rows

Out of scope:
- generalized multi-agent orchestration
- open-ended tool loops/web-search/MCP
- execution operator UI
- generalized policy engine framework beyond explicit bounded rules needed here
