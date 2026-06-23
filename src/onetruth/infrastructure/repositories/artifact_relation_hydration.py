from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from typing import Any, Sequence


MAX_ARTIFACT_RELATION_PAGE_SIZE = 500
MAX_ARTIFACT_RELATION_HYDRATION_IDS = 5000
ARTIFACT_RELATION_SQL_CHUNK_SIZE = 500

_ARTIFACT_COLUMNS = """
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
"""


@dataclass(frozen=True)
class ArtifactRelationHydrationError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def list_artifact_versions_page_for_project(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    limit: int,
    offset: int = 0,
    artifact_kind: str | None = None,
) -> list[dict[str, Any]]:
    """Return one bounded artifact page for a CAPEX project scope."""

    page_limit = _coerce_page_limit(limit)
    page_offset = _coerce_offset(offset)
    query = f"""
        SELECT
            {_ARTIFACT_COLUMNS}
        FROM artifact_versions av
        JOIN workflow_runs wr
            ON wr.workflow_run_id = av.workflow_run_id
        WHERE wr.tenant_id = ?
            AND wr.domain_id = ?
            AND wr.project_id = ?
    """
    params: list[Any] = [tenant_id, domain_id, project_id]
    if artifact_kind is not None:
        query += " AND av.artifact_kind = ?"
        params.append(artifact_kind)
    query += """
        ORDER BY av.created_at DESC, av.artifact_version_id DESC
        LIMIT ? OFFSET ?
    """
    params.extend([page_limit, page_offset])
    return _artifact_rows(connection.execute(query, params).fetchall())


def list_artifact_versions_page_with_relations(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    limit: int,
    offset: int = 0,
    artifact_kind: str | None = None,
    include_provenance: bool = True,
) -> list[dict[str, Any]]:
    """Return one project-scoped page with batch-hydrated relation summaries."""

    rows = list_artifact_versions_page_for_project(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        limit=limit,
        offset=offset,
        artifact_kind=artifact_kind,
    )
    attach_hydrated_artifact_relations(
        connection,
        rows,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        include_provenance=include_provenance,
    )
    return rows


def attach_hydrated_artifact_relations(
    connection: sqlite3.Connection,
    artifacts: Sequence[dict[str, Any]],
    *,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    project_id: str | None = None,
    include_provenance: bool = False,
) -> None:
    artifact_ids = [
        str(artifact["artifact_version_id"])
        for artifact in artifacts
        if artifact.get("artifact_version_id") is not None
    ]
    relations = hydrate_artifact_relations_for_versions(
        connection,
        artifact_ids,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        include_provenance=include_provenance,
    )
    for artifact in artifacts:
        artifact_id = str(artifact["artifact_version_id"])
        hydrated = relations.get(artifact_id, _empty_relations())
        artifact["links"] = hydrated["links"]
        if include_provenance:
            artifact["provenance_edges"] = hydrated["provenance_edges"]


def hydrate_artifact_relations_for_versions(
    connection: sqlite3.Connection,
    artifact_version_ids: Sequence[str],
    *,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    project_id: str | None = None,
    include_provenance: bool = True,
) -> dict[str, dict[str, Any]]:
    """Batch-load links and output-side provenance for known artifact versions."""

    artifact_ids = _normalized_artifact_ids(artifact_version_ids)
    if not artifact_ids:
        return {}
    if tenant_id is not None or domain_id is not None or project_id is not None:
        _require_scope(
            connection,
            artifact_ids=artifact_ids,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
        )

    relations = {artifact_id: _empty_relations() for artifact_id in artifact_ids}
    for artifact_id_chunk in _chunks(artifact_ids):
        placeholders = _placeholders(artifact_id_chunk)
        link_rows = connection.execute(
            f"""
            SELECT
                artifact_version_id,
                workflow_run_id,
                subject_kind,
                subject_id,
                relation_kind,
                created_at,
                created_by_actor_id,
                created_by_actor_type
            FROM artifact_links
            WHERE artifact_version_id IN ({placeholders})
            ORDER BY artifact_version_id ASC, created_at ASC, subject_kind ASC, subject_id ASC
            """,
            artifact_id_chunk,
        ).fetchall()
        for row in link_rows:
            item = dict(row)
            relations[str(item["artifact_version_id"])]["links"].append(item)

    if include_provenance:
        for artifact_id_chunk in _chunks(artifact_ids):
            placeholders = _placeholders(artifact_id_chunk)
            provenance_rows = connection.execute(
                f"""
                SELECT
                    edge_id,
                    workflow_run_id,
                    project_id,
                    output_artifact_version_id,
                    input_artifact_version_id,
                    edge_type,
                    edge_order,
                    metadata_json,
                    created_at
                FROM artifact_provenance_edges
                WHERE output_artifact_version_id IN ({placeholders})
                ORDER BY
                    output_artifact_version_id ASC,
                    CASE WHEN edge_order IS NULL THEN 1 ELSE 0 END ASC,
                    edge_order ASC,
                    edge_type ASC,
                    input_artifact_version_id ASC,
                    edge_id ASC
                """,
                artifact_id_chunk,
            ).fetchall()
            for row in provenance_rows:
                item = dict(row)
                if item["metadata_json"] is not None:
                    item["metadata_json"] = json.loads(item["metadata_json"])
                relations[str(item["output_artifact_version_id"])][
                    "provenance_edges"
                ].append(item)

    for hydrated in relations.values():
        hydrated["link_count"] = len(hydrated["links"])
        hydrated["provenance_edge_count"] = len(hydrated["provenance_edges"])
    return relations


def _artifact_rows(rows: Sequence[sqlite3.Row]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata_json"] = json.loads(item["metadata_json"])
        items.append(item)
    return items


def _normalized_artifact_ids(artifact_version_ids: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(artifact_version_ids):
        artifact_id = str(raw).strip()
        if not artifact_id:
            raise ArtifactRelationHydrationError(
                "artifact_relation_artifact_id_required",
                {"index": index},
            )
        if artifact_id in seen:
            raise ArtifactRelationHydrationError(
                "artifact_relation_duplicate_artifact_id",
                {"artifact_version_id": artifact_id},
            )
        seen.add(artifact_id)
        normalized.append(artifact_id)
    if len(normalized) > MAX_ARTIFACT_RELATION_HYDRATION_IDS:
        raise ArtifactRelationHydrationError(
            "artifact_relation_hydration_id_limit_exceeded",
            {
                "limit": MAX_ARTIFACT_RELATION_HYDRATION_IDS,
                "actual": len(normalized),
            },
        )
    return normalized


def _require_scope(
    connection: sqlite3.Connection,
    *,
    artifact_ids: Sequence[str],
    tenant_id: str | None,
    domain_id: str | None,
    project_id: str | None,
) -> None:
    found: set[str] = set()
    for artifact_id_chunk in _chunks(artifact_ids):
        clauses: list[str] = [
            "av.artifact_version_id IN (" + _placeholders(artifact_id_chunk) + ")"
        ]
        params: list[Any] = list(artifact_id_chunk)
        if tenant_id is not None:
            clauses.append("wr.tenant_id = ?")
            params.append(tenant_id)
        if domain_id is not None:
            clauses.append("wr.domain_id = ?")
            params.append(domain_id)
        if project_id is not None:
            clauses.append("wr.project_id = ?")
            params.append(project_id)
        rows = connection.execute(
            f"""
            SELECT av.artifact_version_id
            FROM artifact_versions av
            JOIN workflow_runs wr
                ON wr.workflow_run_id = av.workflow_run_id
            WHERE {' AND '.join(clauses)}
            """,
            params,
        ).fetchall()
        found.update(str(row["artifact_version_id"]) for row in rows)
    expected = set(artifact_ids)
    if found != expected:
        raise ArtifactRelationHydrationError(
            "artifact_relation_scope_mismatch",
            {
                "missing_or_out_of_scope": sorted(expected - found),
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "project_id": project_id,
            },
        )


def _coerce_page_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError) as exc:
        raise ArtifactRelationHydrationError(
            "artifact_relation_page_limit_invalid",
            {"limit": limit},
        ) from exc
    if value < 1 or value > MAX_ARTIFACT_RELATION_PAGE_SIZE:
        raise ArtifactRelationHydrationError(
            "artifact_relation_page_limit_invalid",
            {"limit": value, "max_limit": MAX_ARTIFACT_RELATION_PAGE_SIZE},
        )
    return value


def _coerce_offset(offset: int) -> int:
    try:
        value = int(offset)
    except (TypeError, ValueError) as exc:
        raise ArtifactRelationHydrationError(
            "artifact_relation_page_offset_invalid",
            {"offset": offset},
        ) from exc
    if value < 0:
        raise ArtifactRelationHydrationError(
            "artifact_relation_page_offset_invalid",
            {"offset": value},
        )
    return value


def _empty_relations() -> dict[str, Any]:
    return {
        "links": [],
        "provenance_edges": [],
        "link_count": 0,
        "provenance_edge_count": 0,
    }


def _placeholders(values: Sequence[str]) -> str:
    return ",".join("?" for _ in values)


def _chunks(values: Sequence[str]) -> list[list[str]]:
    return [
        list(values[index : index + ARTIFACT_RELATION_SQL_CHUNK_SIZE])
        for index in range(0, len(values), ARTIFACT_RELATION_SQL_CHUNK_SIZE)
    ]
