from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers._shared.runtime_effects import (
    create_or_reuse_edge_execution_effects,
    create_or_validate_workflow_artifact_input_effects,
    resolve_or_create_workflow_run_effects,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_versions import create_artifact_version
from onetruth.infrastructure.repositories.workflow_runs import create_workflow_run


NOW = "2026-06-02T10:00:00Z"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _seed_run(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str = "weekly_schedule_planning.v1",
    partition_key: str = "PW-2026-W10",
    activation_key: str = "weekly_schedule_planning.v1:PW-2026-W10",
) -> None:
    create_workflow_run(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=workflow_id,
        workflow_version="v1",
        tenant_id="tenant-a",
        domain_id="domain-x",
        partition_key=partition_key,
        logical_date="2026-03-02",
        activation_key=activation_key,
        state="OPEN",
        created_at=NOW,
    )


def _seed_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    workflow_run_id: str,
    artifact_kind: str = "planning.seed.workbook",
) -> None:
    create_artifact_version(
        connection,
        artifact_version_id=artifact_version_id,
        workflow_run_id=workflow_run_id,
        tenant_id="tenant-a",
        domain_id="domain-x",
        dataset_key=artifact_kind,
        partition_kind="PlanningWeekID",
        partition_key="PW-2026-W10",
        task_run_id=None,
        artifact_kind=artifact_kind,
        artifact_role="official_input",
        media_type="application/octet-stream",
        storage_uri=f"inmem://test/{artifact_version_id}",
        content_digest=f"sha256:{artifact_version_id}",
        byte_size=None,
        metadata_json={},
        parent_artifact_version_id=None,
        supersedes_artifact_version_id=None,
        lineage_note=None,
        created_at=NOW,
    )


def test_resolve_or_create_workflow_run_creates_and_reuses_matching_activation_key() -> None:
    connection = _connection()

    created = resolve_or_create_workflow_run_effects(
        connection,
        workflow_run_id="wr-created",
        workflow_id="weekly_schedule_planning.v1",
        tenant_id="tenant-a",
        domain_id="domain-x",
        partition_kind="PlanningWeekID",
        partition_key="PW-2026-W10",
        logical_date="2026-03-02",
        activation_key="weekly_schedule_planning.v1:PW-2026-W10",
        created_at=NOW,
    )
    replay = resolve_or_create_workflow_run_effects(
        connection,
        workflow_run_id="wr-ignored",
        workflow_id="weekly_schedule_planning.v1",
        tenant_id="tenant-a",
        domain_id="domain-x",
        partition_kind="PlanningWeekID",
        partition_key="PW-2026-W10",
        logical_date="2026-03-02",
        activation_key="weekly_schedule_planning.v1:PW-2026-W10",
        created_at=NOW,
    )

    assert created["workflow_run_id"] == "wr-created"
    assert replay["workflow_run_id"] == "wr-created"


def test_resolve_or_create_workflow_run_rejects_activation_key_drift() -> None:
    connection = _connection()
    _seed_run(connection, workflow_run_id="wr-existing", activation_key="activation:old")

    with pytest.raises(CommandError) as exc_info:
        resolve_or_create_workflow_run_effects(
            connection,
            workflow_id="weekly_schedule_planning.v1",
            tenant_id="tenant-a",
            domain_id="domain-x",
            partition_kind="PlanningWeekID",
            partition_key="PW-2026-W10",
            logical_date="2026-03-02",
            activation_key="activation:new",
            created_at=NOW,
        )

    assert exc_info.value.code == "activation_key_drift_detected"
    assert exc_info.value.details["existing_workflow_run_ids"] == ["wr-existing"]


def test_workflow_artifact_input_helper_creates_replays_conflicts_and_replaces() -> None:
    connection = _connection()
    _seed_run(connection, workflow_run_id="wr-inputs")
    _seed_artifact(connection, workflow_run_id="wr-inputs", artifact_version_id="av-one")
    _seed_artifact(connection, workflow_run_id="wr-inputs", artifact_version_id="av-two")

    created = create_or_validate_workflow_artifact_input_effects(
        connection,
        workflow_run_id="wr-inputs",
        binding_key="stage01.seed",
        source_ref="av-one",
        artifact_version_id="av-one",
        metadata_json={"source": "first"},
        captured_at=NOW,
    )
    replay = create_or_validate_workflow_artifact_input_effects(
        connection,
        workflow_run_id="wr-inputs",
        binding_key="stage01.seed",
        source_ref="av-one",
        artifact_version_id="av-one",
        metadata_json={"source": "first"},
        captured_at=NOW,
    )

    assert created["effect"] == "created"
    assert replay["effect"] == "replay"

    with pytest.raises(CommandError) as exc_info:
        create_or_validate_workflow_artifact_input_effects(
            connection,
            workflow_run_id="wr-inputs",
            binding_key="stage01.seed",
            source_ref="av-two",
            artifact_version_id="av-two",
            metadata_json={"source": "second"},
            captured_at=NOW,
        )
    assert exc_info.value.code == "workflow_input_binding_conflict"

    replaced = create_or_validate_workflow_artifact_input_effects(
        connection,
        workflow_run_id="wr-inputs",
        binding_key="stage01.seed",
        source_ref="av-two",
        artifact_version_id="av-two",
        metadata_json={"source": "second"},
        captured_at=NOW,
        replace_on_conflict=True,
    )

    assert replaced["effect"] == "replaced"
    assert replaced["binding"]["artifact_version_id"] == "av-two"
    assert replaced["binding"]["metadata_json"] == {"source": "second"}


def _edge_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "edge_execution_id": "ee-one",
        "edge_id": "weekly_seed_to_live_dispatch",
        "source_workflow_run_id": "wr-source",
        "source_stage_id": "Stage07",
        "source_artifact_version_id": "av-seed",
        "source_activation_key": "weekly_schedule_planning.v1:PW-2026-W10",
        "target_workflow_id": "live_dispatch.v1",
        "target_stage_id": "Stage01",
        "target_partition_kind": "ServiceDateID",
        "target_partition_key": "SD-2026-03-06",
        "target_activation_key": "live_dispatch.v1:SD-2026-03-06",
        "correlation_key": "corr-one",
        "materialize_idempotency_key": "idem:first",
        "status": "prepared",
        "cursor_state": {"phase": "prepared"},
        "compensation_state": {"mode": "mark_stale", "state": "none"},
        "input_bindings": {"seed_artifact_version_id": "av-seed"},
        "trigger_ref": None,
        "seed_artifact_version_id": "av-seed",
        "target_workflow_run_id": None,
        "activated_at": None,
        "created_at": NOW,
    }
    kwargs.update(overrides)
    return kwargs


def test_edge_execution_helper_reuses_correlation_and_rejects_replay_drift() -> None:
    connection = _connection()
    _seed_run(connection, workflow_run_id="wr-source")
    _seed_artifact(connection, workflow_run_id="wr-source", artifact_version_id="av-seed")

    created = create_or_reuse_edge_execution_effects(connection, **_edge_kwargs())
    replay = create_or_reuse_edge_execution_effects(
        connection,
        **_edge_kwargs(
            edge_execution_id="ee-ignored",
            materialize_idempotency_key="idem:retry",
        ),
    )

    assert created["edge_execution_id"] == "ee-one"
    assert replay["edge_execution_id"] == "ee-one"

    with pytest.raises(CommandError) as exc_info:
        create_or_reuse_edge_execution_effects(
            connection,
            **_edge_kwargs(
                edge_execution_id="ee-conflict",
                target_activation_key="live_dispatch.v1:SD-2026-03-06:drift",
            ),
        )

    assert exc_info.value.code == "edge_execution_replay_conflict"
    assert "target_activation_key" in exc_info.value.details["mismatches"]
