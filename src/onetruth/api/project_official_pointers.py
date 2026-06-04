from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.services.capex_official_pointers import (
    get_project_official_pointer,
    list_project_official_pointers,
    promote_project_official_pointer_command,
    project_official_pointer_snapshot,
    validate_pointer_family,
)

from onetruth.api.dependencies import Page, RequestContext
from onetruth.api.errors import api_error_from_command
from onetruth.api.project_scope import (
    normalize_project_path_id,
    parse_project_child_ref,
    raise_not_found,
    require_project_viewer,
)


def list_project_official_pointers_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    page: Page,
) -> dict[str, Any]:
    project_id = normalize_project_path_id(project_id)
    project = require_project_viewer(connection, context=context, project_id=project_id)
    rows = list_project_official_pointers(connection, project=project)
    paged = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.capex.projects.official_pointers.list",
        "project_id": project_id,
        "official_pointers": paged,
        "snapshots": [project_official_pointer_snapshot(row) for row in paged],
        "page": {"limit": page.limit, "offset": page.offset},
    }


def get_project_official_pointer_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_pointer_family: str,
) -> dict[str, Any]:
    project_id, pointer_family = parse_project_child_ref(
        project_pointer_family,
        "official-pointers",
    )
    try:
        family = validate_pointer_family(pointer_family)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    project = require_project_viewer(connection, context=context, project_id=project_id)
    pointer = get_project_official_pointer(
        connection,
        project=project,
        pointer_family=family,
    )
    if pointer is None:
        raise_not_found("pointer_not_found", {"pointer_family": family})
    return {
        "command": "api.capex.projects.official_pointers.detail",
        "project_id": project_id,
        "pointer_family": family,
        "pointer": pointer,
        "snapshot": project_official_pointer_snapshot(pointer),
    }


def promote_project_official_pointer_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_pointer_family: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, pointer_family = parse_project_child_ref(
        project_pointer_family,
        "official-pointers",
    )
    try:
        result = promote_project_official_pointer_command(
            connection,
            {
                **payload,
                "project_id": project_id,
                "tenant_id": context.tenant_id,
                "domain_id": context.domain_id,
                "pointer_family": pointer_family,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
            },
            include_receipt=True,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    family = validate_pointer_family(pointer_family)
    return {
        "command": "api.capex.projects.official_pointers.promote",
        "project_id": project_id,
        "pointer_family": family,
        "pointer": result["pointer"],
        "snapshot": result["snapshot"],
        "idempotent_replay": result["idempotent_replay"],
        "receipt": result["receipt"],
    }
