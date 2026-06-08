from __future__ import annotations

import sqlite3

import pytest

from onetruth.capex_platform.closure_governance import (
    ClosureDimensionInput,
    ClosureRecurrenceRule,
    ClosureRecurrenceRuleRegistry,
    create_closure_snapshot_from_evaluation,
    evaluate_closure_gate,
    grant_waiver,
    mark_stale_closure_snapshots_for_basis_refs,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_closure_governance import (
    get_closure_snapshot,
)
from onetruth.infrastructure.repositories.capex_projects import create_capex_project
from onetruth.infrastructure.repositories.capex_source_occurrences import (
    create_source_occurrence,
    source_ref_for_occurrence,
    upsert_content_identity,
)


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-alpha"
NOW = "2026-06-08T00:00:00Z"


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
        project_key="CAPEX-A",
        name="CAPEX A",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    return connection


def _source_ref(connection: sqlite3.Connection, source_occurrence_id: str) -> str:
    content_identity_id = upsert_content_identity(
        connection,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        digest_algorithm="sha256",
        content_digest=f"digest-{source_occurrence_id}",
        byte_size=128,
        media_type="application/json",
        canonicalization_profile="sanitized-fixture-manifest-v1",
        metadata_json={},
        created_at=NOW,
    )
    create_source_occurrence(
        connection,
        source_occurrence_id=source_occurrence_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        content_identity_id=content_identity_id,
        occurrence_kind="sanitized_fixture_manifest_entry",
        status="available",
        locator_json={"manifest_ref": "fixture-manifest:alpha", "entry_ref": source_occurrence_id},
        metadata_json={"raw_corpus_material": False},
        registered_by_actor_id="human:admin",
        registered_by_actor_type="human",
        created_at=NOW,
    )
    return source_ref_for_occurrence(source_occurrence_id)


def test_closure_vector_passes_only_when_all_required_dimensions_have_resolved_source_refs() -> None:
    connection = _connection()
    try:
        cost_source = _source_ref(connection, "so-cost")
        schedule_source = _source_ref(connection, "so-schedule")

        evaluation = evaluate_closure_gate(
            connection,
            closure_gate_evaluation_id="cge-pass",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            closure_target_kind="capex_packet",
            closure_target_ref="packet-1",
            dimensions=(
                ClosureDimensionInput("cost_basis", (cost_source,)),
                ClosureDimensionInput("schedule_basis", (schedule_source,)),
            ),
            created_by_actor_id="human:reviewer",
            created_by_actor_type="human",
            now_iso=NOW,
        )

        assert evaluation["result"] == "pass"
        assert [row["dimension_id"] for row in evaluation["missing_dimensions_json"]] == []
        assert {
            row["dimension_id"] for row in evaluation["satisfied_dimensions_json"]
        } == {"cost_basis", "schedule_basis"}
        assert evaluation["basis_version_vector_json"]["basis_refs"] == sorted(
            [cost_source, schedule_source]
        )

        snapshot = create_closure_snapshot_from_evaluation(
            connection,
            closure_snapshot_id="cs-pass",
            closure_gate_evaluation_id="cge-pass",
            created_by_actor_id="human:reviewer",
            created_by_actor_type="human",
            now_iso=NOW,
        )

        assert snapshot["state"] == "current"
        assert snapshot["result"] == "pass"
    finally:
        connection.close()


def test_absence_of_evidence_fails_and_cannot_create_closure_snapshot() -> None:
    connection = _connection()
    try:
        evaluation = evaluate_closure_gate(
            connection,
            closure_gate_evaluation_id="cge-missing",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            closure_target_kind="capex_packet",
            closure_target_ref="packet-1",
            dimensions=(ClosureDimensionInput("cost_basis"),),
            created_by_actor_id="human:reviewer",
            created_by_actor_type="human",
            now_iso=NOW,
        )

        assert evaluation["result"] == "fail"
        assert evaluation["missing_dimensions_json"] == [
            {"dimension_id": "cost_basis", "reason": "missing_source_refs"}
        ]

        with pytest.raises(ValueError, match="failed closure evaluation"):
            create_closure_snapshot_from_evaluation(
                connection,
                closure_snapshot_id="cs-missing",
                closure_gate_evaluation_id="cge-missing",
                created_by_actor_id="human:reviewer",
                created_by_actor_type="human",
                now_iso=NOW,
            )
    finally:
        connection.close()


def test_waiver_satisfies_dimension_without_turning_evaluation_into_pass() -> None:
    connection = _connection()
    try:
        waiver = grant_waiver(
            connection,
            waiver_id="waiver-cost",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            scope_kind="closure_dimension",
            scope_ref="cost_basis",
            reason="Residual risk accepted for pilot evidence only.",
            created_by_actor_id="human:admin",
            created_by_actor_type="human",
            now_iso=NOW,
        )

        evaluation = evaluate_closure_gate(
            connection,
            closure_gate_evaluation_id="cge-waiver",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            closure_target_kind="capex_packet",
            closure_target_ref="packet-1",
            dimensions=(ClosureDimensionInput("cost_basis", waiver_ids=("waiver-cost",)),),
            created_by_actor_id="human:reviewer",
            created_by_actor_type="human",
            now_iso=NOW,
        )

        assert waiver["state"] == "active"
        assert evaluation["result"] == "satisfied_by_waiver"
        assert evaluation["waiver_refs_json"] == [
            {
                "dimension_id": "cost_basis",
                "satisfied_by": "waiver",
                "waiver_id": "waiver-cost",
            }
        ]
        assert evaluation["result"] != "pass"
    finally:
        connection.close()


def test_recurrence_rule_registry_marks_current_snapshots_stale_on_basis_ref_change() -> None:
    connection = _connection()
    try:
        source_ref = _source_ref(connection, "so-cost")
        evaluate_closure_gate(
            connection,
            closure_gate_evaluation_id="cge-stale",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            closure_target_kind="capex_packet",
            closure_target_ref="packet-1",
            dimensions=(ClosureDimensionInput("cost_basis", (source_ref,)),),
            created_by_actor_id="human:reviewer",
            created_by_actor_type="human",
            now_iso=NOW,
        )
        create_closure_snapshot_from_evaluation(
            connection,
            closure_snapshot_id="cs-stale",
            closure_gate_evaluation_id="cge-stale",
            created_by_actor_id="human:reviewer",
            created_by_actor_type="human",
            now_iso=NOW,
        )

        stale_ids = mark_stale_closure_snapshots_for_basis_refs(
            connection,
            changed_basis_refs=(source_ref,),
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            now_iso="2026-06-08T01:00:00Z",
        )

        snapshot = get_closure_snapshot(connection, "cs-stale")
        assert stale_ids == ("cs-stale",)
        assert snapshot is not None
        assert snapshot["state"] == "stale"
        assert snapshot["stale_reason"] == f"basis_ref_changed:{source_ref}"

        with pytest.raises(ValueError, match="duplicate closure recurrence rule_id"):
            ClosureRecurrenceRuleRegistry(
                (
                    ClosureRecurrenceRule("duplicate", "basis_ref_changed"),
                    ClosureRecurrenceRule("duplicate", "waiver_lifecycle_changed"),
                )
            )
    finally:
        connection.close()
