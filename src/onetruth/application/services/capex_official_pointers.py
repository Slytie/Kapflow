from __future__ import annotations

import re
import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import CommandError, _require_fields
from onetruth.application.handlers.pointers import promote_pointer_command
from onetruth.application.services.capex_project_access import (
    PROJECT_CONTRIBUTOR,
    PROJECT_VIEWER,
    require_project_access,
    require_project_membership_role,
)
from onetruth.infrastructure.repositories.approvals import get_approval
from onetruth.infrastructure.repositories.artifact_pointers import list_pointers_by_canonical_scope
from onetruth.infrastructure.repositories.artifact_versions import get_artifact_version

CAPEX_PROJECT_POINTER_SCOPE_KIND = "capex_project"
CAPEX_PROJECT_POINTER_REGISTRY_KIND = "ordered_stream"
CAPEX_PROJECT_POINTER_REASON = "capex_project_official_pointer"
_POINTER_FAMILY_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,127}$")


def validate_pointer_family(value: Any) -> str:
    family = str(value or "").strip().lower()
    if not _POINTER_FAMILY_RE.fullmatch(family):
        raise CommandError(
            code="invalid_pointer_family",
            message="pointer_family must be a lowercase token",
            details={"pointer_family": str(value or "")},
        )
    return family


def pointer_key_for_family(pointer_family: str) -> str:
    return f"official:{validate_pointer_family(pointer_family)}"


def stream_key_for_project_family(*, project_id: str, pointer_family: str) -> str:
    return f"capex-project:{project_id}:pointer-family:{validate_pointer_family(pointer_family)}"


def decorate_project_official_pointer(
    pointer: dict[str, Any],
    *,
    project_id: str,
    pointer_family: str | None = None,
) -> dict[str, Any]:
    family = pointer_family or _family_from_pointer_key(str(pointer.get("pointer_key") or ""))
    return {
        **pointer,
        "project_id": project_id,
        "pointer_family": family,
    }


def project_official_pointer_snapshot(pointer: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": pointer["project_id"],
        "pointer_family": pointer["pointer_family"],
        "pointer_id": pointer["pointer_id"],
        "artifact_version_id": pointer["artifact_version_id"],
        "artifact_kind": pointer["artifact_kind"],
        "generation": pointer["generation"],
        "updated_at": pointer["updated_at"],
    }


def list_project_official_pointers(
    connection: sqlite3.Connection,
    *,
    project: dict[str, Any],
) -> list[dict[str, Any]]:
    project_id = str(project["project_id"])
    rows = list_pointers_by_canonical_scope(
        connection,
        tenant_id=str(project["tenant_id"]),
        domain_id=str(project["domain_id"]),
        registry_kind=CAPEX_PROJECT_POINTER_REGISTRY_KIND,
        scope_kind=CAPEX_PROJECT_POINTER_SCOPE_KIND,
        scope_ref=project_id,
    )
    return [
        decorate_project_official_pointer(row, project_id=project_id)
        for row in rows
        if _family_from_pointer_key(str(row.get("pointer_key") or "")) is not None
    ]


def get_project_official_pointer(
    connection: sqlite3.Connection,
    *,
    project: dict[str, Any],
    pointer_family: str,
) -> dict[str, Any] | None:
    family = validate_pointer_family(pointer_family)
    rows = list_pointers_by_canonical_scope(
        connection,
        tenant_id=str(project["tenant_id"]),
        domain_id=str(project["domain_id"]),
        registry_kind=CAPEX_PROJECT_POINTER_REGISTRY_KIND,
        scope_kind=CAPEX_PROJECT_POINTER_SCOPE_KIND,
        scope_ref=str(project["project_id"]),
        pointer_key=pointer_key_for_family(family),
    )
    if not rows:
        return None
    return decorate_project_official_pointer(
        rows[0],
        project_id=str(project["project_id"]),
        pointer_family=family,
    )


def promote_project_official_pointer_command(
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
            "pointer_family",
            "workflow_run_id",
            "artifact_version_id",
            "artifact_kind",
            "actor_id",
            "actor_type",
            "idempotency_key",
        ],
    )
    project_id = str(payload["project_id"])
    pointer_family = validate_pointer_family(payload["pointer_family"])
    actor_type = str(payload["actor_type"])
    actor_id = str(payload["actor_id"])
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
        min_role=PROJECT_CONTRIBUTOR,
    )

    workflow_run_id = str(payload["workflow_run_id"])
    _require_workflow_run_in_project(
        connection,
        project=project,
        workflow_run_id=workflow_run_id,
        not_found_code="workflow_run_not_found",
        details={"workflow_run_id": workflow_run_id},
    )
    artifact_version_id = str(payload["artifact_version_id"])
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None or str(artifact["artifact_kind"]) != str(payload["artifact_kind"]):
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version not found",
            details={"artifact_version_id": artifact_version_id},
        )
    _require_workflow_run_in_project(
        connection,
        project=project,
        workflow_run_id=str(artifact["workflow_run_id"]),
        not_found_code="artifact_version_not_found",
        details={"artifact_version_id": artifact_version_id},
    )

    approved_by_approval_id = _optional_text(payload.get("approved_by_approval_id"))
    if approved_by_approval_id is not None:
        approval = get_approval(connection, approved_by_approval_id)
        if approval is None:
            raise CommandError(
                code="approval_not_found",
                message="approval not found",
                details={"approval_id": approved_by_approval_id},
            )
        _require_workflow_run_in_project(
            connection,
            project=project,
            workflow_run_id=str(approval["workflow_run_id"]),
            not_found_code="approval_not_found",
            details={"approval_id": approved_by_approval_id},
        )

    promoted_by_task_run_id = _optional_text(payload.get("promoted_by_task_run_id"))
    if promoted_by_task_run_id is not None:
        _require_task_run_in_project(
            connection,
            project=project,
            task_run_id=promoted_by_task_run_id,
        )

    command_payload: dict[str, Any] = {
        "workflow_run_id": workflow_run_id,
        "scope_kind": CAPEX_PROJECT_POINTER_SCOPE_KIND,
        "scope_ref": project_id,
        "pointer_key": pointer_key_for_family(pointer_family),
        "artifact_kind": str(payload["artifact_kind"]),
        "artifact_version_id": artifact_version_id,
        "promotion_reason": str(payload.get("promotion_reason") or CAPEX_PROJECT_POINTER_REASON),
        "promoted_by_task_run_id": promoted_by_task_run_id,
        "approved_by_approval_id": approved_by_approval_id,
        "expected_generation": payload.get("expected_generation"),
        "stream_key": stream_key_for_project_family(
            project_id=project_id,
            pointer_family=pointer_family,
        ),
        "registry_kind": CAPEX_PROJECT_POINTER_REGISTRY_KIND,
        "actor_id": actor_id,
        "actor_type": actor_type,
        "idempotency_key": payload["idempotency_key"],
    }
    promoted = promote_pointer_command(
        connection,
        command_payload,
        include_receipt=include_receipt,
    )
    if include_receipt:
        pointer = decorate_project_official_pointer(
            promoted["result"],
            project_id=project_id,
            pointer_family=pointer_family,
        )
        return {
            "pointer": pointer,
            "snapshot": project_official_pointer_snapshot(pointer),
            "idempotent_replay": promoted["idempotent_replay"],
            "receipt": promoted["receipt"],
        }
    pointer = decorate_project_official_pointer(
        promoted,
        project_id=project_id,
        pointer_family=pointer_family,
    )
    return {
        "pointer": pointer,
        "snapshot": project_official_pointer_snapshot(pointer),
    }


def _family_from_pointer_key(pointer_key: str) -> str | None:
    if not pointer_key.startswith("official:"):
        return None
    family = pointer_key.removeprefix("official:")
    try:
        return validate_pointer_family(family)
    except CommandError:
        return None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _require_workflow_run_in_project(
    connection: sqlite3.Connection,
    *,
    project: dict[str, Any],
    workflow_run_id: str,
    not_found_code: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT workflow_run_id, tenant_id, domain_id, project_id
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    ).fetchone()
    if row is None:
        raise CommandError(
            code=not_found_code,
            message="resource not found",
            details=details,
        )
    item = dict(row)
    if (
        str(item["tenant_id"]) != str(project["tenant_id"])
        or str(item["domain_id"]) != str(project["domain_id"])
        or item.get("project_id") != project["project_id"]
    ):
        raise CommandError(
            code=not_found_code,
            message="resource not found",
            details=details,
        )
    return item


def _require_task_run_in_project(
    connection: sqlite3.Connection,
    *,
    project: dict[str, Any],
    task_run_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT workflow_run_id
        FROM task_runs
        WHERE task_run_id = ?
        """,
        (task_run_id,),
    ).fetchone()
    if row is None:
        raise CommandError(
            code="task_run_not_found",
            message="task run not found",
            details={"task_run_id": task_run_id},
        )
    _require_workflow_run_in_project(
        connection,
        project=project,
        workflow_run_id=str(row["workflow_run_id"]),
        not_found_code="task_run_not_found",
        details={"task_run_id": task_run_id},
    )
