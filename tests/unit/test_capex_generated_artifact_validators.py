from __future__ import annotations

from onetruth.application.handlers._shared.artifact_effects import (
    CAPEX_SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT,
    build_capex_generated_artifact_envelope,
)
from onetruth.capex_platform.generated_artifact_validators import (
    GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION,
    capex_generated_artifact_digest,
    validate_capex_generated_artifact_bundle,
    validate_capex_generated_artifact_envelope,
)


SOURCE_REF = "source_occurrence:so-validator"
INPUT_DIGEST = "sha256:" + ("1" * 64)
OTHER_DIGEST = "sha256:" + ("2" * 64)


def _envelope(
    *,
    artifact_kind: str = "capex.project_intake.profile",
    source_refs: list[str] | None = None,
    input_digests: list[str] | None = None,
    validation_result: str = "planning_only",
) -> dict[str, object]:
    return build_capex_generated_artifact_envelope(
        artifact_kind=artifact_kind,
        artifact_role="evidence",
        source_refs=[SOURCE_REF] if source_refs is None else source_refs,
        input_digests=[INPUT_DIGEST] if input_digests is None else input_digests,
        validation_summary={"result": validation_result},
        payload={"ok": True},
    )


def _artifact(file_name: str, envelope: dict[str, object]) -> dict[str, object]:
    return {
        "file_name": file_name,
        "envelope": envelope,
        "content_digest": capex_generated_artifact_digest(envelope),
    }


def test_generated_artifact_validator_accepts_schema_name_and_digest_consistency() -> None:
    envelope = _envelope()

    result = validate_capex_generated_artifact_envelope(
        file_name="capex.project_intake.profile.v1.json",
        envelope=envelope,
        expected_content_digest=capex_generated_artifact_digest(envelope),
    )

    assert result.valid is True
    assert result.error_codes == ()
    assert result.promotable is False
    assert result.evidence_sufficient is False


def test_generated_artifact_bundle_validator_accepts_cross_reference_consistency() -> None:
    envelope = _envelope()
    bundle = {
        "schema_version": GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION,
        "available_source_refs": [SOURCE_REF],
        "available_input_digests": [INPUT_DIGEST],
        "artifacts": [_artifact("capex.project_intake.profile.v1.json", envelope)],
    }

    result = validate_capex_generated_artifact_bundle(bundle)

    assert result.valid is True
    assert result.error_codes == ()
    assert result.artifact_count == 1


def test_generated_artifact_bundle_validator_fails_closed_for_missing_and_stale_refs() -> None:
    envelope = _envelope(input_digests=[OTHER_DIGEST])
    bundle = {
        "schema_version": GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION,
        "available_source_refs": [],
        "available_input_digests": [INPUT_DIGEST],
        "artifacts": [_artifact("capex.project_intake.profile.v1.json", envelope)],
    }

    result = validate_capex_generated_artifact_bundle(bundle)

    assert result.valid is False
    assert set(result.error_codes) >= {"missing_source_ref", "stale_input_digest"}


def test_generated_artifact_bundle_validator_rejects_duplicate_and_mismatched_names() -> None:
    first = _envelope(artifact_kind="capex.project_intake.profile")
    second = _envelope(artifact_kind="capex.project_intake.handoff_manifest")
    bundle = {
        "schema_version": GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION,
        "available_source_refs": [SOURCE_REF],
        "available_input_digests": [INPUT_DIGEST],
        "artifacts": [
            _artifact("capex.project_intake.profile.v1.json", first),
            _artifact("capex.project_intake.profile.v1.json", second),
        ],
    }

    result = validate_capex_generated_artifact_bundle(bundle)

    assert result.valid is False
    assert set(result.error_codes) >= {
        "duplicate_canonical_artifact_name",
        "artifact_kind_name_mismatch",
    }


def test_generated_artifact_validator_rejects_deprecated_names_and_digest_mismatch() -> None:
    envelope = _envelope()

    result = validate_capex_generated_artifact_envelope(
        file_name="Capex Project Intake Profile.json",
        envelope=envelope,
        expected_content_digest=OTHER_DIGEST,
    )

    assert result.valid is False
    assert set(result.error_codes) >= {
        "invalid_capex_generated_artifact_name",
        "content_digest_mismatch",
    }


def test_generated_artifact_empty_source_refs_exception_is_inventory_only() -> None:
    inventory = _envelope(
        artifact_kind="capex.source_inventory",
        source_refs=[],
        validation_result=CAPEX_SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT,
    )
    accepted = validate_capex_generated_artifact_bundle(
        {
            "schema_version": GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION,
            "available_source_refs": [],
            "available_input_digests": [INPUT_DIGEST],
            "artifacts": [_artifact("capex.source_inventory.v1.json", inventory)],
        }
    )
    invalid = dict(inventory)
    invalid["artifact_kind"] = "capex.project_intake.profile"
    rejected = validate_capex_generated_artifact_envelope(
        file_name="capex.project_intake.profile.v1.json",
        envelope=invalid,
        expected_content_digest=capex_generated_artifact_digest(invalid),
    )

    assert accepted.valid is True
    assert rejected.valid is False
    assert "empty_source_refs_not_allowed" in rejected.error_codes
