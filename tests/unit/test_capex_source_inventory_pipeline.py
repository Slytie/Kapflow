from __future__ import annotations

import sqlite3

import pytest

from onetruth.capex_platform.source_inventory import (
    SOURCE_INVENTORY_ACTIVATION_POSTURE,
    SOURCE_INVENTORY_ARTIFACT_KIND,
    SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT,
    SOURCE_INVENTORY_SCHEMA_VERSION,
    SourceInventoryError,
    build_source_inventory,
    canonical_source_inventory_bytes,
    source_inventory_digest,
    source_inventory_validation_summary,
)
from onetruth.capex_platform.staged_corpus_ingest import plan_staged_corpus_ingest
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


NOW = "2026-06-17T00:00:00Z"
TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-source-inventory"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _descriptor(index: int, *, digest_index: int | None = None) -> dict[str, object]:
    digest_value = index if digest_index is None else digest_index
    return {
        "descriptor_id": f"desc-{index:04d}",
        "mode": "object_store_manifest",
        "manifest_ref": f"manifest:source-inventory:{index:04d}",
        "manifest_digest": "sha256:" + f"{index:064x}",
        "object_ref": f"object://staged/capex/source-inventory/{index:04d}",
        "content_digest": "sha256:" + f"{digest_value:064x}",
        "content_byte_size": 4096 + digest_value,
        "content_media_type": "application/pdf",
        "canonicalization_profile": "staged-observed-bytes-v1",
        "metadata_json": {"fixture": "synthetic", "raw_material_committed": False},
    }


def _plan(descriptors: list[dict[str, object]]) -> dict[str, object]:
    return plan_staged_corpus_ingest(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        ingest_batch_id="ingest-batch-source-inventory",
        idempotency_key="ingest-batch-source-inventory",
        requested_by_actor_id="human:pm",
        requested_by_actor_type="human",
        created_at=NOW,
        descriptors=descriptors,
    )


def _inventory(
    connection: sqlite3.Connection,
    plan: dict[str, object],
    *,
    inventory_id: str = "source-inventory-001",
) -> dict[str, object]:
    return build_source_inventory(
        connection,
        ingest_plan=plan,
        inventory_id=inventory_id,
        created_at=NOW,
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
    )


def test_source_inventory_accepts_1k_sanitized_descriptors_and_is_deterministic() -> None:
    connection = _connection()
    try:
        plan = _plan([_descriptor(index, digest_index=index % 25) for index in range(1_000)])

        inventory = _inventory(connection, plan)
        replay = _inventory(connection, plan)

        assert inventory["schema_version"] == SOURCE_INVENTORY_SCHEMA_VERSION
        assert inventory["activation_posture"] == SOURCE_INVENTORY_ACTIVATION_POSTURE
        assert inventory["descriptor_count"] == 1_000
        assert inventory["unique_content_count"] == 25
        assert canonical_source_inventory_bytes(inventory) == canonical_source_inventory_bytes(
            replay
        )
        assert source_inventory_digest(inventory).startswith("sha256:")
        assert connection.execute(
            "SELECT COUNT(*) FROM capex_content_identities"
        ).fetchone()[0] == 25
    finally:
        connection.close()


def test_same_bytes_multiple_descriptors_share_one_content_identity_and_dedupe_group() -> None:
    connection = _connection()
    try:
        plan = _plan(
            [
                _descriptor(1, digest_index=7),
                _descriptor(2, digest_index=7),
                _descriptor(3, digest_index=8),
            ]
        )

        inventory = _inventory(connection, plan)

        duplicate_group = [
            group
            for group in inventory["dedupe_groups"]  # type: ignore[index]
            if group["occurrence_count"] == 2
        ][0]
        duplicate_items = [
            item
            for item in inventory["items"]  # type: ignore[index]
            if item["content_digest"] == duplicate_group["content_digest"]
        ]

        assert duplicate_group["descriptor_ids"] == ["desc-0001", "desc-0002"]
        assert len({item["content_identity_id"] for item in duplicate_items}) == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM capex_source_occurrences"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_source_inventory_requires_sanitized_content_digest_metadata() -> None:
    connection = _connection()
    try:
        descriptor = _descriptor(1)
        descriptor.pop("content_digest")
        plan = _plan([descriptor])

        with pytest.raises(SourceInventoryError) as exc_info:
            _inventory(connection, plan)

        assert exc_info.value.code == "source_inventory_required_field_missing"
        assert exc_info.value.details["field"] == "descriptors[0].content_digest"
    finally:
        connection.close()


def test_source_inventory_records_no_activation_or_truth_mutation_beyond_digest_store() -> None:
    connection = _connection()
    try:
        inventory = _inventory(connection, _plan([_descriptor(1)]))

        assert SOURCE_INVENTORY_ARTIFACT_KIND == "capex.source_inventory"
        assert source_inventory_validation_summary()["result"] == (
            SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT
        )
        assert inventory["truth_effects"] == {
            "creates_source_occurrences": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        }
        assert connection.execute(
            "SELECT COUNT(*) FROM artifact_versions"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM artifact_pointers"
        ).fetchone()[0] == 0
    finally:
        connection.close()
