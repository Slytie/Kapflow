from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.services.template_registry import (
    load_template_registry,
    list_templates,
)
from onetruth.infrastructure.artifacts.storage import encode_base64_content

from onetruth.api.dependencies import Page, RequestContext
from onetruth.api.errors import ApiError
from onetruth.api.responses import BinaryResponse, sanitize_download_filename


def list_templates_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    del connection  # Templates are repo fixtures, not per-run database rows.
    del context

    workflow_id = query.get("workflow_id")
    stage_id = query.get("stage_id")
    dataset_key = query.get("dataset_key")
    variant = query.get("variant")

    registry = _load_registry()
    rows = list_templates(
        registry=registry,
        workflow_id=workflow_id,
        stage_id=stage_id,
        dataset_key=dataset_key,
        variant=variant,
    )
    rows = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.templates.list",
        "registry": {
            "id": f"{registry.workflow_id.split('.', 1)[0]}.template_registry",
            "workflow_id": registry.workflow_id,
            "version": registry.version,
        },
        "templates": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def download_template_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    template_id: str,
) -> dict[str, Any]:
    template, content = _load_template_bytes(template_id)
    return {
        "command": "api.templates.download",
        "template": template.as_public_dict(),
        "content_base64": encode_base64_content(content),
        "byte_size": len(content),
    }


def download_template_binary_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    template_id: str,
) -> BinaryResponse:
    template, content = _load_template_bytes(template_id)
    return BinaryResponse(
        body=content,
        media_type=template.media_type or "application/octet-stream",
        file_name=sanitize_download_filename(
            template.source_path.name,
            fallback=template_id,
        ),
    )


def _load_template_bytes(template_id: str):
    registry = _load_registry()
    try:
        template = registry.template_by_id(template_id)
    except ValueError as exc:
        raise ApiError(
            status_code=404,
            code="template_not_found",
            message="template not found",
            details={"template_id": template_id},
        ) from exc

    content = template.source_path.read_bytes()
    return template, content


def get_template_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    template_id: str,
) -> dict[str, Any]:
    del connection
    del context

    registry = _load_registry()
    try:
        template = registry.template_by_id(template_id)
    except ValueError as exc:
        raise ApiError(
            status_code=404,
            code="template_not_found",
            message="template not found",
            details={"template_id": template_id},
        ) from exc
    return {
        "command": "api.templates.detail",
        "template": template.as_public_dict(),
    }


def _load_registry():
    try:
        return load_template_registry()
    except Exception as exc:  # pragma: no cover - defensive surface for malformed local fixtures
        raise ApiError(
            status_code=500,
            code="template_registry_invalid",
            message="template registry is unavailable",
            details={"error": exc.__class__.__name__},
        ) from exc
