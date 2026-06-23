from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


STAGED_CORPUS_INGEST_SCHEMA_VERSION = "capex.staged_corpus_ingest_plan.v1"
STAGED_CORPUS_INGEST_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
MAX_STAGED_DESCRIPTOR_COUNT = 5_000
MAX_STAGED_DESCRIPTOR_BATCH_BYTES = 2_000_000
MAX_STAGED_DESCRIPTOR_TEXT_BYTES = 4_096

STAGED_INGEST_MODES = (
    "object_store_manifest",
    "folder_manifest",
    "source_root_snapshot",
)

_DESCRIPTOR_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "document_text",
    "file_name",
    "filename",
    "ocr_text",
    "raw_bytes",
    "raw_content",
    "raw_file",
    "raw_filename",
    "screenshot",
    "source_filename",
}
_ALLOWED_DESCRIPTOR_KEYS = {
    "descriptor_id",
    "mode",
    "manifest_ref",
    "manifest_digest",
    "content_digest",
    "content_byte_size",
    "content_media_type",
    "canonicalization_profile",
    "byte_size",
    "media_type",
    "redacted_path_hint",
    "object_ref",
    "source_root_id",
    "folder_tree_snapshot_id",
    "metadata_json",
}


@dataclass(frozen=True)
class StagedCorpusIngestError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def plan_staged_corpus_ingest(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    ingest_batch_id: str,
    idempotency_key: str,
    requested_by_actor_id: str,
    requested_by_actor_type: str,
    created_at: str,
    descriptors: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate sanitized staged-ingest descriptors and return a manifest-only plan.

    This planner is intentionally side-effect free. It does not read corpus bytes,
    create source occurrences, write artifacts, or grant activation.
    """

    if not descriptors:
        raise StagedCorpusIngestError(
            "staged_ingest_descriptors_required",
            {"minimum": 1},
        )
    if len(descriptors) > MAX_STAGED_DESCRIPTOR_COUNT:
        raise StagedCorpusIngestError(
            "staged_ingest_descriptor_count_exceeded",
            {
                "maximum": MAX_STAGED_DESCRIPTOR_COUNT,
                "actual": len(descriptors),
            },
        )

    normalized_descriptors = [
        _normalize_descriptor(index=index, descriptor=descriptor)
        for index, descriptor in enumerate(descriptors)
    ]
    descriptor_bytes = _canonical_json_bytes(normalized_descriptors)
    if len(descriptor_bytes) > MAX_STAGED_DESCRIPTOR_BATCH_BYTES:
        raise StagedCorpusIngestError(
            "staged_ingest_descriptor_body_limit_exceeded",
            {
                "maximum_bytes": MAX_STAGED_DESCRIPTOR_BATCH_BYTES,
                "actual_bytes": len(descriptor_bytes),
            },
        )

    return {
        "schema_version": STAGED_CORPUS_INGEST_SCHEMA_VERSION,
        "activation_posture": STAGED_CORPUS_INGEST_ACTIVATION_POSTURE,
        "ingest_batch_id": _require_nonempty(ingest_batch_id, "ingest_batch_id"),
        "tenant_id": _require_nonempty(tenant_id, "tenant_id"),
        "domain_id": _require_nonempty(domain_id, "domain_id"),
        "project_id": _require_nonempty(project_id, "project_id"),
        "idempotency_key": _require_nonempty(idempotency_key, "idempotency_key"),
        "requested_by_actor_id": _require_nonempty(
            requested_by_actor_id, "requested_by_actor_id"
        ),
        "requested_by_actor_type": _require_nonempty(
            requested_by_actor_type, "requested_by_actor_type"
        ),
        "created_at": _require_nonempty(created_at, "created_at"),
        "descriptor_count": len(normalized_descriptors),
        "descriptor_fingerprint": _sha256_digest(descriptor_bytes),
        "accepted_modes": list(STAGED_INGEST_MODES),
        "body_limit_policy": {
            "max_descriptor_count": MAX_STAGED_DESCRIPTOR_COUNT,
            "max_descriptor_batch_bytes": MAX_STAGED_DESCRIPTOR_BATCH_BYTES,
            "inline_raw_content_allowed": False,
            "json_base64_command_route_allowed": False,
        },
        "truth_effects": {
            "creates_source_occurrences": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "descriptors": normalized_descriptors,
    }


def _normalize_descriptor(
    *, index: int, descriptor: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(descriptor, Mapping):
        raise StagedCorpusIngestError(
            "staged_ingest_descriptor_must_be_object",
            {"index": index},
        )
    _reject_forbidden_raw_material(descriptor, path=f"descriptors[{index}]")

    unknown_keys = sorted(set(descriptor) - _ALLOWED_DESCRIPTOR_KEYS)
    if unknown_keys:
        raise StagedCorpusIngestError(
            "staged_ingest_descriptor_unknown_fields",
            {"index": index, "fields": unknown_keys},
        )

    descriptor_id = _require_nonempty(
        descriptor.get("descriptor_id"), f"descriptors[{index}].descriptor_id"
    )
    if not _DESCRIPTOR_ID_RE.match(descriptor_id):
        raise StagedCorpusIngestError(
            "staged_ingest_descriptor_id_invalid",
            {"index": index, "descriptor_id": descriptor_id},
        )

    mode = _require_nonempty(descriptor.get("mode"), f"descriptors[{index}].mode")
    if mode not in STAGED_INGEST_MODES:
        raise StagedCorpusIngestError(
            "staged_ingest_mode_invalid",
            {
                "index": index,
                "mode": mode,
                "allowed_modes": list(STAGED_INGEST_MODES),
            },
        )

    manifest_ref = _require_nonempty(
        descriptor.get("manifest_ref"), f"descriptors[{index}].manifest_ref"
    )
    _validate_safe_string(manifest_ref, path=f"descriptors[{index}].manifest_ref")
    manifest_digest = _require_nonempty(
        descriptor.get("manifest_digest"),
        f"descriptors[{index}].manifest_digest",
    ).lower()
    if not _SHA256_RE.match(manifest_digest):
        raise StagedCorpusIngestError(
            "staged_ingest_manifest_digest_invalid",
            {"index": index, "manifest_digest": manifest_digest},
        )

    normalized: dict[str, Any] = {
        "descriptor_id": descriptor_id,
        "mode": mode,
        "manifest_ref": manifest_ref,
        "manifest_digest": manifest_digest,
    }
    content_digest = descriptor.get("content_digest")
    if content_digest is not None:
        normalized_content_digest = _require_nonempty(
            content_digest,
            f"descriptors[{index}].content_digest",
        ).lower()
        if not _SHA256_RE.match(normalized_content_digest):
            raise StagedCorpusIngestError(
                "staged_ingest_content_digest_invalid",
                {"index": index, "content_digest": normalized_content_digest},
            )
        normalized["content_digest"] = normalized_content_digest

    content_byte_size = descriptor.get("content_byte_size")
    if content_byte_size is not None:
        if not isinstance(content_byte_size, int) or content_byte_size < 0:
            raise StagedCorpusIngestError(
                "staged_ingest_content_byte_size_invalid",
                {"index": index, "content_byte_size": content_byte_size},
            )
        normalized["content_byte_size"] = content_byte_size

    for content_optional_key in ("content_media_type", "canonicalization_profile"):
        if descriptor.get(content_optional_key) is not None:
            value = _require_nonempty(
                descriptor[content_optional_key],
                f"descriptors[{index}].{content_optional_key}",
            )
            _validate_safe_string(
                value,
                path=f"descriptors[{index}].{content_optional_key}",
            )
            normalized[content_optional_key] = value

    for optional_key in (
        "byte_size",
        "media_type",
        "redacted_path_hint",
        "object_ref",
        "source_root_id",
        "folder_tree_snapshot_id",
    ):
        if descriptor.get(optional_key) is not None:
            value = descriptor[optional_key]
            if isinstance(value, str):
                _validate_safe_string(
                    value,
                    path=f"descriptors[{index}].{optional_key}",
                )
            normalized[optional_key] = value
    metadata_json = descriptor.get("metadata_json")
    if metadata_json is not None:
        if not isinstance(metadata_json, Mapping):
            raise StagedCorpusIngestError(
                "staged_ingest_metadata_must_be_object",
                {"index": index},
            )
        _reject_forbidden_raw_material(
            metadata_json,
            path=f"descriptors[{index}].metadata_json",
        )
        normalized["metadata_json"] = dict(metadata_json)
    else:
        normalized["metadata_json"] = {}

    _validate_mode_requirements(index=index, mode=mode, descriptor=normalized)
    return normalized


def _validate_mode_requirements(
    *, index: int, mode: str, descriptor: Mapping[str, Any]
) -> None:
    required_by_mode = {
        "object_store_manifest": ("object_ref",),
        "folder_manifest": ("redacted_path_hint",),
        "source_root_snapshot": ("source_root_id", "folder_tree_snapshot_id"),
    }
    missing = [
        field
        for field in required_by_mode[mode]
        if descriptor.get(field) in {None, ""}
    ]
    if missing:
        raise StagedCorpusIngestError(
            "staged_ingest_mode_required_fields_missing",
            {"index": index, "mode": mode, "missing": missing},
        )


def _reject_forbidden_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized_key = key.lower().replace("-", "_")
            if normalized_key in _FORBIDDEN_RAW_KEYS:
                raise StagedCorpusIngestError(
                    "staged_ingest_raw_material_field_forbidden",
                    {"path": f"{path}.{key}", "field": key},
                )
            _reject_forbidden_raw_material(raw_value, path=f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _reject_forbidden_raw_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        _validate_safe_string(value, path=path)


def _validate_safe_string(value: str, *, path: str) -> None:
    encoded_length = len(value.encode("utf-8"))
    if encoded_length > MAX_STAGED_DESCRIPTOR_TEXT_BYTES:
        raise StagedCorpusIngestError(
            "staged_ingest_descriptor_text_field_too_large",
            {
                "path": path,
                "maximum_bytes": MAX_STAGED_DESCRIPTOR_TEXT_BYTES,
                "actual_bytes": encoded_length,
            },
        )
    lowered = value.lower()
    if "base64," in lowered or lowered.startswith("data:"):
        raise StagedCorpusIngestError(
            "staged_ingest_inline_base64_forbidden",
            {"path": path},
        )
    if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
        raise StagedCorpusIngestError(
            "staged_ingest_raw_absolute_path_forbidden",
            {"path": path},
        )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StagedCorpusIngestError(
            "staged_ingest_required_field_missing",
            {"field": field_name},
        )
    return value.strip()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


__all__ = [
    "MAX_STAGED_DESCRIPTOR_BATCH_BYTES",
    "MAX_STAGED_DESCRIPTOR_COUNT",
    "STAGED_CORPUS_INGEST_ACTIVATION_POSTURE",
    "STAGED_CORPUS_INGEST_SCHEMA_VERSION",
    "STAGED_INGEST_MODES",
    "StagedCorpusIngestError",
    "plan_staged_corpus_ingest",
]
