from __future__ import annotations

import base64
from copy import deepcopy
from pathlib import Path
import sqlite3
import json

from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_actual_ops_weekly_stage04_fixture_payloads,
)
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import run_cli, stdout_json
from tests.runtime.helpers.workpage_runs import (
    seed_actual_ops_weekly_schedule_run_with_stage04_outputs,
    seed_actual_ops_weekly_schedule_run,
)


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'runtime.db'}"


def _query_rows(db_path: Path, sql: str, params: tuple[object, ...] = ()) -> list[dict[str, object]]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _client(
    *,
    db_url: str,
    actor_id: str,
    actor_roles: list[str],
) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id=actor_id,
        actor_type="human",
        actor_roles=actor_roles,
    )


def _create_weekly_run(db_url: str, *, run_tag: str) -> dict[str, object]:
    run_cli("--db-url", db_url, "init-db")
    created = run_cli(
        "--db-url",
        db_url,
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": "weekly_schedule_planning.v1",
                "workflow_version": "v1",
                "tenant_id": "tenant-a",
                "domain_id": "domain-x",
                "partition_key": "PW-2026-W13",
                "logical_date": "2026-03-22",
                "activation_key": f"{run_tag}:weekly-run",
                "idempotency_key": f"{run_tag}:runs.create",
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(created)["workflow_run"]


def _create_human_task(
    db_url: str,
    *,
    workflow_run_id: str,
    stage_id: str,
    task_kind: str,
    activation_key: str,
    actor_role: str = "schedule_planner",
) -> dict[str, object]:
    created = run_cli(
        "--db-url",
        db_url,
        "tasks",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "stage_id": stage_id,
                "task_kind": task_kind,
                "activation_key": activation_key,
                "create_human_task": True,
                "candidate_roles": [actor_role],
                "owner_role": actor_role,
                "idempotency_key": f"{activation_key}:tasks.create",
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(created)["result"]


def _create_artifact_version(
    db_url: str,
    *,
    workflow_run_id: str,
    artifact_kind: str,
    artifact_role: str,
    metadata_json: dict[str, object],
    idempotency_key: str,
) -> dict[str, object]:
    created = run_cli(
        "--db-url",
        db_url,
        "artifacts",
        "create-version",
        "--json",
        json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "artifact_kind": artifact_kind,
                "artifact_role": artifact_role,
                "media_type": "application/json",
                "storage_uri": f"inmem://artifacts/{workflow_run_id}/{artifact_kind}/{idempotency_key}",
                "content_digest": f"sha256:{idempotency_key}",
                "metadata_json": metadata_json,
                "idempotency_key": idempotency_key,
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(created)["artifact_version"]


def _update_artifact_metadata_json(
    db_path: Path,
    *,
    artifact_version_id: str,
    metadata_json: dict[str, object],
) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            """
            UPDATE artifact_versions
            SET metadata_json = ?
            WHERE artifact_version_id = ?
            """,
            (json.dumps(metadata_json, separators=(",", ":")), artifact_version_id),
        )
        connection.commit()
    finally:
        connection.close()


def _workspace_item(payload: dict[str, object], *, subject_kind: str, subject_id: str) -> dict[str, object]:
    for key in ("user_work", "blocking_work"):
        rows = payload.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("subject_kind") == subject_kind and row.get("subject_id") == subject_id:
                return row
    raise AssertionError(f"workspace item not found: {subject_kind}:{subject_id}")


def _schedule_submit_rows(
    client: RuntimeApiClient,
    artifact_version_id: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    payload = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}").payload
    sections = payload["workpage"]["sections"]
    assignment_section = next(
        section for section in sections if section.get("table_id") == "assignment_rows"
    )
    reserve_section = next(
        section for section in sections if section.get("table_id") == "reserve_rows"
    )
    return (
        deepcopy(assignment_section["rows"]),
        deepcopy(reserve_section["rows"]),
    )


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


def _claim_human_task(client: RuntimeApiClient, human_task_id: str, *, idempotency_key: str) -> None:
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": idempotency_key},
    )
    assert claimed.status_code == 200, claimed.payload


def _weekly_input_payloads() -> dict[str, dict[str, object]]:
    fixture_payloads = build_actual_ops_weekly_stage04_fixture_payloads()
    return {
        "planning.route_slot_requirements.workbook": dict(
            fixture_payloads["route_slot_requirements"]
        ),
        "planning.driver_capabilities.workbook": dict(fixture_payloads["driver_capabilities"]),
        "planning.approved_availability.workbook": dict(fixture_payloads["approved_availability"]),
        "planning.actual_hours_snapshot.workbook": dict(fixture_payloads["actual_hours"]),
    }


def test_weekly_input_intake_contract_uses_official_input_roles_and_blocks_completion(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    workflow_run = _create_weekly_run(db_url, run_tag="api:weekly-intake-contract")
    created = _create_human_task(
        db_url,
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        stage_id="Stage04",
        task_kind="weekly_input_intake",
        activation_key="api:weekly-intake-contract:stage04-intake",
    )
    human_task_id = str(created["human_task"]["human_task_id"])
    client = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-1",
        actor_roles=["schedule_planner"],
    )
    _claim_human_task(
        client,
        human_task_id,
        idempotency_key="api:weekly-intake-contract:claim",
    )

    workspace = client.get(f"/api/v1/workflow-runs/{workflow_run['workflow_run_id']}/workspace")
    assert workspace.status_code == 200
    item = _workspace_item(
        workspace.payload,
        subject_kind="human_task",
        subject_id=human_task_id,
    )
    required_uploads = item["required_uploads"]
    assert [upload["dataset_key"] for upload in required_uploads] == [
        "planning.route_slot_requirements.workbook",
        "planning.approved_availability.workbook",
        "planning.driver_capabilities.workbook",
        "planning.actual_hours_snapshot.workbook",
        "planning.route_horizon.doc",
        "planning.route_horizon.workbook",
    ]
    assert [upload["artifact_role"] for upload in required_uploads] == [
        "official_input",
        "official_input",
        "official_input",
        "official_input",
        "evidence",
        "evidence",
    ]
    assert [upload["required"] for upload in required_uploads] == [True, True, True, False, False, False]
    assert item["missing_required_inputs"] == [
        "planning.route_slot_requirements.workbook",
        "planning.approved_availability.workbook",
        "planning.driver_capabilities.workbook",
    ]
    assert "complete" not in item["available_actions"]

    denied = client.post(
        f"/api/v1/human-tasks/{human_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-intake-contract:complete",
        },
    )
    assert denied.status_code == 400
    assert denied.payload["error"]["code"] == "task_requirements_not_satisfied"


def test_weekly_input_intake_completion_spawns_stage04_build_and_exposes_run_action(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    workflow_run = _create_weekly_run(db_url, run_tag="api:weekly-intake-complete")
    created = _create_human_task(
        db_url,
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        stage_id="Stage04",
        task_kind="weekly_input_intake",
        activation_key="api:weekly-intake-complete:stage04-intake",
    )
    human_task_id = str(created["human_task"]["human_task_id"])
    client = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-2",
        actor_roles=["schedule_planner"],
    )
    _claim_human_task(
        client,
        human_task_id,
        idempotency_key="api:weekly-intake-complete:claim-intake",
    )

    payloads = _weekly_input_payloads()
    for artifact_kind in (
        "planning.route_slot_requirements.workbook",
        "planning.approved_availability.workbook",
        "planning.driver_capabilities.workbook",
    ):
        _upload_json_artifact(
            client,
            human_task_id=human_task_id,
            artifact_kind=artifact_kind,
            artifact_role="official_input",
            metadata_json=payloads[artifact_kind],
            idempotency_key=f"api:weekly-intake-complete:upload:{artifact_kind}",
        )

    completed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-intake-complete:complete-intake",
        },
    )
    assert completed.status_code == 200, completed.payload
    result = completed.payload["result"]
    assert result["task_run"]["state"] == "COMPLETED"
    assert len(result["spawned_children"]) == 1
    child = result["spawned_children"][0]
    assert child["stage_id"] == "Stage04"
    assert child["task_kind"] == "work_item"

    child_human_task_id = str(child["human_task_id"])
    _claim_human_task(
        client,
        child_human_task_id,
        idempotency_key="api:weekly-intake-complete:claim-build",
    )
    workspace = client.get(f"/api/v1/workflow-runs/{workflow_run['workflow_run_id']}/workspace")
    assert workspace.status_code == 200
    item = _workspace_item(
        workspace.payload,
        subject_kind="human_task",
        subject_id=child_human_task_id,
    )
    assert "run_weekly_stage04_openai_agent" in item["available_actions"]


def test_weekly_stage04_and_stage05_completion_fail_closed_without_required_draft_review_state(
    tmp_path: Path,
) -> None:
    stage04_db_url = f"sqlite:///{tmp_path / 'stage04-runtime.db'}"
    seeded_stage04 = seed_actual_ops_weekly_schedule_run(
        db_url=stage04_db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:weekly-stage04-missing-draft",
    )
    build_created = _create_human_task(
        stage04_db_url,
        workflow_run_id=str(seeded_stage04["workflow_run_id"]),
        stage_id="Stage04",
        task_kind="work_item",
        activation_key="api:weekly-stage04-missing-draft:build",
    )
    build_task_id = str(build_created["human_task"]["human_task_id"])
    planner_client = _client(
        db_url=stage04_db_url,
        actor_id="human:schedule-planner-3",
        actor_roles=["schedule_planner"],
    )
    _claim_human_task(
        planner_client,
        build_task_id,
        idempotency_key="api:weekly-stage04-missing-draft:claim",
    )

    denied_build = planner_client.post(
        f"/api/v1/human-tasks/{build_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-stage04-missing-draft:complete",
        },
    )
    assert denied_build.status_code == 400
    assert denied_build.payload["error"]["code"] == "task_requirements_not_satisfied"
    assert "required_artifact_missing:planning.draft_weekly_schedule.workbook" in (
        denied_build.payload["error"]["details"]["blocking_reason_codes"]
    )

    stage05_db_url = f"sqlite:///{tmp_path / 'stage05-runtime.db'}"
    stage05_run = _create_weekly_run(
        stage05_db_url,
        run_tag="api:weekly-stage05-missing-review",
    )
    _create_artifact_version(
        stage05_db_url,
        workflow_run_id=str(stage05_run["workflow_run_id"]),
        artifact_kind="planning.draft_weekly_schedule.workbook",
        artifact_role="draft_output",
        metadata_json={"columns": ["route_id"], "rows": [["R-001"]]},
        idempotency_key="api:weekly-stage05-missing-review:draft",
    )
    review_created = _create_human_task(
        stage05_db_url,
        workflow_run_id=str(stage05_run["workflow_run_id"]),
        stage_id="Stage05",
        task_kind="final_review",
        activation_key="api:weekly-stage05-missing-review:final-review",
    )
    review_task_id = str(review_created["human_task"]["human_task_id"])
    review_client = _client(
        db_url=stage05_db_url,
        actor_id="human:schedule-planner-4",
        actor_roles=["schedule_planner"],
    )
    _claim_human_task(
        review_client,
        review_task_id,
        idempotency_key="api:weekly-stage05-missing-review:claim",
    )

    denied_without_upload = review_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-stage05-missing-review:complete-no-upload",
        },
    )
    assert denied_without_upload.status_code == 400
    assert denied_without_upload.payload["error"]["code"] == "task_requirements_not_satisfied"
    assert "required_upload_missing:planning.manager_review.doc" in (
        denied_without_upload.payload["error"]["details"]["blocking_reason_codes"]
    )

    _upload_json_artifact(
        review_client,
        human_task_id=review_task_id,
        artifact_kind="planning.manager_review.doc",
        artifact_role="evidence",
        metadata_json={"review_status": "ready"},
        idempotency_key="api:weekly-stage05-missing-review:upload-manager-review",
    )
    denied_without_confirmation = review_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-stage05-missing-review:complete-no-confirmation",
        },
    )
    assert denied_without_confirmation.status_code == 400
    assert denied_without_confirmation.payload["error"]["code"] == "task_requirements_not_satisfied"
    assert "required_review_confirmation_missing:planning.draft_weekly_schedule.workbook" in (
        denied_without_confirmation.payload["error"]["details"]["blocking_reason_codes"]
    )


def test_weekly_publish_approval_auto_publishes_reviewed_latest_draft(tmp_path: Path) -> None:
    db_path = tmp_path / "happy-runtime.db"
    db_url = f"sqlite:///{db_path}"
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:weekly-happy",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    draft_artifact_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    build_created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage04",
        task_kind="work_item",
        activation_key="api:weekly-happy:stage04-build",
    )
    build_task_id = str(build_created["human_task"]["human_task_id"])
    planner_client = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-5",
        actor_roles=["schedule_planner"],
    )
    _claim_human_task(
        planner_client,
        build_task_id,
        idempotency_key="api:weekly-happy:claim-build",
    )
    build_completed = planner_client.post(
        f"/api/v1/human-tasks/{build_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-happy:complete-build",
        },
    )
    assert build_completed.status_code == 200, build_completed.payload
    review_task_id = str(build_completed.payload["result"]["spawned_children"][0]["human_task_id"])
    manager_client = _client(
        db_url=db_url,
        actor_id="human:operations-manager-1",
        actor_roles=["operations_manager"],
    )
    _claim_human_task(
        manager_client,
        review_task_id,
        idempotency_key="api:weekly-happy:claim-review",
    )

    review_workspace = manager_client.get(f"/api/v1/workflow-runs/{workflow_run_id}/workspace")
    review_item = _workspace_item(
        review_workspace.payload,
        subject_kind="human_task",
        subject_id=review_task_id,
    )
    assert review_item["workpage_actions"] == [
        {
            "action_id": "workpage.schedule-v0.open_latest_draft",
            "workpage_kind": "schedule-v0",
            "label": "Open schedule draft",
            "presentation": "open_route",
            "state": "available",
            "route": (
                f"/runs/{workflow_run_id}/workpages/schedule-v0/artifacts/{draft_artifact_id}"
            ),
            "create_path": None,
            "subject_context": {
                "subject_kind": "human_task",
                "subject_id": review_task_id,
                "workflow_run_id": workflow_run_id,
            },
            "link_policy": {
                "create_relation_kind": None,
                "submit_relation_kind": "response",
            },
            "disabled_reason": None,
        }
    ]

    assignment_rows, reserve_rows = _schedule_submit_rows(manager_client, draft_artifact_id)
    assignment_rows[0]["assigned_driver_id"] = "DRV-MANUAL-0152"
    assignment_rows[0]["assignment_status"] = "manual_override"
    submitted = manager_client.post(
        f"/api/v1/workpages/artifacts/{draft_artifact_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "subject_link": {
                "subject_kind": "human_task",
                "subject_id": review_task_id,
            },
            "idempotency_key": "api:weekly-happy:submit-draft",
        },
    )
    assert submitted.status_code == 200, submitted.payload
    latest_draft_artifact_id = str(submitted.payload["submitted"]["artifact_version_id"])

    _upload_json_artifact(
        manager_client,
        human_task_id=review_task_id,
        artifact_kind="planning.manager_review.doc",
        artifact_role="evidence",
        metadata_json={"review_status": "approved_for_publish"},
        idempotency_key="api:weekly-happy:upload-manager-review",
    )
    confirmed = manager_client.post(
        f"/api/v1/human-tasks/{review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [latest_draft_artifact_id],
            "idempotency_key": "api:weekly-happy:confirm-review",
        },
    )
    assert confirmed.status_code == 200, confirmed.payload

    review_completed = manager_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-happy:complete-review",
        },
    )
    assert review_completed.status_code == 200, review_completed.payload
    requested_approvals = review_completed.payload["result"]["requested_approvals"]
    assert len(requested_approvals) == 1
    approval_id = str(requested_approvals[0]["approval_id"])

    approved = manager_client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "response_reason": "publish the reviewed weekly schedule",
            "idempotency_key": "api:weekly-happy:approve-publish",
        },
    )
    assert approved.status_code == 200, approved.payload

    artifacts = _query_rows(
        db_path,
        """
        SELECT artifact_kind, artifact_role
        FROM artifact_versions
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC
        """,
        (workflow_run_id,),
    )
    artifact_kinds = [str(row["artifact_kind"]) for row in artifacts]
    assert "planning.publish_packet.doc" in artifact_kinds
    assert "planning.published_weekly_schedule.workbook" in artifact_kinds
    assert not any(kind.startswith("planning.daily_dispatch_seed.") for kind in artifact_kinds)

    pointer_rows = _query_rows(
        db_path,
        """
        SELECT pointer_key, artifact_kind, promotion_reason, approved_by_approval_id
        FROM artifact_pointers
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    )
    assert pointer_rows == [
        {
            "pointer_key": "official:planning.published_weekly_schedule.workbook",
            "artifact_kind": "planning.published_weekly_schedule.workbook",
            "promotion_reason": "official_publish",
            "approved_by_approval_id": approval_id,
        }
    ]

    events = _query_rows(
        db_path,
        """
        SELECT event_type
        FROM timeline_events
        WHERE workflow_run_id = ?
        ORDER BY sequence_no ASC
        """,
        (workflow_run_id,),
    )
    assert any(str(row["event_type"]) == "artifact.pointer.promoted" for row in events)

    workspace = manager_client.get(f"/api/v1/workflow-runs/{workflow_run_id}/workspace")
    assert workspace.status_code == 200
    assert any(
        output["artifact_version"]["artifact_kind"] == "planning.published_weekly_schedule.workbook"
        for output in workspace.payload["official_outputs"]["outputs"]
        if isinstance(output.get("artifact_version"), dict)
    )


def test_weekly_publish_approval_fails_closed_when_reviewed_draft_is_stale(tmp_path: Path) -> None:
    db_path = tmp_path / "stale-runtime.db"
    db_url = f"sqlite:///{db_path}"
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:weekly-stale-publish",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    initial_draft_artifact_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage05",
        task_kind="final_review",
        activation_key="api:weekly-stale-publish:final-review",
    )
    review_task_id = str(created["human_task"]["human_task_id"])
    planner_client = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-6",
        actor_roles=["schedule_planner"],
    )
    _claim_human_task(
        planner_client,
        review_task_id,
        idempotency_key="api:weekly-stale-publish:claim-review",
    )

    _upload_json_artifact(
        planner_client,
        human_task_id=review_task_id,
        artifact_kind="planning.manager_review.doc",
        artifact_role="evidence",
        metadata_json={"review_status": "approved_pending_publish"},
        idempotency_key="api:weekly-stale-publish:upload-manager-review",
    )
    confirmed = planner_client.post(
        f"/api/v1/human-tasks/{review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [initial_draft_artifact_id],
            "idempotency_key": "api:weekly-stale-publish:confirm-review-initial",
        },
    )
    assert confirmed.status_code == 200, confirmed.payload

    review_completed = planner_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-stale-publish:complete-review",
        },
    )
    assert review_completed.status_code == 200, review_completed.payload
    approval_id = str(review_completed.payload["result"]["requested_approvals"][0]["approval_id"])

    assignment_rows, reserve_rows = _schedule_submit_rows(planner_client, initial_draft_artifact_id)
    assignment_rows[0]["assigned_driver_id"] = "DRV-STALE-0152"
    assignment_rows[0]["assignment_status"] = "manual_override"
    submitted = planner_client.post(
        f"/api/v1/workpages/artifacts/{initial_draft_artifact_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "subject_link": {
                "subject_kind": "approval",
                "subject_id": approval_id,
            },
            "idempotency_key": "api:weekly-stale-publish:submit-late-draft",
        },
    )
    assert submitted.status_code == 200, submitted.payload

    manager_client = _client(
        db_url=db_url,
        actor_id="human:operations-manager-2",
        actor_roles=["operations_manager"],
    )
    denied = manager_client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "response_reason": "attempt publish after a newer draft appeared",
            "idempotency_key": "api:weekly-stale-publish:approve",
        },
    )
    assert denied.status_code == 400
    assert denied.payload["error"]["code"] == "stable_base_schedule_required"

    approvals = _query_rows(
        db_path,
        """
        SELECT state, response_kind
        FROM approvals
        WHERE approval_id = ?
        """,
        (approval_id,),
    )
    assert approvals == [{"state": "PENDING", "response_kind": None}]

    artifacts = _query_rows(
        db_path,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC
        """,
        (workflow_run_id,),
    )
    artifact_kinds = [str(row["artifact_kind"]) for row in artifacts]
    assert "planning.publish_packet.doc" not in artifact_kinds
    assert "planning.published_weekly_schedule.workbook" not in artifact_kinds

    pointers = _query_rows(
        db_path,
        """
        SELECT pointer_key
        FROM artifact_pointers
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    )
    assert pointers == []


def test_weekly_publish_approval_fails_closed_when_reviewed_draft_dependencies_drift(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "dependency-drift-runtime.db"
    db_url = f"sqlite:///{db_path}"
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:weekly-drifted-publish",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    initial_draft_artifact_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    route_requirements_artifact = seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage05",
        task_kind="final_review",
        activation_key="api:weekly-drifted-publish:final-review",
    )
    review_task_id = str(created["human_task"]["human_task_id"])
    planner_client = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-7",
        actor_roles=["schedule_planner"],
    )
    _claim_human_task(
        planner_client,
        review_task_id,
        idempotency_key="api:weekly-drifted-publish:claim-review",
    )

    _upload_json_artifact(
        planner_client,
        human_task_id=review_task_id,
        artifact_kind="planning.manager_review.doc",
        artifact_role="evidence",
        metadata_json={"review_status": "approved_pending_publish"},
        idempotency_key="api:weekly-drifted-publish:upload-manager-review",
    )
    confirmed = planner_client.post(
        f"/api/v1/human-tasks/{review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [initial_draft_artifact_id],
            "idempotency_key": "api:weekly-drifted-publish:confirm-review",
        },
    )
    assert confirmed.status_code == 200, confirmed.payload

    review_completed = planner_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-drifted-publish:complete-review",
        },
    )
    assert review_completed.status_code == 200, review_completed.payload
    approval_id = str(review_completed.payload["result"]["requested_approvals"][0]["approval_id"])

    _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="planning.route_slot_requirements.workbook",
        artifact_role="official_input",
        metadata_json=dict(route_requirements_artifact["metadata_json"]),
        idempotency_key="api:weekly-drifted-publish:new-route-requirements",
    )

    manager_client = _client(
        db_url=db_url,
        actor_id="human:operations-manager-3",
        actor_roles=["operations_manager"],
    )
    denied = manager_client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "response_reason": "attempt publish after route demand drifted",
            "idempotency_key": "api:weekly-drifted-publish:approve",
        },
    )
    assert denied.status_code == 400
    assert denied.payload["error"]["code"] == "dependency_drift_detected"

    approvals = _query_rows(
        db_path,
        """
        SELECT state, response_kind
        FROM approvals
        WHERE approval_id = ?
        """,
        (approval_id,),
    )
    assert approvals == [{"state": "PENDING", "response_kind": None}]

    artifacts = _query_rows(
        db_path,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC
        """,
        (workflow_run_id,),
    )
    artifact_kinds = [str(row["artifact_kind"]) for row in artifacts]
    assert "planning.publish_packet.doc" not in artifact_kinds
    assert "planning.published_weekly_schedule.workbook" not in artifact_kinds

    pointers = _query_rows(
        db_path,
        """
        SELECT pointer_key
        FROM artifact_pointers
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    )
    assert pointers == []


def test_weekly_publish_approval_fails_closed_when_reviewed_draft_has_no_pinned_baseline(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "baseline-missing-runtime.db"
    db_url = f"sqlite:///{db_path}"
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:weekly-baseline-missing-publish",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    initial_draft_artifact_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    draft_rows = _query_rows(
        db_path,
        """
        SELECT metadata_json
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (initial_draft_artifact_id,),
    )
    draft_metadata = json.loads(str(draft_rows[0]["metadata_json"]))
    draft_metadata.pop("dependency_manifest", None)
    _update_artifact_metadata_json(
        db_path,
        artifact_version_id=initial_draft_artifact_id,
        metadata_json=draft_metadata,
    )
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage05",
        task_kind="final_review",
        activation_key="api:weekly-baseline-missing-publish:final-review",
    )
    review_task_id = str(created["human_task"]["human_task_id"])
    planner_client = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-8",
        actor_roles=["schedule_planner"],
    )
    _claim_human_task(
        planner_client,
        review_task_id,
        idempotency_key="api:weekly-baseline-missing-publish:claim-review",
    )

    _upload_json_artifact(
        planner_client,
        human_task_id=review_task_id,
        artifact_kind="planning.manager_review.doc",
        artifact_role="evidence",
        metadata_json={"review_status": "approved_pending_publish"},
        idempotency_key="api:weekly-baseline-missing-publish:upload-manager-review",
    )
    confirmed = planner_client.post(
        f"/api/v1/human-tasks/{review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [initial_draft_artifact_id],
            "idempotency_key": "api:weekly-baseline-missing-publish:confirm-review",
        },
    )
    assert confirmed.status_code == 200, confirmed.payload

    review_completed = planner_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:weekly-baseline-missing-publish:complete-review",
        },
    )
    assert review_completed.status_code == 200, review_completed.payload
    approval_id = str(review_completed.payload["result"]["requested_approvals"][0]["approval_id"])

    manager_client = _client(
        db_url=db_url,
        actor_id="human:operations-manager-4",
        actor_roles=["operations_manager"],
    )
    denied = manager_client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "response_reason": "attempt publish with missing pinned baseline",
            "idempotency_key": "api:weekly-baseline-missing-publish:approve",
        },
    )
    assert denied.status_code == 400
    assert denied.payload["error"]["code"] == "dependency_baseline_unavailable"

    approvals = _query_rows(
        db_path,
        """
        SELECT state, response_kind
        FROM approvals
        WHERE approval_id = ?
        """,
        (approval_id,),
    )
    assert approvals == [{"state": "PENDING", "response_kind": None}]

    artifacts = _query_rows(
        db_path,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC
        """,
        (workflow_run_id,),
    )
    artifact_kinds = [str(row["artifact_kind"]) for row in artifacts]
    assert "planning.publish_packet.doc" not in artifact_kinds
    assert "planning.published_weekly_schedule.workbook" not in artifact_kinds

    pointers = _query_rows(
        db_path,
        """
        SELECT pointer_key
        FROM artifact_pointers
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    )
    assert pointers == []
