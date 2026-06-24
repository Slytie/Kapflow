from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


MANIFEST_GENERATION_ATTESTATION_OUTPUTS_SCHEMA_VERSION = (
    "capex.manifest_generation_attestation.outputs.v1"
)
MANIFEST_GENERATION_ATTESTATION_SCHEMA_VERSION = (
    "capex.manifest_generation_attestation.v1"
)
GENERATED_CORPUS_REGISTER_MANIFEST_SCHEMA_VERSION = (
    "capex.generated_corpus_register_manifest.v1"
)
MANIFEST_GENERATION_ATTESTATION_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(?:7z|csv|doc|docx|eml|jpeg|jpg|msg|pdf|png|rar|txt|xls|xlsx|zip)$"
)
_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_BARE_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_ALLOWED_RELATION_TYPES = frozenset(
    {
        "duplicate_of",
        "archive_contains",
        "archive_member_of",
        "derivative_of",
        "redaction_of",
    }
)
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
class ManifestGenerationAttestationError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_manifest_generation_attestation_outputs(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    attestation_id: str,
    generated_register_id: str,
    generator_id: str,
    generator_version: str,
    generator_config_digest: str,
    policy_version: str,
    input_digests: Mapping[str, Any],
    content_identity_rows: Sequence[Mapping[str, Any]],
    source_occurrence_rows: Sequence[Mapping[str, Any]],
    relation_rows: Sequence[Mapping[str, Any]] = (),
    generated_at: str,
    generated_by_actor_id: str,
    generated_by_actor_type: str,
) -> dict[str, Any]:
    """Build a deterministic attestation for a generated corpus register."""

    scope = {
        "tenant_id": _require_nonempty(tenant_id, "tenant_id"),
        "domain_id": _require_nonempty(domain_id, "domain_id"),
        "project_id": _require_nonempty(project_id, "project_id"),
    }
    content_identities = _content_identity_index(content_identity_rows, scope)
    source_occurrences = _source_occurrence_rows(
        source_occurrence_rows,
        scope,
        content_identities,
    )
    relations = _relation_rows(relation_rows, scope, source_occurrences)
    normalized_input_digests = _input_digests(input_digests)
    generator_config_digest = _require_sha256(
        generator_config_digest,
        "generator_config_digest",
    )

    source_relation_refs: dict[str, list[str]] = {
        row["source_occurrence_id"]: [] for row in source_occurrences
    }
    for relation in relations:
        relation_ref = f"source_occurrence_relation:{relation['source_occurrence_relation_id']}"
        source_relation_refs[relation["source_occurrence_id"]].append(relation_ref)
        source_relation_refs[relation["target_source_occurrence_id"]].append(
            relation_ref
        )

    register_rows = [
        _register_manifest_row(row, content_identities, source_relation_refs)
        for row in source_occurrences
    ]
    register_rows = sorted(
        register_rows,
        key=lambda row: (
            row["source_occurrence_id"],
            row["content_identity_id"],
        ),
    )
    for row in register_rows:
        row["row_digest"] = _digest(
            {key: value for key, value in row.items() if key != "row_digest"}
        )

    relation_digest = _digest(relations)
    register_digest = _digest(register_rows)
    physical_basis_digest = _digest(
        {
            "content_identity_rows": sorted(
                content_identities.values(),
                key=lambda row: row["content_identity_id"],
            ),
            "source_occurrence_rows": source_occurrences,
            "relation_rows": relations,
        }
    )

    return {
        "schema_version": MANIFEST_GENERATION_ATTESTATION_OUTPUTS_SCHEMA_VERSION,
        "activation_posture": MANIFEST_GENERATION_ATTESTATION_ACTIVATION_POSTURE,
        "attestation_id": _require_nonempty(attestation_id, "attestation_id"),
        "generated_register_id": _require_nonempty(
            generated_register_id,
            "generated_register_id",
        ),
        **scope,
        "generated_at": _require_nonempty(generated_at, "generated_at"),
        "generated_by_actor": {
            "id": _require_nonempty(generated_by_actor_id, "generated_by_actor_id"),
            "type": _require_nonempty(
                generated_by_actor_type,
                "generated_by_actor_type",
            ),
        },
        "generator": {
            "id": _require_nonempty(generator_id, "generator_id"),
            "version": _require_nonempty(generator_version, "generator_version"),
            "config_digest": generator_config_digest,
            "policy_version": _require_nonempty(policy_version, "policy_version"),
        },
        "basis": {
            "source_tables": [
                "capex_content_identities",
                "capex_source_occurrences",
                "capex_source_occurrence_relations",
            ],
            "generated_from_physical_rows_only": True,
            "input_digests": normalized_input_digests,
            "content_identity_count": len(content_identities),
            "source_occurrence_count": len(source_occurrences),
            "relation_count": len(relations),
            "physical_basis_digest": physical_basis_digest,
            "relation_rows_digest": relation_digest,
        },
        "generated_corpus_register_manifest": {
            "schema_version": GENERATED_CORPUS_REGISTER_MANIFEST_SCHEMA_VERSION,
            "artifact_kind": "capex.generated_corpus_register_manifest",
            "artifact_role": "evidence",
            "rows": register_rows,
            "row_count": len(register_rows),
            "snapshot_digest": register_digest,
        },
        "manifest_generation_attestation": {
            "schema_version": MANIFEST_GENERATION_ATTESTATION_SCHEMA_VERSION,
            "attestation_ref": f"generated_row:capex.manifest_generation_attestation:{attestation_id}",
            "generated_register_ref": (
                "generated_row:capex.generated_corpus_register_manifest:"
                + generated_register_id
            ),
            "generated_register_digest": register_digest,
            "physical_basis_digest": physical_basis_digest,
            "content_identity_count": len(content_identities),
            "source_occurrence_count": len(source_occurrences),
            "relation_count": len(relations),
            "source_occurrence_ids": [
                row["source_occurrence_id"] for row in register_rows
            ],
            "relation_ids": [
                row["source_occurrence_relation_id"] for row in relations
            ],
            "generated_register_is_source_authority": False,
            "generated_register_can_promote_official_pointer": False,
        },
        "truth_effects": {
            "creates_content_identities": False,
            "creates_source_occurrences": False,
            "creates_relation_rows": False,
            "creates_ingest_jobs": False,
            "writes_artifacts": False,
            "emits_timeline_events": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "raw_corpus_import",
            "source_occurrence_creation",
            "relation_creation",
            "generated_register_as_source_authority",
            "evidence_sufficiency_claim",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_manifest_generation_attestation_bytes(
    outputs: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def manifest_generation_attestation_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_manifest_generation_attestation_bytes(outputs)
    ).hexdigest()


def _content_identity_index(
    rows: Sequence[Mapping[str, Any]],
    scope: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    if not rows:
        raise ManifestGenerationAttestationError(
            "manifest_attestation_content_identity_rows_required",
            {"field": "content_identity_rows"},
        )
    result: dict[str, dict[str, Any]] = {}
    for index, raw_row in enumerate(rows):
        if not isinstance(raw_row, Mapping):
            raise ManifestGenerationAttestationError(
                "manifest_attestation_content_identity_row_must_be_object",
                {"index": index},
            )
        _reject_raw_material(raw_row, path=f"content_identity_rows[{index}]")
        _require_scope(raw_row, scope, f"content_identity_rows[{index}]", project_required=False)
        content_identity_id = _require_nonempty(
            raw_row.get("content_identity_id"),
            f"content_identity_rows[{index}].content_identity_id",
        )
        if content_identity_id in result:
            raise ManifestGenerationAttestationError(
                "manifest_attestation_duplicate_content_identity_id",
                {"index": index, "content_identity_id": content_identity_id},
            )
        digest_algorithm = _require_nonempty(
            raw_row.get("digest_algorithm"),
            f"content_identity_rows[{index}].digest_algorithm",
        ).lower()
        if digest_algorithm != "sha256":
            raise ManifestGenerationAttestationError(
                "manifest_attestation_digest_algorithm_invalid",
                {"index": index, "digest_algorithm": digest_algorithm},
            )
        result[content_identity_id] = {
            "content_identity_id": content_identity_id,
            "tenant_id": scope["tenant_id"],
            "domain_id": scope["domain_id"],
            "digest_algorithm": digest_algorithm,
            "content_digest": _normalize_sha256(
                raw_row.get("content_digest"),
                f"content_identity_rows[{index}].content_digest",
            ),
            "byte_size": _optional_nonnegative_int(
                raw_row.get("byte_size"),
                f"content_identity_rows[{index}].byte_size",
            ),
            "media_type": raw_row.get("media_type"),
            "canonicalization_profile": raw_row.get("canonicalization_profile"),
        }
    return result


def _source_occurrence_rows(
    rows: Sequence[Mapping[str, Any]],
    scope: Mapping[str, str],
    content_identities: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not rows:
        raise ManifestGenerationAttestationError(
            "manifest_attestation_source_occurrence_rows_required",
            {"field": "source_occurrence_rows"},
        )
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_row in enumerate(rows):
        if not isinstance(raw_row, Mapping):
            raise ManifestGenerationAttestationError(
                "manifest_attestation_source_occurrence_row_must_be_object",
                {"index": index},
            )
        _reject_raw_material(raw_row, path=f"source_occurrence_rows[{index}]")
        _require_scope(raw_row, scope, f"source_occurrence_rows[{index}]")
        source_occurrence_id = _require_nonempty(
            raw_row.get("source_occurrence_id"),
            f"source_occurrence_rows[{index}].source_occurrence_id",
        )
        if source_occurrence_id in seen_ids:
            raise ManifestGenerationAttestationError(
                "manifest_attestation_duplicate_source_occurrence_id",
                {"index": index, "source_occurrence_id": source_occurrence_id},
            )
        content_identity_id = _require_nonempty(
            raw_row.get("content_identity_id"),
            f"source_occurrence_rows[{index}].content_identity_id",
        )
        if content_identity_id not in content_identities:
            raise ManifestGenerationAttestationError(
                "manifest_attestation_content_identity_not_found",
                {"index": index, "content_identity_id": content_identity_id},
            )
        source_ref = _require_source_ref(
            raw_row.get("source_ref") or f"source_occurrence:{source_occurrence_id}",
            f"source_occurrence_rows[{index}].source_ref",
        )
        expected_ref = f"source_occurrence:{source_occurrence_id}"
        if source_ref != expected_ref:
            raise ManifestGenerationAttestationError(
                "manifest_attestation_source_ref_mismatch",
                {
                    "index": index,
                    "source_occurrence_id": source_occurrence_id,
                    "source_ref": source_ref,
                    "expected_source_ref": expected_ref,
                },
            )
        seen_ids.add(source_occurrence_id)
        result.append(
            {
                "source_occurrence_id": source_occurrence_id,
                "source_ref": source_ref,
                "content_identity_id": content_identity_id,
                "occurrence_kind": _require_nonempty(
                    raw_row.get("occurrence_kind"),
                    f"source_occurrence_rows[{index}].occurrence_kind",
                ),
                "status": _require_nonempty(
                    raw_row.get("status"),
                    f"source_occurrence_rows[{index}].status",
                ),
                "created_at": raw_row.get("created_at"),
            }
        )
    return sorted(result, key=lambda row: row["source_occurrence_id"])


def _relation_rows(
    rows: Sequence[Mapping[str, Any]],
    scope: Mapping[str, str],
    source_occurrences: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    known_occurrences = {row["source_occurrence_id"] for row in source_occurrences}
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_row in enumerate(rows):
        if not isinstance(raw_row, Mapping):
            raise ManifestGenerationAttestationError(
                "manifest_attestation_relation_row_must_be_object",
                {"index": index},
            )
        _reject_raw_material(raw_row, path=f"relation_rows[{index}]")
        _require_scope(raw_row, scope, f"relation_rows[{index}]")
        relation_id = _require_nonempty(
            raw_row.get("source_occurrence_relation_id"),
            f"relation_rows[{index}].source_occurrence_relation_id",
        )
        if relation_id in seen_ids:
            raise ManifestGenerationAttestationError(
                "manifest_attestation_duplicate_relation_id",
                {"index": index, "source_occurrence_relation_id": relation_id},
            )
        relation_type = _require_nonempty(
            raw_row.get("relation_type"),
            f"relation_rows[{index}].relation_type",
        )
        if relation_type not in _ALLOWED_RELATION_TYPES:
            raise ManifestGenerationAttestationError(
                "manifest_attestation_relation_type_invalid",
                {"index": index, "relation_type": relation_type},
            )
        source_occurrence_id = _require_nonempty(
            raw_row.get("source_occurrence_id"),
            f"relation_rows[{index}].source_occurrence_id",
        )
        target_source_occurrence_id = _require_nonempty(
            raw_row.get("target_source_occurrence_id"),
            f"relation_rows[{index}].target_source_occurrence_id",
        )
        missing = sorted(
            {
                source_occurrence_id,
                target_source_occurrence_id,
            }
            - known_occurrences
        )
        if missing:
            raise ManifestGenerationAttestationError(
                "manifest_attestation_relation_occurrence_not_found",
                {"index": index, "missing_source_occurrence_ids": missing},
            )
        seen_ids.add(relation_id)
        result.append(
            {
                "source_occurrence_relation_id": relation_id,
                "relation_type": relation_type,
                "source_occurrence_id": source_occurrence_id,
                "target_source_occurrence_id": target_source_occurrence_id,
                "status": str(raw_row.get("status") or "active"),
                "basis_ref": _require_source_ref(
                    raw_row.get("basis_ref"),
                    f"relation_rows[{index}].basis_ref",
                ),
                "policy_version": _require_nonempty(
                    raw_row.get("policy_version"),
                    f"relation_rows[{index}].policy_version",
                ),
            }
        )
    return sorted(
        result,
        key=lambda row: (
            row["relation_type"],
            row["source_occurrence_id"],
            row["target_source_occurrence_id"],
            row["source_occurrence_relation_id"],
        ),
    )


def _register_manifest_row(
    row: Mapping[str, Any],
    content_identities: Mapping[str, Mapping[str, Any]],
    source_relation_refs: Mapping[str, list[str]],
) -> dict[str, Any]:
    content = content_identities[row["content_identity_id"]]
    return {
        "source_occurrence_id": row["source_occurrence_id"],
        "source_ref": row["source_ref"],
        "content_identity_id": row["content_identity_id"],
        "content_identity_ref": f"content_identity:{row['content_identity_id']}",
        "content_digest": content["content_digest"],
        "content_byte_size": content["byte_size"],
        "content_media_type": content["media_type"],
        "canonicalization_profile": content["canonicalization_profile"],
        "occurrence_kind": row["occurrence_kind"],
        "status": row["status"],
        "relation_refs": sorted(source_relation_refs[row["source_occurrence_id"]]),
    }


def _input_digests(values: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(values, Mapping) or not values:
        raise ManifestGenerationAttestationError(
            "manifest_attestation_input_digests_required",
            {"field": "input_digests"},
        )
    result: dict[str, str] = {}
    for key, value in sorted(values.items()):
        digest_name = _require_nonempty(key, "input_digests.key")
        result[digest_name] = _require_sha256(value, f"input_digests.{digest_name}")
    return result


def _require_scope(
    row: Mapping[str, Any],
    scope: Mapping[str, str],
    path: str,
    *,
    project_required: bool = True,
) -> None:
    fields = ("tenant_id", "domain_id", "project_id") if project_required else ("tenant_id", "domain_id")
    for field in fields:
        if row.get(field) != scope[field]:
            raise ManifestGenerationAttestationError(
                "manifest_attestation_scope_mismatch",
                {
                    "path": path,
                    "field": field,
                    "expected": scope[field],
                    "actual": row.get(field),
                },
            )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestGenerationAttestationError(
            "manifest_attestation_required_field_missing",
            {"field": field_name},
        )
    return value.strip()


def _require_source_ref(value: Any, field_name: str) -> str:
    source_ref = _require_nonempty(value, field_name)
    if not _SOURCE_REF_RE.match(source_ref):
        raise ManifestGenerationAttestationError(
            "manifest_attestation_source_ref_invalid",
            {"field": field_name, "source_ref": source_ref},
        )
    return source_ref


def _require_sha256(value: Any, field_name: str) -> str:
    digest = _require_nonempty(value, field_name).lower()
    if not _SHA256_RE.match(digest):
        raise ManifestGenerationAttestationError(
            "manifest_attestation_digest_invalid",
            {"field": field_name, "value": value},
        )
    return digest


def _normalize_sha256(value: Any, field_name: str) -> str:
    digest = _require_nonempty(value, field_name).lower()
    if _BARE_SHA256_RE.match(digest):
        return f"sha256:{digest}"
    if _SHA256_RE.match(digest):
        return digest
    raise ManifestGenerationAttestationError(
        "manifest_attestation_digest_invalid",
        {"field": field_name, "value": value},
    )


def _optional_nonnegative_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or value < 0:
        raise ManifestGenerationAttestationError(
            "manifest_attestation_nonnegative_integer_required",
            {"field": field_name, "value": value},
        )
    return value


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized_key = key.lower().replace("-", "_")
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise ManifestGenerationAttestationError(
                    "manifest_attestation_raw_material_field_forbidden",
                    {"path": f"{path}.{key}", "field": key},
                )
            _reject_raw_material(raw_value, path=f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _reject_raw_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, bytes | bytearray):
        raise ManifestGenerationAttestationError(
            "manifest_attestation_blob_bytes_forbidden",
            {"path": path},
        )
    if isinstance(value, str):
        lowered = value.lower()
        if "base64," in lowered or lowered.startswith("data:"):
            raise ManifestGenerationAttestationError(
                "manifest_attestation_inline_base64_forbidden",
                {"path": path},
            )
        if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
            raise ManifestGenerationAttestationError(
                "manifest_attestation_raw_absolute_path_forbidden",
                {"path": path},
            )
        if _RAW_FILENAME_RE.match(value):
            raise ManifestGenerationAttestationError(
                "manifest_attestation_raw_filename_forbidden",
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
    "GENERATED_CORPUS_REGISTER_MANIFEST_SCHEMA_VERSION",
    "MANIFEST_GENERATION_ATTESTATION_ACTIVATION_POSTURE",
    "MANIFEST_GENERATION_ATTESTATION_OUTPUTS_SCHEMA_VERSION",
    "MANIFEST_GENERATION_ATTESTATION_SCHEMA_VERSION",
    "ManifestGenerationAttestationError",
    "build_manifest_generation_attestation_outputs",
    "canonical_manifest_generation_attestation_bytes",
    "manifest_generation_attestation_digest",
]
