from __future__ import annotations

import pytest

from onetruth.capex_platform.staged_corpus_ingest import (
    STAGED_CORPUS_INGEST_ACTIVATION_POSTURE,
    STAGED_CORPUS_INGEST_SCHEMA_VERSION,
    StagedCorpusIngestError,
    plan_staged_corpus_ingest,
)


SHA256_A = "sha256:" + ("a" * 64)
SHA256_B = "sha256:" + ("b" * 64)
SHA256_C = "sha256:" + ("c" * 64)


def _descriptor(index: int, *, mode: str = "object_store_manifest") -> dict[str, object]:
    descriptor: dict[str, object] = {
        "descriptor_id": f"desc-{index:04d}",
        "mode": mode,
        "manifest_ref": f"manifest:batch-001:{index:04d}",
        "manifest_digest": SHA256_A,
        "content_digest": "sha256:" + f"{index % 7:064x}",
        "content_byte_size": 2048 + index,
        "content_media_type": "application/pdf",
        "canonicalization_profile": "staged-observed-bytes-v1",
        "byte_size": 128 + index,
        "media_type": "application/json",
        "metadata_json": {"fixture": "synthetic", "raw_material_committed": False},
    }
    if mode == "object_store_manifest":
        descriptor["object_ref"] = f"object://staged/capex/batch-001/{index:04d}"
    elif mode == "folder_manifest":
        descriptor["redacted_path_hint"] = "~/Client/..."
    elif mode == "source_root_snapshot":
        descriptor["source_root_id"] = "sr-001"
        descriptor["folder_tree_snapshot_id"] = f"snap-{index:04d}"
    return descriptor


def _plan(descriptors: list[dict[str, object]]) -> dict[str, object]:
    return plan_staged_corpus_ingest(
        tenant_id="tenant-a",
        domain_id="domain-x",
        project_id="cp-alpha",
        ingest_batch_id="ingest-batch-001",
        idempotency_key="ingest-batch-001",
        requested_by_actor_id="human:pm",
        requested_by_actor_type="human",
        created_at="2026-06-17T00:00:00Z",
        descriptors=descriptors,
    )


def test_staged_corpus_ingest_accepts_1k_synthetic_manifest_descriptors() -> None:
    descriptors = [_descriptor(index) for index in range(1_000)]

    plan = _plan(descriptors)

    assert plan["schema_version"] == STAGED_CORPUS_INGEST_SCHEMA_VERSION
    assert plan["activation_posture"] == STAGED_CORPUS_INGEST_ACTIVATION_POSTURE
    assert plan["descriptor_count"] == 1_000
    assert str(plan["descriptor_fingerprint"]).startswith("sha256:")
    assert plan["descriptors"][0]["content_digest"].startswith("sha256:")  # type: ignore[index]
    assert plan["descriptors"][0]["canonicalization_profile"] == (  # type: ignore[index]
        "staged-observed-bytes-v1"
    )
    assert plan["truth_effects"] == {
        "creates_source_occurrences": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }


def test_staged_corpus_ingest_represents_object_folder_and_source_root_modes() -> None:
    plan = _plan(
        [
            _descriptor(1, mode="object_store_manifest"),
            {**_descriptor(2, mode="folder_manifest"), "manifest_digest": SHA256_B},
            {**_descriptor(3, mode="source_root_snapshot"), "manifest_digest": SHA256_C},
        ]
    )

    modes = {descriptor["mode"] for descriptor in plan["descriptors"]}  # type: ignore[index]

    assert modes == {
        "object_store_manifest",
        "folder_manifest",
        "source_root_snapshot",
    }
    assert plan["body_limit_policy"]["json_base64_command_route_allowed"] is False  # type: ignore[index]


def test_staged_corpus_ingest_rejects_inline_raw_content_and_base64() -> None:
    cases = [
        {**_descriptor(1), "content": "raw text from a document"},
        {
            **_descriptor(2),
            "metadata_json": {"preview": "data:application/pdf;base64,AAAA"},
        },
    ]

    for descriptor in cases:
        with pytest.raises(StagedCorpusIngestError) as exc_info:
            _plan([descriptor])
        assert exc_info.value.code in {
            "staged_ingest_raw_material_field_forbidden",
            "staged_ingest_inline_base64_forbidden",
        }


def test_staged_corpus_ingest_rejects_raw_absolute_path_hints_and_filenames() -> None:
    cases = [
        {**_descriptor(1, mode="folder_manifest"), "redacted_path_hint": "/Users/pm/Client"},
        {**_descriptor(2), "file_name": "real-client-file.pdf"},
        {**_descriptor(3), "manifest_ref": "C:\\Users\\pm\\client\\manifest.json"},
    ]

    for descriptor in cases:
        with pytest.raises(StagedCorpusIngestError) as exc_info:
            _plan([descriptor])
        assert exc_info.value.code in {
            "staged_ingest_raw_absolute_path_forbidden",
            "staged_ingest_raw_material_field_forbidden",
        }


def test_staged_corpus_ingest_rejects_missing_mode_specific_basis() -> None:
    descriptor = _descriptor(1, mode="source_root_snapshot")
    descriptor.pop("folder_tree_snapshot_id")

    with pytest.raises(StagedCorpusIngestError) as exc_info:
        _plan([descriptor])

    assert exc_info.value.code == "staged_ingest_mode_required_fields_missing"
    assert exc_info.value.details["missing"] == ["folder_tree_snapshot_id"]
