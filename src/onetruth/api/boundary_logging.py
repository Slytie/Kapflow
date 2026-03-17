from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from onetruth.api.dependencies import BoundaryProfile, RequestContext

_BOUNDARY_LOGGER = logging.getLogger("onetruth.api.boundary")
_SAFE_AGGREGATE_FIELDS = (
    "workflow_run_id",
    "human_task_id",
    "approval_id",
    "flag_id",
    "artifact_version_id",
    "subject_kind",
    "subject_id",
)
_RECEIPT_FIELD_NAMES = {
    "command_name": "receipt_command_name",
    "scope_key": "receipt_scope_key",
    "idempotency_key": "receipt_idempotency_key",
}


def log_request_started(
    *,
    request_id: str,
    boundary_profile: BoundaryProfile,
    method: str,
    path: str,
    route_name: str | None,
    route_params: Mapping[str, str] | None,
) -> None:
    _emit(
        logging.INFO,
        {
            "event": "request_started",
            "request_id": request_id,
            "boundary_profile": boundary_profile,
            "method": method,
            "path": path,
            "route_name": route_name,
            "route_params": dict(route_params) if route_params is not None else None,
        },
    )


def log_request_finished(
    *,
    request_id: str,
    boundary_profile: BoundaryProfile,
    method: str,
    path: str,
    route_name: str | None,
    route_params: Mapping[str, str] | None,
    request_context: RequestContext | None,
    status_code: int,
    latency_ms: int,
    response_kind: str,
    error_code: str | None = None,
    response_payload: Mapping[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "request_finished",
        "request_id": request_id,
        "boundary_profile": boundary_profile,
        "method": method,
        "path": path,
        "route_name": route_name,
        "route_params": dict(route_params) if route_params is not None else None,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "response_kind": response_kind,
    }
    payload.update(_request_context_fields(request_context))
    if error_code is not None:
        payload["error_code"] = error_code
    payload.update(extract_mutation_log_fields(response_payload))
    _emit(logging.INFO, payload)


def log_request_failed(
    *,
    request_id: str,
    boundary_profile: BoundaryProfile,
    method: str,
    path: str,
    route_name: str | None,
    route_params: Mapping[str, str] | None,
    request_context: RequestContext | None,
    status_code: int,
    latency_ms: int,
    response_kind: str,
    error_code: str,
    exception: Exception,
) -> None:
    payload: dict[str, Any] = {
        "event": "request_failed",
        "request_id": request_id,
        "boundary_profile": boundary_profile,
        "method": method,
        "path": path,
        "route_name": route_name,
        "route_params": dict(route_params) if route_params is not None else None,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "response_kind": response_kind,
        "error_code": error_code,
        "exception_class": exception.__class__.__name__,
    }
    payload.update(_request_context_fields(request_context))
    _emit(logging.ERROR, payload)


def extract_error_code(payload: Mapping[str, Any] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    error = payload.get("error")
    if not isinstance(error, Mapping):
        return None
    code = error.get("code")
    if isinstance(code, str) and code:
        return code
    return None


def extract_mutation_log_fields(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}

    fields: dict[str, Any] = {}
    command = payload.get("command")
    if isinstance(command, str) and command:
        fields["command"] = command

    replay = payload.get("idempotent_replay")
    if isinstance(replay, bool):
        fields["idempotent_replay"] = replay

    for field_name in _SAFE_AGGREGATE_FIELDS:
        value = payload.get(field_name)
        if isinstance(value, str) and value:
            fields[field_name] = value

    receipt = payload.get("receipt")
    if isinstance(receipt, Mapping):
        for source_name, target_name in _RECEIPT_FIELD_NAMES.items():
            value = receipt.get(source_name)
            if isinstance(value, str) and value:
                fields[target_name] = value

    for key, value in payload.items():
        if key in {"receipt", "error"} or not isinstance(value, Mapping):
            continue
        for field_name in _SAFE_AGGREGATE_FIELDS:
            nested_value = value.get(field_name)
            if isinstance(nested_value, str) and nested_value:
                fields.setdefault(field_name, nested_value)

    return fields


def _request_context_fields(
    request_context: RequestContext | None,
) -> dict[str, Any]:
    if request_context is None:
        return {}
    return {
        "tenant_id": request_context.tenant_id,
        "domain_id": request_context.domain_id,
        "actor_type": request_context.actor_type,
    }


def _emit(level: int, payload: dict[str, Any]) -> None:
    _BOUNDARY_LOGGER.log(level, _serialize_log_payload(payload))


def _serialize_log_payload(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
    )
