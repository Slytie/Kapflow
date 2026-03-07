from __future__ import annotations

import json
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT, run_cli, stdout_json
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_STAGE06_PUBLISH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)


def _client(
    harness: RuntimeScenarioHarness,
    *,
    tenant_id: str = "tenant-a",
    domain_id: str = "domain-x",
    actor_id: str = "human:dispatch-supervisor-1",
    actor_roles: list[str] | None = None,
) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_id=actor_id,
        actor_type="human",
        actor_roles=actor_roles or ["dispatch_supervisor"],
    )


def test_pointer_list_endpoint_supports_canonical_filters_without_run_filter(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    harness.run_steps()

    workflow_run = stdout_json(
        run_cli(
            "--db-url",
            harness.db_url,
            "runs",
            "show",
            "--workflow-run-id",
            harness.workflow_run_id,
            "--json",
        )
    )["workflow_run"]

    client = _client(harness)
    result = client.get(
        "/api/v1/pointers",
        query={
            "dataset_key": "schedule.published_schedule.workbook",
            "partition_kind": "ScheduleDateID",
            "partition_key": str(workflow_run["partition_key"]),
        },
    )
    assert result.status_code == 200
    assert result.payload["status"] == "ok"
    assert result.payload["command"] == "api.pointers.list"
    pointers = result.payload["pointers"]
    assert len(pointers) == 1
    assert pointers[0]["pointer_key"] == "official:schedule.published_schedule.workbook"
    assert pointers[0]["pointer_id"]
    assert pointers[0]["dataset_key"] == "schedule.published_schedule.workbook"
    assert pointers[0]["partition_kind"] == "ScheduleDateID"
    assert pointers[0]["partition_key"] == str(workflow_run["partition_key"])


def test_pointer_list_endpoint_keeps_workflow_run_filter_as_compatibility_shape(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    harness.run_steps()

    client = _client(harness)
    result = client.get(
        "/api/v1/pointers",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert result.status_code == 200
    pointers = result.payload["pointers"]
    assert len(pointers) == 1
    assert pointers[0]["pointer_key"] == "official:schedule.published_schedule.workbook"
    assert pointers[0]["pointer_id"]


def test_pointer_list_workflow_run_filter_resolves_after_same_scope_cross_run_repoint(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    harness.run_steps()

    primary_run = stdout_json(
        run_cli(
            "--db-url",
            harness.db_url,
            "runs",
            "show",
            "--workflow-run-id",
            harness.workflow_run_id,
            "--json",
        )
    )["workflow_run"]

    sibling_run = stdout_json(
        run_cli(
            "--db-url",
            harness.db_url,
            "runs",
            "create",
            "--json",
            json.dumps(
                {
                    "workflow_id": "schedule_planning.v1",
                    "workflow_version": "v1",
                    "tenant_id": primary_run["tenant_id"],
                    "domain_id": primary_run["domain_id"],
                    "partition_key": primary_run["partition_key"],
                    "logical_date": primary_run.get("logical_date"),
                    "activation_key": "pointer-api-cross-run-sibling",
                    "idempotency_key": "pointer-api-cross-run-sibling-run",
                }
            ),
        )
    )["workflow_run"]
    sibling_artifact = stdout_json(
        run_cli(
            "--db-url",
            harness.db_url,
            "artifacts",
            "create-version",
            "--json",
            json.dumps(
                {
                    "workflow_run_id": sibling_run["workflow_run_id"],
                    "artifact_kind": "schedule.published_schedule.workbook",
                    "artifact_role": "official_output",
                    "media_type": "application/json",
                    "storage_uri": "s3://runtime/pointer-api-cross-run-sibling.json",
                    "content_digest": "sha256:pointer-api-cross-run-sibling",
                    "byte_size": 256,
                    "metadata_json": {"source": "pointer-api-contract-test"},
                    "idempotency_key": "pointer-api-cross-run-sibling-artifact",
                }
            ),
        )
    )["artifact_version"]
    run_cli(
        "--db-url",
        harness.db_url,
        "pointers",
        "promote",
        "--json",
        json.dumps(
            {
                "workflow_run_id": sibling_run["workflow_run_id"],
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "pointer_key": "official:schedule.published_schedule.workbook",
                "artifact_kind": "schedule.published_schedule.workbook",
                "artifact_version_id": sibling_artifact["artifact_version_id"],
                "promotion_reason": "manual_promote",
                "expected_generation": 0,
                "idempotency_key": "pointer-api-cross-run-repoint",
            }
        ),
    )

    client = _client(harness)
    response = client.get(
        "/api/v1/pointers",
        query={
            "workflow_run_id": harness.workflow_run_id,
            "pointer_key": "official:schedule.published_schedule.workbook",
        },
    )
    assert response.status_code == 200
    pointers = response.payload["pointers"]
    assert len(pointers) == 1
    assert pointers[0]["artifact_version_id"] == sibling_artifact["artifact_version_id"]
    assert pointers[0]["pointer_key"] == "official:schedule.published_schedule.workbook"
