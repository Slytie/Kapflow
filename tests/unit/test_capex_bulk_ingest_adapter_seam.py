from __future__ import annotations

import inspect

import pytest

import onetruth.capex_platform.bulk_ingest_adapter_seam as adapter_module
from onetruth.capex_platform.bulk_ingest_adapter_seam import (
    BULK_INGEST_ADAPTER_SEAM_ACTIVATION_POSTURE,
    BULK_INGEST_ADAPTER_SEAM_SCHEMA_VERSION,
    BulkIngestAdapterSeamError,
    build_bulk_ingest_adapter_seam_outputs,
    bulk_ingest_adapter_seam_digest,
    canonical_bulk_ingest_adapter_seam_bytes,
)
from onetruth.capex_platform.staged_corpus_ingest import (
    STAGED_CORPUS_INGEST_SCHEMA_VERSION,
)


NOW = "2026-06-23T00:00:00Z"
TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-bulk-ingest-seam"
SHA256_A = "sha256:" + ("a" * 64)
SHA256_B = "sha256:" + ("b" * 64)
SHA256_C = "sha256:" + ("c" * 64)


def _descriptor(
    index: int,
    *,
    mode: str = "object_store_manifest",
) -> dict[str, object]:
    descriptor: dict[str, object] = {
        "descriptor_id": f"desc-{index:04d}",
        "mode": mode,
        "manifest_ref": f"manifest:bulk-seam:{index:04d}",
        "manifest_digest": "sha256:" + f"{index:064x}",
        "content_digest": "sha256:" + f"{index + 7:064x}",
        "content_byte_size": 4096 + index,
        "content_media_type": "application/pdf",
        "canonicalization_profile": "staged-observed-bytes-v1",
        "metadata_json": {"fixture": "synthetic", "raw_material_committed": False},
    }
    if mode == "object_store_manifest":
        descriptor["object_ref"] = f"object://staged/capex/bulk-seam/{index:04d}"
    elif mode == "folder_manifest":
        descriptor["redacted_path_hint"] = "~/Client/..."
    elif mode == "source_root_snapshot":
        descriptor["source_root_id"] = "source-root-001"
        descriptor["folder_tree_snapshot_id"] = f"snapshot-{index:04d}"
    return descriptor


def _outputs(descriptors: list[dict[str, object]]) -> dict[str, object]:
    return build_bulk_ingest_adapter_seam_outputs(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        adapter_request_id="bulk-adapter-request-001",
        ingest_batch_id="ingest-batch-bulk-seam",
        idempotency_key="bulk-seam:ingest-batch-001",
        requested_by_actor_id="human:pm",
        requested_by_actor_type="human",
        created_at=NOW,
        descriptors=descriptors,
    )


def test_bulk_ingest_adapter_seam_is_deterministic_for_supported_modes() -> None:
    descriptors = [
        {**_descriptor(1, mode="object_store_manifest"), "manifest_digest": SHA256_A},
        {**_descriptor(2, mode="folder_manifest"), "manifest_digest": SHA256_B},
        {**_descriptor(3, mode="source_root_snapshot"), "manifest_digest": SHA256_C},
    ]

    outputs = _outputs(descriptors)
    replay = _outputs(descriptors)

    assert outputs["schema_version"] == BULK_INGEST_ADAPTER_SEAM_SCHEMA_VERSION
    assert outputs["activation_posture"] == BULK_INGEST_ADAPTER_SEAM_ACTIVATION_POSTURE
    assert outputs["descriptor_count"] == 3
    assert outputs["staged_ingest_plan_schema_version"] == (
        STAGED_CORPUS_INGEST_SCHEMA_VERSION
    )
    assert outputs["descriptor_fingerprint"] == outputs["staged_ingest_plan"][
        "descriptor_fingerprint"
    ]
    assert {
        descriptor["mode"]
        for descriptor in outputs["staged_ingest_plan"]["descriptors"]  # type: ignore[index]
    } == {
        "object_store_manifest",
        "folder_manifest",
        "source_root_snapshot",
    }
    assert canonical_bulk_ingest_adapter_seam_bytes(
        outputs
    ) == canonical_bulk_ingest_adapter_seam_bytes(replay)
    assert bulk_ingest_adapter_seam_digest(outputs).startswith("sha256:")


def test_bulk_ingest_adapter_seam_records_no_runtime_or_official_truth_effects() -> None:
    outputs = _outputs([_descriptor(1)])

    assert outputs["handoff"] == {
        "next_planning_step": "capex.source_inventory.v1",
        "uses_json_base64_artifact_route": False,
        "uses_local_source_path_artifact_route": False,
        "calls_artifact_ingress_descriptor_request_bytes": False,
        "creates_source_occurrences": False,
        "creates_artifact_versions": False,
        "promotes_official_pointers": False,
    }
    assert outputs["truth_effects"] == {
        "imports_raw_corpus": False,
        "uses_json_base64_command_route": False,
        "uses_local_source_path_artifact_route": False,
        "creates_source_occurrences": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }


def test_bulk_ingest_adapter_seam_rejects_duplicate_descriptor_ids() -> None:
    descriptors = [_descriptor(1), {**_descriptor(2), "descriptor_id": "desc-0001"}]

    with pytest.raises(BulkIngestAdapterSeamError) as exc_info:
        _outputs(descriptors)

    assert exc_info.value.code == "bulk_ingest_adapter_duplicate_descriptor_id"
    assert exc_info.value.details["descriptor_id"] == "desc-0001"


def test_bulk_ingest_adapter_seam_wraps_invalid_mode_and_missing_basis() -> None:
    cases = [
        {**_descriptor(1), "mode": "json_base64_upload"},
        {
            key: value
            for key, value in _descriptor(
                2,
                mode="source_root_snapshot",
            ).items()
            if key != "folder_tree_snapshot_id"
        },
        {**_descriptor(3), "manifest_digest": "not-a-sha"},
    ]

    for descriptor in cases:
        with pytest.raises(BulkIngestAdapterSeamError) as exc_info:
            _outputs([descriptor])
        assert exc_info.value.code == "bulk_ingest_adapter_staged_plan_invalid"
        assert str(exc_info.value.details["upstream_code"]).startswith(
            "staged_ingest_"
        )


def test_bulk_ingest_adapter_seam_rejects_raw_body_and_route_material() -> None:
    cases = [
        {**_descriptor(1), "content_base64": "AAAA"},
        {**_descriptor(2), "source_path": "/Users/pm/client/source.pdf"},
        {**_descriptor(3), "file_name": "client-source.pdf"},
        {
            **_descriptor(4),
            "metadata_json": {"preview": "data:application/pdf;base64,AAAA"},
        },
        {**_descriptor(5), "manifest_ref": "C:\\Users\\pm\\client\\manifest.json"},
        {**_descriptor(6), "metadata_json": {"blob_bytes": b"raw-bytes"}},
    ]

    for descriptor in cases:
        with pytest.raises(BulkIngestAdapterSeamError) as exc_info:
            _outputs([descriptor])
        assert exc_info.value.code in {
            "bulk_ingest_adapter_raw_material_field_forbidden",
            "bulk_ingest_adapter_inline_base64_forbidden",
            "bulk_ingest_adapter_raw_absolute_path_forbidden",
            "bulk_ingest_adapter_blob_bytes_forbidden",
        }


def test_bulk_ingest_adapter_seam_does_not_import_artifact_ingress_surfaces() -> None:
    source = inspect.getsource(adapter_module)

    assert "ingest_artifact_document_command" not in source
    assert "ArtifactIngressDescriptor" not in source
    assert "ArtifactIngressDescriptor.request_bytes" not in source
