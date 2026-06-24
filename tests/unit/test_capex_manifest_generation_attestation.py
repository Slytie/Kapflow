from __future__ import annotations

import pytest

from onetruth.capex_platform.manifest_generation_attestation import (
    MANIFEST_GENERATION_ATTESTATION_ACTIVATION_POSTURE,
    MANIFEST_GENERATION_ATTESTATION_OUTPUTS_SCHEMA_VERSION,
    ManifestGenerationAttestationError,
    build_manifest_generation_attestation_outputs,
    canonical_manifest_generation_attestation_bytes,
    manifest_generation_attestation_digest,
)


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-manifest-attestation"
NOW = "2026-06-23T00:00:00Z"
SHA256_A = "sha256:" + ("a" * 64)
SHA256_B = "sha256:" + ("b" * 64)
BARE_SHA256_C = "c" * 64


def _content_identity(
    content_identity_id: str = "cci:alpha",
    *,
    content_digest: str = BARE_SHA256_C,
) -> dict[str, object]:
    return {
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "content_identity_id": content_identity_id,
        "digest_algorithm": "sha256",
        "content_digest": content_digest,
        "byte_size": 4096,
        "media_type": "application/pdf",
        "canonicalization_profile": "sanitized-fixture-manifest-v1",
    }


def _source_occurrence(
    source_occurrence_id: str = "so-alpha",
    *,
    content_identity_id: str = "cci:alpha",
    project_id: str = PROJECT_ID,
) -> dict[str, object]:
    return {
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "project_id": project_id,
        "source_occurrence_id": source_occurrence_id,
        "source_ref": f"source_occurrence:{source_occurrence_id}",
        "content_identity_id": content_identity_id,
        "occurrence_kind": "sanitized_fixture_manifest_entry",
        "status": "available",
        "created_at": NOW,
    }


def _relation(
    relation_id: str = "sor-alpha",
    *,
    source_occurrence_id: str = "so-alpha",
    target_source_occurrence_id: str = "so-beta",
    relation_type: str = "duplicate_of",
    project_id: str = PROJECT_ID,
) -> dict[str, object]:
    return {
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "project_id": project_id,
        "source_occurrence_relation_id": relation_id,
        "relation_type": relation_type,
        "source_occurrence_id": source_occurrence_id,
        "target_source_occurrence_id": target_source_occurrence_id,
        "status": "active",
        "basis_ref": f"source_occurrence:{source_occurrence_id}",
        "policy_version": "capex-source-relation-policy-v1",
    }


def _outputs(
    *,
    content_identity_rows: list[dict[str, object]] | None = None,
    source_occurrence_rows: list[dict[str, object]] | None = None,
    relation_rows: list[dict[str, object]] | None = None,
    input_digests: dict[str, object] | None = None,
    generator_config_digest: str = SHA256_A,
) -> dict[str, object]:
    return build_manifest_generation_attestation_outputs(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        attestation_id="manifest-attestation-001",
        generated_register_id="generated-register-001",
        generator_id="capex-manifest-generator",
        generator_version="v1",
        generator_config_digest=generator_config_digest,
        policy_version="capex-manifest-generation-policy-v1",
        input_digests=input_digests
        or {
            "capex_content_identities": SHA256_A,
            "capex_source_occurrences": SHA256_B,
        },
        content_identity_rows=content_identity_rows
        or [_content_identity(), _content_identity("cci:beta", content_digest=SHA256_B)],
        source_occurrence_rows=source_occurrence_rows
        or [
            _source_occurrence(),
            _source_occurrence("so-beta", content_identity_id="cci:beta"),
        ],
        relation_rows=relation_rows or [_relation()],
        generated_at=NOW,
        generated_by_actor_id="service:capex-manifest-generator",
        generated_by_actor_type="service",
    )


def test_manifest_generation_attestation_is_deterministic_from_physical_rows() -> None:
    outputs = _outputs()
    replay = _outputs()

    assert outputs["schema_version"] == (
        MANIFEST_GENERATION_ATTESTATION_OUTPUTS_SCHEMA_VERSION
    )
    assert outputs["activation_posture"] == (
        MANIFEST_GENERATION_ATTESTATION_ACTIVATION_POSTURE
    )
    assert outputs["basis"]["generated_from_physical_rows_only"] is True
    assert outputs["basis"]["source_tables"] == [
        "capex_content_identities",
        "capex_source_occurrences",
        "capex_source_occurrence_relations",
    ]
    manifest = outputs["generated_corpus_register_manifest"]
    attestation = outputs["manifest_generation_attestation"]
    assert manifest["row_count"] == 2
    assert all(row["row_digest"].startswith("sha256:") for row in manifest["rows"])
    assert attestation["generated_register_digest"] == manifest["snapshot_digest"]
    assert attestation["generated_register_is_source_authority"] is False
    assert canonical_manifest_generation_attestation_bytes(
        outputs
    ) == canonical_manifest_generation_attestation_bytes(replay)
    assert manifest_generation_attestation_digest(outputs).startswith("sha256:")


def test_manifest_generation_attestation_records_no_runtime_or_official_truth_effects() -> None:
    outputs = _outputs()

    assert outputs["truth_effects"] == {
        "creates_content_identities": False,
        "creates_source_occurrences": False,
        "creates_relation_rows": False,
        "creates_ingest_jobs": False,
        "writes_artifacts": False,
        "emits_timeline_events": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert "generated_register_as_source_authority" in outputs["cannot_be_used_for"]


def test_manifest_generation_attestation_rejects_scope_unknown_refs_and_duplicates() -> None:
    with pytest.raises(ManifestGenerationAttestationError) as scope_exc:
        _outputs(source_occurrence_rows=[_source_occurrence(project_id="other")])
    assert scope_exc.value.code == "manifest_attestation_scope_mismatch"

    with pytest.raises(ManifestGenerationAttestationError) as content_exc:
        _outputs(source_occurrence_rows=[_source_occurrence(content_identity_id="missing")])
    assert content_exc.value.code == "manifest_attestation_content_identity_not_found"

    with pytest.raises(ManifestGenerationAttestationError) as relation_exc:
        _outputs(
            relation_rows=[
                _relation(target_source_occurrence_id="so-not-known"),
            ]
        )
    assert relation_exc.value.code == "manifest_attestation_relation_occurrence_not_found"

    with pytest.raises(ManifestGenerationAttestationError) as duplicate_exc:
        _outputs(
            content_identity_rows=[
                _content_identity(),
                _content_identity(),
            ]
        )
    assert duplicate_exc.value.code == "manifest_attestation_duplicate_content_identity_id"


def test_manifest_generation_attestation_rejects_bad_digests_and_source_refs() -> None:
    with pytest.raises(ManifestGenerationAttestationError) as input_digest_exc:
        _outputs(input_digests={"capex_source_occurrences": "not-a-sha"})
    assert input_digest_exc.value.code == "manifest_attestation_digest_invalid"

    with pytest.raises(ManifestGenerationAttestationError) as config_digest_exc:
        _outputs(generator_config_digest="not-a-sha")
    assert config_digest_exc.value.code == "manifest_attestation_digest_invalid"

    with pytest.raises(ManifestGenerationAttestationError) as content_digest_exc:
        _outputs(content_identity_rows=[_content_identity(content_digest="not-a-sha")])
    assert content_digest_exc.value.code == "manifest_attestation_digest_invalid"

    with pytest.raises(ManifestGenerationAttestationError) as source_ref_exc:
        _outputs(
            source_occurrence_rows=[
                {
                    **_source_occurrence(),
                    "source_ref": "source_occurrence:other",
                }
            ]
        )
    assert source_ref_exc.value.code == "manifest_attestation_source_ref_mismatch"


def test_manifest_generation_attestation_rejects_raw_material() -> None:
    cases = [
        {"source_occurrence_rows": [{**_source_occurrence(), "filename": "client.pdf"}]},
        {
            "source_occurrence_rows": [
                {
                    **_source_occurrence(),
                    "locator": "/Users/pm/project/client.pdf",
                }
            ]
        },
        {
            "source_occurrence_rows": [
                {
                    **_source_occurrence(),
                    "metadata": {"preview": "data:application/pdf;base64,AAAA"},
                }
            ]
        },
        {
            "source_occurrence_rows": [
                {
                    **_source_occurrence(),
                    "metadata": {"blob_bytes": b"raw-bytes"},
                }
            ]
        },
    ]

    for kwargs in cases:
        with pytest.raises(ManifestGenerationAttestationError):
            _outputs(**kwargs)
