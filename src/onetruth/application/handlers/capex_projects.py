from __future__ import annotations

import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import (
    VALID_ACTOR_TYPES,
    CommandError,
    _command_receipt_payload,
    _event_envelope,
    _execute_with_command_receipt,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
    _require_fields,
)
from onetruth.application.services.capex_project_access import (
    PROJECT_ADMIN,
    PROJECT_CONTRIBUTOR,
    PROJECT_VIEWER,
    require_project_access,
    require_project_membership_role,
    validate_project_role,
)
from onetruth.capex_platform.project_access import AuthorizedProjectsQuery
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.capex_projects import (
    create_capex_project,
    create_project_membership,
    get_capex_project,
    get_project_membership,
    list_project_memberships,
)

PROJECT_STATES = {"active", "archived"}
MEMBERSHIP_STATES = {"active"}


def create_capex_project_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "tenant_id",
            "domain_id",
            "project_key",
            "name",
            "actor_id",
            "actor_type",
            "idempotency_key",
        ],
    )
    actor_type = _validate_actor_type(str(payload["actor_type"]))
    requested_project_id = payload.get("project_id")
    project_id = str(requested_project_id or f"cp-{uuid4()}")
    project_key = _required_non_empty(payload["project_key"], "project_key")
    name = _required_non_empty(payload["name"], "name")
    state = _validate_project_state(str(payload.get("state", "active")))
    metadata_json = _metadata(payload.get("metadata_json"))
    actor_id = str(payload["actor_id"])

    receipt = _prepare_command_receipt(
        command_name="capex.projects.create",
        payload=payload,
        fingerprint_payload={
            "project_id": (
                str(requested_project_id)
                if requested_project_id is not None
                else None
            ),
            "tenant_id": str(payload["tenant_id"]),
            "domain_id": str(payload["domain_id"]),
            "project_key": project_key,
            "name": name,
            "state": state,
            "metadata_json": metadata_json,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        tenant_id=str(payload["tenant_id"]),
        domain_id=str(payload["domain_id"]),
        workflow_run_id=None,
        idempotency_required=True,
    )
    project_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "capex.projects.create.capex.project.created",
    )
    membership_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "capex.projects.create.capex.project_membership.granted",
    )

    def _operation() -> dict[str, Any]:
        now = utc_now_iso()
        create_capex_project(
            connection,
            project_id=project_id,
            tenant_id=str(payload["tenant_id"]),
            domain_id=str(payload["domain_id"]),
            project_key=project_key,
            name=name,
            state=state,
            metadata_json=metadata_json,
            created_by_actor_id=actor_id,
            created_by_actor_type=actor_type,
            created_at=now,
        )
        admin_membership_id = f"pm-{uuid4()}"
        create_project_membership(
            connection,
            project_membership_id=admin_membership_id,
            project_id=project_id,
            tenant_id=str(payload["tenant_id"]),
            domain_id=str(payload["domain_id"]),
            actor_type=actor_type,
            actor_id=actor_id,
            role=PROJECT_ADMIN,
            state="active",
            granted_by_actor_id=actor_id,
            granted_by_actor_type=actor_type,
            created_at=now,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="capex.project.created",
                tenant_id=str(payload["tenant_id"]),
                domain_id=str(payload["domain_id"]),
                actor_type=actor_type,
                actor_id=actor_id,
                links=[
                    {"rel": "subject", "type": "capex_project", "id": project_id},
                ],
                payload={
                    "project_id": project_id,
                    "project_key": project_key,
                    "name": name,
                    "state": state,
                    "created_by_actor_id": actor_id,
                    "created_by_actor_type": actor_type,
                },
                idempotency_key=project_event_idempotency,
            ),
        )
        append_event(
            connection,
            _event_envelope(
                event_type="capex.project_membership.granted",
                tenant_id=str(payload["tenant_id"]),
                domain_id=str(payload["domain_id"]),
                actor_type=actor_type,
                actor_id=actor_id,
                links=[
                    {"rel": "project", "type": "capex_project", "id": project_id},
                    {
                        "rel": "subject",
                        "type": "project_membership",
                        "id": admin_membership_id,
                    },
                ],
                payload={
                    "project_membership_id": admin_membership_id,
                    "project_id": project_id,
                    "actor_id": actor_id,
                    "actor_type": actor_type,
                    "role": PROJECT_ADMIN,
                    "state": "active",
                    "granted_by_actor_id": actor_id,
                    "granted_by_actor_type": actor_type,
                },
                idempotency_key=membership_event_idempotency,
            ),
        )
        project = get_capex_project(connection, project_id)
        membership = get_project_membership(connection, admin_membership_id)
        if project is None or membership is None:
            raise CommandError(
                code="capex_project_not_found",
                message="CAPEX project was not found after creation",
                details={"project_id": project_id},
            )
        return {"project": project, "admin_membership": membership}

    try:
        result, replay = _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=_operation,
        )
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if "capex_projects.project_id" in message:
            raise CommandError(
                code="duplicate_capex_project_id",
                message="project_id already exists",
                details={"project_id": project_id},
            ) from exc
        raise CommandError(
            code="duplicate_capex_project_key",
            message="project_key already exists in scope",
            details={
                "tenant_id": str(payload["tenant_id"]),
                "domain_id": str(payload["domain_id"]),
                "project_key": project_key,
            },
        ) from exc

    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def grant_project_membership_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "project_id",
            "tenant_id",
            "domain_id",
            "actor_id",
            "actor_type",
            "target_actor_id",
            "target_actor_type",
            "role",
            "idempotency_key",
        ],
    )
    project_id = str(payload["project_id"])
    actor_id = str(payload["actor_id"])
    actor_type = _validate_actor_type(str(payload["actor_type"]))
    target_actor_id = str(payload["target_actor_id"])
    target_actor_type = _validate_actor_type(str(payload["target_actor_type"]))
    role = validate_project_role(str(payload["role"]))
    project = require_project_access(
        connection,
        project_id=project_id,
        tenant_id=str(payload["tenant_id"]),
        domain_id=str(payload["domain_id"]),
        actor_type=actor_type,
        actor_id=actor_id,
        min_role=PROJECT_VIEWER,
    )
    require_project_membership_role(
        connection,
        project=project,
        actor_type=actor_type,
        actor_id=actor_id,
        min_role=PROJECT_ADMIN,
    )

    requested_membership_id = payload.get("project_membership_id")
    project_membership_id = str(requested_membership_id or f"pm-{uuid4()}")
    receipt = _prepare_command_receipt(
        command_name="capex.project_memberships.grant",
        payload=payload,
        fingerprint_payload={
            "project_membership_id": (
                str(requested_membership_id)
                if requested_membership_id is not None
                else None
            ),
            "project_id": project_id,
            "tenant_id": str(payload["tenant_id"]),
            "domain_id": str(payload["domain_id"]),
            "actor_id": actor_id,
            "actor_type": actor_type,
            "target_actor_id": target_actor_id,
            "target_actor_type": target_actor_type,
            "role": role,
        },
        tenant_id=str(payload["tenant_id"]),
        domain_id=str(payload["domain_id"]),
        workflow_run_id=None,
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "capex.project_memberships.grant.capex.project_membership.granted",
    )

    def _operation() -> dict[str, Any]:
        now = utc_now_iso()
        create_project_membership(
            connection,
            project_membership_id=project_membership_id,
            project_id=project_id,
            tenant_id=str(project["tenant_id"]),
            domain_id=str(project["domain_id"]),
            actor_type=target_actor_type,
            actor_id=target_actor_id,
            role=role,
            state="active",
            granted_by_actor_id=actor_id,
            granted_by_actor_type=actor_type,
            created_at=now,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="capex.project_membership.granted",
                tenant_id=str(project["tenant_id"]),
                domain_id=str(project["domain_id"]),
                actor_type=actor_type,
                actor_id=actor_id,
                links=[
                    {"rel": "project", "type": "capex_project", "id": project_id},
                    {
                        "rel": "subject",
                        "type": "project_membership",
                        "id": project_membership_id,
                    },
                ],
                payload={
                    "project_membership_id": project_membership_id,
                    "project_id": project_id,
                    "actor_id": target_actor_id,
                    "actor_type": target_actor_type,
                    "role": role,
                    "state": "active",
                    "granted_by_actor_id": actor_id,
                    "granted_by_actor_type": actor_type,
                },
                idempotency_key=event_idempotency,
            ),
        )
        membership = get_project_membership(connection, project_membership_id)
        if membership is None:
            raise CommandError(
                code="project_membership_not_found",
                message="project membership was not found after grant",
                details={"project_membership_id": project_membership_id},
            )
        return {"project": project, "membership": membership}

    try:
        result, replay = _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=_operation,
        )
    except sqlite3.IntegrityError as exc:
        if "project_memberships.project_membership_id" in str(exc):
            raise CommandError(
                code="duplicate_project_membership_id",
                message="project_membership_id already exists",
                details={"project_membership_id": project_membership_id},
            ) from exc
        raise CommandError(
            code="duplicate_project_membership",
            message="actor already has a project membership",
            details={
                "project_id": project_id,
                "actor_type": target_actor_type,
                "actor_id": target_actor_id,
            },
        ) from exc

    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def list_capex_projects_command(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
) -> list[dict[str, Any]]:
    return AuthorizedProjectsQuery(connection).for_actor(
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_type=actor_type,
        actor_id=actor_id,
    ).to_dicts()


def show_capex_project_command(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
) -> dict[str, Any]:
    return require_project_access(
        connection,
        project_id=project_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_type=actor_type,
        actor_id=actor_id,
        min_role=PROJECT_VIEWER,
    )


def list_project_memberships_command(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
) -> list[dict[str, Any]]:
    project = require_project_access(
        connection,
        project_id=project_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_type=actor_type,
        actor_id=actor_id,
        min_role=PROJECT_VIEWER,
    )
    require_project_membership_role(
        connection,
        project=project,
        actor_type=actor_type,
        actor_id=actor_id,
        min_role=PROJECT_ADMIN,
    )
    return list_project_memberships(connection, project_id=project_id)


def _validate_actor_type(actor_type: str) -> str:
    if actor_type not in VALID_ACTOR_TYPES:
        raise CommandError(
            code="invalid_actor_type",
            message=f"unsupported actor_type: {actor_type}",
            details={"allowed_actor_types": sorted(VALID_ACTOR_TYPES)},
        )
    return actor_type


def _required_non_empty(value: Any, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise CommandError(
            code="invalid_payload",
            message=f"{field_name} must be a non-empty string",
            details={"field": field_name},
        )
    return normalized


def _validate_project_state(state: str) -> str:
    if state not in PROJECT_STATES:
        raise CommandError(
            code="invalid_project_state",
            message=f"unsupported project state: {state}",
            details={"allowed_states": sorted(PROJECT_STATES)},
        )
    return state


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CommandError(
            code="invalid_project_metadata",
            message="metadata_json must be an object",
            details={"field": "metadata_json"},
        )
    return dict(value)


__all__ = [
    "PROJECT_ADMIN",
    "PROJECT_CONTRIBUTOR",
    "PROJECT_VIEWER",
    "create_capex_project_command",
    "grant_project_membership_command",
    "list_capex_projects_command",
    "list_project_memberships_command",
    "show_capex_project_command",
]
