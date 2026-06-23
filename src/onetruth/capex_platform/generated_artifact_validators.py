from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator

from onetruth.application.handlers._shared.artifact_effects import (
    CAPEX_SOURCE_INVENTORY_ARTIFACT_KIND,
    CAPEX_SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT,
    canonical_json_bytes,
    validate_capex_generated_artifact_file_name,
)
from onetruth.application.handlers._shared.command_boundary import CommandError


GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION = "capex.generated_artifact_bundle.v1"
VALIDATOR_POLICY_ID = "capex.generated_artifact_schema_bundle_validator.v1"
VALIDATOR_ACTIVATION_POSTURE = "planning_only_no_capex_activation"

_ROOT = Path(__file__).resolve().parents[3]
_ENVELOPE_SCHEMA_PATH = (
    _ROOT / "schemas/runtime/capex_generated_artifact_envelope.schema.json"
)
_VERSIONED_FILE_RE = re.compile(
    r"^(?P<artifact_kind>capex(?:\.[a-z0-9_]+)+)\.v[1-9][0-9]*\.json$"
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class CapexGeneratedArtifactValidationResult:
    valid: bool
    error_codes: tuple[str, ...]
    artifact_count: int
    promotable: bool = False
    evidence_sufficient: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "error_codes": list(self.error_codes),
            "artifact_count": self.artifact_count,
            "promotable": self.promotable,
            "evidence_sufficient": self.evidence_sufficient,
            "policy_id": VALIDATOR_POLICY_ID,
            "activation_posture": VALIDATOR_ACTIVATION_POSTURE,
        }


def validate_capex_generated_artifact_envelope(
    *,
    file_name: str,
    envelope: Mapping[str, Any],
    expected_content_digest: str | None = None,
) -> CapexGeneratedArtifactValidationResult:
    errors = _validate_single_artifact(
        file_name=file_name,
        envelope=envelope,
        expected_content_digest=expected_content_digest,
    )
    return _result(errors, artifact_count=1)


def validate_capex_generated_artifact_bundle(
    bundle: Mapping[str, Any],
) -> CapexGeneratedArtifactValidationResult:
    errors: list[str] = []
    if bundle.get("schema_version") != GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION:
        errors.append("bundle_schema_version_invalid")

    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("bundle_artifacts_required")
        return _result(errors, artifact_count=0)

    available_source_refs = _string_set(bundle.get("available_source_refs"))
    available_input_digests = {
        value.lower() for value in _string_set(bundle.get("available_input_digests"))
    }
    seen_names: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, Mapping):
            errors.append("bundle_artifact_must_be_object")
            continue
        file_name = str(artifact.get("file_name") or "")
        envelope = artifact.get("envelope")
        content_digest = artifact.get("content_digest")
        if file_name in seen_names:
            errors.append("duplicate_canonical_artifact_name")
        seen_names.add(file_name)
        if not isinstance(envelope, Mapping):
            errors.append("bundle_artifact_envelope_required")
            continue
        errors.extend(
            _validate_single_artifact(
                file_name=file_name,
                envelope=envelope,
                expected_content_digest=(
                    str(content_digest) if content_digest is not None else None
                ),
            )
        )
        errors.extend(
            _validate_bundle_refs(
                envelope=envelope,
                available_source_refs=available_source_refs,
                available_input_digests=available_input_digests,
                index=index,
            )
        )

    return _result(errors, artifact_count=len(artifacts))


def capex_generated_artifact_digest(envelope: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(envelope)).hexdigest()


def _validate_single_artifact(
    *,
    file_name: str,
    envelope: Mapping[str, Any],
    expected_content_digest: str | None,
) -> list[str]:
    errors: list[str] = []
    schema_errors = sorted(
        _schema_validator().iter_errors(dict(envelope)),
        key=lambda error: list(error.path),
    )
    if schema_errors:
        errors.append("schema_invalid")
    try:
        validate_capex_generated_artifact_file_name(file_name)
    except CommandError:
        errors.append("invalid_capex_generated_artifact_name")

    match = _VERSIONED_FILE_RE.match(str(file_name))
    artifact_kind = str(envelope.get("artifact_kind") or "")
    if match is not None and artifact_kind and match.group("artifact_kind") != artifact_kind:
        errors.append("artifact_kind_name_mismatch")

    source_refs = envelope.get("source_refs")
    if isinstance(source_refs, list) and not source_refs and not _allows_empty_source_refs(envelope):
        errors.append("empty_source_refs_not_allowed")

    input_digests = envelope.get("input_digests")
    if isinstance(input_digests, list):
        invalid_input_digests = [
            digest for digest in input_digests if not _SHA256_RE.match(str(digest))
        ]
        if invalid_input_digests:
            errors.append("input_digest_invalid")

    if expected_content_digest is not None:
        normalized_expected = str(expected_content_digest).lower()
        if not _SHA256_RE.match(normalized_expected):
            errors.append("expected_content_digest_invalid")
        elif capex_generated_artifact_digest(envelope) != normalized_expected:
            errors.append("content_digest_mismatch")

    return errors


def _validate_bundle_refs(
    *,
    envelope: Mapping[str, Any],
    available_source_refs: set[str],
    available_input_digests: set[str],
    index: int,
) -> list[str]:
    errors: list[str] = []
    source_refs = envelope.get("source_refs")
    if isinstance(source_refs, list):
        missing_source_refs = [
            str(source_ref)
            for source_ref in source_refs
            if str(source_ref) not in available_source_refs
        ]
        if missing_source_refs:
            errors.append("missing_source_ref")
    input_digests = envelope.get("input_digests")
    if isinstance(input_digests, list):
        stale_digests = [
            str(digest).lower()
            for digest in input_digests
            if str(digest).lower() not in available_input_digests
        ]
        if stale_digests:
            errors.append("stale_input_digest")
    return errors


def _allows_empty_source_refs(envelope: Mapping[str, Any]) -> bool:
    validation_summary = envelope.get("validation_summary")
    return (
        envelope.get("artifact_kind") == CAPEX_SOURCE_INVENTORY_ARTIFACT_KIND
        and isinstance(validation_summary, Mapping)
        and validation_summary.get("result")
        == CAPEX_SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT
    )


def _schema_validator() -> Draft202012Validator:
    schema = json.loads(_ENVELOPE_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value}


def _result(
    errors: Sequence[str],
    *,
    artifact_count: int,
) -> CapexGeneratedArtifactValidationResult:
    unique_errors = tuple(dict.fromkeys(errors))
    return CapexGeneratedArtifactValidationResult(
        valid=not unique_errors,
        error_codes=unique_errors,
        artifact_count=artifact_count,
        promotable=False,
        evidence_sufficient=False,
    )


__all__ = [
    "GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION",
    "VALIDATOR_ACTIVATION_POSTURE",
    "VALIDATOR_POLICY_ID",
    "CapexGeneratedArtifactValidationResult",
    "capex_generated_artifact_digest",
    "validate_capex_generated_artifact_bundle",
    "validate_capex_generated_artifact_envelope",
]
