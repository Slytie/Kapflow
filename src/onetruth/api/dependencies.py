from __future__ import annotations

from dataclasses import dataclass
import os
import sqlite3
from typing import Any, Callable, Literal, Mapping, Sequence

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    show_workflow_run_command,
)
from onetruth.infrastructure.db.session import DEFAULT_DB_URL, open_sqlite_connection

from .errors import ApiError, api_error_from_command

TENANT_HEADER = "x-onetruth-tenant-id"
DOMAIN_HEADER = "x-onetruth-domain-id"
ACTOR_ID_HEADER = "x-onetruth-actor-id"
ACTOR_TYPE_HEADER = "x-onetruth-actor-type"
ACTOR_ROLES_HEADER = "x-onetruth-actor-roles"

VALID_ACTOR_TYPES = {"human", "agent", "service", "system"}
BOUNDARY_PROFILES = ("local_dev", "ci_test", "shared_env")
DEFAULT_API_BOUNDARY_PROFILE = "shared_env"
PRINCIPAL_RESOLVER_UNAVAILABLE_CODE = "principal_resolver_unavailable"

BoundaryProfile = Literal["local_dev", "ci_test", "shared_env"]
PrincipalResolver = Callable[[Mapping[str, str]], "RequestContext"]


@dataclass(frozen=True)
class RequestContext:
    tenant_id: str
    domain_id: str
    actor_id: str
    actor_type: str
    actor_roles: tuple[str, ...]
    request_id: str | None = None


@dataclass(frozen=True)
class Page:
    limit: int
    offset: int


def resolve_db_url(configured_db_url: str | None = None) -> str:
    if configured_db_url is not None:
        return configured_db_url
    return os.environ.get("ONETRUTH_DB_URL", DEFAULT_DB_URL)


def open_connection(db_url: str) -> sqlite3.Connection:
    return open_sqlite_connection(db_url)


def trusted_header_principal_resolver(headers: Mapping[str, str]) -> RequestContext:
    def _required(name: str) -> str:
        value = headers.get(name)
        if value is None or not value.strip():
            raise ApiError(
                status_code=400,
                code="invalid_request_context",
                message=f"missing required header: {name}",
                details={"required_header": name},
            )
        return value.strip()

    actor_type = normalize_actor_type(
        _required(ACTOR_TYPE_HEADER),
        status_code=400,
        code="invalid_request_context",
        source=ACTOR_TYPE_HEADER,
    )
    actor_roles = normalize_actor_roles(
        _required(ACTOR_ROLES_HEADER),
        status_code=400,
        code="invalid_request_context",
        source=ACTOR_ROLES_HEADER,
    )

    return RequestContext(
        tenant_id=_required(TENANT_HEADER),
        domain_id=_required(DOMAIN_HEADER),
        actor_id=_required(ACTOR_ID_HEADER),
        actor_type=actor_type,
        actor_roles=actor_roles,
    )


def unavailable_principal_resolver(headers: Mapping[str, str]) -> RequestContext:
    raise ApiError(
        status_code=503,
        code=PRINCIPAL_RESOLVER_UNAVAILABLE_CODE,
        message="principal resolver is not configured for the shared_env boundary profile",
        details={"boundary_profile": DEFAULT_API_BOUNDARY_PROFILE},
    )


def request_context_from_headers(headers: Mapping[str, str]) -> RequestContext:
    return trusted_header_principal_resolver(headers)


def normalize_actor_type(
    raw_actor_type: object,
    *,
    status_code: int,
    code: str,
    source: str,
) -> str:
    actor_type = _required_non_empty_string(
        raw_actor_type,
        status_code=status_code,
        code=code,
        source=source,
        field_name="actor_type",
    )
    if actor_type not in VALID_ACTOR_TYPES:
        raise ApiError(
            status_code=status_code,
            code=code,
            message=f"unsupported actor_type from {source}: {actor_type}",
            details={
                "source": source,
                "field": "actor_type",
                "allowed_actor_types": sorted(VALID_ACTOR_TYPES),
            },
        )
    return actor_type


def normalize_actor_roles(
    raw_actor_roles: object,
    *,
    status_code: int,
    code: str,
    source: str,
) -> tuple[str, ...]:
    roles: tuple[str, ...]
    if isinstance(raw_actor_roles, str):
        roles = tuple(role.strip() for role in raw_actor_roles.split(",") if role.strip())
    elif isinstance(raw_actor_roles, Sequence) and not isinstance(
        raw_actor_roles,
        (bytes, bytearray, str),
    ):
        normalized: list[str] = []
        for role in raw_actor_roles:
            if not isinstance(role, str) or not role.strip():
                raise ApiError(
                    status_code=status_code,
                    code=code,
                    message=f"actor_roles from {source} must contain only non-empty strings",
                    details={"source": source, "field": "actor_roles"},
                )
            normalized.append(role.strip())
        roles = tuple(normalized)
    else:
        raise ApiError(
            status_code=status_code,
            code=code,
            message=f"actor_roles from {source} must be a comma-delimited string or string list",
            details={"source": source, "field": "actor_roles"},
        )

    if not roles:
        raise ApiError(
            status_code=status_code,
            code=code,
            message=f"actor_roles from {source} must contain at least one role",
            details={"source": source, "field": "actor_roles"},
        )
    return roles


def _required_non_empty_string(
    raw_value: object,
    *,
    status_code: int,
    code: str,
    source: str,
    field_name: str,
) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ApiError(
            status_code=status_code,
            code=code,
            message=f"{field_name} from {source} must be a non-empty string",
            details={"source": source, "field": field_name},
        )
    return raw_value.strip()


def scoped_workflow_run(
    connection: sqlite3.Connection,
    context: RequestContext,
    workflow_run_id: str,
) -> dict[str, Any]:
    try:
        workflow_run = show_workflow_run_command(connection, workflow_run_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    if (
        str(workflow_run["tenant_id"]) != context.tenant_id
        or str(workflow_run["domain_id"]) != context.domain_id
    ):
        raise ApiError(
            status_code=404,
            code="workflow_run_not_found",
            message="workflow run not found",
            details={"workflow_run_id": workflow_run_id},
        )
    return workflow_run


def enforce_scope_filter(
    *,
    context: RequestContext,
    tenant_id: str | None,
    domain_id: str | None,
) -> None:
    if tenant_id is not None and tenant_id != context.tenant_id:
        raise ApiError(
            status_code=403,
            code="scope_filter_denied",
            message="tenant_id query filter does not match request scope",
            details={
                "tenant_id": tenant_id,
                "context_tenant_id": context.tenant_id,
            },
        )
    if domain_id is not None and domain_id != context.domain_id:
        raise ApiError(
            status_code=403,
            code="scope_filter_denied",
            message="domain_id query filter does not match request scope",
            details={
                "domain_id": domain_id,
                "context_domain_id": context.domain_id,
            },
        )


def parse_page(query: Mapping[str, str]) -> Page:
    limit = parse_int(
        query,
        key="limit",
        default=100,
        min_value=1,
        max_value=500,
    )
    offset = parse_int(
        query,
        key="offset",
        default=0,
        min_value=0,
        max_value=100000,
    )
    return Page(limit=limit, offset=offset)


def parse_int(
    query: Mapping[str, str],
    *,
    key: str,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    raw = query.get(key)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiError(
            status_code=400,
            code="invalid_query_parameter",
            message=f"query parameter {key} must be an integer",
            details={"parameter": key, "value": raw},
        ) from exc
    if value < min_value or value > max_value:
        raise ApiError(
            status_code=400,
            code="invalid_query_parameter",
            message=f"query parameter {key} out of range",
            details={
                "parameter": key,
                "value": value,
                "min": min_value,
                "max": max_value,
            },
        )
    return value
