from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import sqlite3
from typing import Any, Callable

from onetruth.infrastructure.events.event_store import (
    DuplicateIdempotencyKeyError,
    create_command_receipt,
    event_id_for_type,
    get_command_receipt,
    get_event_by_idempotency_key,
    utc_now_iso,
)
from onetruth.infrastructure.repositories.task_runs import get_task_run
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run

VALID_ACTOR_TYPES = {"human", "agent", "service", "system"}


@dataclass
class CommandError(Exception):
    code: str
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class CommandReceiptContext:
    command_name: str
    scope_key: str
    idempotency_key: str
    request_fingerprint: str
    event_idempotency_base: str
    tenant_id: str | None
    domain_id: str | None
    workflow_run_id: str | None


def _normalize_actor_roles(
    raw_roles: Any,
    *,
    required: bool,
) -> tuple[str, ...]:
    if raw_roles is None:
        if required:
            raise CommandError(
                code="invalid_actor_roles",
                message="actor_roles must be provided for this command",
                details={"required_field": "actor_roles"},
            )
        return ()
    if not isinstance(raw_roles, (list, tuple)):
        raise CommandError(
            code="invalid_actor_roles",
            message="actor_roles must be a list of role ids",
            details={"required_field": "actor_roles"},
        )
    actor_roles = tuple(str(role).strip() for role in raw_roles if str(role).strip())
    if required and not actor_roles:
        raise CommandError(
            code="invalid_actor_roles",
            message="actor_roles must contain at least one role id",
            details={"required_field": "actor_roles"},
        )
    return actor_roles


def _principal_from_payload(
    payload: dict[str, Any],
    *,
    require_roles: bool,
):
    from onetruth.application.services.capabilities import Principal

    return Principal(
        actor_id=str(payload["actor_id"]),
        actor_type=str(payload["actor_type"]),
        actor_roles=_normalize_actor_roles(
            payload.get("actor_roles"),
            required=require_roles,
        ),
    )


def _decision_has_reason(
    decision: Any,
    reason_code: str,
) -> bool:
    return any(getattr(reason, "code", None) == reason_code for reason in decision.reasons)


def _forbidden_command_error(
    *,
    code: str,
    message: str,
    decision: Any,
    **details: Any,
) -> CommandError:
    from onetruth.application.services.capabilities import decision_denial_details

    return CommandError(
        code=code,
        message=message,
        details=decision_denial_details(decision, **details),
    )


def _begin_transaction(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")


def _normalize_command_idempotency_key(
    idempotency_key: Any,
    *,
    required: bool,
) -> str | None:
    if idempotency_key is None:
        if required:
            raise CommandError(
                code="invalid_idempotency_key",
                message="idempotency_key must be a non-empty string",
                details={},
            )
        return None
    key = str(idempotency_key).strip()
    if key:
        return key
    if required:
        raise CommandError(
            code="invalid_idempotency_key",
            message="idempotency_key must be a non-empty string",
            details={},
        )
    return None


def _command_scope_key(parts: tuple[Any, ...]) -> str:
    normalized = [None if value is None else str(value) for value in parts]
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)


def _public_command_scope_key(command_name: str, payload: dict[str, Any]) -> str:
    action_or_default = None
    if payload.get("scope_kind") is not None and payload.get("scope_ref") is not None:
        action_or_default = str(payload.get("action") or f"{payload['scope_kind']}:{payload['scope_ref']}")

    if command_name == "runs.create":
        return _command_scope_key(
            (
                payload.get("tenant_id"),
                payload.get("domain_id"),
                payload.get("workflow_id"),
                payload.get("partition_key"),
                payload.get("activation_key"),
            )
        )
    if command_name == "tasks.create":
        return _command_scope_key(
            (
                payload.get("workflow_run_id"),
                payload.get("activation_key"),
            )
        )
    if command_name in {"tasks.claim", "tasks.complete", "tasks.confirm-review"}:
        return _command_scope_key((payload.get("human_task_id"),))
    if command_name == "flags.create":
        resolved_dedupe_key = payload.get("dedupe_key")
        if resolved_dedupe_key is None:
            resolved_dedupe_key = payload.get("idempotency_key")
        return _command_scope_key(
            (
                payload.get("workflow_run_id"),
                resolved_dedupe_key,
            )
        )
    if command_name == "flags.transition":
        return _command_scope_key((payload.get("flag_id"),))
    if command_name == "approvals.request":
        return _command_scope_key(
            (
                payload.get("workflow_run_id"),
                payload.get("approval_kind"),
                payload.get("scope_kind"),
                payload.get("scope_ref"),
                payload.get("task_run_id"),
                action_or_default,
            )
        )
    if command_name == "approvals.respond":
        return _command_scope_key((payload.get("approval_id"),))
    if command_name in {"artifacts.create-version", "artifacts.ingest"}:
        return _command_scope_key(
            (
                payload.get("workflow_run_id"),
                payload.get("task_run_id"),
                payload.get("artifact_kind"),
            )
        )
    if command_name == "workpages.eod-drafts.create":
        return _command_scope_key(
            (
                payload.get("tenant_id"),
                payload.get("domain_id"),
                payload.get("workflow_id"),
                payload.get("partition_key"),
                payload.get("workpage_id"),
            )
        )
    if command_name == "workpages.driver-preferences.snapshots.create":
        return _command_scope_key(
            (
                payload.get("workflow_run_id"),
                payload.get("workflow_id"),
                payload.get("workpage_id"),
            )
        )
    if command_name == "workpages.driver-preferences.availability-exceptions.add":
        return _command_scope_key(
            (
                payload.get("workflow_run_id"),
                payload.get("workflow_id"),
                payload.get("workpage_id"),
            )
        )
    if command_name == "workpages.artifact.submit":
        return _command_scope_key((payload.get("artifact_version_id"),))
    if command_name == "workpages.schedule.sick_no_show":
        return _command_scope_key((payload.get("artifact_version_id"),))
    if command_name == "artifacts.seed-corpus":
        return _command_scope_key(
            (
                payload.get("workflow_run_id"),
                payload.get("seed_set_id"),
                payload.get("manifest_path") or "default_manifest",
            )
        )
    if command_name == "pointers.promote":
        return _command_scope_key(
            (
                payload.get("workflow_run_id"),
                payload.get("pointer_key"),
            )
        )
    if command_name == "execution-sessions.create":
        return _command_scope_key(
            (
                payload.get("workflow_run_id"),
                payload.get("task_run_id"),
                payload.get("execution_spec_id"),
                payload.get("owner_mode"),
            )
        )
    if command_name == "execution-sessions.transition":
        return _command_scope_key((payload.get("execution_session_id"),))
    if command_name == "tool-executions.request":
        return _command_scope_key(
            (
                payload.get("execution_session_id"),
                payload.get("tool_class"),
                payload.get("tool_name"),
            )
        )
    if command_name == "tool-executions.complete":
        return _command_scope_key((payload.get("tool_execution_id"),))
    raise ValueError(f"unsupported public command scope: {command_name}")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def _command_request_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _scoped_event_idempotency_base(
    *,
    command_name: str,
    scope_key: str,
    idempotency_key: str,
) -> str:
    digest = hashlib.sha256(
        _canonical_json(
            {
                "command_name": command_name,
                "scope_key": scope_key,
                "idempotency_key": idempotency_key,
            }
        ).encode("utf-8")
    ).hexdigest()
    return f"command-receipt:{digest}"


def _prepare_command_receipt(
    *,
    command_name: str,
    payload: dict[str, Any],
    fingerprint_payload: dict[str, Any],
    tenant_id: str | None,
    domain_id: str | None,
    workflow_run_id: str | None,
    idempotency_required: bool,
) -> CommandReceiptContext | None:
    normalized_idempotency_key = _normalize_command_idempotency_key(
        payload.get("idempotency_key"),
        required=idempotency_required,
    )
    if normalized_idempotency_key is None:
        return None
    scope_key = _public_command_scope_key(command_name, payload)
    return CommandReceiptContext(
        command_name=command_name,
        scope_key=scope_key,
        idempotency_key=normalized_idempotency_key,
        request_fingerprint=_command_request_fingerprint(fingerprint_payload),
        event_idempotency_base=_scoped_event_idempotency_base(
            command_name=command_name,
            scope_key=scope_key,
            idempotency_key=normalized_idempotency_key,
        ),
        tenant_id=tenant_id,
        domain_id=domain_id,
        workflow_run_id=workflow_run_id,
    )


def _receipt_event_idempotency_key(
    receipt: CommandReceiptContext | None,
    suffix: str,
) -> str | None:
    if receipt is None:
        return None
    return f"{receipt.event_idempotency_base}:{suffix}"


def _event_idempotency_key(idempotency_key: Any, suffix: str) -> str | None:
    if idempotency_key is None:
        return None
    key = str(idempotency_key).strip()
    if not key:
        return None
    return f"{key}:{suffix}"


def _required_event_idempotency_key(idempotency_key: Any, suffix: str) -> str:
    key = _event_idempotency_key(idempotency_key, suffix)
    if key is None:
        raise CommandError(
            code="invalid_idempotency_key",
            message="idempotency_key must be a non-empty string",
            details={},
        )
    return key


def _assert_idempotency_available(
    connection: sqlite3.Connection,
    event_idempotency_key: str | None,
) -> None:
    if event_idempotency_key is None:
        return
    existing = get_event_by_idempotency_key(connection, event_idempotency_key)
    if existing is None:
        return
    raise DuplicateIdempotencyKeyError(
        event_idempotency_key,
        str(existing["event_id"]),
    )


def _future_iso(lease_seconds: int) -> str:
    now = utc_now_iso()
    parsed = _parse_iso_datetime(now)
    return (parsed + timedelta(seconds=lease_seconds)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _execute_with_command_receipt(
    connection: sqlite3.Connection,
    *,
    receipt: CommandReceiptContext | None,
    operation: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    _begin_transaction(connection)
    try:
        if receipt is not None:
            existing = get_command_receipt(
                connection,
                command_name=receipt.command_name,
                scope_key=receipt.scope_key,
                idempotency_key=receipt.idempotency_key,
            )
            if existing is not None:
                if existing["request_fingerprint"] != receipt.request_fingerprint:
                    raise CommandError(
                        code="command_receipt_mismatch",
                        message="idempotency key was already used for a different request in this command scope",
                        details={
                            "command_name": receipt.command_name,
                            "scope_key": receipt.scope_key,
                            "idempotency_key": receipt.idempotency_key,
                        },
                    )
                connection.rollback()
                return dict(existing["result_json"]), True

        result = operation()
        if receipt is not None:
            create_command_receipt(
                connection,
                command_name=receipt.command_name,
                scope_key=receipt.scope_key,
                idempotency_key=receipt.idempotency_key,
                request_fingerprint=receipt.request_fingerprint,
                result_json=result,
                tenant_id=receipt.tenant_id,
                domain_id=receipt.domain_id,
                workflow_run_id=receipt.workflow_run_id,
            )
        connection.commit()
        return result, False
    except sqlite3.IntegrityError:
        connection.rollback()
        if receipt is not None:
            existing = get_command_receipt(
                connection,
                command_name=receipt.command_name,
                scope_key=receipt.scope_key,
                idempotency_key=receipt.idempotency_key,
            )
            if existing is not None and existing["request_fingerprint"] == receipt.request_fingerprint:
                return dict(existing["result_json"]), True
        raise
    except Exception:
        connection.rollback()
        raise


def _command_receipt_payload(
    raw_result: dict[str, Any],
    *,
    receipt: CommandReceiptContext | None,
    replay: bool,
    include_receipt: bool,
) -> dict[str, Any]:
    if not include_receipt:
        return raw_result
    return {
        "result": raw_result,
        "idempotent_replay": replay,
        "receipt": (
            {
                "command_name": receipt.command_name,
                "scope_key": receipt.scope_key,
                "idempotency_key": receipt.idempotency_key,
            }
            if receipt is not None
            else None
        ),
    }


def _event_envelope(
    *,
    event_type: str,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
    links: list[dict[str, str]],
    payload: dict[str, Any],
    idempotency_key: str | None,
) -> dict[str, Any]:
    _assert_actor_type(actor_type)
    occurred_at = utc_now_iso()
    clean_payload = {key: value for key, value in payload.items() if value is not None}
    return {
        "event_id": event_id_for_type(event_type),
        "event_type": event_type,
        "schema_version": "1.0",
        "occurred_at": occurred_at,
        "recorded_at": occurred_at,
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "actor": {"type": actor_type, "id": actor_id},
        "links": links,
        "payload": clean_payload,
        "idempotency_key": idempotency_key,
    }


def _require_fields(payload: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if field not in payload or payload[field] is None]
    if missing:
        raise CommandError(
            code="invalid_payload",
            message=f"missing required fields: {', '.join(missing)}",
            details={"missing_fields": missing},
        )


def _assert_actor_type(actor_type: str) -> None:
    if actor_type not in VALID_ACTOR_TYPES:
        raise CommandError(
            code="invalid_actor_type",
            message=f"unsupported actor_type: {actor_type}",
            details={"allowed_actor_types": sorted(VALID_ACTOR_TYPES)},
        )


def _validate_task_run_belongs_to_workflow(
    connection: sqlite3.Connection,
    *,
    task_run_id: str,
    workflow_run_id: str,
) -> dict[str, Any]:
    task_run = get_task_run(connection, task_run_id)
    if task_run is None:
        raise CommandError(
            code="task_run_not_found",
            message="task run not found",
            details={"task_run_id": task_run_id},
        )
    if str(task_run["workflow_run_id"]) != workflow_run_id:
        raise CommandError(
            code="cross_workflow_task_reference",
            message="task_run belongs to a different workflow_run",
            details={
                "task_run_id": task_run_id,
                "task_workflow_run_id": str(task_run["workflow_run_id"]),
                "workflow_run_id": workflow_run_id,
            },
        )
    return task_run


def _workflow_scope(connection: sqlite3.Connection, workflow_run_id: str) -> dict[str, str]:
    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found",
            details={"workflow_run_id": workflow_run_id},
        )
    return {
        "tenant_id": str(workflow_run["tenant_id"]),
        "domain_id": str(workflow_run["domain_id"]),
        "partition_key": str(workflow_run["partition_key"]),
    }


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
