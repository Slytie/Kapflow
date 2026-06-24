from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


ARCHIVE_LINEAGE_METADATA_OUTPUTS_SCHEMA_VERSION = (
    "capex.archive_lineage_metadata.outputs.v1"
)
ARCHIVE_LINEAGE_REGISTER_SCHEMA_VERSION = "capex.archive_lineage_register.v1"
NESTED_ARCHIVE_MEMBER_METADATA_SCHEMA_VERSION = (
    "capex.nested_archive_member_metadata.v1"
)
ARCHIVE_LINEAGE_METADATA_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)
ARCHIVE_RELATION_TYPES = frozenset({"archive_contains", "archive_member_of"})
ARCHIVE_MEMBER_STATUSES = frozenset(
    {"observed", "pending_extraction", "unsupported", "metadata_only"}
)

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(?:7z|csv|doc|docx|eml|jpeg|jpg|msg|pdf|png|rar|txt|xls|xlsx|zip)$"
)
_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:@-]+$")
_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "content_base64",
    "document_text",
    "entry_filename",
    "extracted_text",
    "file_name",
    "filename",
    "full_text",
    "local_path",
    "ocr_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_error",
    "raw_file",
    "raw_filename",
    "raw_log",
    "source_file_path",
    "source_filename",
    "source_path",
    "stderr",
    "stdout",
    "text",
    "text_excerpt",
}


@dataclass(frozen=True)
class ArchiveLineageMetadataError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_archive_lineage_metadata_outputs(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    archive_lineage_id: str,
    source_occurrences: Sequence[Mapping[str, Any]],
    relation_rows: Sequence[Mapping[str, Any]],
    member_metadata_rows: Sequence[Mapping[str, Any]],
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build metadata-only archive lineage outputs from existing source rows."""

    scope = {
        "tenant_id": _require_nonempty(tenant_id, "tenant_id"),
        "domain_id": _require_nonempty(domain_id, "domain_id"),
        "project_id": _require_nonempty(project_id, "project_id"),
    }
    if not source_occurrences:
        raise ArchiveLineageMetadataError(
            "archive_lineage_source_occurrences_required",
            {"field": "source_occurrences"},
        )
    if not relation_rows:
        raise ArchiveLineageMetadataError(
            "archive_lineage_relation_rows_required",
            {"field": "relation_rows"},
        )
    if not member_metadata_rows:
        raise ArchiveLineageMetadataError(
            "archive_lineage_member_metadata_rows_required",
            {"field": "member_metadata_rows"},
        )

    occurrence_index = _source_occurrence_index(source_occurrences, scope)
    lineage_rows: list[dict[str, Any]] = []
    seen_relation_ids: set[str] = set()
    graph: dict[str, set[str]] = {}
    for index, raw_row in enumerate(relation_rows):
        if not isinstance(raw_row, Mapping):
            raise ArchiveLineageMetadataError(
                "archive_lineage_relation_row_must_be_object",
                {"index": index},
            )
        row = _lineage_row(index, raw_row, scope, occurrence_index)
        if row["source_occurrence_relation_id"] in seen_relation_ids:
            raise ArchiveLineageMetadataError(
                "archive_lineage_duplicate_relation_id",
                {
                    "index": index,
                    "source_occurrence_relation_id": row[
                        "source_occurrence_relation_id"
                    ],
                },
            )
        seen_relation_ids.add(row["source_occurrence_relation_id"])
        graph.setdefault(row["container_source_occurrence_id"], set()).add(
            row["member_source_occurrence_id"]
        )
        lineage_rows.append(row)

    _reject_archive_cycles(graph)
    depths = _archive_depths(graph)
    relation_pairs = {
        (row["container_source_occurrence_id"], row["member_source_occurrence_id"])
        for row in lineage_rows
    }

    metadata_rows: list[dict[str, Any]] = []
    seen_metadata_ids: set[str] = set()
    seen_metadata_pairs: set[tuple[str, str]] = set()
    for index, raw_row in enumerate(member_metadata_rows):
        if not isinstance(raw_row, Mapping):
            raise ArchiveLineageMetadataError(
                "archive_lineage_member_metadata_row_must_be_object",
                {"index": index},
            )
        row = _member_metadata_row(index, raw_row, scope, occurrence_index, depths)
        metadata_id = row["member_metadata_id"]
        if metadata_id in seen_metadata_ids:
            raise ArchiveLineageMetadataError(
                "archive_lineage_duplicate_member_metadata_id",
                {"index": index, "member_metadata_id": metadata_id},
            )
        pair = (row["container_source_occurrence_id"], row["member_source_occurrence_id"])
        if pair not in relation_pairs:
            raise ArchiveLineageMetadataError(
                "archive_lineage_member_metadata_relation_not_found",
                {"index": index, "relation_pair": list(pair)},
            )
        if pair in seen_metadata_pairs:
            raise ArchiveLineageMetadataError(
                "archive_lineage_duplicate_member_metadata_pair",
                {"index": index, "relation_pair": list(pair)},
            )
        seen_metadata_ids.add(metadata_id)
        seen_metadata_pairs.add(pair)
        metadata_rows.append(row)

    if relation_pairs != seen_metadata_pairs:
        missing = sorted(relation_pairs - seen_metadata_pairs)
        raise ArchiveLineageMetadataError(
            "archive_lineage_member_metadata_missing",
            {"missing_relation_pairs": [list(pair) for pair in missing]},
        )

    metadata_by_pair = {
        (row["container_source_occurrence_id"], row["member_source_occurrence_id"]): row
        for row in metadata_rows
    }
    lineage_rows = [
        {
            **row,
            "nesting_depth": metadata_by_pair[
                (row["container_source_occurrence_id"], row["member_source_occurrence_id"])
            ]["nesting_depth"],
            "member_metadata_ref": (
                "generated_row:capex.nested_archive_member_metadata:"
                + metadata_by_pair[
                    (
                        row["container_source_occurrence_id"],
                        row["member_source_occurrence_id"],
                    )
                ]["member_metadata_id"]
            ),
        }
        for row in lineage_rows
    ]
    lineage_rows = sorted(
        lineage_rows,
        key=lambda row: (
            row["nesting_depth"],
            row["container_source_occurrence_id"],
            row["member_source_occurrence_id"],
            row["source_occurrence_relation_id"],
        ),
    )
    metadata_rows = sorted(
        metadata_rows,
        key=lambda row: (
            row["nesting_depth"],
            row["container_source_occurrence_id"],
            row["entry_index"],
            row["member_metadata_id"],
        ),
    )

    return {
        "schema_version": ARCHIVE_LINEAGE_METADATA_OUTPUTS_SCHEMA_VERSION,
        "activation_posture": ARCHIVE_LINEAGE_METADATA_ACTIVATION_POSTURE,
        "archive_lineage_id": _require_nonempty(
            archive_lineage_id,
            "archive_lineage_id",
        ),
        **scope,
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "basis": {
            "source_occurrence_table": "capex_source_occurrences",
            "source_occurrence_relation_table": "capex_source_occurrence_relations",
            "source_occurrence_count": len(occurrence_index),
            "relation_count": len(lineage_rows),
            "accepted_relation_types": sorted(ARCHIVE_RELATION_TYPES),
        },
        "archive_lineage_register": {
            "schema_version": ARCHIVE_LINEAGE_REGISTER_SCHEMA_VERSION,
            "artifact_kind": "capex.archive_lineage_register",
            "artifact_role": "evidence",
            "rows": lineage_rows,
            "row_count": len(lineage_rows),
            "snapshot_digest": _digest(lineage_rows),
        },
        "nested_archive_member_metadata": {
            "schema_version": NESTED_ARCHIVE_MEMBER_METADATA_SCHEMA_VERSION,
            "artifact_kind": "capex.nested_archive_member_metadata",
            "artifact_role": "evidence",
            "rows": metadata_rows,
            "row_count": len(metadata_rows),
            "snapshot_digest": _digest(metadata_rows),
        },
        "truth_effects": {
            "creates_relation_rows": False,
            "creates_source_occurrences": False,
            "creates_content_identities": False,
            "creates_extraction_jobs": False,
            "starts_workers": False,
            "runs_archive_extractor": False,
            "writes_artifacts": False,
            "emits_timeline_events": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "archive_extraction_runtime_activation",
            "locator_union_activation",
            "parser_runtime_activation",
            "raw_corpus_import",
            "evidence_sufficiency_claim",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_archive_lineage_metadata_bytes(outputs: Mapping[str, Any]) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def archive_lineage_metadata_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_archive_lineage_metadata_bytes(outputs)
    ).hexdigest()


def _source_occurrence_index(
    source_occurrences: Sequence[Mapping[str, Any]],
    scope: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, raw_row in enumerate(source_occurrences):
        if not isinstance(raw_row, Mapping):
            raise ArchiveLineageMetadataError(
                "archive_lineage_source_occurrence_must_be_object",
                {"index": index},
            )
        _reject_raw_material(raw_row, path=f"source_occurrences[{index}]")
        source_occurrence_id = _require_nonempty(
            raw_row.get("source_occurrence_id"),
            f"source_occurrences[{index}].source_occurrence_id",
        )
        if source_occurrence_id in result:
            raise ArchiveLineageMetadataError(
                "archive_lineage_duplicate_source_occurrence_id",
                {"index": index, "source_occurrence_id": source_occurrence_id},
            )
        _require_scope(raw_row, scope, f"source_occurrences[{index}]")
        source_ref = str(
            raw_row.get("source_ref") or f"source_occurrence:{source_occurrence_id}"
        )
        expected_ref = f"source_occurrence:{source_occurrence_id}"
        if source_ref != expected_ref or not _SOURCE_REF_RE.match(source_ref):
            raise ArchiveLineageMetadataError(
                "archive_lineage_source_ref_invalid",
                {
                    "index": index,
                    "source_occurrence_id": source_occurrence_id,
                    "source_ref": source_ref,
                    "expected_source_ref": expected_ref,
                },
            )
        result[source_occurrence_id] = {
            "source_occurrence_id": source_occurrence_id,
            "source_ref": source_ref,
        }
    return result


def _lineage_row(
    index: int,
    raw_row: Mapping[str, Any],
    scope: Mapping[str, str],
    occurrence_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _reject_raw_material(raw_row, path=f"relation_rows[{index}]")
    _require_scope(raw_row, scope, f"relation_rows[{index}]")
    relation_type = _require_nonempty(
        raw_row.get("relation_type"),
        f"relation_rows[{index}].relation_type",
    )
    if relation_type not in ARCHIVE_RELATION_TYPES:
        raise ArchiveLineageMetadataError(
            "archive_lineage_relation_type_invalid",
            {
                "index": index,
                "relation_type": relation_type,
                "allowed_relation_types": sorted(ARCHIVE_RELATION_TYPES),
            },
        )
    relation_id = _require_nonempty(
        raw_row.get("source_occurrence_relation_id"),
        f"relation_rows[{index}].source_occurrence_relation_id",
    )
    source_id = _require_nonempty(
        raw_row.get("source_occurrence_id"),
        f"relation_rows[{index}].source_occurrence_id",
    )
    target_id = _require_nonempty(
        raw_row.get("target_source_occurrence_id"),
        f"relation_rows[{index}].target_source_occurrence_id",
    )
    if source_id == target_id:
        raise ArchiveLineageMetadataError(
            "archive_lineage_self_relation",
            {"index": index, "source_occurrence_id": source_id},
        )
    _require_known_occurrence(source_id, occurrence_index, index, "source")
    _require_known_occurrence(target_id, occurrence_index, index, "target")
    if relation_type == "archive_contains":
        container_id, member_id = source_id, target_id
    else:
        container_id, member_id = target_id, source_id
    basis_ref = _require_nonempty(
        raw_row.get("basis_ref"),
        f"relation_rows[{index}].basis_ref",
    )
    _validate_source_ref(basis_ref, index, "basis_ref")
    return {
        "source_occurrence_relation_id": relation_id,
        "source_occurrence_relation_ref": f"source_occurrence_relation:{relation_id}",
        "relation_type": relation_type,
        "container_source_occurrence_id": container_id,
        "container_source_ref": f"source_occurrence:{container_id}",
        "member_source_occurrence_id": member_id,
        "member_source_ref": f"source_occurrence:{member_id}",
        "status": str(raw_row.get("status") or "active"),
        "basis_ref": basis_ref,
        "policy_version": _require_nonempty(
            raw_row.get("policy_version"),
            f"relation_rows[{index}].policy_version",
        ),
    }


def _member_metadata_row(
    index: int,
    raw_row: Mapping[str, Any],
    scope: Mapping[str, str],
    occurrence_index: Mapping[str, Mapping[str, Any]],
    depths: Mapping[str, int],
) -> dict[str, Any]:
    _reject_raw_material(raw_row, path=f"member_metadata_rows[{index}]")
    _require_scope(raw_row, scope, f"member_metadata_rows[{index}]")
    metadata_id = _require_nonempty(
        raw_row.get("member_metadata_id"),
        f"member_metadata_rows[{index}].member_metadata_id",
    )
    container_id = _require_nonempty(
        raw_row.get("container_source_occurrence_id"),
        f"member_metadata_rows[{index}].container_source_occurrence_id",
    )
    member_id = _require_nonempty(
        raw_row.get("member_source_occurrence_id"),
        f"member_metadata_rows[{index}].member_source_occurrence_id",
    )
    _require_known_occurrence(container_id, occurrence_index, index, "container")
    _require_known_occurrence(member_id, occurrence_index, index, "member")
    if container_id == member_id:
        raise ArchiveLineageMetadataError(
            "archive_lineage_member_metadata_self_reference",
            {"index": index, "source_occurrence_id": member_id},
        )
    nesting_depth = _require_nonnegative_int(
        raw_row.get("nesting_depth"),
        f"member_metadata_rows[{index}].nesting_depth",
    )
    expected_depth = depths.get(member_id)
    if expected_depth is None or nesting_depth != expected_depth:
        raise ArchiveLineageMetadataError(
            "archive_lineage_nesting_depth_invalid",
            {
                "index": index,
                "member_source_occurrence_id": member_id,
                "nesting_depth": nesting_depth,
                "expected_nesting_depth": expected_depth,
            },
        )
    entry_index = _require_nonnegative_int(
        raw_row.get("entry_index"),
        f"member_metadata_rows[{index}].entry_index",
    )
    logical_member_ref = _require_safe_token(
        raw_row.get("logical_member_ref"),
        f"member_metadata_rows[{index}].logical_member_ref",
    )
    logical_path_segments = raw_row.get("logical_path_segments")
    if not isinstance(logical_path_segments, Sequence) or isinstance(
        logical_path_segments,
        str | bytes | bytearray,
    ):
        raise ArchiveLineageMetadataError(
            "archive_lineage_logical_path_segments_required",
            {"index": index},
        )
    normalized_segments = [
        _require_safe_token(
            segment,
            f"member_metadata_rows[{index}].logical_path_segments[{segment_index}]",
        )
        for segment_index, segment in enumerate(logical_path_segments)
    ]
    status = str(raw_row.get("extraction_metadata_status") or "metadata_only")
    if status not in ARCHIVE_MEMBER_STATUSES:
        raise ArchiveLineageMetadataError(
            "archive_lineage_member_status_invalid",
            {
                "index": index,
                "extraction_metadata_status": status,
                "allowed_statuses": sorted(ARCHIVE_MEMBER_STATUSES),
            },
        )
    content_digest = raw_row.get("member_content_digest")
    if content_digest is not None:
        content_digest = _require_sha256(
            content_digest,
            f"member_metadata_rows[{index}].member_content_digest",
        )
    return {
        "member_metadata_id": metadata_id,
        "container_source_occurrence_id": container_id,
        "container_source_ref": f"source_occurrence:{container_id}",
        "member_source_occurrence_id": member_id,
        "member_source_ref": f"source_occurrence:{member_id}",
        "logical_member_ref": logical_member_ref,
        "logical_path_segments": normalized_segments,
        "nesting_depth": nesting_depth,
        "entry_index": entry_index,
        "extraction_metadata_status": status,
        "member_content_digest": content_digest,
        "compressed_byte_size": _optional_nonnegative_int(
            raw_row.get("compressed_byte_size"),
            f"member_metadata_rows[{index}].compressed_byte_size",
        ),
        "uncompressed_byte_size": _optional_nonnegative_int(
            raw_row.get("uncompressed_byte_size"),
            f"member_metadata_rows[{index}].uncompressed_byte_size",
        ),
        "metadata": dict(raw_row.get("metadata") or {}),
    }


def _reject_archive_cycles(graph: Mapping[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, path: list[str]) -> None:
        if node in visiting:
            raise ArchiveLineageMetadataError(
                "archive_lineage_cycle_detected",
                {"cycle": path + [node]},
            )
        if node in visited:
            return
        visiting.add(node)
        for child in sorted(graph.get(node, set())):
            visit(child, path + [node])
        visiting.remove(node)
        visited.add(node)

    for root in sorted(graph):
        visit(root, [])


def _archive_depths(graph: Mapping[str, set[str]]) -> dict[str, int]:
    children = {child for members in graph.values() for child in members}
    roots = sorted(set(graph) - children)
    depths: dict[str, int] = {}

    def walk(node: str, depth: int) -> None:
        for child in sorted(graph.get(node, set())):
            next_depth = depth + 1
            if child in depths and depths[child] != next_depth:
                raise ArchiveLineageMetadataError(
                    "archive_lineage_multiple_depths_for_member",
                    {
                        "member_source_occurrence_id": child,
                        "existing_depth": depths[child],
                        "next_depth": next_depth,
                    },
                )
            depths[child] = next_depth
            walk(child, next_depth)

    for root in roots:
        walk(root, 0)
    return depths


def _require_scope(
    row: Mapping[str, Any],
    scope: Mapping[str, str],
    path: str,
) -> None:
    for field in ("tenant_id", "domain_id", "project_id"):
        if row.get(field) != scope[field]:
            raise ArchiveLineageMetadataError(
                "archive_lineage_scope_mismatch",
                {
                    "path": path,
                    "field": field,
                    "expected": scope[field],
                    "actual": row.get(field),
                },
            )


def _require_known_occurrence(
    source_occurrence_id: str,
    occurrence_index: Mapping[str, Mapping[str, Any]],
    index: int,
    role: str,
) -> None:
    if source_occurrence_id not in occurrence_index:
        raise ArchiveLineageMetadataError(
            "archive_lineage_source_occurrence_not_found",
            {
                "index": index,
                "role": role,
                "source_occurrence_id": source_occurrence_id,
            },
        )


def _validate_source_ref(source_ref: str, index: int, field_name: str) -> None:
    if not _SOURCE_REF_RE.match(source_ref):
        raise ArchiveLineageMetadataError(
            "archive_lineage_source_ref_invalid",
            {"index": index, "field": field_name, "source_ref": source_ref},
        )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArchiveLineageMetadataError(
            "archive_lineage_required_field_missing",
            {"field": field_name},
        )
    return value.strip()


def _require_safe_token(value: Any, field_name: str) -> str:
    token = _require_nonempty(value, field_name)
    if not _SAFE_TOKEN_RE.match(token):
        raise ArchiveLineageMetadataError(
            "archive_lineage_safe_token_invalid",
            {"field": field_name, "value": token},
        )
    if _RAW_FILENAME_RE.match(token):
        raise ArchiveLineageMetadataError(
            "archive_lineage_raw_filename_forbidden",
            {"field": field_name, "value": token},
        )
    return token


def _require_sha256(value: Any, field_name: str) -> str:
    digest = _require_nonempty(value, field_name).lower()
    if not _SHA256_RE.match(digest):
        raise ArchiveLineageMetadataError(
            "archive_lineage_digest_invalid",
            {"field": field_name, "value": value},
        )
    return digest


def _require_nonnegative_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ArchiveLineageMetadataError(
            "archive_lineage_nonnegative_integer_required",
            {"field": field_name, "value": value},
        )
    return value


def _optional_nonnegative_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _require_nonnegative_int(value, field_name)


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized_key = key.lower().replace("-", "_")
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise ArchiveLineageMetadataError(
                    "archive_lineage_raw_material_field_forbidden",
                    {"path": f"{path}.{key}", "field": key},
                )
            _reject_raw_material(raw_value, path=f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _reject_raw_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, bytes | bytearray):
        raise ArchiveLineageMetadataError(
            "archive_lineage_blob_bytes_forbidden",
            {"path": path},
        )
    if isinstance(value, str):
        lowered = value.lower()
        if "base64," in lowered or lowered.startswith("data:"):
            raise ArchiveLineageMetadataError(
                "archive_lineage_inline_base64_forbidden",
                {"path": path},
            )
        if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
            raise ArchiveLineageMetadataError(
                "archive_lineage_raw_absolute_path_forbidden",
                {"path": path},
            )
        if _RAW_FILENAME_RE.match(value):
            raise ArchiveLineageMetadataError(
                "archive_lineage_raw_filename_forbidden",
                {"path": path},
            )


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "ARCHIVE_LINEAGE_METADATA_ACTIVATION_POSTURE",
    "ARCHIVE_LINEAGE_METADATA_OUTPUTS_SCHEMA_VERSION",
    "ARCHIVE_LINEAGE_REGISTER_SCHEMA_VERSION",
    "NESTED_ARCHIVE_MEMBER_METADATA_SCHEMA_VERSION",
    "ArchiveLineageMetadataError",
    "archive_lineage_metadata_digest",
    "build_archive_lineage_metadata_outputs",
    "canonical_archive_lineage_metadata_bytes",
]
