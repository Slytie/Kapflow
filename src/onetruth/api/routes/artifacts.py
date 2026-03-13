from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    download_artifact_blob_command,
    ingest_artifact_document_command,
    list_artifacts_for_subject_command,
    list_artifacts_for_workflow_run_command,
    show_approval_command,
    show_artifact_version_command,
    show_flag_command,
    show_human_task_command,
)
from onetruth.infrastructure.artifacts.storage import (
    ArtifactIngressDescriptor,
    default_storage_root_for_db_url,
    encode_base64_content,
)
from onetruth.infrastructure.events.event_store import DuplicateIdempotencyKeyError
from onetruth.infrastructure.repositories.artifact_links import list_artifact_links_for_artifact

from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run
from onetruth.api.errors import api_error_from_command, api_error_from_duplicate_idempotency


def list_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    workflow_run_id = query.get("workflow_run_id")
    subject_kind = query.get("subject_kind")
    subject_id = query.get("subject_id")
    artifact_kind = query.get("artifact_kind")

    if subject_kind is not None or subject_id is not None:
        if workflow_run_id is None or subject_kind is None or subject_id is None:
            raise api_error_from_command(
                CommandError(
                    code="invalid_payload",
                    message="workflow_run_id, subject_kind, and subject_id are required together",
                    details={},
                )
            )
        scoped_workflow_run(connection, context, workflow_run_id)
        rows = list_artifacts_for_subject_command(
            connection,
            workflow_run_id=workflow_run_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
        )
    elif workflow_run_id is not None:
        scoped_workflow_run(connection, context, workflow_run_id)
        rows = list_artifacts_for_workflow_run_command(connection, workflow_run_id)
    else:
        rows = query_artifacts_in_scope(
            connection,
            context=context,
            artifact_kind=artifact_kind,
            page=page,
        )
        return {
            "command": "api.artifacts.list",
            "artifact_versions": rows,
            "page": {"limit": page.limit, "offset": page.offset},
        }

    if artifact_kind is not None:
        rows = [row for row in rows if str(row["artifact_kind"]) == artifact_kind]
    rows = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.artifacts.list",
        "artifact_versions": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def ingest_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    workflow_run_id = str(payload.get("workflow_run_id") or "")
    if not workflow_run_id:
        raise api_error_from_command(
            CommandError(
                code="invalid_payload",
                message="workflow_run_id is required",
                details={},
            )
        )
    scoped_workflow_run(connection, context, workflow_run_id)
    ingress_descriptor = _shared_http_request_bytes_descriptor(
        payload,
        endpoint="api.artifacts.ingest",
    )
    ingest_payload = {
        "workflow_run_id": workflow_run_id,
        "task_run_id": payload.get("task_run_id"),
        "artifact_kind": payload.get("artifact_kind"),
        "artifact_role": payload.get("artifact_role"),
        "file_name": payload.get("file_name"),
        "media_type": payload.get("media_type"),
        "metadata_json": payload.get("metadata_json"),
        "parent_artifact_version_id": payload.get("parent_artifact_version_id"),
        "supersedes_artifact_version_id": payload.get("supersedes_artifact_version_id"),
        "lineage_note": payload.get("lineage_note"),
        "links": payload.get("links"),
        "idempotency_key": payload.get("idempotency_key"),
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
    }
    try:
        result = ingest_artifact_document_command(
            connection,
            ingest_payload,
            storage_root=default_storage_root_for_db_url(db_url),
            ingress_descriptor=ingress_descriptor,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.artifacts.ingest",
        **result,
    }


def get_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    artifact_version_id: str,
) -> dict[str, Any]:
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    scoped_workflow_run(connection, context, str(artifact["workflow_run_id"]))
    return {
        "command": "api.artifacts.detail",
        "artifact_version": artifact,
    }


def download_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    artifact_version_id: str,
) -> dict[str, Any]:
    try:
        downloaded = download_artifact_blob_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    artifact = downloaded["artifact_version"]
    scoped_workflow_run(connection, context, str(artifact["workflow_run_id"]))
    content_bytes = downloaded["content_bytes"]
    return {
        "command": "api.artifacts.download",
        "artifact_version": artifact,
        "content_base64": encode_base64_content(content_bytes),
        "byte_size": len(content_bytes),
    }


def upload_workflow_run_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    scoped_workflow_run(connection, context, workflow_run_id)
    return _upload_for_subject(
        connection,
        context=context,
        db_url=db_url,
        payload=payload,
        workflow_run_id=workflow_run_id,
        subject_kind="workflow_run",
        subject_id=workflow_run_id,
        task_run_id=(
            str(payload["task_run_id"])
            if payload.get("task_run_id") is not None
            else None
        ),
    )


def list_workflow_run_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    page: Page,
) -> dict[str, Any]:
    scoped_workflow_run(connection, context, workflow_run_id)
    rows = list_artifacts_for_subject_command(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind="workflow_run",
        subject_id=workflow_run_id,
    )
    rows = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.workflow_runs.artifacts.list",
        "workflow_run_id": workflow_run_id,
        "artifact_versions": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def list_human_task_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
    page: Page,
) -> dict[str, Any]:
    try:
        human_task = show_human_task_command(connection, human_task_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    workflow_run_id = str(human_task["workflow_run_id"])
    scoped_workflow_run(connection, context, workflow_run_id)
    rows = list_artifacts_for_subject_command(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind="human_task",
        subject_id=human_task_id,
    )
    rows = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.human_tasks.artifacts.list",
        "human_task_id": human_task_id,
        "artifact_versions": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def upload_human_task_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        human_task = show_human_task_command(connection, human_task_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    workflow_run_id = str(human_task["workflow_run_id"])
    scoped_workflow_run(connection, context, workflow_run_id)
    return _upload_for_subject(
        connection,
        context=context,
        db_url=db_url,
        payload=payload,
        workflow_run_id=workflow_run_id,
        subject_kind="human_task",
        subject_id=human_task_id,
        task_run_id=str(human_task["task_run_id"]),
    )


def list_approval_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    approval_id: str,
    page: Page,
) -> dict[str, Any]:
    try:
        approval = show_approval_command(connection, approval_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    workflow_run_id = str(approval["workflow_run_id"])
    scoped_workflow_run(connection, context, workflow_run_id)
    rows = list_artifacts_for_subject_command(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind="approval",
        subject_id=approval_id,
    )
    rows = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.approvals.artifacts.list",
        "approval_id": approval_id,
        "artifact_versions": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def upload_approval_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    approval_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        approval = show_approval_command(connection, approval_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    workflow_run_id = str(approval["workflow_run_id"])
    scoped_workflow_run(connection, context, workflow_run_id)
    task_run_id = (
        str(approval["task_run_id"])
        if approval.get("task_run_id") is not None
        else None
    )
    return _upload_for_subject(
        connection,
        context=context,
        db_url=db_url,
        payload=payload,
        workflow_run_id=workflow_run_id,
        subject_kind="approval",
        subject_id=approval_id,
        task_run_id=task_run_id,
    )


def list_flag_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    flag_id: str,
    page: Page,
) -> dict[str, Any]:
    try:
        flag = show_flag_command(connection, flag_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    workflow_run_id = str(flag["workflow_run_id"])
    scoped_workflow_run(connection, context, workflow_run_id)
    rows = list_artifacts_for_subject_command(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind="flag",
        subject_id=flag_id,
    )
    rows = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.flags.artifacts.list",
        "flag_id": flag_id,
        "artifact_versions": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def upload_flag_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    flag_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        flag = show_flag_command(connection, flag_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    workflow_run_id = str(flag["workflow_run_id"])
    scoped_workflow_run(connection, context, workflow_run_id)
    return _upload_for_subject(
        connection,
        context=context,
        db_url=db_url,
        payload=payload,
        workflow_run_id=workflow_run_id,
        subject_kind="flag",
        subject_id=flag_id,
        task_run_id=(
            str(payload["task_run_id"])
            if payload.get("task_run_id") is not None
            else None
        ),
    )


def query_artifacts_in_scope(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    artifact_kind: str | None,
    page: Page,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            av.artifact_version_id,
            av.workflow_run_id,
            av.task_run_id,
            av.artifact_kind,
            av.artifact_role,
            av.media_type,
            av.storage_uri,
            av.content_digest,
            av.byte_size,
            av.metadata_json,
            av.parent_artifact_version_id,
            av.supersedes_artifact_version_id,
            av.lineage_note,
            av.created_at
        FROM artifact_versions av
        JOIN workflow_runs wr
            ON wr.workflow_run_id = av.workflow_run_id
        WHERE wr.tenant_id = ? AND wr.domain_id = ?
    """
    params: list[Any] = [context.tenant_id, context.domain_id]
    if artifact_kind is not None:
        query += " AND av.artifact_kind = ?"
        params.append(artifact_kind)
    query += " ORDER BY av.created_at DESC, av.artifact_version_id ASC LIMIT ? OFFSET ?"
    params.extend([page.limit, page.offset])

    rows = connection.execute(query, params).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        artifact = dict(row)
        artifact["metadata_json"] = json_loads(artifact["metadata_json"])
        artifact["links"] = list_artifact_links_for_artifact(
            connection,
            artifact_version_id=str(artifact["artifact_version_id"]),
        )
        items.append(artifact)
    return items


def _upload_for_subject(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    payload: dict[str, Any],
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
    task_run_id: str | None,
) -> dict[str, Any]:
    ingress_descriptor = _shared_http_request_bytes_descriptor(
        payload,
        endpoint=f"api.{subject_kind}.artifacts.upload",
    )
    ingest_payload = {
        "workflow_run_id": workflow_run_id,
        "task_run_id": task_run_id,
        "artifact_kind": payload.get("artifact_kind"),
        "artifact_role": payload.get("artifact_role"),
        "file_name": payload.get("file_name"),
        "media_type": payload.get("media_type"),
        "metadata_json": payload.get("metadata_json") or {},
        "parent_artifact_version_id": payload.get("parent_artifact_version_id"),
        "supersedes_artifact_version_id": payload.get("supersedes_artifact_version_id"),
        "lineage_note": payload.get("lineage_note"),
        "idempotency_key": payload.get("idempotency_key"),
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "links": [
            {
                "subject_kind": subject_kind,
                "subject_id": subject_id,
                "relation_kind": str(payload.get("relation_kind") or "attachment"),
            }
        ],
    }
    try:
        result = ingest_artifact_document_command(
            connection,
            ingest_payload,
            storage_root=default_storage_root_for_db_url(db_url),
            ingress_descriptor=ingress_descriptor,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": f"api.{subject_kind}.artifacts.upload",
        "subject_kind": subject_kind,
        "subject_id": subject_id,
        "artifact_version": result["artifact_version"],
        "ingress": result["ingress"],
    }


def json_loads(raw: Any) -> Any:
    import json

    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _shared_http_request_bytes_descriptor(
    payload: dict[str, Any],
    *,
    endpoint: str,
) -> ArtifactIngressDescriptor:
    forbidden_fields = [
        field
        for field in ("source_path", "storage_root")
        if payload.get(field) is not None
    ]
    if forbidden_fields:
        raise api_error_from_command(
            CommandError(
                code="invalid_artifact_ingress",
                message="shared HTTP artifact ingress accepts request bytes only",
                details={"endpoint": endpoint, "forbidden_fields": forbidden_fields},
            )
        )

    content_base64 = payload.get("content_base64")
    if content_base64 is None:
        raise api_error_from_command(
            CommandError(
                code="invalid_artifact_ingress",
                message="content_base64 is required for shared HTTP artifact ingress",
                details={"endpoint": endpoint, "required_field": "content_base64"},
            )
        )

    return ArtifactIngressDescriptor.request_bytes(
        content_base64=str(content_base64)
    )
