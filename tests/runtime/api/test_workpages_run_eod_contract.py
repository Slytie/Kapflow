from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from onetruth.infrastructure.db.session import open_sqlite_connection
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.workpage_runs import (
    seed_actual_ops_weekly_schedule_run,
    seed_dispatch_reporting_workpage_run,
)


EXPECTED_SOURCE_DATASET_KEYS = [
    "reporting.eos_raw.workbook",
    "reporting.actuals_normalized.workbook",
    "reporting.upd_draft.workbook",
]

EXPECTED_VALIDATION_WARNINGS = [
    "This run-backed EOD landing is generated from canonical dispatch-reporting artifacts sourced from an intentionally partial 2026-03-16 example family.",
    "Workbook summary formulas were broken in the source material, so row-level actuals remain the primary truth for this projection.",
    "Create draft opens the immutable reporting workbook edit lane, and submit creates a new superseding workbook artifact version.",
]


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'runtime.db'}"


def _client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager", "dispatch_supervisor", "schedule_planner"],
    )


def _other_scope_client(tmp_path: Path) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-b",
        domain_id="domain-y",
        actor_id="human:ops-manager-9",
        actor_type="human",
        actor_roles=["operations_manager"],
    )


def test_eod_workflow_run_workpage_contract_returns_run_backed_landing_without_draft(
    tmp_path: Path,
) -> None:
    seed = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-eod:no-draft",
    )
    workflow_run_id = str(seed["workflow_run_id"])
    client = _client(tmp_path)

    response = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0")
    assert response.status_code == 200

    payload = response.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.workpages.workflow_run"
    assert "artifact_context" not in payload

    workpage = payload["workpage"]
    assert workpage["workpage_id"] == "eod-v0"
    assert workpage["version"] == 2
    assert workpage["title"] == "End-of-day report"
    assert workpage["mode"] == "example"
    assert workpage["workflow_id"] == "dispatch_reporting.v1"
    assert workpage["dataset_key"] == "reporting.upd_draft.workbook"
    assert workpage["source_artifact_version_id"] is None
    assert workpage["source_examples"] == {}
    assert workpage["summary"] == {
        "service_date": "2026-03-16",
        "station_code": "DVC4",
        "dsp_name": "QDCI",
        "total_routes_actual": 3,
        "packages_dispatched": 786,
        "actual_dispatched": 786,
        "packages_delivered": 783,
        "packages_returned": 3,
        "delivered_pct": 99.62,
        "return_pct": 0.38,
        "average_route_time": "9:47:00",
        "formula_integrity_warning": True,
        "warning_note": (
            "This EOD projection is built from canonical dispatch-reporting artifacts sourced from "
            "an intentionally partial 2026-03-16 QDCI / DVC4 example family. Row-level actuals "
            "remain the primary truth because the source workbook summary tabs contained broken "
            "formulas."
        ),
    }
    assert [section["kind"] for section in workpage["sections"]] == [
        "summary_cards",
        "note_panel",
        "table",
        "form",
        "checklist",
        "history_stub",
    ]
    assert workpage["validation"]["warnings"] == EXPECTED_VALIDATION_WARNINGS

    source = payload["source"]
    assert source["mode"] == "run_projection"
    assert source["primary_dataset_key"] == "reporting.upd_draft.workbook"
    assert source["source_dataset_keys"] == EXPECTED_SOURCE_DATASET_KEYS
    assert source["source_artifact_version_id"] is None
    assert source["source_refs"] == [
        f"/api/v1/artifacts/{seed['artifacts_by_kind']['reporting.eos_raw.workbook']['artifact_version_id']}",
        f"/api/v1/artifacts/{seed['artifacts_by_kind']['reporting.actuals_normalized.workbook']['artifact_version_id']}",
    ]

    freshness = payload["freshness"]
    assert freshness["source_kind"] == "workflow_run_projection"
    assert freshness["source_version"] == workflow_run_id
    assert freshness["generated_at"]

    run_context = payload["run_context"]
    assert run_context == {
        "workflow_run_id": workflow_run_id,
        "workflow_id": "dispatch_reporting.v1",
        "workflow_version": "v1",
        "partition_key": "SD-2026-03-16",
        "logical_date": "2026-03-16",
        "activation_key": "api:workpages:run-eod:no-draft:dispatch-reporting-workpage",
        "state": "OPEN",
    }
    assert payload["draft_resolution"] == {
        "state": "no_draft",
        "latest_artifact_version_id": None,
        "artifact_route": None,
        "open_action_ref": None,
        "create_action_ref": {
            "action_id": "workpage.eod-v0.create_draft",
            "workpage_kind": "eod-v0",
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": None,
            "subject": None,
        },
    }
    assert payload["artifact_history"] is None


def test_eod_workflow_run_workpage_contract_returns_latest_draft_resolution(
    tmp_path: Path,
) -> None:
    seed = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-eod:latest-draft",
    )
    workflow_run_id = str(seed["workflow_run_id"])
    client = _client(tmp_path)

    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={"idempotency_key": "api:workpages:run-eod:latest-draft:create"},
    )
    artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    response = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0")
    assert response.status_code == 200

    payload = response.payload
    assert payload["draft_resolution"] == {
        "state": "latest_draft_available",
        "latest_artifact_version_id": artifact_version_id,
        "artifact_route": (
            f"/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}"
        ),
        "open_action_ref": {
            "action_id": "workpage.eod-v0.open_latest_draft",
            "workpage_kind": "eod-v0",
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": artifact_version_id,
            "subject": None,
        },
        "create_action_ref": None,
    }
    assert payload["freshness"]["source_version"] == artifact_version_id
    assert payload["source"]["source_refs"] == [
        f"/api/v1/artifacts/{seed['artifacts_by_kind']['reporting.eos_raw.workbook']['artifact_version_id']}",
        f"/api/v1/artifacts/{seed['artifacts_by_kind']['reporting.actuals_normalized.workbook']['artifact_version_id']}",
        f"/api/v1/artifacts/{artifact_version_id}",
    ]
    assert payload["artifact_history"] is None


def test_eod_workflow_run_workpage_reads_are_stable_except_for_generated_at(
    tmp_path: Path,
) -> None:
    seed = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-eod:stable",
    )
    client = _client(tmp_path)
    path = f"/api/v1/workpages/workflow-runs/{seed['workflow_run_id']}/eod-v0"

    first = client.get(path)
    second = client.get(path)

    assert first.status_code == 200
    assert second.status_code == 200
    assert _without_generated_at(first.payload) == _without_generated_at(second.payload)


def test_create_workflow_run_eod_draft_returns_canonical_route_and_replays_idempotently(
    tmp_path: Path,
) -> None:
    seed = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-eod:create",
    )
    workflow_run_id = str(seed["workflow_run_id"])
    client = _client(tmp_path)
    path = f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts"

    first = client.post(
        path,
        payload={"idempotency_key": "api:workpages:run-eod:create"},
    )
    second = client.post(
        path,
        payload={"idempotency_key": "api:workpages:run-eod:create"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.payload == first.payload

    artifact_version_id = str(first.payload["draft"]["artifact_version_id"])
    assert first.payload["draft"] == {
        "workflow_run_id": workflow_run_id,
        "artifact_version_id": artifact_version_id,
        "route": f"/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}",
    }

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        artifact_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM artifact_versions
            WHERE workflow_run_id = ? AND artifact_kind = ?
            """,
            (workflow_run_id, "reporting.upd_draft.workbook"),
        ).fetchone()[0]
    assert artifact_count == 1


def test_eod_workflow_run_workpage_uses_latest_draft_after_submit(
    tmp_path: Path,
) -> None:
    seed = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-eod:latest-after-submit",
    )
    workflow_run_id = str(seed["workflow_run_id"])
    client = _client(tmp_path)

    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={"idempotency_key": "api:workpages:run-eod:latest-after-submit:create"},
    )
    base_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    submitted = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"eod-v0/artifacts/{base_artifact_version_id}/submit",
        payload={
            "form_values": {
                "dispatcher_comment": "Run-backed landing should reopen the latest draft.",
            },
            "checklist_values": [],
            "idempotency_key": "api:workpages:run-eod:latest-after-submit:submit",
        },
    )
    latest_artifact_version_id = str(submitted.payload["submitted"]["artifact_version_id"])

    landing = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0")
    assert landing.status_code == 200
    assert landing.payload["draft_resolution"] == {
        "state": "latest_draft_available",
        "latest_artifact_version_id": latest_artifact_version_id,
        "artifact_route": (
            f"/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{latest_artifact_version_id}"
        ),
        "open_action_ref": {
            "action_id": "workpage.eod-v0.open_latest_draft",
            "workpage_kind": "eod-v0",
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": latest_artifact_version_id,
            "subject": None,
        },
        "create_action_ref": None,
    }
    assert landing.payload["source"]["source_refs"][-1] == f"/api/v1/artifacts/{latest_artifact_version_id}"
    assert landing.payload["freshness"]["source_version"] == latest_artifact_version_id


def test_eod_workflow_run_workpage_unknown_kind_returns_404(tmp_path: Path) -> None:
    seed = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-eod:wrong-kind",
    )
    client = _client(tmp_path)

    response = client.get(
        f"/api/v1/workpages/workflow-runs/{seed['workflow_run_id']}/unknown-workpage"
    )
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "workpage_not_found"
    assert response.payload["error"]["details"] == {
        "workflow_run_id": seed["workflow_run_id"],
        "workpage_id": "unknown-workpage",
    }


def test_eod_workflow_run_workpage_rejects_non_reporting_run_for_get_and_post(
    tmp_path: Path,
) -> None:
    seed = seed_actual_ops_weekly_schedule_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-eod:wrong-workflow",
    )
    workflow_run_id = str(seed["workflow_run_id"])
    client = _client(tmp_path)

    get_response = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0")
    assert get_response.status_code == 404
    assert get_response.payload["error"]["code"] == "workpage_not_found"
    assert get_response.payload["error"]["details"] == {
        "workflow_run_id": workflow_run_id,
        "workpage_id": "eod-v0",
    }

    post_response = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={"idempotency_key": "api:workpages:run-eod:wrong-workflow:create"},
    )
    assert post_response.status_code == 404
    assert post_response.payload["error"]["code"] == "workpage_not_found"
    assert post_response.payload["error"]["details"] == {
        "workflow_run_id": workflow_run_id,
        "workpage_id": "eod-v0",
    }


def test_eod_workflow_run_workpage_cross_scope_is_hidden_for_get_and_post(
    tmp_path: Path,
) -> None:
    seed = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:run-eod:scope",
    )
    workflow_run_id = str(seed["workflow_run_id"])
    client = _other_scope_client(tmp_path)

    get_response = client.get(f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0")
    assert get_response.status_code == 404
    assert get_response.payload["error"]["code"] == "workflow_run_not_found"
    assert get_response.payload["error"]["details"] == {
        "workflow_run_id": workflow_run_id,
    }

    post_response = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={"idempotency_key": "api:workpages:run-eod:scope:create"},
    )
    assert post_response.status_code == 404
    assert post_response.payload["error"]["code"] == "workflow_run_not_found"
    assert post_response.payload["error"]["details"] == {
        "workflow_run_id": workflow_run_id,
    }


def _without_generated_at(payload: dict[str, object]) -> dict[str, object]:
    copied = deepcopy(payload)
    freshness = copied.get("freshness")
    assert isinstance(freshness, dict)
    freshness.pop("generated_at", None)
    return copied
