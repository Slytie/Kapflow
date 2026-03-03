from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    activate_stage07_issue_from_flag_command,
    create_artifact_version_command,
    create_flag_command,
    claim_human_task_command,
    complete_human_task_command,
    create_task_run_command,
    create_workflow_run_command,
    list_approvals_for_workflow_run_command,
    list_artifacts_for_workflow_run_command,
    list_flags_for_workflow_run_command,
    list_pointers_for_workflow_run_command,
    list_tasks_for_workflow_run_command,
    list_workflow_runs_command,
    promote_pointer_command,
    reconcile_stage07_command,
    request_approval_command,
    respond_approval_command,
    show_flag_command,
    show_approval_command,
    show_artifact_version_command,
    show_human_task_command,
    show_pointer_command,
    show_workflow_run_command,
    sweep_leases_command,
    transition_flag_state_command,
)
from onetruth.infrastructure.db.session import DEFAULT_DB_URL, open_sqlite_connection
from onetruth.infrastructure.events.event_store import (
    DuplicateEventIdError,
    DuplicateIdempotencyKeyError,
    append_event,
    create_sqlite_substrate,
    list_events,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _json_print(payload: Any, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, separators=(",", ":")) + "\n")


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
    artifacts_show = artifacts_sub.add_parser("show", help="Show one artifact version.")
    artifacts_show.add_argument("--artifact-version-id", required=True)
    artifacts_show.add_argument("--json", dest="json_output", required=True, action="store_true")
    artifacts_show.set_defaults(handler=_handle_artifacts_show)
    artifacts_list = artifacts_sub.add_parser("list", help="List artifact versions for a workflow run.")
    artifacts_list.add_argument("--workflow-run-id", required=True)
    artifacts_list.add_argument("--json", dest="json_output", required=True, action="store_true")
    artifacts_list.set_defaults(handler=_handle_artifacts_list)

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
        result = create_workflow_run_command(connection, payload)
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
    _json_print({"status": "ok", "command": "runs.create", "workflow_run": result})
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
        result = create_task_run_command(connection, payload)
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
    _json_print({"status": "ok", "command": "tasks.create", "result": result})
    return 0


def _handle_tasks_claim(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = claim_human_task_command(connection, payload)
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
    _json_print({"status": "ok", "command": "tasks.claim", "result": result})
    return 0


def _handle_tasks_complete(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        result = complete_human_task_command(connection, payload)
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
    _json_print({"status": "ok", "command": "tasks.complete", "result": result})
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
        flag = create_flag_command(connection, payload)
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
    _json_print({"status": "ok", "command": "flags.create", "flag": flag})
    return 0


def _handle_flags_transition(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        flag = transition_flag_state_command(connection, payload)
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
    _json_print({"status": "ok", "command": "flags.transition", "flag": flag})
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


def _handle_approvals_request(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        approval = request_approval_command(connection, payload)
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
    _json_print({"status": "ok", "command": "approvals.request", "approval": approval})
    return 0


def _handle_approvals_respond(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        approval = respond_approval_command(connection, payload)
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
    _json_print({"status": "ok", "command": "approvals.respond", "approval": approval})
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
        artifact_version = create_artifact_version_command(connection, payload)
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
        {
            "status": "ok",
            "command": "artifacts.create-version",
            "artifact_version": artifact_version,
        }
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


def _handle_pointers_promote(args: argparse.Namespace) -> int:
    payload = _parse_json_object(args.json_payload)
    if isinstance(payload, int):
        return payload
    connection = _open_connection_or_emit(args.db_url)
    if isinstance(connection, int):
        return connection
    try:
        pointer = promote_pointer_command(connection, payload)
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
    _json_print({"status": "ok", "command": "pointers.promote", "pointer": pointer})
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
