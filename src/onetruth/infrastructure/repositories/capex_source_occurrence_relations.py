from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import re
import sqlite3
from typing import Any


SOURCE_OCCURRENCE_RELATION_COLUMNS = """
    source_occurrence_relation_id,
    tenant_id,
    domain_id,
    project_id,
    relation_type,
    source_occurrence_id,
    target_source_occurrence_id,
    status,
    basis_ref,
    policy_version,
    metadata_json,
    created_by_actor_id,
    created_by_actor_type,
    created_at,
    updated_at
"""

SOURCE_OCCURRENCE_RELATION_TYPES = (
    "duplicate_of",
    "archive_contains",
    "archive_member_of",
    "derivative_of",
    "redaction_of",
)
SOURCE_OCCURRENCE_RELATION_STATUSES = ("active", "superseded", "rejected")
SOURCE_OCCURRENCE_RELATION_TERMINAL_STATUSES = frozenset({"superseded", "rejected"})

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"^[^/\s]+\.(?:csv|doc|docx|eml|jpeg|jpg|msg|pdf|png|txt|xls|xlsx|zip)$",
    re.IGNORECASE,
)
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "content_base64",
    "document_text",
    "file_name",
    "filename",
    "local_path",
    "ocr_text",
    "raw_bytes",
    "raw_content",
    "raw_file",
    "raw_filename",
    "source_file_path",
    "source_filename",
    "source_path",
    "stderr",
    "stdout",
}


@dataclass(frozen=True)
class SourceOccurrenceRelationError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def create_source_occurrence_relation(
    connection: sqlite3.Connection,
    *,
    source_occurrence_relation_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    relation_type: str,
    source_occurrence_id: str,
    target_source_occurrence_id: str,
    basis_ref: str,
    policy_version: str,
    metadata_json: dict[str, Any],
    created_by_actor_id: str,
    created_by_actor_type: str,
    created_at: str,
    status: str = "active",
) -> dict[str, Any]:
    """Create an internal same-project source-occurrence relation row.

    This repository records relation state only. It does not create source
    occurrences, locator unions, artifacts, workers, events, or official
    pointers.
    """

    _validate_relation_type(relation_type)
    _validate_status(status)
    _require_nonempty(source_occurrence_relation_id, "source_occurrence_relation_id")
    _require_nonempty(project_id, "project_id")
    _require_nonempty(policy_version, "policy_version")
    _reject_raw_material(basis_ref, path="basis_ref")
    _reject_raw_material(metadata_json, path="metadata_json")
    if source_occurrence_id == target_source_occurrence_id:
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_self_reference",
            {"source_occurrence_id": source_occurrence_id},
        )

    _require_project_scope(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    _require_occurrence_scope(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        source_occurrence_id=source_occurrence_id,
        role="source",
    )
    _require_occurrence_scope(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        source_occurrence_id=target_source_occurrence_id,
        role="target",
    )
    if relation_type == "duplicate_of":
        _reject_active_inverse_duplicate(
            connection,
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
            source_occurrence_id=source_occurrence_id,
            target_source_occurrence_id=target_source_occurrence_id,
        )

    connection.execute(
        """
        INSERT INTO capex_source_occurrence_relations (
            source_occurrence_relation_id,
            tenant_id,
            domain_id,
            project_id,
            relation_type,
            source_occurrence_id,
            target_source_occurrence_id,
            status,
            basis_ref,
            policy_version,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_occurrence_relation_id,
            tenant_id,
            domain_id,
            project_id,
            relation_type,
            source_occurrence_id,
            target_source_occurrence_id,
            status,
            basis_ref,
            policy_version,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            created_at,
        ),
    )
    row = get_source_occurrence_relation(connection, source_occurrence_relation_id)
    if row is None:
        raise RuntimeError("source occurrence relation insert failed")
    return row


def get_source_occurrence_relation(
    connection: sqlite3.Connection,
    source_occurrence_relation_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {SOURCE_OCCURRENCE_RELATION_COLUMNS}
        FROM capex_source_occurrence_relations
        WHERE source_occurrence_relation_id = ?
        """,
        (source_occurrence_relation_id,),
    ).fetchone()
    return _relation_row(row)


def list_source_occurrence_relations_for_occurrence(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    source_occurrence_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT {SOURCE_OCCURRENCE_RELATION_COLUMNS}
        FROM capex_source_occurrence_relations
        WHERE tenant_id = ?
          AND domain_id = ?
          AND project_id = ?
          AND (
            source_occurrence_id = ?
            OR target_source_occurrence_id = ?
          )
        ORDER BY relation_type ASC, created_at ASC, source_occurrence_relation_id ASC
        """,
        (
            tenant_id,
            domain_id,
            project_id,
            source_occurrence_id,
            source_occurrence_id,
        ),
    ).fetchall()
    return [_relation_row(row) for row in rows if row is not None]


def transition_source_occurrence_relation_status(
    connection: sqlite3.Connection,
    *,
    source_occurrence_relation_id: str,
    status: str,
    updated_at: str,
) -> dict[str, Any]:
    _validate_status(status)
    current = get_source_occurrence_relation(connection, source_occurrence_relation_id)
    if current is None:
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_not_found",
            {"source_occurrence_relation_id": source_occurrence_relation_id},
        )
    if (
        current["status"] in SOURCE_OCCURRENCE_RELATION_TERMINAL_STATUSES
        and current["status"] != status
    ):
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_terminal_status",
            {
                "source_occurrence_relation_id": source_occurrence_relation_id,
                "current_status": current["status"],
                "requested_status": status,
            },
        )
    connection.execute(
        """
        UPDATE capex_source_occurrence_relations
        SET status = ?, updated_at = ?
        WHERE source_occurrence_relation_id = ?
        """,
        (status, updated_at, source_occurrence_relation_id),
    )
    updated = get_source_occurrence_relation(connection, source_occurrence_relation_id)
    if updated is None:
        raise RuntimeError("source occurrence relation update failed")
    return updated


def _validate_relation_type(relation_type: str) -> None:
    if relation_type not in SOURCE_OCCURRENCE_RELATION_TYPES:
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_type_invalid",
            {"relation_type": relation_type},
        )


def _validate_status(status: str) -> None:
    if status not in SOURCE_OCCURRENCE_RELATION_STATUSES:
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_status_invalid",
            {"status": status},
        )


def _require_project_scope(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT project_id
        FROM capex_projects
        WHERE project_id = ?
          AND tenant_id = ?
          AND domain_id = ?
        """,
        (project_id, tenant_id, domain_id),
    ).fetchone()
    if row is None:
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_project_scope_mismatch",
            {
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "project_id": project_id,
            },
        )


def _require_occurrence_scope(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    source_occurrence_id: str,
    role: str,
) -> None:
    row = connection.execute(
        """
        SELECT tenant_id, domain_id, project_id
        FROM capex_source_occurrences
        WHERE source_occurrence_id = ?
        """,
        (source_occurrence_id,),
    ).fetchone()
    if row is None:
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_occurrence_not_found",
            {"source_occurrence_id": source_occurrence_id, "role": role},
        )
    if row["project_id"] is None:
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_project_required",
            {"source_occurrence_id": source_occurrence_id, "role": role},
        )
    if (
        row["tenant_id"] != tenant_id
        or row["domain_id"] != domain_id
        or row["project_id"] != project_id
    ):
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_occurrence_scope_mismatch",
            {
                "source_occurrence_id": source_occurrence_id,
                "role": role,
                "expected_scope": {
                    "tenant_id": tenant_id,
                    "domain_id": domain_id,
                    "project_id": project_id,
                },
                "actual_scope": {
                    "tenant_id": row["tenant_id"],
                    "domain_id": row["domain_id"],
                    "project_id": row["project_id"],
                },
            },
        )


def _reject_active_inverse_duplicate(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    source_occurrence_id: str,
    target_source_occurrence_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT source_occurrence_relation_id
        FROM capex_source_occurrence_relations
        WHERE tenant_id = ?
          AND domain_id = ?
          AND project_id = ?
          AND relation_type = 'duplicate_of'
          AND source_occurrence_id = ?
          AND target_source_occurrence_id = ?
          AND status = 'active'
        """,
        (
            tenant_id,
            domain_id,
            project_id,
            target_source_occurrence_id,
            source_occurrence_id,
        ),
    ).fetchone()
    if row is not None:
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_duplicate_inverse_exists",
            {
                "existing_relation_id": row["source_occurrence_relation_id"],
                "source_occurrence_id": source_occurrence_id,
                "target_source_occurrence_id": target_source_occurrence_id,
            },
        )


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized_key = key.lower().replace("-", "_")
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise SourceOccurrenceRelationError(
                    "source_occurrence_relation_raw_material_field_forbidden",
                    {"path": f"{path}.{key}", "field": key},
                )
            _reject_raw_material(raw_value, path=f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _reject_raw_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, bytes | bytearray):
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_blob_bytes_forbidden",
            {"path": path},
        )
    if isinstance(value, str):
        lowered = value.lower()
        if "base64," in lowered or lowered.startswith("data:"):
            raise SourceOccurrenceRelationError(
                "source_occurrence_relation_inline_base64_forbidden",
                {"path": path},
            )
        if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
            raise SourceOccurrenceRelationError(
                "source_occurrence_relation_raw_absolute_path_forbidden",
                {"path": path},
            )
        if _RAW_FILENAME_RE.match(value):
            raise SourceOccurrenceRelationError(
                "source_occurrence_relation_raw_filename_forbidden",
                {"path": path},
            )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceOccurrenceRelationError(
            "source_occurrence_relation_required_field_missing",
            {"field": field_name},
        )
    return value.strip()


def _relation_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


__all__ = [
    "SOURCE_OCCURRENCE_RELATION_STATUSES",
    "SOURCE_OCCURRENCE_RELATION_TYPES",
    "SourceOccurrenceRelationError",
    "create_source_occurrence_relation",
    "get_source_occurrence_relation",
    "list_source_occurrence_relations_for_occurrence",
    "transition_source_occurrence_relation_status",
]
