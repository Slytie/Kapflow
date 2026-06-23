from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.source_occurrence_register import (
    SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION,
)


ROLE_ASSIGNMENT_REGISTER_SCHEMA_VERSION = "capex.role_assignment_register.v1"
PACKET_REGISTER_SCHEMA_VERSION = "capex.packet_register.v1"
ROLE_PACKET_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
ROLE_ASSIGNMENT_REGISTER_ARTIFACT_KIND = "capex.role_assignment_register"
PACKET_REGISTER_ARTIFACT_KIND = "capex.packet_register"
ROLE_PACKET_ARTIFACT_ROLE = "evidence"

ROLE_REVIEW_STATES = frozenset({"draft_ai_suggested", "human_reviewed", "rejected"})
PACKET_REVIEW_STATES = frozenset({"draft_ai_suggested", "human_reviewed", "split", "merged"})
SOURCE_ROLES = frozenset(
    {
        "primary_evidence",
        "supporting_evidence",
        "context",
        "duplicate",
        "superseded",
        "out_of_scope",
    }
)

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip)$"
)
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
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
class RolePacketRegisterError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_role_assignment_register(
    *,
    source_occurrence_register: Mapping[str, Any],
    role_assignments: Sequence[Mapping[str, Any]],
    register_id: str,
    created_at: str,
    reviewed_by_actor_id: str,
    reviewed_by_actor_type: str,
) -> dict[str, Any]:
    _require_occurrence_register(source_occurrence_register)
    rows_by_ref = {
        _require_nonempty(row.get("source_ref"), "source_occurrence_register.rows[].source_ref"): row
        for row in _require_rows(source_occurrence_register.get("rows"), "source_occurrence_register.rows")
    }
    if not role_assignments:
        raise RolePacketRegisterError(
            "role_assignment_rows_required",
            {"field": "role_assignments"},
        )

    rows: list[dict[str, Any]] = []
    seen_source_refs: set[str] = set()
    for index, assignment in enumerate(role_assignments):
        if not isinstance(assignment, Mapping):
            raise RolePacketRegisterError(
                "role_assignment_must_be_object",
                {"index": index},
            )
        row = _role_row(
            index=index,
            assignment=assignment,
            rows_by_ref=rows_by_ref,
            register_id=register_id,
        )
        if row["source_ref"] in seen_source_refs:
            raise RolePacketRegisterError(
                "role_assignment_duplicate_source_ref",
                {"index": index, "source_ref": row["source_ref"]},
            )
        seen_source_refs.add(row["source_ref"])
        rows.append(row)

    rows = sorted(rows, key=lambda row: row["role_assignment_id"])
    return {
        "schema_version": ROLE_ASSIGNMENT_REGISTER_SCHEMA_VERSION,
        "activation_posture": ROLE_PACKET_ACTIVATION_POSTURE,
        "register_id": _require_nonempty(register_id, "register_id"),
        "source_occurrence_register_id": _require_nonempty(
            source_occurrence_register.get("register_id"),
            "source_occurrence_register.register_id",
        ),
        "tenant_id": _require_nonempty(source_occurrence_register.get("tenant_id"), "tenant_id"),
        "domain_id": _require_nonempty(source_occurrence_register.get("domain_id"), "domain_id"),
        "project_id": _require_nonempty(source_occurrence_register.get("project_id"), "project_id"),
        "created_at": _require_nonempty(created_at, "created_at"),
        "reviewed_by_actor": {
            "id": _require_nonempty(reviewed_by_actor_id, "reviewed_by_actor_id"),
            "type": _require_nonempty(reviewed_by_actor_type, "reviewed_by_actor_type"),
        },
        "row_count": len(rows),
        "rows": rows,
        "snapshot_digest": _digest(rows),
        "truth_effects": {
            "creates_role_assignments": True,
            "creates_packet_register": False,
            "creates_reviewed_baseline": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def build_packet_register(
    *,
    role_assignment_register: Mapping[str, Any],
    packets: Sequence[Mapping[str, Any]],
    register_id: str,
    created_at: str,
    reviewed_by_actor_id: str,
    reviewed_by_actor_type: str,
) -> dict[str, Any]:
    _require_role_register(role_assignment_register)
    role_rows = {
        _require_nonempty(row.get("source_ref"), "role_assignment_register.rows[].source_ref"): row
        for row in _require_rows(role_assignment_register.get("rows"), "role_assignment_register.rows")
    }
    if not packets:
        raise RolePacketRegisterError(
            "packet_rows_required",
            {"field": "packets"},
        )

    rows: list[dict[str, Any]] = []
    seen_packet_ids: set[str] = set()
    for index, packet in enumerate(packets):
        if not isinstance(packet, Mapping):
            raise RolePacketRegisterError("packet_must_be_object", {"index": index})
        row = _packet_row(index=index, packet=packet, role_rows=role_rows)
        if row["packet_id"] in seen_packet_ids:
            raise RolePacketRegisterError(
                "packet_duplicate_id",
                {"index": index, "packet_id": row["packet_id"]},
            )
        seen_packet_ids.add(row["packet_id"])
        rows.append(row)

    rows = sorted(rows, key=lambda row: row["packet_id"])
    return {
        "schema_version": PACKET_REGISTER_SCHEMA_VERSION,
        "activation_posture": ROLE_PACKET_ACTIVATION_POSTURE,
        "register_id": _require_nonempty(register_id, "register_id"),
        "role_assignment_register_id": _require_nonempty(
            role_assignment_register.get("register_id"),
            "role_assignment_register.register_id",
        ),
        "source_occurrence_register_id": _require_nonempty(
            role_assignment_register.get("source_occurrence_register_id"),
            "role_assignment_register.source_occurrence_register_id",
        ),
        "tenant_id": _require_nonempty(role_assignment_register.get("tenant_id"), "tenant_id"),
        "domain_id": _require_nonempty(role_assignment_register.get("domain_id"), "domain_id"),
        "project_id": _require_nonempty(role_assignment_register.get("project_id"), "project_id"),
        "created_at": _require_nonempty(created_at, "created_at"),
        "reviewed_by_actor": {
            "id": _require_nonempty(reviewed_by_actor_id, "reviewed_by_actor_id"),
            "type": _require_nonempty(reviewed_by_actor_type, "reviewed_by_actor_type"),
        },
        "packet_count": len(rows),
        "rows": rows,
        "snapshot_digest": _digest(rows),
        "truth_effects": {
            "creates_packet_register": True,
            "creates_reviewed_baseline": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def canonical_role_packet_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def role_packet_digest(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_role_packet_bytes(value)).hexdigest()


def _role_row(
    *,
    index: int,
    assignment: Mapping[str, Any],
    rows_by_ref: Mapping[str, Mapping[str, Any]],
    register_id: str,
) -> dict[str, Any]:
    _reject_raw_material(assignment, path=f"role_assignments[{index}]")
    source_ref = _require_nonempty(assignment.get("source_ref"), f"role_assignments[{index}].source_ref")
    occurrence = rows_by_ref.get(source_ref)
    if occurrence is None:
        raise RolePacketRegisterError(
            "role_assignment_unknown_source_ref",
            {"index": index, "source_ref": source_ref},
        )
    source_role = _require_nonempty(assignment.get("source_role"), f"role_assignments[{index}].source_role")
    if source_role not in SOURCE_ROLES:
        raise RolePacketRegisterError(
            "role_assignment_source_role_invalid",
            {"index": index, "source_role": source_role, "allowed_roles": sorted(SOURCE_ROLES)},
        )
    review_state = _require_nonempty(
        assignment.get("review_state"),
        f"role_assignments[{index}].review_state",
    )
    if review_state not in ROLE_REVIEW_STATES:
        raise RolePacketRegisterError(
            "role_assignment_review_state_invalid",
            {
                "index": index,
                "review_state": review_state,
                "allowed_review_states": sorted(ROLE_REVIEW_STATES),
            },
        )
    rationale = _require_nonempty(
        assignment.get("review_rationale"),
        f"role_assignments[{index}].review_rationale",
    )
    return {
        "role_assignment_id": str(
            assignment.get("role_assignment_id")
            or f"{register_id}:role:{index + 1:04d}"
        ),
        "source_ref": source_ref,
        "source_occurrence_id": _require_nonempty(
            occurrence.get("source_occurrence_id"),
            f"source_occurrence_register.rows[{source_ref}].source_occurrence_id",
        ),
        "content_identity_id": _require_nonempty(
            occurrence.get("content_identity_id"),
            f"source_occurrence_register.rows[{source_ref}].content_identity_id",
        ),
        "source_role": source_role,
        "review_state": review_state,
        "review_rationale": rationale,
        "ai_suggested": bool(assignment.get("ai_suggested", False)),
        "official_truth": False,
    }


def _packet_row(
    *,
    index: int,
    packet: Mapping[str, Any],
    role_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _reject_raw_material(packet, path=f"packets[{index}]")
    packet_id = _require_nonempty(packet.get("packet_id"), f"packets[{index}].packet_id")
    packet_kind = _require_nonempty(packet.get("packet_kind"), f"packets[{index}].packet_kind")
    review_state = _require_nonempty(packet.get("review_state"), f"packets[{index}].review_state")
    if review_state not in PACKET_REVIEW_STATES:
        raise RolePacketRegisterError(
            "packet_review_state_invalid",
            {
                "index": index,
                "review_state": review_state,
                "allowed_review_states": sorted(PACKET_REVIEW_STATES),
            },
        )
    source_refs = packet.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        raise RolePacketRegisterError(
            "packet_source_refs_required",
            {"index": index},
        )
    normalized_refs: list[str] = []
    for ref_index, raw_ref in enumerate(source_refs):
        source_ref = _require_nonempty(raw_ref, f"packets[{index}].source_refs[{ref_index}]")
        if source_ref not in role_rows:
            raise RolePacketRegisterError(
                "packet_source_ref_not_role_assigned",
                {"index": index, "source_ref": source_ref},
            )
        if source_ref in normalized_refs:
            raise RolePacketRegisterError(
                "packet_duplicate_source_ref",
                {"index": index, "source_ref": source_ref},
            )
        normalized_refs.append(source_ref)
    rationale = _require_nonempty(packet.get("review_rationale"), f"packets[{index}].review_rationale")
    return {
        "packet_id": packet_id,
        "packet_kind": packet_kind,
        "review_state": review_state,
        "source_refs": sorted(normalized_refs),
        "source_roles": sorted({str(role_rows[source_ref]["source_role"]) for source_ref in normalized_refs}),
        "review_rationale": rationale,
        "official_truth": False,
    }


def _require_occurrence_register(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION:
        raise RolePacketRegisterError(
            "role_packet_requires_source_occurrence_register",
            {
                "expected_schema_version": SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _require_role_register(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != ROLE_ASSIGNMENT_REGISTER_SCHEMA_VERSION:
        raise RolePacketRegisterError(
            "packet_requires_role_assignment_register",
            {
                "expected_schema_version": ROLE_ASSIGNMENT_REGISTER_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _require_rows(value: Any, field_name: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise RolePacketRegisterError(
            "role_packet_rows_required",
            {"field": field_name},
        )
    rows: list[Mapping[str, Any]] = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise RolePacketRegisterError(
                "role_packet_row_must_be_object",
                {"field": field_name, "index": index},
            )
        rows.append(row)
    return rows


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_RAW_KEYS or key_text.startswith("raw_"):
                raise RolePacketRegisterError(
                    "role_packet_raw_field_forbidden",
                    {"path": path, "field": key_text},
                )
            _reject_raw_material(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, list | tuple):
        for index, nested in enumerate(value):
            _reject_raw_material(nested, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        if value.lower().startswith("data:") or "base64," in value.lower():
            raise RolePacketRegisterError(
                "role_packet_inline_content_forbidden",
                {"path": path},
            )
        if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
            raise RolePacketRegisterError(
                "role_packet_raw_value_forbidden",
                {"path": path},
            )
        if _RAW_FILENAME_RE.match(value):
            raise RolePacketRegisterError(
                "role_packet_raw_value_forbidden",
                {"path": path},
            )


def _require_nonempty(value: Any, field_name: str) -> str:
    if value is None:
        raise RolePacketRegisterError(
            "role_packet_required_field_missing",
            {"field": field_name},
        )
    normalized = str(value).strip()
    if not normalized:
        raise RolePacketRegisterError(
            "role_packet_required_field_missing",
            {"field": field_name},
        )
    return normalized


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
    "PACKET_REGISTER_ARTIFACT_KIND",
    "PACKET_REGISTER_SCHEMA_VERSION",
    "PACKET_REVIEW_STATES",
    "ROLE_ASSIGNMENT_REGISTER_ARTIFACT_KIND",
    "ROLE_ASSIGNMENT_REGISTER_SCHEMA_VERSION",
    "ROLE_PACKET_ACTIVATION_POSTURE",
    "ROLE_PACKET_ARTIFACT_ROLE",
    "ROLE_REVIEW_STATES",
    "SOURCE_ROLES",
    "RolePacketRegisterError",
    "build_packet_register",
    "build_role_assignment_register",
    "canonical_role_packet_bytes",
    "role_packet_digest",
]
