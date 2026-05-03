from __future__ import annotations

import base64
import json
from pathlib import Path
import sqlite3

from onetruth.application.services.logistics_local_demo import (
    UPLOAD_PACK_ROOT,
    seed_weekly_first_logistics_local_demo,
)
from onetruth.application.services.logistics_weekly_agent_pilot import (
    _APPROVED_AVAILABILITY_METADATA,
    _DRIVER_CAPABILITIES_METADATA,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from tests.runtime.api.test_weekly_stage04_openai_agent_api import (
    _mock_stage04_runner,
)
from tests.runtime.helpers.dispatch_reporting import (
    SUPPORTED_REPORTING_WORKBOOK_PATH,
    XLSX_MEDIA_TYPE,
    reporting_workbook_upload_metadata,
)
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import run_cli


def _query_rows(db_path: Path, sql: str, params: tuple[object, ...] = ()) -> list[dict[str, object]]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _client(*, db_url: str) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-logistics",
        domain_id="domain-hub",
        actor_id="human:demo-operator",
        actor_type="human",
        actor_roles=["schedule_planner", "dispatch_supervisor", "operations_manager"],
    )


def _upload_pack_json(relative_path: str) -> dict[str, object]:
    return json.loads((UPLOAD_PACK_ROOT / relative_path).read_text(encoding="utf-8"))


def _claim_human_task(client: RuntimeApiClient, human_task_id: str, *, idempotency_key: str) -> None:
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": idempotency_key},
    )
    assert claimed.status_code == 200, claimed.payload


def _upload_json_artifact(
    client: RuntimeApiClient,
    *,
    human_task_id: str,
    artifact_kind: str,
    artifact_role: str,
    metadata_json: dict[str, object],
    idempotency_key: str,
) -> dict[str, object]:
    content = json.dumps(metadata_json, separators=(",", ":"), sort_keys=True).encode("utf-8")
    uploaded = client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": artifact_kind,
            "artifact_role": artifact_role,
            "media_type": "application/json",
            "file_name": f"{artifact_kind}.json",
            "metadata_json": metadata_json,
            "content_base64": base64.b64encode(content).decode("ascii"),
            "idempotency_key": idempotency_key,
        },
    )
    assert uploaded.status_code == 200, uploaded.payload
    return uploaded.payload["artifact_version"]


def _upload_binary_artifact(
    client: RuntimeApiClient,
    *,
    human_task_id: str,
    artifact_kind: str,
    artifact_role: str,
    content: bytes,
    file_name: str,
    media_type: str,
    metadata_json: dict[str, object],
    idempotency_key: str,
) -> dict[str, object]:
    uploaded = client.post(
        f"/api/v1/human-tasks/{human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": artifact_kind,
            "artifact_role": artifact_role,
            "media_type": media_type,
            "file_name": file_name,
            "metadata_json": metadata_json,
            "content_base64": base64.b64encode(content).decode("ascii"),
            "idempotency_key": idempotency_key,
        },
    )
    assert uploaded.status_code == 200, uploaded.payload
    return uploaded.payload["artifact_version"]


def _latest_artifact_id(db_path: Path, *, workflow_run_id: str, artifact_kind: str) -> str:
    rows = _query_rows(
        db_path,
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_kind = ?
        ORDER BY created_at DESC, artifact_version_id DESC
        LIMIT 1
        """,
        (workflow_run_id, artifact_kind),
    )
    assert rows, artifact_kind
    return str(rows[0]["artifact_version_id"])


def _latest_human_task_id(db_path: Path, *, workflow_run_id: str, task_kind: str) -> str:
    rows = _query_rows(
        db_path,
        """
        SELECT human_task_id
        FROM human_tasks
        WHERE workflow_run_id = ? AND task_kind = ?
        ORDER BY created_at DESC, human_task_id DESC
        LIMIT 1
        """,
        (workflow_run_id, task_kind),
    )
    assert rows, task_kind
    return str(rows[0]["human_task_id"])


def _latest_approval_id(db_path: Path, *, workflow_run_id: str, scope_ref: str) -> str:
    rows = _query_rows(
        db_path,
        """
        SELECT approval_id
        FROM approvals
        WHERE workflow_run_id = ? AND scope_ref = ?
        ORDER BY requested_at DESC, approval_id DESC
        LIMIT 1
        """,
        (workflow_run_id, scope_ref),
    )
    assert rows, scope_ref
    return str(rows[0]["approval_id"])


def test_weekly_first_local_demo_seed_smoke_path_walks_weekly_live_and_reporting_loops(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    artifact_root = tmp_path / "artifacts"

    run_cli("--db-url", db_url, "init-db")
    connection = open_sqlite_connection(db_url)
    try:
        seeded = seed_weekly_first_logistics_local_demo(
            connection,
            db_url=db_url,
            planning_week_id="PW-2026-W10",
            service_date_id="SD-2026-03-06",
        )
    finally:
        connection.close()

    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setattr(
        "onetruth.application.services.weekly_stage04_openai_agent.build_weekly_stage04_openai_agent_runner_from_env",
        lambda: _mock_stage04_runner(),
    )

    client = _client(db_url=db_url)
    weekly_run_id = str(seeded["weekly_run_id"])
    reporting_run_id = str(seeded["reporting_run_id"])
    weekly_intake_task_id = _latest_human_task_id(
        db_path,
        workflow_run_id=weekly_run_id,
        task_kind="weekly_input_intake",
    )
    _claim_human_task(
        client,
        weekly_intake_task_id,
        idempotency_key="api:local-demo:weekly-intake-claim",
    )
    route_slot_requirements = _upload_pack_json("weekly/weekly_route_slot_requirements.xlsx")
    for artifact_kind, payload in (
        ("planning.route_slot_requirements.workbook", route_slot_requirements),
        ("planning.approved_availability.workbook", _APPROVED_AVAILABILITY_METADATA),
        ("planning.driver_capabilities.workbook", _DRIVER_CAPABILITIES_METADATA),
    ):
        _upload_json_artifact(
            client,
            human_task_id=weekly_intake_task_id,
            artifact_kind=artifact_kind,
            artifact_role="official_input",
            metadata_json=dict(payload),
            idempotency_key=f"api:local-demo:weekly-upload:{artifact_kind}",
        )
    intake_complete = client.post(
        f"/api/v1/human-tasks/{weekly_intake_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:local-demo:weekly-intake-complete",
        },
    )
    assert intake_complete.status_code == 200, intake_complete.payload

    route_demand = client.get(
        f"/api/v1/workpages/workflow-runs/{weekly_run_id}/route-demand-v0"
    )
    assert route_demand.status_code == 200, route_demand.payload
    route_demand_payload = route_demand.payload
    day_cards = route_demand_payload["calculations"]["day_cards"]
    assert len(day_cards) == 14
    assert day_cards[0]["service_date"] == "2026-03-22"
    assert day_cards[-1]["service_date"] == "2026-04-04"
    assert route_demand_payload["workpage"]["summary"]["planning_week_id"] == "PW-2026-W13"
    assert route_demand_payload["workpage"]["summary"]["service_day_count"] == 7
    assert route_demand_payload["workpage"]["summary"]["planned_route_total"] == 134
    assert route_demand_payload["future_week_options"] == [
        {
            "option_id": "next_week",
            "label": "Week 2",
            "planning_week_id": "PW-2026-W14",
            "start_date": "2026-03-29",
            "end_date": "2026-04-04",
            "date_range_label": "2026-03-29 to 2026-04-04",
        }
    ]

    created_next_week = client.post(
        f"/api/v1/workpages/workflow-runs/{weekly_run_id}/route-demand-v0/next-week",
        payload={"idempotency_key": "api:local-demo:route-demand:add-next-week"},
    )
    assert created_next_week.status_code == 200, created_next_week.payload
    future_workflow_run_id = str(created_next_week.payload["created"]["workflow_run_id"])
    future_artifact_version_id = str(created_next_week.payload["created"]["artifact_version_id"])
    future_run_rows = _query_rows(
        db_path,
        """
        SELECT partition_key, logical_date
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (future_workflow_run_id,),
    )
    assert future_run_rows == [
        {
            "partition_key": "PW-2026-W14",
            "logical_date": "2026-03-30",
        }
    ]
    future_route_demand = client.get(
        f"/api/v1/workpages/workflow-runs/{future_workflow_run_id}/"
        f"route-demand-v0/artifacts/{future_artifact_version_id}"
    )
    assert future_route_demand.status_code == 200, future_route_demand.payload
    future_day_cards = future_route_demand.payload["calculations"]["day_cards"]
    assert len(future_day_cards) == 7
    assert future_day_cards[0]["service_date"] == "2026-03-29"
    assert future_day_cards[-1]["service_date"] == "2026-04-04"
    assert all(int(card["planned_route_count"]) == 0 for card in future_day_cards)

    weekly_build_task_id = str(intake_complete.payload["result"]["spawned_children"][0]["human_task_id"])

    _claim_human_task(
        client,
        weekly_build_task_id,
        idempotency_key="api:local-demo:weekly-build-claim",
    )
    stage04_run = client.post(
        f"/api/v1/human-tasks/{weekly_build_task_id}/weekly-stage04-openai-agent",
        payload={"idempotency_key": "api:local-demo:weekly-stage04-run"},
    )
    assert stage04_run.status_code == 200, stage04_run.payload
    build_complete = client.post(
        f"/api/v1/human-tasks/{weekly_build_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:local-demo:weekly-build-complete",
        },
    )
    assert build_complete.status_code == 200, build_complete.payload
    weekly_review_task_id = str(build_complete.payload["result"]["spawned_children"][0]["human_task_id"])

    _claim_human_task(
        client,
        weekly_review_task_id,
        idempotency_key="api:local-demo:weekly-review-claim",
    )
    weekly_draft_artifact_id = _latest_artifact_id(
        db_path,
        workflow_run_id=weekly_run_id,
        artifact_kind="planning.draft_weekly_schedule.workbook",
    )
    _upload_json_artifact(
        client,
        human_task_id=weekly_review_task_id,
        artifact_kind="planning.manager_review.doc",
        artifact_role="evidence",
        metadata_json={"status": "ready_for_publish"},
        idempotency_key="api:local-demo:weekly-manager-review-upload",
    )
    weekly_confirmed = client.post(
        f"/api/v1/human-tasks/{weekly_review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [weekly_draft_artifact_id],
            "idempotency_key": "api:local-demo:weekly-review-confirm",
        },
    )
    assert weekly_confirmed.status_code == 200, weekly_confirmed.payload
    weekly_review_complete = client.post(
        f"/api/v1/human-tasks/{weekly_review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:local-demo:weekly-review-complete",
        },
    )
    assert weekly_review_complete.status_code == 200, weekly_review_complete.payload
    weekly_approval_id = _latest_approval_id(db_path, workflow_run_id=weekly_run_id, scope_ref="Stage06")
    weekly_approved = client.post(
        f"/api/v1/approvals/{weekly_approval_id}/respond",
        payload={
            "response_kind": "approve",
            "idempotency_key": "api:local-demo:weekly-approval-approve",
        },
    )
    assert weekly_approved.status_code == 200, weekly_approved.payload
    weekly_published_artifact_id = _latest_artifact_id(
        db_path,
        workflow_run_id=weekly_run_id,
        artifact_kind="planning.published_weekly_schedule.workbook",
    )

    prepared = client.post(
        f"/api/v1/workflow-runs/{weekly_run_id}/prepare-live-dispatch-day",
        payload={
            "published_artifact_version_id": weekly_published_artifact_id,
            "service_date_id": "SD-2026-03-06",
            "idempotency_key": "api:local-demo:prepare-live-dispatch",
        },
    )
    assert prepared.status_code == 200, prepared.payload
    live_run_id = str(prepared.payload["result"]["target_workflow_run"]["workflow_run_id"])
    live_intake_task_id = str(prepared.payload["result"]["seed_intake_task"]["human_task_id"])

    _claim_human_task(
        client,
        live_intake_task_id,
        idempotency_key="api:local-demo:live-intake-claim",
    )
    _upload_json_artifact(
        client,
        human_task_id=live_intake_task_id,
        artifact_kind="dispatch.route_delta_intake.workbook",
        artifact_role="official_input",
        metadata_json={"rows": [{"route_id": "R-001", "delta": 1}]},
        idempotency_key="api:local-demo:live-route-delta-upload",
    )
    live_intake_complete = client.post(
        f"/api/v1/human-tasks/{live_intake_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:local-demo:live-intake-complete",
        },
    )
    assert live_intake_complete.status_code == 200, live_intake_complete.payload
    live_review_task_id = str(live_intake_complete.payload["result"]["spawned_children"][0]["human_task_id"])

    _claim_human_task(
        client,
        live_review_task_id,
        idempotency_key="api:local-demo:live-review-claim",
    )
    live_route_delta_artifact_id = _latest_artifact_id(
        db_path,
        workflow_run_id=live_run_id,
        artifact_kind="dispatch.route_delta_intake.workbook",
    )
    _upload_json_artifact(
        client,
        human_task_id=live_review_task_id,
        artifact_kind="dispatch.dispatcher_review.doc",
        artifact_role="evidence",
        metadata_json={"status": "reviewed_small_change"},
        idempotency_key="api:local-demo:live-review-doc-upload",
    )
    live_confirmed = client.post(
        f"/api/v1/human-tasks/{live_review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [live_route_delta_artifact_id],
            "idempotency_key": "api:local-demo:live-review-confirm",
        },
    )
    assert live_confirmed.status_code == 200, live_confirmed.payload
    live_review_complete = client.post(
        f"/api/v1/human-tasks/{live_review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:local-demo:live-review-complete",
        },
    )
    assert live_review_complete.status_code == 200, live_review_complete.payload
    _latest_artifact_id(
        db_path,
        workflow_run_id=live_run_id,
        artifact_kind="dispatch.official_replan_delta.workbook",
    )

    reporting_intake_task_id = _latest_human_task_id(
        db_path,
        workflow_run_id=reporting_run_id,
        task_kind="eos_input_intake",
    )
    _claim_human_task(
        client,
        reporting_intake_task_id,
        idempotency_key="api:local-demo:reporting-intake-claim",
    )
    _upload_binary_artifact(
        client,
        human_task_id=reporting_intake_task_id,
        artifact_kind="reporting.eos_raw.workbook",
        artifact_role="official_input",
        content=SUPPORTED_REPORTING_WORKBOOK_PATH.read_bytes(),
        file_name=SUPPORTED_REPORTING_WORKBOOK_PATH.name,
        media_type=XLSX_MEDIA_TYPE,
        metadata_json=reporting_workbook_upload_metadata("2026-03-06"),
        idempotency_key="api:local-demo:reporting-eos-upload",
    )
    reporting_intake_complete = client.post(
        f"/api/v1/human-tasks/{reporting_intake_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:local-demo:reporting-intake-complete",
        },
    )
    assert reporting_intake_complete.status_code == 200, reporting_intake_complete.payload
    reporting_review_task_id = str(
        reporting_intake_complete.payload["result"]["spawned_children"][0]["human_task_id"]
    )

    _claim_human_task(
        client,
        reporting_review_task_id,
        idempotency_key="api:local-demo:reporting-review-claim",
    )
    reporting_draft_artifact_id = _latest_artifact_id(
        db_path,
        workflow_run_id=reporting_run_id,
        artifact_kind="reporting.upd_draft.workbook",
    )
    _upload_json_artifact(
        client,
        human_task_id=reporting_review_task_id,
        artifact_kind="reporting.manager_review.doc",
        artifact_role="evidence",
        metadata_json={"status": "approved_for_finalize"},
        idempotency_key="api:local-demo:reporting-review-doc-upload",
    )
    reporting_confirmed = client.post(
        f"/api/v1/human-tasks/{reporting_review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [reporting_draft_artifact_id],
            "idempotency_key": "api:local-demo:reporting-review-confirm",
        },
    )
    assert reporting_confirmed.status_code == 200, reporting_confirmed.payload
    reporting_review_complete = client.post(
        f"/api/v1/human-tasks/{reporting_review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:local-demo:reporting-review-complete",
        },
    )
    assert reporting_review_complete.status_code == 200, reporting_review_complete.payload
    reporting_approval_id = _latest_approval_id(
        db_path,
        workflow_run_id=reporting_run_id,
        scope_ref="Stage04",
    )
    reporting_approved = client.post(
        f"/api/v1/approvals/{reporting_approval_id}/respond",
        payload={
            "response_kind": "approve",
            "idempotency_key": "api:local-demo:reporting-approval-approve",
        },
    )
    assert reporting_approved.status_code == 200, reporting_approved.payload

    _latest_artifact_id(
        db_path,
        workflow_run_id=reporting_run_id,
        artifact_kind="reporting.final_packet.workbook",
    )
    weekly_actual_hours_rows = _query_rows(
        db_path,
        """
        SELECT COUNT(*) AS artifact_count
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_kind = 'planning.actual_hours_snapshot.workbook'
        """,
        (weekly_run_id,),
    )
    assert int(weekly_actual_hours_rows[0]["artifact_count"]) >= 2
