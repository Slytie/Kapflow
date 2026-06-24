from __future__ import annotations

import pytest

from onetruth.capex_platform.archive_lineage_metadata import (
    ARCHIVE_LINEAGE_METADATA_ACTIVATION_POSTURE,
    ARCHIVE_LINEAGE_METADATA_OUTPUTS_SCHEMA_VERSION,
    ArchiveLineageMetadataError,
    archive_lineage_metadata_digest,
    build_archive_lineage_metadata_outputs,
    canonical_archive_lineage_metadata_bytes,
)


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-archive-lineage"
NOW = "2026-06-23T00:00:00Z"
SHA256_A = "sha256:" + ("a" * 64)


def _occurrence(source_occurrence_id: str, *, project_id: str = PROJECT_ID) -> dict[str, object]:
    return {
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "project_id": project_id,
        "source_occurrence_id": source_occurrence_id,
        "source_ref": f"source_occurrence:{source_occurrence_id}",
    }


def _relation(
    relation_id: str,
    *,
    relation_type: str = "archive_contains",
    source_occurrence_id: str = "so-archive-root",
    target_source_occurrence_id: str = "so-nested-archive",
    project_id: str = PROJECT_ID,
) -> dict[str, object]:
    return {
        "source_occurrence_relation_id": relation_id,
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "project_id": project_id,
        "relation_type": relation_type,
        "source_occurrence_id": source_occurrence_id,
        "target_source_occurrence_id": target_source_occurrence_id,
        "status": "active",
        "basis_ref": f"source_occurrence:{source_occurrence_id}",
        "policy_version": "capex-archive-lineage-policy-v1",
    }


def _metadata(
    metadata_id: str,
    *,
    container_source_occurrence_id: str = "so-archive-root",
    member_source_occurrence_id: str = "so-nested-archive",
    depth: int = 1,
    entry_index: int = 0,
) -> dict[str, object]:
    return {
        "member_metadata_id": metadata_id,
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "project_id": PROJECT_ID,
        "container_source_occurrence_id": container_source_occurrence_id,
        "member_source_occurrence_id": member_source_occurrence_id,
        "logical_member_ref": f"archive-member:{metadata_id}",
        "logical_path_segments": ["archive-root", f"entry-{entry_index:04d}"],
        "nesting_depth": depth,
        "entry_index": entry_index,
        "extraction_metadata_status": "metadata_only",
        "member_content_digest": SHA256_A,
        "compressed_byte_size": 128,
        "uncompressed_byte_size": 256,
        "metadata": {"fixture": "synthetic"},
    }


def _outputs(
    *,
    source_occurrences: list[dict[str, object]] | None = None,
    relation_rows: list[dict[str, object]] | None = None,
    member_metadata_rows: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return build_archive_lineage_metadata_outputs(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        archive_lineage_id="archive-lineage-001",
        source_occurrences=source_occurrences
        or [
            _occurrence("so-archive-root"),
            _occurrence("so-nested-archive"),
            _occurrence("so-member-document"),
        ],
        relation_rows=relation_rows
        or [
            _relation("sor-archive-001"),
            _relation(
                "sor-archive-002",
                relation_type="archive_member_of",
                source_occurrence_id="so-member-document",
                target_source_occurrence_id="so-nested-archive",
            ),
        ],
        member_metadata_rows=member_metadata_rows
        or [
            _metadata("archive-member-001"),
            _metadata(
                "archive-member-002",
                container_source_occurrence_id="so-nested-archive",
                member_source_occurrence_id="so-member-document",
                depth=2,
                entry_index=1,
            ),
        ],
        created_at=NOW,
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
    )


def test_archive_lineage_metadata_is_deterministic_for_nested_archives() -> None:
    outputs = _outputs()
    replay = _outputs()

    assert outputs["schema_version"] == ARCHIVE_LINEAGE_METADATA_OUTPUTS_SCHEMA_VERSION
    assert outputs["activation_posture"] == ARCHIVE_LINEAGE_METADATA_ACTIVATION_POSTURE
    assert outputs["basis"]["accepted_relation_types"] == [
        "archive_contains",
        "archive_member_of",
    ]
    lineage = outputs["archive_lineage_register"]
    member_metadata = outputs["nested_archive_member_metadata"]
    assert lineage["row_count"] == 2
    assert member_metadata["row_count"] == 2
    assert [row["nesting_depth"] for row in lineage["rows"]] == [1, 2]
    assert lineage["rows"][0]["member_metadata_ref"] == (
        "generated_row:capex.nested_archive_member_metadata:archive-member-001"
    )
    assert canonical_archive_lineage_metadata_bytes(
        outputs
    ) == canonical_archive_lineage_metadata_bytes(replay)
    assert archive_lineage_metadata_digest(outputs).startswith("sha256:")


def test_archive_lineage_metadata_records_no_runtime_or_official_truth_effects() -> None:
    outputs = _outputs()

    assert outputs["truth_effects"] == {
        "creates_relation_rows": False,
        "creates_source_occurrences": False,
        "creates_content_identities": False,
        "creates_extraction_jobs": False,
        "starts_workers": False,
        "runs_archive_extractor": False,
        "writes_artifacts": False,
        "emits_timeline_events": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert "official_pointer_creation" in outputs["cannot_be_used_for"]


def test_archive_lineage_metadata_rejects_unknown_source_and_scope_mismatch() -> None:
    with pytest.raises(ArchiveLineageMetadataError) as missing_exc:
        _outputs(
            relation_rows=[
                _relation(
                    "sor-missing",
                    target_source_occurrence_id="so-not-known",
                )
            ],
            member_metadata_rows=[],
        )
    assert missing_exc.value.code == "archive_lineage_source_occurrence_not_found"

    with pytest.raises(ArchiveLineageMetadataError) as scope_exc:
        _outputs(source_occurrences=[_occurrence("so-archive-root", project_id="other")])
    assert scope_exc.value.code == "archive_lineage_scope_mismatch"


def test_archive_lineage_metadata_rejects_invalid_relation_type_duplicates_and_cycles() -> None:
    with pytest.raises(ArchiveLineageMetadataError) as type_exc:
        _outputs(relation_rows=[_relation("sor-invalid", relation_type="duplicate_of")])
    assert type_exc.value.code == "archive_lineage_relation_type_invalid"

    with pytest.raises(ArchiveLineageMetadataError) as duplicate_exc:
        _outputs(
            member_metadata_rows=[
                _metadata("archive-member-001"),
                _metadata(
                    "archive-member-001",
                    container_source_occurrence_id="so-nested-archive",
                    member_source_occurrence_id="so-member-document",
                    depth=2,
                    entry_index=1,
                ),
            ]
        )
    assert duplicate_exc.value.code == "archive_lineage_duplicate_member_metadata_id"

    with pytest.raises(ArchiveLineageMetadataError) as cycle_exc:
        _outputs(
            relation_rows=[
                _relation("sor-cycle-001"),
                _relation(
                    "sor-cycle-002",
                    source_occurrence_id="so-nested-archive",
                    target_source_occurrence_id="so-archive-root",
                ),
            ],
            member_metadata_rows=[
                _metadata("archive-member-001"),
                _metadata(
                    "archive-member-002",
                    container_source_occurrence_id="so-nested-archive",
                    member_source_occurrence_id="so-archive-root",
                    depth=1,
                    entry_index=1,
                ),
            ],
        )
    assert cycle_exc.value.code == "archive_lineage_cycle_detected"


def test_archive_lineage_metadata_rejects_bad_depth_digest_and_raw_material() -> None:
    cases = [
        [
            {
                **_metadata("archive-member-001"),
                "nesting_depth": 9,
            }
        ],
        [
            {
                **_metadata("archive-member-001"),
                "member_content_digest": "not-a-sha",
            }
        ],
        [
            {
                **_metadata("archive-member-001"),
                "logical_path_segments": ["client-source.pdf"],
            }
        ],
        [
            {
                **_metadata("archive-member-001"),
                "metadata": {"preview": "data:application/pdf;base64,AAAA"},
            }
        ],
        [
            {
                **_metadata("archive-member-001"),
                "metadata": {"blob_bytes": b"raw-bytes"},
            }
        ],
    ]

    for member_metadata_rows in cases:
        with pytest.raises(ArchiveLineageMetadataError):
            _outputs(member_metadata_rows=member_metadata_rows)
