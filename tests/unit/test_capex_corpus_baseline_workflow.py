from __future__ import annotations

import sqlite3

import pytest

from onetruth.capex_platform.corpus_baseline_workflow import (
    CORPUS_BASELINE_ACTIVATION_POSTURE,
    CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
    CorpusBaselineWorkflowError,
    build_corpus_baseline_workflow_outputs,
    corpus_baseline_workflow_digest,
)
from onetruth.capex_platform.role_packet_register import (
    build_packet_register,
    build_role_assignment_register,
)
from onetruth.capex_platform.source_inventory import build_source_inventory
from onetruth.capex_platform.source_occurrence_register import build_source_occurrence_register
from onetruth.capex_platform.staged_corpus_ingest import plan_staged_corpus_ingest
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_projects import create_capex_project


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-corpus-baseline"
NOW = "2026-06-17T00:00:00Z"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    create_capex_project(
        connection,
        project_id=PROJECT_ID,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_key="CP-CORPUS",
        name="Corpus Baseline Fixture",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    return connection


def _descriptor(index: int) -> dict[str, object]:
    return {
        "descriptor_id": f"desc-{index:04d}",
        "mode": "object_store_manifest",
        "manifest_ref": f"manifest:baseline:{index:04d}",
        "manifest_digest": "sha256:" + f"{index:064x}",
        "object_ref": f"object://staged/capex/{PROJECT_ID}/{index:04d}",
        "content_digest": "sha256:" + f"{index + 100:064x}",
        "content_byte_size": 1024 + index,
        "content_media_type": "application/pdf",
        "canonicalization_profile": "staged-observed-bytes-v1",
    }


def _chain(connection: sqlite3.Connection) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    ingest_plan = plan_staged_corpus_ingest(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        ingest_batch_id="ingest-corpus-baseline",
        idempotency_key="idem-corpus-baseline",
        requested_by_actor_id="human:pm",
        requested_by_actor_type="human",
        created_at=NOW,
        descriptors=[_descriptor(1), _descriptor(2)],
    )
    inventory = build_source_inventory(
        connection,
        ingest_plan=ingest_plan,
        inventory_id="inventory-corpus-baseline",
        created_at=NOW,
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
    )
    occurrence_register = build_source_occurrence_register(
        connection,
        source_inventory=inventory,
        occurrence_contexts=[
            {
                "source_occurrence_id": "so-baseline-primary",
                "descriptor_id": "desc-0001",
                "occurrence_kind": "sanitized_folder_manifest_entry",
                "locator_json": {
                    "manifest_ref": "manifest:baseline:0001",
                    "container_ref": "folder:baseline",
                    "entry_ref": "entry:primary",
                },
                "metadata_json": {"context_profile": "baseline"},
            },
            {
                "source_occurrence_id": "so-baseline-supporting",
                "descriptor_id": "desc-0002",
                "occurrence_kind": "sanitized_archive_member",
                "locator_json": {
                    "manifest_ref": "manifest:baseline:0002",
                    "container_ref": "archive:baseline",
                    "entry_ref": "entry:supporting",
                },
                "metadata_json": {"context_profile": "baseline"},
            },
        ],
        register_id="source-occurrence-register-corpus",
        created_at=NOW,
        registered_by_actor_id="human:pm",
        registered_by_actor_type="human",
    )
    role_register = build_role_assignment_register(
        source_occurrence_register=occurrence_register,
        role_assignments=[
            {
                "source_ref": "source_occurrence:so-baseline-primary",
                "source_role": "primary_evidence",
                "review_state": "human_reviewed",
                "review_rationale": "Primary sanitized occurrence for corpus baseline.",
                "ai_suggested": True,
            },
            {
                "source_ref": "source_occurrence:so-baseline-supporting",
                "source_role": "supporting_evidence",
                "review_state": "human_reviewed",
                "review_rationale": "Supporting sanitized occurrence for corpus baseline.",
            },
        ],
        register_id="role-register-corpus",
        created_at=NOW,
        reviewed_by_actor_id="human:pm",
        reviewed_by_actor_type="human",
    )
    packet_register = build_packet_register(
        role_assignment_register=role_register,
        packets=[
            {
                "packet_id": "packet-corpus-baseline",
                "packet_kind": "corpus_baseline",
                "review_state": "human_reviewed",
                "source_refs": [
                    "source_occurrence:so-baseline-primary",
                    "source_occurrence:so-baseline-supporting",
                ],
                "review_rationale": "Reviewed packet for baseline workflow evidence.",
            }
        ],
        register_id="packet-register-corpus",
        created_at=NOW,
        reviewed_by_actor_id="human:pm",
        reviewed_by_actor_type="human",
    )
    return inventory, occurrence_register, role_register, packet_register


def _outputs(connection: sqlite3.Connection) -> dict[str, object]:
    inventory, occurrence_register, role_register, packet_register = _chain(connection)
    return build_corpus_baseline_workflow_outputs(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        workflow_id="corpus-baseline-workflow-001",
        created_at=NOW,
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
        source_inventory=inventory,
        source_occurrence_register=occurrence_register,
        role_assignment_register=role_register,
        packet_register=packet_register,
        handoff_manifest_ref="handoff:corpus-baseline",
    )


def test_corpus_baseline_workflow_composes_valid_chain_and_generated_artifacts() -> None:
    connection = _connection()
    try:
        outputs = _outputs(connection)

        assert outputs["schema_version"] == CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION
        assert outputs["activation_posture"] == CORPUS_BASELINE_ACTIVATION_POSTURE
        assert outputs["summary"] == {
            "descriptor_count": 2,
            "source_occurrence_count": 2,
            "role_assignment_count": 2,
            "packet_count": 1,
        }
        assert outputs["validator_result"]["valid"] is True  # type: ignore[index]
        assert outputs["validator_result"]["promotable"] is False  # type: ignore[index]
        assert {
            artifact["file_name"] for artifact in outputs["generated_artifacts"]  # type: ignore[index]
        } == {
            "capex.role_assignment_register.v1.json",
            "capex.packet_register.v1.json",
        }
        assert corpus_baseline_workflow_digest(outputs).startswith("sha256:")
    finally:
        connection.close()


def test_corpus_baseline_workflow_requires_role_and_packet_prerequisites() -> None:
    connection = _connection()
    try:
        inventory, occurrence_register, role_register, packet_register = _chain(connection)
        empty_role = dict(role_register)
        empty_role["row_count"] = 0

        with pytest.raises(CorpusBaselineWorkflowError) as role_exc:
            build_corpus_baseline_workflow_outputs(
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                workflow_id="corpus-baseline-workflow-001",
                created_at=NOW,
                created_by_actor_id="human:pm",
                created_by_actor_type="human",
                source_inventory=inventory,
                source_occurrence_register=occurrence_register,
                role_assignment_register=empty_role,
                packet_register=packet_register,
                handoff_manifest_ref="handoff:corpus-baseline",
            )
        assert role_exc.value.code == "corpus_baseline_role_register_empty"

        empty_packet = dict(packet_register)
        empty_packet["packet_count"] = 0
        with pytest.raises(CorpusBaselineWorkflowError) as packet_exc:
            build_corpus_baseline_workflow_outputs(
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                workflow_id="corpus-baseline-workflow-001",
                created_at=NOW,
                created_by_actor_id="human:pm",
                created_by_actor_type="human",
                source_inventory=inventory,
                source_occurrence_register=occurrence_register,
                role_assignment_register=role_register,
                packet_register=empty_packet,
                handoff_manifest_ref="handoff:corpus-baseline",
            )
        assert packet_exc.value.code == "corpus_baseline_packet_register_empty"
    finally:
        connection.close()


def test_corpus_baseline_workflow_fails_closed_on_scope_mismatch() -> None:
    connection = _connection()
    try:
        inventory, occurrence_register, role_register, packet_register = _chain(connection)
        mismatched_packet = dict(packet_register)
        mismatched_packet["project_id"] = "other-project"

        with pytest.raises(CorpusBaselineWorkflowError) as exc_info:
            build_corpus_baseline_workflow_outputs(
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                workflow_id="corpus-baseline-workflow-001",
                created_at=NOW,
                created_by_actor_id="human:pm",
                created_by_actor_type="human",
                source_inventory=inventory,
                source_occurrence_register=occurrence_register,
                role_assignment_register=role_register,
                packet_register=mismatched_packet,
                handoff_manifest_ref="handoff:corpus-baseline",
            )
        assert exc_info.value.code == "corpus_baseline_scope_mismatch"
    finally:
        connection.close()


def test_corpus_baseline_workflow_has_no_activation_or_official_truth_effects() -> None:
    connection = _connection()
    try:
        outputs = _outputs(connection)

        assert set(outputs["cannot_be_used_for"]) >= {  # type: ignore[arg-type]
            "authored_workflow_pack_activation",
            "workflow_run_creation",
            "public_route_activation",
            "frontend_route_activation",
            "raw_corpus_import",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        }
        assert outputs["truth_effects"] == {
            "creates_workflow_run": False,
            "creates_reviewed_baseline": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        }
    finally:
        connection.close()
