from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3
from typing import Any

from onetruth.capex_platform.source_inventory import SOURCE_INVENTORY_SCHEMA_VERSION
from onetruth.infrastructure.repositories.capex_source_occurrences import (
    SOURCE_OCCURRENCE_STATUSES,
    create_source_occurrence,
    get_content_identity,
    get_source_occurrence,
)


SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION = "capex.source_occurrence_register.v1"
SOURCE_OCCURRENCE_REGISTER_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)
SOURCE_OCCURRENCE_REGISTER_ARTIFACT_KIND = "capex.source_occurrence_register"
SOURCE_OCCURRENCE_REGISTER_ARTIFACT_ROLE = "evidence"

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip)$"
)
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_LOCATOR_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "document_text",
    "file_name",
    "filename",
    "local_path",
    "ocr_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_file",
    "raw_filename",
    "source_filename",
}


@dataclass(frozen=True)
class SourceOccurrenceRegisterError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_source_occurrence_register(
    connection: sqlite3.Connection,
    *,
    source_inventory: Mapping[str, Any],
    occurrence_contexts: Sequence[Mapping[str, Any]],
    register_id: str,
    created_at: str,
    registered_by_actor_id: str,
    registered_by_actor_type: str,
) -> dict[str, Any]:
    """Create source occurrences and return a deterministic register payload."""

    _require_inventory_schema(source_inventory)
    tenant_id = _require_nonempty(source_inventory.get("tenant_id"), "tenant_id")
    domain_id = _require_nonempty(source_inventory.get("domain_id"), "domain_id")
    project_id = _require_nonempty(source_inventory.get("project_id"), "project_id")
    inventory_items = {
        _require_nonempty(item.get("descriptor_id"), "inventory.items[].descriptor_id"): item
        for item in _require_item_list(source_inventory.get("items"))
    }
    if not occurrence_contexts:
        raise SourceOccurrenceRegisterError(
            "source_occurrence_contexts_required",
            {"field": "occurrence_contexts"},
        )

    rows: list[dict[str, Any]] = []
    for index, context in enumerate(occurrence_contexts):
        if not isinstance(context, Mapping):
            raise SourceOccurrenceRegisterError(
                "source_occurrence_context_must_be_object",
                {"index": index},
            )
        rows.append(
            _create_occurrence_from_context(
                connection,
                tenant_id=tenant_id,
                domain_id=domain_id,
                project_id=project_id,
                register_id=register_id,
                inventory_items=inventory_items,
                context=context,
                index=index,
                created_at=created_at,
                registered_by_actor_id=registered_by_actor_id,
                registered_by_actor_type=registered_by_actor_type,
            )
        )

    rows = sorted(rows, key=lambda row: row["source_occurrence_id"])
    snapshot_digest = source_occurrence_register_snapshot_digest(rows)
    return {
        "schema_version": SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION,
        "activation_posture": SOURCE_OCCURRENCE_REGISTER_ACTIVATION_POSTURE,
        "register_id": _require_nonempty(register_id, "register_id"),
        "source_inventory_id": _require_nonempty(
            source_inventory.get("inventory_id"),
            "source_inventory.inventory_id",
        ),
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "project_id": project_id,
        "created_at": _require_nonempty(created_at, "created_at"),
        "registered_by_actor": {
            "id": _require_nonempty(
                registered_by_actor_id,
                "registered_by_actor_id",
            ),
            "type": _require_nonempty(
                registered_by_actor_type,
                "registered_by_actor_type",
            ),
        },
        "row_count": len(rows),
        "physical_row_count": _physical_row_count(
            connection,
            [row["source_occurrence_id"] for row in rows],
        ),
        "snapshot_digest": snapshot_digest,
        "rows": rows,
        "truth_effects": {
            "creates_source_occurrences": True,
            "creates_role_assignments": False,
            "creates_packet_register": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def canonical_source_occurrence_register_bytes(register: Mapping[str, Any]) -> bytes:
    return json.dumps(
        register,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def source_occurrence_register_digest(register: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_source_occurrence_register_bytes(register)
    ).hexdigest()


def source_occurrence_register_snapshot_digest(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            list(rows),
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _create_occurrence_from_context(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    register_id: str,
    inventory_items: Mapping[str, Mapping[str, Any]],
    context: Mapping[str, Any],
    index: int,
    created_at: str,
    registered_by_actor_id: str,
    registered_by_actor_type: str,
) -> dict[str, Any]:
    descriptor_id = _require_nonempty(
        context.get("descriptor_id"),
        f"occurrence_contexts[{index}].descriptor_id",
    )
    if descriptor_id not in inventory_items:
        raise SourceOccurrenceRegisterError(
            "source_occurrence_inventory_item_not_found",
            {"index": index, "descriptor_id": descriptor_id},
        )
    inventory_item = inventory_items[descriptor_id]
    content_identity_id = _require_nonempty(
        inventory_item.get("content_identity_id"),
        f"inventory.items[{descriptor_id}].content_identity_id",
    )
    content_identity = get_content_identity(connection, content_identity_id)
    if content_identity is None:
        raise SourceOccurrenceRegisterError(
            "source_occurrence_content_identity_not_found",
            {"index": index, "content_identity_id": content_identity_id},
        )
    if (
        str(content_identity["tenant_id"]) != tenant_id
        or str(content_identity["domain_id"]) != domain_id
    ):
        raise SourceOccurrenceRegisterError(
            "source_occurrence_content_identity_scope_mismatch",
            {"index": index, "content_identity_id": content_identity_id},
        )

    status = str(context.get("status") or "available")
    if status not in SOURCE_OCCURRENCE_STATUSES:
        raise SourceOccurrenceRegisterError(
            "source_occurrence_status_invalid",
            {
                "index": index,
                "status": status,
                "allowed_statuses": list(SOURCE_OCCURRENCE_STATUSES),
            },
        )
    locator_json = context.get("locator_json")
    if not isinstance(locator_json, Mapping):
        raise SourceOccurrenceRegisterError(
            "source_occurrence_locator_required",
            {"index": index},
        )
    _reject_raw_locator_material(locator_json, path=f"occurrence_contexts[{index}].locator_json")
    metadata_json = context.get("metadata_json")
    if metadata_json is None:
        metadata_json = {}
    if not isinstance(metadata_json, Mapping):
        raise SourceOccurrenceRegisterError(
            "source_occurrence_metadata_must_be_object",
            {"index": index},
        )
    _reject_raw_locator_material(metadata_json, path=f"occurrence_contexts[{index}].metadata_json")

    source_occurrence_id = str(
        context.get("source_occurrence_id")
        or _derived_occurrence_id(register_id, descriptor_id, index)
    )
    create_source_occurrence(
        connection,
        source_occurrence_id=source_occurrence_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
        content_identity_id=content_identity_id,
        occurrence_kind=_require_nonempty(
            context.get("occurrence_kind"),
            f"occurrence_contexts[{index}].occurrence_kind",
        ),
        status=status,
        locator_json=dict(locator_json),
        metadata_json={
            **dict(metadata_json),
            "source_occurrence_register_id": register_id,
            "source_inventory_descriptor_id": descriptor_id,
            "role_assignment_created": False,
            "packet_register_created": False,
        },
        registered_by_actor_id=_require_nonempty(
            registered_by_actor_id,
            "registered_by_actor_id",
        ),
        registered_by_actor_type=_require_nonempty(
            registered_by_actor_type,
            "registered_by_actor_type",
        ),
        created_at=created_at,
    )
    created = get_source_occurrence(connection, source_occurrence_id)
    if created is None:
        raise SourceOccurrenceRegisterError(
            "source_occurrence_create_failed",
            {"source_occurrence_id": source_occurrence_id},
        )
    return {
        "source_occurrence_id": source_occurrence_id,
        "source_ref": str(created["source_ref"]),
        "descriptor_id": descriptor_id,
        "content_identity_id": content_identity_id,
        "digest_algorithm": str(inventory_item["digest_algorithm"]),
        "content_digest": str(inventory_item["content_digest"]),
        "occurrence_kind": str(created["occurrence_kind"]),
        "status": str(created["status"]),
        "project_id": str(created["project_id"]),
        "locator_json": created["locator_json"],
    }


def _require_inventory_schema(source_inventory: Mapping[str, Any]) -> None:
    if source_inventory.get("schema_version") != SOURCE_INVENTORY_SCHEMA_VERSION:
        raise SourceOccurrenceRegisterError(
            "source_occurrence_register_requires_source_inventory",
            {
                "expected_schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
                "actual_schema_version": source_inventory.get("schema_version"),
            },
        )


def _require_item_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise SourceOccurrenceRegisterError(
            "source_occurrence_register_inventory_items_required",
            {"field": "source_inventory.items"},
        )
    if not all(isinstance(item, Mapping) for item in value):
        raise SourceOccurrenceRegisterError(
            "source_occurrence_register_inventory_item_must_be_object",
            {"field": "source_inventory.items"},
        )
    return value


def _reject_raw_locator_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized_key = key.lower().replace("-", "_")
            if normalized_key in _FORBIDDEN_LOCATOR_KEYS:
                raise SourceOccurrenceRegisterError(
                    "source_occurrence_raw_locator_field_forbidden",
                    {"path": f"{path}.{key}", "field": key},
                )
            _reject_raw_locator_material(raw_value, path=f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _reject_raw_locator_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        _validate_safe_string(value, path=path)


def _validate_safe_string(value: str, *, path: str) -> None:
    lowered = value.lower()
    if lowered.startswith("data:") or "base64," in lowered:
        raise SourceOccurrenceRegisterError(
            "source_occurrence_inline_content_forbidden",
            {"path": path},
        )
    if (
        _ABSOLUTE_PATH_RE.match(value)
        or any(marker in value for marker in _RAW_PATH_MARKERS)
        or _RAW_FILENAME_RE.match(value)
    ):
        raise SourceOccurrenceRegisterError(
            "source_occurrence_raw_locator_value_forbidden",
            {"path": path, "value": value},
        )


def _physical_row_count(
    connection: sqlite3.Connection,
    source_occurrence_ids: Sequence[str],
) -> int:
    if not source_occurrence_ids:
        return 0
    placeholders = ",".join("?" for _ in source_occurrence_ids)
    row = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM capex_source_occurrences
        WHERE source_occurrence_id IN ({placeholders})
        """,
        tuple(source_occurrence_ids),
    ).fetchone()
    return int(row[0])


def _derived_occurrence_id(register_id: str, descriptor_id: str, index: int) -> str:
    digest = hashlib.sha256(
        f"{register_id}:{descriptor_id}:{index}".encode("utf-8")
    ).hexdigest()
    return f"so-{digest[:24]}"


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceOccurrenceRegisterError(
            "source_occurrence_required_field_missing",
            {"field": field_name},
        )
    return value.strip()


__all__ = [
    "SOURCE_OCCURRENCE_REGISTER_ACTIVATION_POSTURE",
    "SOURCE_OCCURRENCE_REGISTER_ARTIFACT_KIND",
    "SOURCE_OCCURRENCE_REGISTER_ARTIFACT_ROLE",
    "SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION",
    "SourceOccurrenceRegisterError",
    "build_source_occurrence_register",
    "canonical_source_occurrence_register_bytes",
    "source_occurrence_register_digest",
    "source_occurrence_register_snapshot_digest",
]
