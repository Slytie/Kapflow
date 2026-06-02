from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.artifact_effects import (
    _create_artifact_version_effects,
    _ingest_artifact_document_effects,
    _normalize_artifact_links,
)
from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _command_receipt_payload,
    _execute_with_command_receipt,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
    _require_fields,
)
from onetruth.application.read_commands import show_artifact_version_command
from onetruth.infrastructure.artifacts.storage import (
    ArtifactIngressDescriptor,
    ArtifactStorageError,
    ArtifactStorageRootError,
    infer_media_type,
    read_blob,
    resolve_artifact_ingress,
)


def create_artifact_version_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "artifact_kind",
            "media_type",
            "storage_uri",
            "content_digest",
            "metadata_json",
            "idempotency_key",
        ],
    )
    requested_artifact_version_id = payload.get("artifact_version_id")
    artifact_version_id = str(requested_artifact_version_id or f"av-{uuid4()}")
    workflow_run_id = str(payload["workflow_run_id"])
    task_run_id = str(payload["task_run_id"]) if payload.get("task_run_id") is not None else None
    artifact_kind = str(payload["artifact_kind"])
    receipt = _prepare_command_receipt(
        command_name="artifacts.create-version",
        payload=payload,
        fingerprint_payload={
            "artifact_version_id": (
                str(requested_artifact_version_id)
                if requested_artifact_version_id is not None
                else None
            ),
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": (
                str(payload["artifact_role"])
                if payload.get("artifact_role") is not None
                else None
            ),
            "media_type": str(payload["media_type"]),
            "storage_uri": str(payload["storage_uri"]),
            "content_digest": str(payload["content_digest"]),
            "byte_size": (
                int(payload["byte_size"])
                if payload.get("byte_size") is not None
                else None
            ),
            "metadata_json": payload.get("metadata_json"),
            "parent_artifact_version_id": (
                str(payload["parent_artifact_version_id"])
                if payload.get("parent_artifact_version_id") is not None
                else None
            ),
            "supersedes_artifact_version_id": (
                str(payload["supersedes_artifact_version_id"])
                if payload.get("supersedes_artifact_version_id") is not None
                else None
            ),
            "lineage_note": (
                str(payload["lineage_note"])
                if payload.get("lineage_note") is not None
                else None
            ),
            "links": _normalize_artifact_links(payload.get("links")),
            "canonical_partition_kind": payload.get("canonical_partition_kind"),
            "canonical_partition_key": payload.get("canonical_partition_key"),
            "actor_id": str(payload.get("actor_id", "system:runtime")),
            "actor_type": str(payload.get("actor_type", "system")),
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=workflow_run_id,
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "artifacts.create-version.artifact.version.created",
    )

    try:
        result, replay = _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=lambda: _create_artifact_version_effects(
                connection,
                {
                    **payload,
                    "artifact_version_id": artifact_version_id,
                },
                event_idempotency=event_idempotency,
            ),
        )
    except sqlite3.IntegrityError as exc:
        if "artifact_versions.artifact_version_id" in str(exc):
            raise CommandError(
                code="duplicate_artifact_version_id",
                message="artifact_version_id already exists",
                details={"artifact_version_id": artifact_version_id},
            ) from exc
        if "uq_artifact_links_subject" in str(exc):
            raise CommandError(
                code="duplicate_artifact_link",
                message="artifact link already exists for this artifact",
                details={"artifact_version_id": artifact_version_id},
            ) from exc
        raise

    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def ingest_artifact_document_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    storage_root: Path,
    ingress_descriptor: ArtifactIngressDescriptor | None = None,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "artifact_kind",
            "idempotency_key",
        ],
    )
    from onetruth.application.services.capabilities import upload_decision

    upload_decision()

    if ingress_descriptor is None:
        source_path = payload.get("source_path")
        content_base64 = payload.get("content_base64")
        if source_path is None and content_base64 is None:
            raise CommandError(
                code="invalid_payload",
                message="either source_path or content_base64 is required",
                details={},
            )
        if source_path is not None and content_base64 is not None:
            raise CommandError(
                code="invalid_payload",
                message="source_path and content_base64 are mutually exclusive",
                details={},
            )
        try:
            if source_path is not None:
                ingress_descriptor = ArtifactIngressDescriptor.local_source_path(
                    source_path=str(source_path)
                )
            else:
                ingress_descriptor = ArtifactIngressDescriptor.request_bytes(
                    content_base64=str(content_base64)
                )
        except ArtifactStorageError as exc:
            raise CommandError(
                code="invalid_payload",
                message=str(exc),
                details={},
            ) from exc

    try:
        raw_content, default_name = resolve_artifact_ingress(ingress_descriptor)
    except ArtifactStorageError as exc:
        raise CommandError(
            code="artifact_ingress_failed",
            message=str(exc),
            details={},
        ) from exc

    file_name = str(payload.get("file_name") or default_name)
    media_type = str(payload.get("media_type") or infer_media_type(file_name))
    receipt = _prepare_command_receipt(
        command_name="artifacts.ingest",
        payload=payload,
        fingerprint_payload={
            "artifact_version_id": payload.get("artifact_version_id"),
            "workflow_run_id": str(payload["workflow_run_id"]),
            "task_run_id": (
                str(payload["task_run_id"])
                if payload.get("task_run_id") is not None
                else None
            ),
            "artifact_kind": str(payload["artifact_kind"]),
            "artifact_role": (
                str(payload["artifact_role"])
                if payload.get("artifact_role") is not None
                else None
            ),
            "file_name": file_name,
            "media_type": media_type,
            "content_digest": f"sha256:{hashlib.sha256(raw_content).hexdigest()}",
            "byte_size": len(raw_content),
            "ingress_kind": ingress_descriptor.ingress_kind,
            "ingress_source_path": (
                str(ingress_descriptor.source_path)
                if ingress_descriptor.source_path is not None
                else None
            ),
            "storage_root": str(storage_root),
            "metadata_json": payload.get("metadata_json"),
            "parent_artifact_version_id": payload.get("parent_artifact_version_id"),
            "supersedes_artifact_version_id": payload.get("supersedes_artifact_version_id"),
            "lineage_note": payload.get("lineage_note"),
            "links": payload.get("links"),
            "actor_id": payload.get("actor_id", "system:runtime"),
            "actor_type": payload.get("actor_type", "system"),
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=str(payload["workflow_run_id"]),
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "artifacts.ingest.artifact.version.created",
    )
    result, replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=lambda: _ingest_artifact_document_effects(
            connection,
            payload,
            storage_root=storage_root,
            ingress_descriptor=ingress_descriptor,
            raw_content=raw_content,
            file_name=file_name,
            media_type=media_type,
            event_idempotency=event_idempotency,
        ),
    )
    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def download_artifact_blob_command(
    connection: sqlite3.Connection,
    artifact_version_id: str,
    *,
    storage_root: Path | None = None,
) -> dict[str, Any]:
    artifact = show_artifact_version_command(connection, artifact_version_id)
    storage_uri = str(artifact["storage_uri"])
    try:
        content = read_blob(storage_uri, storage_root=storage_root)
    except ArtifactStorageRootError as exc:
        raise CommandError(
            code="artifact_blob_forbidden",
            message=str(exc),
            details={
                "artifact_version_id": artifact_version_id,
                "storage_uri": storage_uri,
            },
        ) from exc
    except ArtifactStorageError as exc:
        if str(artifact.get("artifact_kind") or "") == "planning.draft_weekly_schedule.workbook":
            from onetruth.application.services.schedule_control.draft_workbook import (
                draft_workbook_bytes_from_metadata_json,
            )

            try:
                content = draft_workbook_bytes_from_metadata_json(artifact.get("metadata_json"))
            except ValueError as metadata_exc:
                raise CommandError(
                    code="artifact_blob_not_found",
                    message=str(metadata_exc),
                    details={
                        "artifact_version_id": artifact_version_id,
                        "storage_uri": storage_uri,
                    },
                ) from metadata_exc
        else:
            raise CommandError(
                code="artifact_blob_not_found",
                message=str(exc),
                details={
                    "artifact_version_id": artifact_version_id,
                    "storage_uri": storage_uri,
                },
            ) from exc
    return {
        "artifact_version": artifact,
        "content_bytes": content,
    }
