from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_missing_information_branch.yaml"
)

EXPECTED_KEYS = {
    "flag_id",
    "workflow_run_id",
    "tenant_id",
    "domain_id",
    "workflow_id",
    "partition_key",
    "kind",
    "severity",
    "state",
    "summary",
    "details_json",
    "assigned_group",
    "created_at",
    "closed_at",
    "created_by_actor_id",
    "created_by_actor_type",
    "source_event_id",
    "dedupe_key",
    "updated_at",
}


def _api_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager"],
    )


def test_flag_list_contract_filters_and_detail(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_flag")
    flag_id = created["flag"]["flag_id"]

    client = _api_client(harness)
    listed = client.get(
        "/api/v1/flags",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert listed.status_code == 200
    assert listed.payload["status"] == "ok"
    rows = listed.payload["flags"]
    assert len(rows) == 1
    assert set(rows[0].keys()) == EXPECTED_KEYS
    assert rows[0]["flag_id"] == flag_id
    assert rows[0]["state"] == "open"

    detail = client.get(f"/api/v1/flags/{flag_id}")
    assert detail.status_code == 200
    assert detail.payload["status"] == "ok"
    assert detail.payload["command"] == "api.flags.detail"
    assert set(detail.payload["flag"].keys()) == EXPECTED_KEYS
    assert detail.payload["flag"]["summary"] == "Vehicle V-42 became unavailable"

    filtered = client.get(
        "/api/v1/flags",
        query={
            "workflow_run_id": harness.workflow_run_id,
            "state": "open",
            "kind": "vehicle_issue",
            "severity": "medium",
        },
    )
    assert filtered.status_code == 200
    assert len(filtered.payload["flags"]) == 1

    filtered_none = client.get(
        "/api/v1/flags",
        query={"workflow_run_id": harness.workflow_run_id, "state": "closed"},
    )
    assert filtered_none.status_code == 200
    assert filtered_none.payload["flags"] == []
