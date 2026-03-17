from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _prepare_command_receipt,
)
from onetruth.application.handlers.approvals import (
    list_approvals_for_workflow_run_command,
    request_approval_command,
    respond_approval_command,
    show_approval_command,
)
from onetruth.application.handlers.artifacts import (
    create_artifact_version_command,
    download_artifact_blob_command,
    ingest_artifact_document_command,
)
from onetruth.application.handlers.flags import (
    activate_stage07_issue_from_flag_command,
    create_flag_command,
    reconcile_stage07_command,
    transition_flag_state_command,
)
from onetruth.application.handlers.pointers import promote_pointer_command
from onetruth.application.read_commands import (
    list_artifacts_for_subject_command,
    list_artifacts_for_workflow_run_command,
    list_execution_sessions_for_workflow_run_command,
    list_flags_for_workflow_run_command,
    list_pointers_for_workflow_run_command,
    list_tasks_for_workflow_run_command,
    list_workflow_runs_command,
    show_artifact_version_command,
    show_execution_session_command,
    show_flag_command,
    show_human_task_command,
    show_pointer_command,
    show_policy_decision_command,
    show_tool_execution_command,
    show_workflow_run_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_execution_session_command,
    claim_human_task_command,
    complete_human_task_command,
    confirm_human_task_review_command,
    create_task_run_command,
    create_workflow_run_command,
    reconcile_executions_command,
    request_tool_execution_command,
    sweep_leases_command,
    transition_execution_session_state_command,
)
from onetruth.application.handlers.logistics_handoff import (
    activate_live_dispatch_command,
    list_edge_executions_command,
    materialize_weekly_seeds_command,
    notify_only_handoff_command,
    show_edge_execution_command,
)
from onetruth.application.handlers.schedule_control import (
    build_weekly_schedule_control_command,
)
from onetruth.application.projections.coherence_harness import (
    COHERENCE_POLICY_WARN_VISIBLE,
    COHERENCE_STATUS_FAILED,
    evaluate_handoff_operator_view_coherence,
    maybe_emit_projection_coherence_failed,
)
from onetruth.application.services.example_document_corpus import (
    load_example_document_corpus,
    seed_payloads_for_set,
)
from onetruth.infrastructure.artifacts.storage import (
    default_storage_root_for_db_url,
    encode_base64_content,
)
from onetruth.infrastructure.db.session import DEFAULT_DB_URL, open_sqlite_connection
from onetruth.infrastructure.events.event_store import (
    DuplicateEventIdError,
    DuplicateIdempotencyKeyError,
    append_event,
    create_command_receipt,
    create_sqlite_substrate,
    get_command_receipt,
    list_events,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _json_print(payload: Any, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, separators=(",", ":")) + "\n")


def _public_command_success_payload(
    *,
    command: str,
    command_result: dict[str, Any],
    result_key: str | None = None,
    flatten_result: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ok",
        "command": command,
        "idempotent_replay": bool(command_result["idempotent_replay"]),
        "receipt": command_result["receipt"],
    }
    raw_result = command_result["result"]
    if flatten_result:
        if not isinstance(raw_result, dict):
            raise TypeError(f"{command} expected a dict result for flatten_result")
        payload.update(raw_result)
        return payload
    if result_key is None:
        payload["result"] = raw_result
    else:
        payload[result_key] = raw_result
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="onetruthctl")
    parser.add_argument(
        "--db-url",
        default=os.environ.get("ONETRUTH_DB_URL", DEFAULT_DB_URL),
        help="SQLAlchemy database URL.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db = subparsers.add_parser("init-db", help="Run Alembic migrations up to head.")
    init_db.set_defaults(handler=_handle_init_db)

    events = subparsers.add_parser("events", help="Append and list canonical timeline events.")
    events_sub = events.add_subparsers(dest="events_command", required=True)
    events_append = events_sub.add_parser("append", help="Append one envelope event.")
    events_append.add_argument("--json", dest="json_payload", required=True, help="Full event envelope JSON.")
    events_append.set_defaults(handler=_handle_events_append)
    events_list = events_sub.add_parser("list", help="List envelope events.")
    events_list.add_argument("--run-id", default=None, help="Filter by workflow_run id.")
    events_list.add_argument("--since-event-id", default=None, help="List events after this event id.")
    events_list.add_argument("--limit", type=int, default=100, help="Maximum rows to return (1..1000).")
    events_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    events_list.set_defaults(handler=_handle_events_list)

    runs = subparsers.add_parser("runs", help="Workflow run lifecycle commands.")
    runs_sub = runs.add_subparsers(dest="runs_command", required=True)
    runs_create = runs_sub.add_parser("create", help="Create a workflow run.")
    runs_create.add_argument("--json", dest="json_payload", required=True)
    runs_create.set_defaults(handler=_handle_runs_create)
    runs_show = runs_sub.add_parser("show", help="Show one workflow run.")
    runs_show.add_argument("--workflow-run-id", required=True)
    runs_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    runs_show.set_defaults(handler=_handle_runs_show)
    runs_list = runs_sub.add_parser("list", help="List workflow runs.")
    runs_list.add_argument("--workflow-id", default=None)
    runs_list.add_argument("--tenant-id", default=None)
    runs_list.add_argument("--domain-id", default=None)
    runs_list.add_argument("--state", default=None)
    runs_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    runs_list.set_defaults(handler=_handle_runs_list)

    tasks = subparsers.add_parser("tasks", help="Task and human-task lifecycle commands.")
    tasks_sub = tasks.add_subparsers(dest="tasks_command", required=True)

    tasks_create = tasks_sub.add_parser("create", help="Create a task run and optional human task.")
    tasks_create.add_argument("--json", dest="json_payload", required=True)
    tasks_create.set_defaults(handler=_handle_tasks_create)

    tasks_claim = tasks_sub.add_parser("claim", help="Claim an open human task.")
    tasks_claim.add_argument("--json", dest="json_payload", required=True)
    tasks_claim.set_defaults(handler=_handle_tasks_claim)

    tasks_complete = tasks_sub.add_parser("complete", help="Complete a claimed human task.")
    tasks_complete.add_argument("--json", dest="json_payload", required=True)
    tasks_complete.set_defaults(handler=_handle_tasks_complete)

    tasks_confirm_review = tasks_sub.add_parser(
        "confirm-review",
        help="Create canonical review-confirmation evidence for a human task.",
    )
    tasks_confirm_review.add_argument("--json", dest="json_payload", required=True)
    tasks_confirm_review.set_defaults(handler=_handle_tasks_confirm_review)

    tasks_show = tasks_sub.add_parser("show", help="Show one human task.")
    tasks_show.add_argument("--human-task-id", required=True)
    tasks_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    tasks_show.set_defaults(handler=_handle_tasks_show)

    tasks_list = tasks_sub.add_parser("list", help="List human tasks for a workflow run.")
    tasks_list.add_argument("--workflow-run-id", required=True)
    tasks_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    tasks_list.set_defaults(handler=_handle_tasks_list)

    approvals = subparsers.add_parser("approvals", help="Approval lifecycle commands.")
    approvals_sub = approvals.add_subparsers(dest="approvals_command", required=True)
    approvals_request = approvals_sub.add_parser("request", help="Request an approval.")
    approvals_request.add_argument("--json", dest="json_payload", required=True)
    approvals_request.set_defaults(handler=_handle_approvals_request)
    approvals_respond = approvals_sub.add_parser("respond", help="Respond to an approval.")
    approvals_respond.add_argument("--json", dest="json_payload", required=True)
    approvals_respond.set_defaults(handler=_handle_approvals_respond)
    approvals_show = approvals_sub.add_parser("show", help="Show one approval.")
    approvals_show.add_argument("--approval-id", required=True)
    approvals_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    approvals_show.set_defaults(handler=_handle_approvals_show)
    approvals_list = approvals_sub.add_parser("list", help="List approvals for a workflow run.")
    approvals_list.add_argument("--workflow-run-id", required=True)
    approvals_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    approvals_list.set_defaults(handler=_handle_approvals_list)

    artifacts = subparsers.add_parser("artifacts", help="Artifact version commands.")
    artifacts_sub = artifacts.add_subparsers(dest="artifacts_command", required=True)
    artifacts_create = artifacts_sub.add_parser("create-version", help="Create an artifact version.")
    artifacts_create.add_argument("--json", dest="json_payload", required=True)
    artifacts_create.set_defaults(handler=_handle_artifacts_create_version)
    artifacts_ingest = artifacts_sub.add_parser(
        "ingest",
        help="Ingest document bytes and create an artifact version through canonical ingress.",
    )
    artifacts_ingest.add_argument("--json", dest="json_payload", required=True)
    artifacts_ingest.set_defaults(handler=_handle_artifacts_ingest)
    artifacts_show = artifacts_sub.add_parser("show", help="Show one artifact version.")
    artifacts_show.add_argument("--artifact-version-id", required=True)
    artifacts_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    artifacts_show.set_defaults(handler=_handle_artifacts_show)
    artifacts_list = artifacts_sub.add_parser("list", help="List artifact versions for a workflow run.")
    artifacts_list.add_argument("--workflow-run-id", required=True)
    artifacts_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    artifacts_list.set_defaults(handler=_handle_artifacts_list)
    artifacts_list_linked = artifacts_sub.add_parser(
        "list-linked",
        help="List artifact versions linked to a subject.",
    )
    artifacts_list_linked.add_argument("--workflow-run-id", required=True)
    artifacts_list_linked.add_argument("--subject-kind", required=True)
    artifacts_list_linked.add_argument("--subject-id", required=True)
    artifacts_list_linked.add_argument("--json", dest="json_output", required=True, action="store_true")
    artifacts_list_linked.set_defaults(handler=_handle_artifacts_list_linked)
    artifacts_download = artifacts_sub.add_parser("download", help="Download artifact bytes to a local file.")
    artifacts_download.add_argument("--artifact-version-id", required=True)
    artifacts_download.add_argument("--output-path", required=True)
    artifacts_download.add_argument("--json", dest="json_output", required=True, action="store_true")
    artifacts_download.set_defaults(handler=_handle_artifacts_download)
    artifacts_seed_corpus = artifacts_sub.add_parser(
        "seed-corpus",
        help="Seed a manifest-defined example document set through canonical artifact ingress.",
    )
    artifacts_seed_corpus.add_argument("--json", dest="json_payload", required=True)
    artifacts_seed_corpus.set_defaults(handler=_handle_artifacts_seed_corpus)

    pointers = subparsers.add_parser("pointers", help="Pointer promotion commands.")
    pointers_sub = pointers.add_subparsers(dest="pointers_command", required=True)
    pointers_promote = pointers_sub.add_parser("promote", help="Promote a pointer to an artifact version.")
    pointers_promote.add_argument("--json", dest="json_payload", required=True)
    pointers_promote.set_defaults(handler=_handle_pointers_promote)
    pointers_show = pointers_sub.add_parser("show", help="Show one pointer row.")
    pointers_show.add_argument("--pointer-key", required=True)
    pointers_show.add_argument("--workflow-run-id", required=True)
    pointers_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    pointers_show.set_defaults(handler=_handle_pointers_show)
    pointers_list = pointers_sub.add_parser("list", help="List pointers for a workflow run.")
    pointers_list.add_argument("--workflow-run-id", required=True)
    pointers_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    pointers_list.set_defaults(handler=_handle_pointers_list)

    handoffs = subparsers.add_parser("handoffs", help="Logistics weekly-to-live handoff commands.")
    handoffs_sub = handoffs.add_subparsers(dest="handoffs_command", required=True)
    handoffs_materialize = handoffs_sub.add_parser(
        "materialize-weekly-seeds",
        help="Materialize Stage07 daily seeds and edge execution rows for weekly->live handoff.",
    )
    handoffs_materialize.add_argument("--json", dest="json_payload", required=True)
    handoffs_materialize.set_defaults(handler=_handle_handoffs_materialize_weekly_seeds)
    handoffs_activate = handoffs_sub.add_parser(
        "activate-live-dispatch",
        help="Lazily activate live_dispatch.v1 from a prepared handoff edge execution.",
    )
    handoffs_activate.add_argument("--json", dest="json_payload", required=True)
    handoffs_activate.set_defaults(handler=_handle_handoffs_activate_live_dispatch)
    handoffs_notify = handoffs_sub.add_parser(
        "notify-only",
        help="Dispatch a generic notify_only logistics handoff edge using compiled family metadata.",
    )
    handoffs_notify.add_argument("--json", dest="json_payload", required=True)
    handoffs_notify.set_defaults(handler=_handle_handoffs_notify_only)
    handoffs_show = handoffs_sub.add_parser("show", help="Show one edge execution row.")
    handoffs_show.add_argument("--edge-execution-id", required=True)
    handoffs_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    handoffs_show.set_defaults(handler=_handle_handoffs_show)
    handoffs_list = handoffs_sub.add_parser("list", help="List edge execution rows.")
    handoffs_list.add_argument("--edge-id", default=None)
    handoffs_list.add_argument("--source-workflow-run-id", default=None)
    handoffs_list.add_argument("--target-workflow-run-id", default=None)
    handoffs_list.add_argument("--status", default=None)
    handoffs_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    handoffs_list.set_defaults(handler=_handle_handoffs_list)

    schedule_control = subparsers.add_parser(
        "schedule-control",
        help="Deterministic weekly/live schedule-control service commands.",
    )
    schedule_control_sub = schedule_control.add_subparsers(
        dest="schedule_control_command",
        required=True,
    )
    schedule_control_build_weekly = schedule_control_sub.add_parser(
        "build-weekly",
        help="Run deterministic Stage04 weekly schedule-control build and lower canonical artifacts.",
    )
    schedule_control_build_weekly.add_argument("--json", dest="json_payload", required=True)
    schedule_control_build_weekly.set_defaults(handler=_handle_schedule_control_build_weekly)

    flags = subparsers.add_parser("flags", help="Flag lifecycle commands.")
    flags_sub = flags.add_subparsers(dest="flags_command", required=True)
    flags_create = flags_sub.add_parser("create", help="Create a flag.")
    flags_create.add_argument("--json", dest="json_payload", required=True)
    flags_create.set_defaults(handler=_handle_flags_create)
    flags_transition = flags_sub.add_parser("transition", help="Transition a flag state.")
    flags_transition.add_argument("--json", dest="json_payload", required=True)
    flags_transition.set_defaults(handler=_handle_flags_transition)
    flags_show = flags_sub.add_parser("show", help="Show one flag row.")
    flags_show.add_argument("--flag-id", required=True)
    flags_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    flags_show.set_defaults(handler=_handle_flags_show)
    flags_list = flags_sub.add_parser("list", help="List flags for a workflow run.")
    flags_list.add_argument("--workflow-run-id", required=True)
    flags_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    flags_list.set_defaults(handler=_handle_flags_list)

    stage07 = subparsers.add_parser("stage07", help="Stage07 issue activation commands.")
    stage07_sub = stage07.add_subparsers(dest="stage07_command", required=True)
    stage07_activate = stage07_sub.add_parser(
        "activate-issue",
        help="Ensure a Stage07 issue task exists for an open flag.",
    )
    stage07_activate.add_argument("--json", dest="json_payload", required=True)
    stage07_activate.set_defaults(handler=_handle_stage07_activate_issue)

    execution_sessions = subparsers.add_parser(
        "execution-sessions",
        help="Execution session lifecycle commands.",
    )
    execution_sessions_sub = execution_sessions.add_subparsers(
        dest="execution_sessions_command",
        required=True,
    )
    execution_sessions_create = execution_sessions_sub.add_parser(
        "create",
        help="Create an execution session row and canonical events.",
    )
    execution_sessions_create.add_argument("--json", dest="json_payload", required=True)
    execution_sessions_create.set_defaults(handler=_handle_execution_sessions_create)
    execution_sessions_show = execution_sessions_sub.add_parser("show", help="Show one execution session.")
    execution_sessions_show.add_argument("--execution-session-id", required=True)
    execution_sessions_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    execution_sessions_show.set_defaults(handler=_handle_execution_sessions_show)
    execution_sessions_list = execution_sessions_sub.add_parser(
        "list",
        help="List execution sessions for a workflow run.",
    )
    execution_sessions_list.add_argument("--workflow-run-id", required=True)
    execution_sessions_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    execution_sessions_list.set_defaults(handler=_handle_execution_sessions_list)
    execution_sessions_transition = execution_sessions_sub.add_parser(
        "transition",
        help="Transition an execution session state.",
    )
    execution_sessions_transition.add_argument("--json", dest="json_payload", required=True)
    execution_sessions_transition.set_defaults(handler=_handle_execution_sessions_transition)

    tool_executions = subparsers.add_parser("tool-executions", help="Tool execution commands.")
    tool_executions_sub = tool_executions.add_subparsers(dest="tool_executions_command", required=True)
    tool_executions_request = tool_executions_sub.add_parser(
        "request",
        help="Request a tool execution under an execution session.",
    )
    tool_executions_request.add_argument("--json", dest="json_payload", required=True)
    tool_executions_request.set_defaults(handler=_handle_tool_executions_request)
    tool_executions_show = tool_executions_sub.add_parser("show", help="Show one tool execution row.")
    tool_executions_show.add_argument("--tool-execution-id", required=True)
    tool_executions_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    tool_executions_show.set_defaults(handler=_handle_tool_executions_show)

    policy_decisions = subparsers.add_parser("policy-decisions", help="Policy decision read commands.")
    policy_decisions_sub = policy_decisions.add_subparsers(dest="policy_decisions_command", required=True)
    policy_decisions_show = policy_decisions_sub.add_parser("show", help="Show one policy decision row.")
    policy_decisions_show.add_argument("--policy-decision-id", required=True)
    policy_decisions_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    policy_decisions_show.set_defaults(handler=_handle_policy_decisions_show)

    maintenance = subparsers.add_parser("maintenance", help="Maintenance/recovery commands.")
    maintenance_sub = maintenance.add_subparsers(dest="maintenance_command", required=True)
    maintenance_sweep = maintenance_sub.add_parser("sweep-leases", help="Sweep and reopen expired leases.")
    maintenance_sweep.add_argument("--json", dest="json_payload", required=True)
    maintenance_sweep.set_defaults(handler=_handle_maintenance_sweep_leases)
    maintenance_reconcile = maintenance_sub.add_parser(
        "reconcile-stage07",
        help="Reconcile Stage07 issue activation for open flags.",
    )
    maintenance_reconcile.add_argument("--json", dest="json_payload", required=True)
    maintenance_reconcile.set_defaults(handler=_handle_maintenance_reconcile_stage07)
    maintenance_reconcile_executions = maintenance_sub.add_parser(
        "reconcile-executions",
        help="Reconcile stale or partially completed execution sessions.",
    )
    maintenance_reconcile_executions.add_argument("--json", dest="json_payload", required=True)
    maintenance_reconcile_executions.set_defaults(handler=_handle_maintenance_reconcile_executions)

    return parser


def _handle_init_db(args: argparse.Namespace) -> int:
    method = "alembic"
    if _try_alembic_upgrade(args.db_url):
        _json_print({"status": "ok", "command": "init-db", "db_url": args.db_url, "method": method})
        return 0

    try:
        connection = open_sqlite_connection(args.db_url)
    except ValueError as exc:
        return _emit_error(code="unsupported_db_url", message=str(exc), details={})
    try:
        create_sqlite_substrate(connection)
    finally:
        connection.close()

    _json_print(
        {
            "status": "ok",
            "command": "init-db",
            "db_url": args.db_url,
            "method": "sqlite-bootstrap",
            "note": "alembic unavailable in this environment; used SQLite bootstrap DDL",
        }
    )
    return 0


def _handle_events_append(args: argparse.Namespace) -> int:
    envelope = _parse_json_object(args.json_payload)
    if isinstance(envelope, int):
        return envelope
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection

    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            event_id = append_event(connection, envelope)
            connection.commit()
        except DuplicateIdempotencyKeyError as exc:
            connection.rollback()
            return _emit_error(
                code="duplicate_idempotency_key",
                message=str(exc),
                details={
                    "idempotency_key": exc.idempotency_key,
                    "existing_event_id": exc.existing_event_id,
                },
            )
        except DuplicateEventIdError as exc:
            connection.rollback()
            return _emit_error(
                code="duplicate_event_id",
                message=str(exc),
                details={"event_id": exc.event_id},
            )
        except ValueError as exc:
            connection.rollback()
            return _emit_error(code="invalid_envelope", message=str(exc), details={})
    finally:
        connection.close()

    _json_print({"status": "ok", "command": "events.append", "event_id": event_id})
    return 0


def _handle_events_list(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        events = list_events(
            connection=connection,
            run_id=args.run_id,
            since_event_id=args.since_event_id,
            limit=args.limit,
        )
    finally:
        connection.close()
    _json_print(events)
    return 0


def _handle_runs_create(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = create_workflow_run_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="runs.create",
            command_result=result,
            result_key="workflow_run",
        )
    )
    return 0


def _handle_runs_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        workflow_run = show_workflow_run_command(connection, args.workflow_run_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "runs.show", "workflow_run": workflow_run})
    return 0


def _handle_runs_list(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        workflow_runs = list_workflow_runs_command(
            connection,
            workflow_id=args.workflow_id,
            tenant_id=args.tenant_id,
            domain_id=args.domain_id,
            state=args.state,
        )
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "runs.list", "workflow_runs": workflow_runs})
    return 0


def _handle_tasks_create(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = create_task_run_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="tasks.create",
            command_result=result,
        )
    )
    return 0


def _handle_tasks_claim(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = claim_human_task_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="tasks.claim",
            command_result=result,
        )
    )
    return 0


def _handle_tasks_complete(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = complete_human_task_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="tasks.complete",
            command_result=result,
        )
    )
    return 0


def _handle_tasks_confirm_review(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = confirm_human_task_review_command(
            connection,
            payload,
            storage_root=default_storage_root_for_db_url(
                args.db_url,
                override=payload.get("storage_root"),
            ),
            include_receipt=True,
        )
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="tasks.confirm-review",
            command_result=result,
        )
    )
    return 0


def _handle_tasks_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        human_task = show_human_task_command(connection, args.human_task_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "tasks.show", "human_task": human_task})
    return 0


def _handle_tasks_list(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        tasks = list_tasks_for_workflow_run_command(connection, args.workflow_run_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "tasks.list", "tasks": tasks})
    return 0


def _handle_flags_create(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        flag = create_flag_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="flags.create",
            command_result=flag,
            result_key="flag",
        )
    )
    return 0


def _handle_flags_transition(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        flag = transition_flag_state_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="flags.transition",
            command_result=flag,
            result_key="flag",
        )
    )
    return 0


def _handle_flags_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        flag = show_flag_command(connection, args.flag_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "flags.show", "flag": flag})
    return 0


def _handle_flags_list(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        flags = list_flags_for_workflow_run_command(connection, args.workflow_run_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "flags.list", "flags": flags})
    return 0


def _handle_stage07_activate_issue(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = activate_stage07_issue_from_flag_command(connection, payload)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "stage07.activate-issue", "result": result})
    return 0


def _handle_execution_sessions_create(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        session = create_execution_session_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="execution-sessions.create",
            command_result=session,
            result_key="execution_session",
        )
    )
    return 0


def _handle_execution_sessions_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        session = show_execution_session_command(connection, args.execution_session_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "execution-sessions.show", "execution_session": session})
    return 0


def _handle_execution_sessions_list(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        sessions = list_execution_sessions_for_workflow_run_command(connection, args.workflow_run_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "execution-sessions.list", "execution_sessions": sessions})
    return 0


def _handle_execution_sessions_transition(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        session = transition_execution_session_state_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="execution-sessions.transition",
            command_result=session,
            result_key="execution_session",
        )
    )
    return 0


def _handle_tool_executions_request(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        tool_execution = request_tool_execution_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="tool-executions.request",
            command_result=tool_execution,
            result_key="tool_execution",
        )
    )
    return 0


def _handle_tool_executions_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        tool_execution = show_tool_execution_command(connection, args.tool_execution_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "tool-executions.show", "tool_execution": tool_execution})
    return 0


def _handle_policy_decisions_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        policy_decision = show_policy_decision_command(connection, args.policy_decision_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "policy-decisions.show", "policy_decision": policy_decision})
    return 0


def _handle_maintenance_sweep_leases(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = sweep_leases_command(connection, payload)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "maintenance.sweep-leases", "result": result})
    return 0


def _handle_maintenance_reconcile_stage07(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = reconcile_stage07_command(connection, payload)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "maintenance.reconcile-stage07", "result": result})
    return 0


def _handle_maintenance_reconcile_executions(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = reconcile_executions_command(connection, payload)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "maintenance.reconcile-executions", "result": result})
    return 0


def _handle_approvals_request(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        approval = request_approval_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="approvals.request",
            command_result=approval,
            result_key="approval",
        )
    )
    return 0


def _handle_approvals_respond(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        approval = respond_approval_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="approvals.respond",
            command_result=approval,
            result_key="approval",
        )
    )
    return 0


def _handle_approvals_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        approval = show_approval_command(connection, args.approval_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "approvals.show", "approval": approval})
    return 0


def _handle_approvals_list(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        approvals = list_approvals_for_workflow_run_command(connection, args.workflow_run_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "approvals.list", "approvals": approvals})
    return 0


def _handle_artifacts_create_version(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        artifact_version = create_artifact_version_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="artifacts.create-version",
            command_result=artifact_version,
            result_key="artifact_version",
        )
    )
    return 0


def _handle_artifacts_ingest(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    storage_root = default_storage_root_for_db_url(
        args.db_url,
        override=(
            str(payload.get("storage_root"))
            if payload.get("storage_root") is not None
            else os.environ.get("ONETRUTH_ARTIFACT_STORAGE_ROOT")
        ),
    )
    try:
        result = ingest_artifact_document_command(
            connection,
            payload,
            storage_root=storage_root,
            include_receipt=True,
        )
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="artifacts.ingest",
            command_result=result,
            flatten_result=True,
        )
    )
    return 0


def _handle_artifacts_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        artifact_version = show_artifact_version_command(connection, args.artifact_version_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "artifacts.show", "artifact_version": artifact_version})
    return 0


def _handle_artifacts_list(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        artifact_versions = list_artifacts_for_workflow_run_command(connection, args.workflow_run_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "artifacts.list", "artifact_versions": artifact_versions})
    return 0


def _handle_artifacts_list_linked(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        artifact_versions = list_artifacts_for_subject_command(
            connection,
            workflow_run_id=args.workflow_run_id,
            subject_kind=args.subject_kind,
            subject_id=args.subject_id,
        )
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print(
        {
            "status": "ok",
            "command": "artifacts.list-linked",
            "workflow_run_id": args.workflow_run_id,
            "subject_kind": args.subject_kind,
            "subject_id": args.subject_id,
            "artifact_versions": artifact_versions,
        }
    )
    return 0


def _handle_artifacts_download(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = download_artifact_blob_command(connection, args.artifact_version_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()

    output_path = Path(args.output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content_bytes = result["content_bytes"]
    output_path.write_bytes(content_bytes)
    _json_print(
        {
            "status": "ok",
            "command": "artifacts.download",
            "artifact_version": result["artifact_version"],
            "output_path": str(output_path),
            "byte_size": len(content_bytes),
            "content_digest": result["artifact_version"]["content_digest"],
            "content_base64": encode_base64_content(content_bytes),
        }
    )
    return 0


def _handle_artifacts_seed_corpus(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    if payload.get("workflow_run_id") is None or payload.get("seed_set_id") is None:
        return _emit_error(
            code="invalid_payload",
            message="workflow_run_id and seed_set_id are required",
            details={},
        )
    manifest_path = (
        Path(str(payload["manifest_path"])).expanduser().resolve()
        if payload.get("manifest_path") is not None
        else None
    )
    try:
        corpus = load_example_document_corpus(manifest_path)
        seed_payloads = seed_payloads_for_set(
            corpus=corpus,
            seed_set_id=str(payload["seed_set_id"]),
            workflow_run_id=str(payload["workflow_run_id"]),
            idempotency_prefix=str(
                payload.get("idempotency_prefix")
                or f"seed-corpus:{payload['workflow_run_id']}"
            ),
        )
    except Exception as exc:
        return _emit_error(
            code="invalid_example_document_corpus",
            message=str(exc),
            details={},
        )

    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    storage_root = default_storage_root_for_db_url(
        args.db_url,
        override=(
            str(payload.get("storage_root"))
            if payload.get("storage_root") is not None
            else os.environ.get("ONETRUTH_ARTIFACT_STORAGE_ROOT")
        ),
    )
    command_idempotency_key = str(
        payload.get("idempotency_key")
        or payload.get("idempotency_prefix")
        or f"seed-corpus:{payload['workflow_run_id']}"
    )
    receipt = _prepare_command_receipt(
        command_name="artifacts.seed-corpus",
        payload={
            **payload,
            "idempotency_key": command_idempotency_key,
            "manifest_path": str(corpus.manifest_path),
        },
        fingerprint_payload={
            "workflow_run_id": str(payload["workflow_run_id"]),
            "seed_set_id": str(payload["seed_set_id"]),
            "manifest_path": str(corpus.manifest_path),
            "idempotency_prefix": str(
                payload.get("idempotency_prefix")
                or f"seed-corpus:{payload['workflow_run_id']}"
            ),
            "storage_root": str(storage_root),
            "actor_id": payload.get("actor_id", "system:fixture-seeder"),
            "actor_type": payload.get("actor_type", "system"),
            "links": payload.get("links"),
            "seed_payloads": seed_payloads,
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=str(payload["workflow_run_id"]),
        idempotency_required=True,
    )
    seeded: list[dict[str, Any]] = []
    try:
        existing = get_command_receipt(
            connection,
            command_name=receipt.command_name,
            scope_key=receipt.scope_key,
            idempotency_key=receipt.idempotency_key,
        )
        if existing is not None:
            if existing["request_fingerprint"] != receipt.request_fingerprint:
                return _emit_error(
                    code="command_receipt_mismatch",
                    message="idempotency key was already used for a different request in this command scope",
                    details={
                        "command_name": receipt.command_name,
                        "scope_key": receipt.scope_key,
                        "idempotency_key": receipt.idempotency_key,
                    },
                )
            replay_payload = {
                "workflow_run_id": existing["result_json"]["workflow_run_id"],
                "seed_set_id": existing["result_json"]["seed_set_id"],
                "manifest_path": existing["result_json"]["manifest_path"],
                "artifact_versions": existing["result_json"]["artifact_versions"],
            }
            _json_print(
                _public_command_success_payload(
                    command="artifacts.seed-corpus",
                    command_result={
                        "result": replay_payload,
                        "idempotent_replay": True,
                        "receipt": {
                            "command_name": receipt.command_name,
                            "scope_key": receipt.scope_key,
                            "idempotency_key": receipt.idempotency_key,
                        },
                    },
                    flatten_result=True,
                )
            )
            return 0
        for seed_payload in seed_payloads:
            merged = {
                **seed_payload,
                "actor_id": payload.get("actor_id", "system:fixture-seeder"),
                "actor_type": payload.get("actor_type", "system"),
                "links": payload.get("links"),
            }
            seeded.append(
                ingest_artifact_document_command(
                    connection,
                    merged,
                    storage_root=storage_root,
                )["artifact_version"]
            )
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    try:
        result_payload = {
            "workflow_run_id": str(payload["workflow_run_id"]),
            "seed_set_id": str(payload["seed_set_id"]),
            "manifest_path": str(corpus.manifest_path),
            "artifact_versions": seeded,
        }
        connection.execute("BEGIN IMMEDIATE")
        create_command_receipt(
            connection,
            command_name=receipt.command_name,
            scope_key=receipt.scope_key,
            idempotency_key=receipt.idempotency_key,
            request_fingerprint=receipt.request_fingerprint,
            result_json=result_payload,
            tenant_id=receipt.tenant_id,
            domain_id=receipt.domain_id,
            workflow_run_id=receipt.workflow_run_id,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    _json_print(
        _public_command_success_payload(
            command="artifacts.seed-corpus",
            command_result={
                "result": result_payload,
                "idempotent_replay": False,
                "receipt": {
                    "command_name": receipt.command_name,
                    "scope_key": receipt.scope_key,
                    "idempotency_key": receipt.idempotency_key,
                },
            },
            flatten_result=True,
        )
    )
    return 0


def _handle_pointers_promote(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        pointer = promote_pointer_command(connection, payload, include_receipt=True)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    except DuplicateIdempotencyKeyError as exc:
        return _emit_error(
            code="duplicate_idempotency_key",
            message=str(exc),
            details={"idempotency_key": exc.idempotency_key, "existing_event_id": exc.existing_event_id},
        )
    finally:
        connection.close()
    _json_print(
        _public_command_success_payload(
            command="pointers.promote",
            command_result=pointer,
            result_key="pointer",
        )
    )
    return 0


def _handle_pointers_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        pointer = show_pointer_command(
            connection,
            workflow_run_id=args.workflow_run_id,
            pointer_key=args.pointer_key,
        )
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "pointers.show", "pointer": pointer})
    return 0


def _handle_pointers_list(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        pointers = list_pointers_for_workflow_run_command(connection, args.workflow_run_id)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "pointers.list", "pointers": pointers})
    return 0


def _handle_handoffs_materialize_weekly_seeds(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = materialize_weekly_seeds_command(connection, payload)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "handoffs.materialize-weekly-seeds", "result": result})
    return 0


def _handle_handoffs_activate_live_dispatch(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = activate_live_dispatch_command(connection, payload)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "handoffs.activate-live-dispatch", "result": result})
    return 0


def _handle_handoffs_notify_only(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = notify_only_handoff_command(connection, payload)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "handoffs.notify-only", "result": result})
    return 0


def _handle_schedule_control_build_weekly(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = build_weekly_schedule_control_command(connection, payload)
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print({"status": "ok", "command": "schedule-control.build-weekly", "result": result})
    return 0


def _handle_handoffs_show(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        edge_execution = show_edge_execution_command(connection, args.edge_execution_id)
        coherence = evaluate_handoff_operator_view_coherence(
            connection,
            projection_id=f"handoff_operator_view:{edge_execution['edge_execution_id']}",
            edge_execution=edge_execution,
            policy_on_drift=COHERENCE_POLICY_WARN_VISIBLE,
        )
        _emit_handoff_coherence_event_if_needed(
            connection,
            edge_execution=edge_execution,
            coherence=coherence,
        )
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print(
        {
            "status": "ok",
            "command": "handoffs.show",
            "edge_execution": edge_execution,
            "coherence": coherence,
        }
    )
    return 0


def _handle_handoffs_list(args: argparse.Namespace) -> int:
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        edge_executions = list_edge_executions_command(
            connection,
            edge_id=args.edge_id,
            source_workflow_run_id=args.source_workflow_run_id,
            status=args.status,
            target_workflow_run_id=args.target_workflow_run_id,
        )
        coherence_failures: list[dict[str, Any]] = []
        for edge_execution in edge_executions:
            coherence = evaluate_handoff_operator_view_coherence(
                connection,
                projection_id=f"handoff_operator_view:{edge_execution['edge_execution_id']}",
                edge_execution=edge_execution,
                policy_on_drift=COHERENCE_POLICY_WARN_VISIBLE,
            )
            edge_execution["coherence"] = coherence
            if coherence.get("coherence_status") == COHERENCE_STATUS_FAILED:
                coherence_failures.append(coherence)
            _emit_handoff_coherence_event_if_needed(
                connection,
                edge_execution=edge_execution,
                coherence=coherence,
            )
    except CommandError as exc:
        return _emit_error(code=exc.code, message=exc.message, details=exc.details)
    finally:
        connection.close()
    _json_print(
        {
            "status": "ok",
            "command": "handoffs.list",
            "edge_executions": edge_executions,
            "coherence_failures": coherence_failures,
        }
    )
    return 0


def _emit_handoff_coherence_event_if_needed(
    connection: sqlite3.Connection,
    *,
    edge_execution: dict[str, Any],
    coherence: dict[str, Any],
) -> None:
    if coherence.get("coherence_status") != COHERENCE_STATUS_FAILED:
        return
    source_workflow_run_id = str(edge_execution.get("source_workflow_run_id") or "")
    if not source_workflow_run_id:
        return
    row = connection.execute(
        """
        SELECT tenant_id, domain_id
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (source_workflow_run_id,),
    ).fetchone()
    if row is None:
        return
    maybe_emit_projection_coherence_failed(
        connection,
        tenant_id=str(row["tenant_id"]),
        domain_id=str(row["domain_id"]),
        workflow_run_id=source_workflow_run_id,
        coherence=coherence,
    )


def _parse_json_object(raw_payload: str) -> dict[str, Any] | int:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        return _emit_error(
            code="invalid_json",
            message=f"invalid JSON payload: {exc.msg}",
            details={"pos": exc.pos},
        )
    if not isinstance(payload, dict):
        return _emit_error(
            code="invalid_payload",
            message="expected JSON object payload",
            details={},
        )
    return payload


def _open_connection_or_emit(database_url: str) -> sqlite3.Connection | int:
    try:
        return open_sqlite_connection(database_url)
    except ValueError as exc:
        return _emit_error(code="unsupported_db_url", message=str(exc), details={})


def _emit_error(code: str, message: str, details: dict[str, Any]) -> int:
    _json_print(
        {"status": "error", "error_code": code, "message": message, "details": details},
        sys.stderr,
    )
    return 2


def _try_alembic_upgrade(database_url: str) -> bool:
    try:
        from alembic import command
        from alembic.config import Config
    except Exception:
        return False

    try:
        config = Config(str(_repo_root() / "alembic.ini"))
        config.set_main_option("script_location", str(_repo_root() / "alembic"))
        config.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(config, "head")
    except Exception:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
