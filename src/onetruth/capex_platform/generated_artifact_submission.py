from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Any

from onetruth.application.handlers._shared.artifact_effects import (
    build_capex_generated_artifact_envelope,
    canonical_json_bytes,
)
from onetruth.application.handlers._shared.command_boundary import CommandError


SUBMITTED_GENERATED_ARTIFACT_SCHEMA_VERSION = "capex.submitted_generated_artifact.v1"
RUNTIME_GENERATED_ARTIFACT_VIEW_SCHEMA_VERSION = (
    "capex.runtime_generated_artifact_view.v1"
)
SHA256_DIGEST_RE = re.compile(r"\Asha256:[0-9a-f]{64}\Z")
CAPEX_ARTIFACT_KIND_RE = re.compile(r"\Acapex(\.[a-z0-9_]+)+\Z")

RUNTIME_OWNED_FIELD_MARKERS = {
    "artifact_identity_digest",
    "artifact_identity_profile",
    "artifact_version_id",
    "byte_size",
    "content_digest",
    "created_at",
    "event_id",
    "is_official",
    "official_status",
    "officialness",
    "pointer_family",
    "pointer_id",
    "pointer_key",
    "storage_uri",
    "updated_at",
}

RAW_MATERIAL_KEY_MARKERS = {
    "absolute_path",
    "base64",
    "blob",
    "blob_bytes",
    "bytes",
    "content_base64",
    "excerpt",
    "file_name",
    "filename",
    "local_path",
    "log",
    "ocr_text",
    "raw_content",
    "raw_filename",
    "raw_log",
    "raw_material",
    "raw_text",
    "source_path",
}


@dataclass(frozen=True)
class CapexGeneratedArtifactSubmissionError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def validate_submitted_generated_artifact(
    submission: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(submission, Mapping):
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"reason": "submission_must_be_object"},
        )
    normalized = dict(submission)
    _reject_runtime_owned_fields(normalized, path="$")
    _reject_raw_material(normalized, path="$")
    _validate_required_shape(normalized)
    canonical_json_bytes(normalized)
    return normalized


def build_submitted_generated_artifact_envelope(
    submission: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = validate_submitted_generated_artifact(submission)
    try:
        return build_capex_generated_artifact_envelope(
            artifact_kind=str(normalized["artifact_kind"]),
            artifact_role=str(normalized["artifact_role"]),
            source_refs=list(normalized["source_refs"]),
            input_digests=list(normalized["input_digests"]),
            validation_summary=dict(normalized["validation_summary"]),
            payload=normalized["payload"],
        )
    except CommandError as exc:
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"reason": exc.code, **exc.details},
        ) from exc


def build_runtime_generated_artifact_view(
    artifact_version: Mapping[str, Any],
) -> dict[str, Any]:
    artifact_kind = str(artifact_version.get("artifact_kind") or "")
    if not CAPEX_ARTIFACT_KIND_RE.match(artifact_kind):
        raise CapexGeneratedArtifactSubmissionError(
            code="runtime_generated_artifact_view_invalid",
            details={"reason": "artifact_kind_not_capex", "artifact_kind": artifact_kind},
        )
    content_digest = str(artifact_version.get("content_digest") or "")
    if not SHA256_DIGEST_RE.match(content_digest):
        raise CapexGeneratedArtifactSubmissionError(
            code="runtime_generated_artifact_view_invalid",
            details={"reason": "content_digest_invalid"},
        )
    metadata_json = artifact_version.get("metadata_json") or {}
    if not isinstance(metadata_json, dict):
        raise CapexGeneratedArtifactSubmissionError(
            code="runtime_generated_artifact_view_invalid",
            details={"reason": "metadata_json_invalid"},
        )
    view = {
        "schema_version": RUNTIME_GENERATED_ARTIFACT_VIEW_SCHEMA_VERSION,
        "artifact_version_id": str(artifact_version["artifact_version_id"]),
        "workflow_run_id": str(artifact_version["workflow_run_id"]),
        "tenant_id": artifact_version.get("tenant_id"),
        "domain_id": artifact_version.get("domain_id"),
        "project_id": artifact_version.get("project_id"),
        "artifact_kind": artifact_kind,
        "artifact_role": artifact_version.get("artifact_role"),
        "media_type": str(artifact_version["media_type"]),
        "storage_uri": str(artifact_version["storage_uri"]),
        "content_digest": content_digest,
        "byte_size": artifact_version.get("byte_size"),
        "artifact_identity_profile": artifact_version.get("artifact_identity_profile"),
        "artifact_identity_digest": artifact_version.get("artifact_identity_digest"),
        "metadata_json": dict(metadata_json),
        "runtime_state": {
            "promotable": False,
            "evidence_sufficient": False,
            "reviewed_baseline": False,
            "pointer_bound": False,
        },
        "created_at": str(artifact_version["created_at"]),
    }
    canonical_json_bytes(view)
    return view


def _validate_required_shape(submission: dict[str, Any]) -> None:
    expected_keys = {
        "schema_version",
        "artifact_kind",
        "artifact_role",
        "source_refs",
        "input_digests",
        "validation_summary",
        "payload",
    }
    missing = sorted(expected_keys - set(submission))
    extra = sorted(set(submission) - expected_keys)
    if missing or extra:
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"missing": missing, "extra": extra},
        )
    if submission["schema_version"] != SUBMITTED_GENERATED_ARTIFACT_SCHEMA_VERSION:
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"field": "schema_version"},
        )
    artifact_kind = str(submission["artifact_kind"])
    if not CAPEX_ARTIFACT_KIND_RE.match(artifact_kind):
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"field": "artifact_kind"},
        )
    if not str(submission["artifact_role"]).strip():
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"field": "artifact_role"},
        )
    _validate_source_refs(submission["source_refs"])
    _validate_input_digests(submission["input_digests"])
    if not isinstance(submission["validation_summary"], dict):
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"field": "validation_summary"},
        )


def _validate_source_refs(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"field": "source_refs"},
        )
    invalid = [
        source_ref
        for source_ref in value
        if not isinstance(source_ref, str)
        or not source_ref.startswith("source_occurrence:")
        or any(character.isspace() for character in source_ref)
    ]
    if invalid:
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"field": "source_refs", "invalid": invalid},
        )


def _validate_input_digests(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"field": "input_digests"},
        )
    invalid = [
        digest
        for digest in value
        if not isinstance(digest, str) or not SHA256_DIGEST_RE.match(digest)
    ]
    if invalid:
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_invalid",
            details={"field": "input_digests", "invalid": invalid},
        )


def _reject_runtime_owned_fields(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if normalized_key in RUNTIME_OWNED_FIELD_MARKERS:
                raise CapexGeneratedArtifactSubmissionError(
                    code="submitted_generated_artifact_runtime_field",
                    details={"path": f"{path}.{key}", "field": str(key)},
                )
            _reject_runtime_owned_fields(child, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_runtime_owned_fields(child, path=f"{path}[{index}]")


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if normalized_key in RAW_MATERIAL_KEY_MARKERS:
                raise CapexGeneratedArtifactSubmissionError(
                    code="submitted_generated_artifact_raw_material",
                    details={"path": f"{path}.{key}", "field": str(key)},
                )
            _reject_raw_material(child, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_raw_material(child, path=f"{path}[{index}]")
        return
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise CapexGeneratedArtifactSubmissionError(
            code="submitted_generated_artifact_raw_material",
            details={"path": path},
        )
    if isinstance(value, str):
        if value.startswith(("/", "file://")) or "\\Users\\" in value or ":\\Users\\" in value:
            raise CapexGeneratedArtifactSubmissionError(
                code="submitted_generated_artifact_raw_material",
                details={"path": path},
            )
