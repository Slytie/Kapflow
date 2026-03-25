from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.services.template_registry import (
    TemplateRegistry,
    TemplateRegistryCatalog,
    load_template_registry_catalog,
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

    catalog = _load_catalog()
    rows = list_templates(
        registry=catalog,
        workflow_id=workflow_id,
        stage_id=stage_id,
        dataset_key=dataset_key,
        variant=variant,
    )
    matched_registries = _matched_registries(
        catalog,
        rows=rows,
        workflow_id=workflow_id,
    )
    rows = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.templates.list",
        "registry": (
            matched_registries[0].as_public_dict()
            if len(matched_registries) == 1
            else None
        ),
        "registries": [item.as_public_dict() for item in matched_registries],
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
    catalog = _load_catalog()
    try:
        template = catalog.template_by_id(template_id)
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

    catalog = _load_catalog()
    try:
        template = catalog.template_by_id(template_id)
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


def _load_catalog() -> TemplateRegistryCatalog:
    try:
        return load_template_registry_catalog()
    except Exception as exc:  # pragma: no cover - defensive surface for malformed local fixtures
        raise ApiError(
            status_code=500,
            code="template_registry_invalid",
            message="template registry is unavailable",
            details={"error": exc.__class__.__name__},
        ) from exc


def _matched_registries(
    catalog: TemplateRegistryCatalog,
    *,
    rows: list[dict[str, Any]],
    workflow_id: str | None,
) -> list[TemplateRegistry]:
    if workflow_id is not None:
        registry = catalog.registry_by_workflow_id(workflow_id)
        return [registry] if registry is not None else []

    matched_workflow_ids = {
        str(item["workflow_id"])
        for item in rows
        if item.get("workflow_id") is not None
    }
    return [
        registry
        for registry in catalog.registries
        if registry.workflow_id in matched_workflow_ids
    ]
