from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any


ARTIFACT_VERSION_IDENTITY_PROFILE = (
    "onetruth.artifact_version_identity.canonical_json.sha256.v1"
)


class ArtifactProjectIdentityError(ValueError):
    def __init__(
        self,
        artifact_version_id: str,
        *,
        tenant_id: str,
        domain_id: str,
        project_id: str,
    ) -> None:
        super().__init__(
            "artifact version does not belong to the required project scope "
            f"(artifact_version_id={artifact_version_id}, project_id={project_id})"
        )
        self.artifact_version_id = artifact_version_id
        self.tenant_id = tenant_id
        self.domain_id = domain_id
        self.project_id = project_id


def create_artifact_version(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    workflow_run_id: str,
    task_run_id: str | None,
    artifact_kind: str,
    artifact_role: str | None,
    media_type: str,
    storage_uri: str,
    content_digest: str,
    byte_size: int | None,
    metadata_json: dict[str, Any],
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    lineage_note: str | None,
    created_at: str,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    dataset_key: str | None = None,
    partition_kind: str | None = None,
    partition_key: str | None = None,
    project_id: str | None = None,
) -> None:
    resolved_project_id = _resolve_project_id_for_workflow(
        connection,
        workflow_run_id=workflow_run_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    artifact_identity_digest = build_artifact_version_identity_digest(
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=resolved_project_id,
        workflow_run_id=workflow_run_id,
        dataset_key=dataset_key,
        partition_kind=partition_kind,
        partition_key=partition_key,
        artifact_kind=artifact_kind,
        media_type=media_type,
        content_digest=content_digest,
        byte_size=byte_size,
    )
    connection.execute(
        """
        INSERT INTO artifact_versions (
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            project_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            artifact_identity_profile,
            artifact_identity_digest,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            resolved_project_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            json.dumps(metadata_json, separators=(",", ":")),
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            ARTIFACT_VERSION_IDENTITY_PROFILE,
            artifact_identity_digest,
            created_at,
        ),
    )


def get_artifact_version(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            project_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            artifact_identity_profile,
            artifact_identity_digest,
            created_at
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (artifact_version_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(item["metadata_json"])
    return item


def get_superseding_artifact_version(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            project_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            artifact_identity_profile,
            artifact_identity_digest,
            created_at
        FROM artifact_versions
        WHERE supersedes_artifact_version_id = ?
        ORDER BY created_at DESC, artifact_version_id DESC
        LIMIT 1
        """,
        (artifact_version_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(item["metadata_json"])
    return item


def get_latest_artifact_version_in_chain(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any] | None:
    current = get_artifact_version(connection, artifact_version_id)
    if current is None:
        return None

    seen_artifact_version_ids = {artifact_version_id}
    while True:
        superseding = get_superseding_artifact_version(
            connection,
            str(current["artifact_version_id"]),
        )
        if superseding is None:
            return current
        current_id = str(superseding["artifact_version_id"])
        if current_id in seen_artifact_version_ids:
            raise ValueError(
                f"artifact_version supersession cycle detected: {current_id}"
            )
        seen_artifact_version_ids.add(current_id)
        current = superseding


def list_artifact_versions_for_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            project_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            artifact_identity_profile,
            artifact_identity_digest,
            created_at
        FROM artifact_versions
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC, artifact_version_id ASC
        """,
        (workflow_run_id,),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata_json"] = json.loads(item["metadata_json"])
        items.append(item)
    return items


def list_artifact_versions_for_scope_and_kind(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    artifact_kind: str,
    workflow_id: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            av.artifact_version_id,
            av.workflow_run_id,
            av.tenant_id,
            av.domain_id,
            av.project_id,
            av.dataset_key,
            av.partition_kind,
            av.partition_key,
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
            av.artifact_identity_profile,
            av.artifact_identity_digest,
            av.created_at,
            wr.workflow_id AS workflow_id,
            wr.partition_key AS workflow_partition_key,
            wr.logical_date AS workflow_logical_date,
            wr.state AS workflow_state
        FROM artifact_versions av
        JOIN workflow_runs wr
          ON wr.workflow_run_id = av.workflow_run_id
        WHERE av.tenant_id = ?
          AND av.domain_id = ?
          AND av.artifact_kind = ?
    """
    params: list[Any] = [tenant_id, domain_id, artifact_kind]
    if workflow_id is not None:
        query += " AND wr.workflow_id = ?"
        params.append(workflow_id)
    query += """
        ORDER BY
            wr.logical_date ASC,
            av.created_at ASC,
            av.artifact_version_id ASC
    """
    rows = connection.execute(query, params).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata_json"] = json.loads(item["metadata_json"])
        items.append(item)
    return items


def require_artifact_project_identity(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> dict[str, Any]:
    artifact = get_artifact_version(connection, artifact_version_id)
    if (
        artifact is None
        or artifact.get("tenant_id") != tenant_id
        or artifact.get("domain_id") != domain_id
        or artifact.get("project_id") != project_id
    ):
        raise ArtifactProjectIdentityError(
            artifact_version_id,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
        )
    return artifact


def artifact_version_identity_payload(
    *,
    tenant_id: str | None,
    domain_id: str | None,
    project_id: str | None,
    workflow_run_id: str,
    dataset_key: str | None,
    partition_kind: str | None,
    partition_key: str | None,
    artifact_kind: str,
    media_type: str,
    content_digest: str,
    byte_size: int | None,
) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "project_id": project_id,
        "workflow_run_id": workflow_run_id,
        "dataset_key": dataset_key,
        "partition_kind": partition_kind,
        "partition_key": partition_key,
        "artifact_kind": artifact_kind,
        "media_type": media_type,
        "content_digest": content_digest,
        "byte_size": byte_size,
    }


def build_artifact_version_identity_digest(
    *,
    tenant_id: str | None,
    domain_id: str | None,
    project_id: str | None,
    workflow_run_id: str,
    dataset_key: str | None,
    partition_kind: str | None,
    partition_key: str | None,
    artifact_kind: str,
    media_type: str,
    content_digest: str,
    byte_size: int | None,
) -> str:
    payload = artifact_version_identity_payload(
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        dataset_key=dataset_key,
        partition_kind=partition_kind,
        partition_key=partition_key,
        artifact_kind=artifact_kind,
        media_type=media_type,
        content_digest=content_digest,
        byte_size=byte_size,
    )
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _resolve_project_id_for_workflow(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    tenant_id: str | None,
    domain_id: str | None,
    project_id: str | None,
) -> str | None:
    row = connection.execute(
        """
        SELECT tenant_id, domain_id, project_id
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    ).fetchone()
    if row is None:
        return project_id
    if tenant_id is not None and row["tenant_id"] != tenant_id:
        raise ValueError("artifact tenant_id must match workflow_runs.tenant_id")
    if domain_id is not None and row["domain_id"] != domain_id:
        raise ValueError("artifact domain_id must match workflow_runs.domain_id")
    workflow_project_id = (
        str(row["project_id"]) if row["project_id"] is not None else None
    )
    if project_id is not None and workflow_project_id != project_id:
        raise ValueError("artifact project_id must match workflow_runs.project_id")
    return project_id if project_id is not None else workflow_project_id
