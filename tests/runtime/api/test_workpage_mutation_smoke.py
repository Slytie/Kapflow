from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from onetruth.infrastructure.db.session import open_sqlite_connection
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import run_cli, stdout_json
from tests.runtime.helpers.workpage_runs import (
    seed_actual_ops_weekly_schedule_run_with_stage04_outputs,
    seed_dispatch_reporting_workpage_run,
)


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'runtime.db'}"


def _client(
    *,
    db_url: str,
    actor_id: str = "human:ops-manager-2",
    actor_roles: list[str] | None = None,
) -> RuntimeApiClient:
    roles = actor_roles or [
        "operations_manager",
        "dispatch_supervisor",
        "schedule_planner",
    ]
    return RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id=actor_id,
        actor_type="human",
        actor_roles=roles,
    )


def _query_rows(
    db_url: str,
    sql: str,
    params: tuple[object, ...] = (),
) -> list[dict[str, object]]:
    with open_sqlite_connection(db_url) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def _count_artifacts(
    db_url: str,
    *,
    workflow_run_id: str,
    artifact_kind: str,
) -> int:
    with open_sqlite_connection(db_url) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM artifact_versions
            WHERE workflow_run_id = ?
              AND artifact_kind = ?
            """,
            (workflow_run_id, artifact_kind),
        ).fetchone()[0]
    return int(count)


def _count_successors(
    db_url: str,
    *,
    workflow_run_id: str,
    artifact_kind: str,
    base_artifact_version_id: str,
) -> int:
    with open_sqlite_connection(db_url) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM artifact_versions
            WHERE workflow_run_id = ?
              AND artifact_kind = ?
              AND supersedes_artifact_version_id = ?
            """,
            (workflow_run_id, artifact_kind, base_artifact_version_id),
        ).fetchone()[0]
    return int(count)


def _action_ref(
    *,
    action_id: str,
    workpage_kind: str,
    workflow_run_id: str,
    artifact_version_id: str | None,
    subject_kind: str | None = None,
    subject_id: str | None = None,
) -> dict[str, object]:
    subject = None
    if subject_kind is not None and subject_id is not None:
        subject = {
            "subject_kind": subject_kind,
            "subject_id": subject_id,
        }
    return {
        "action_id": action_id,
        "workpage_kind": workpage_kind,
        "workflow_run_id": workflow_run_id,
        "artifact_version_id": artifact_version_id,
        "subject": subject,
    }


def _eod_draft_create_path(workflow_run_id: str) -> str:
    return f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts"


def _eod_artifact_path(workflow_run_id: str, artifact_version_id: str) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"eod-v0/artifacts/{artifact_version_id}"
    )


def _eod_submit_path(workflow_run_id: str, artifact_version_id: str) -> str:
    return f"{_eod_artifact_path(workflow_run_id, artifact_version_id)}/submit"


def _schedule_artifact_path(workflow_run_id: str, artifact_version_id: str) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{artifact_version_id}"
    )


def _schedule_submit_path(workflow_run_id: str, artifact_version_id: str) -> str:
    return f"{_schedule_artifact_path(workflow_run_id, artifact_version_id)}/submit"


def _schedule_submit_rows(
    client: RuntimeApiClient,
    workflow_run_id: str,
    artifact_version_id: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    payload = client.get(_schedule_artifact_path(workflow_run_id, artifact_version_id)).payload
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


def _route_demand_submit_rows(route_artifact: dict[str, object]) -> list[dict[str, object]]:
    metadata_json = route_artifact["metadata_json"]
    assert isinstance(metadata_json, dict)
    rows = []
    for item in metadata_json["daily_demand_rows"]:
        rows.append(
            {
                "service_date": str(item[0]),
                "planned_route_count": int(item[1]),
                "on_call_target": int(item[2]),
            }
        )
    return rows


def _create_human_task(
    db_url: str,
    *,
    workflow_run_id: str,
    stage_id: str,
    task_kind: str,
    activation_key: str,
    actor_role: str,
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


def _claim_human_task(
    client: RuntimeApiClient,
    human_task_id: str,
    *,
    idempotency_key: str,
) -> None:
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": idempotency_key},
    )
    assert claimed.status_code == 200, claimed.payload


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


def test_workpage_mutation_smoke_eod_create_replay_is_idempotent(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpage-smoke:eod-create",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(db_url=db_url)

    first = client.post(
        _eod_draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:workpage-smoke:eod-create"},
    )
    second = client.post(
        _eod_draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:workpage-smoke:eod-create"},
    )

    assert first.status_code == 200, first.payload
    assert second.status_code == 200, second.payload
    assert second.payload == first.payload
    assert _count_artifacts(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="reporting.upd_draft.workbook",
    ) == 1


def test_workpage_mutation_smoke_eod_submit_replay_creates_one_successor(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpage-smoke:eod-submit",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(db_url=db_url)
    created = client.post(
        _eod_draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:workpage-smoke:eod-submit:create"},
    )
    base_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])
    submit_payload = {
        "form_values": {"dispatcher_comment": "Smoke submit"},
        "checklist_values": [],
        "idempotency_key": "api:workpage-smoke:eod-submit",
    }

    first = client.post(
        _eod_submit_path(workflow_run_id, base_artifact_version_id),
        payload=submit_payload,
    )
    second = client.post(
        _eod_submit_path(workflow_run_id, base_artifact_version_id),
        payload=submit_payload,
    )

    assert first.status_code == 200, first.payload
    assert second.status_code == 200, second.payload
    assert second.payload == first.payload
    assert _count_artifacts(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="reporting.upd_draft.workbook",
    ) == 2
    assert _count_successors(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="reporting.upd_draft.workbook",
        base_artifact_version_id=base_artifact_version_id,
    ) == 1


def test_workpage_mutation_smoke_schedule_submit_replay_creates_one_successor(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpage-smoke:schedule-submit",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    base_artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(db_url=db_url)
    assignment_rows, reserve_rows = _schedule_submit_rows(
        client,
        workflow_run_id,
        base_artifact_version_id,
    )
    assignment_rows[0]["assigned_driver_id"] = "DRV-SMOKE-77"
    assignment_rows[0]["assignment_status"] = "manual_override"
    reserve_rows[0]["assigned_driver_id"] = "DRV-SMOKE-88"
    reserve_rows[0]["assignment_status"] = "manual_override"
    submit_payload = {
        "rows": assignment_rows,
        "reserve_rows": reserve_rows,
        "idempotency_key": "api:workpage-smoke:schedule-submit",
    }

    first = client.post(
        _schedule_submit_path(workflow_run_id, base_artifact_version_id),
        payload=submit_payload,
    )
    second = client.post(
        _schedule_submit_path(workflow_run_id, base_artifact_version_id),
        payload=submit_payload,
    )

    assert first.status_code == 200, first.payload
    assert second.status_code == 200, second.payload
    assert second.payload == first.payload
    assert _count_successors(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="planning.draft_weekly_schedule.workbook",
        base_artifact_version_id=base_artifact_version_id,
    ) == 1


def test_workpage_mutation_smoke_route_demand_submit_replay_keeps_no_refresh_task(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpage-smoke:route-demand",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    route_artifact = seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]
    base_artifact_version_id = str(route_artifact["artifact_version_id"])
    client = _client(db_url=db_url)
    submit_rows = _route_demand_submit_rows(route_artifact)
    submit_rows[0]["planned_route_count"] = int(submit_rows[0]["planned_route_count"]) + 2
    submit_payload = {
        "daily_demand_rows": submit_rows,
        "idempotency_key": "api:workpage-smoke:route-demand",
    }

    first = client.post(
        (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"route-demand-v0/artifacts/{base_artifact_version_id}/submit"
        ),
        payload=submit_payload,
    )
    second = client.post(
        (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"route-demand-v0/artifacts/{base_artifact_version_id}/submit"
        ),
        payload=submit_payload,
    )

    assert first.status_code == 200, first.payload
    assert second.status_code == 200, second.payload
    assert second.payload == first.payload
    assert _count_successors(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="planning.route_slot_requirements.workbook",
        base_artifact_version_id=base_artifact_version_id,
    ) == 1

    refresh_rows = _query_rows(
        db_url,
        """
        SELECT ht.state, tr.activation_key
        FROM human_tasks ht
        JOIN task_runs tr ON tr.task_run_id = ht.task_run_id
        WHERE ht.workflow_run_id = ?
        """,
        (workflow_run_id,),
    )
    refresh_rows = [
        row
        for row in refresh_rows
        if str(row["activation_key"]).startswith("workpage.route-demand-v0.schedule-refresh:")
    ]
    assert refresh_rows == []


def test_workpage_mutation_smoke_driver_preferences_create_and_submit_replay(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpage-smoke:driver-preferences",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(db_url=db_url)
    create_path = (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        "driver-preferences-v0/snapshots"
    )

    created_first = client.post(
        create_path,
        payload={"idempotency_key": "api:workpage-smoke:driver-preferences:create"},
    )
    created_second = client.post(
        create_path,
        payload={"idempotency_key": "api:workpage-smoke:driver-preferences:create"},
    )

    assert created_first.status_code == 200, created_first.payload
    assert created_second.status_code == 200, created_second.payload
    assert created_second.payload == created_first.payload

    base_artifact_version_id = str(created_first.payload["created"]["artifact_version_id"])
    assert _count_artifacts(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="planning.driver_shift_preferences.workbook",
    ) == 1

    current = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"driver-preferences-v0/artifacts/{base_artifact_version_id}"
    )
    assert current.status_code == 200, current.payload
    driver_rows = deepcopy(current.payload["preference_grid"]["drivers"])
    driver_rows[0]["preferences_by_weekday"]["mon"] = "open_to_work"
    submit_payload = {
        "driver_rows": [
            {
                "driver_id": row["driver_id"],
                "driver_quality": row["driver_quality"],
                "preferences_by_weekday": row["preferences_by_weekday"],
            }
            for row in driver_rows
        ],
        "idempotency_key": "api:workpage-smoke:driver-preferences:submit",
    }

    submitted_first = client.post(
        (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"driver-preferences-v0/artifacts/{base_artifact_version_id}/submit"
        ),
        payload=submit_payload,
    )
    submitted_second = client.post(
        (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"driver-preferences-v0/artifacts/{base_artifact_version_id}/submit"
        ),
        payload=submit_payload,
    )

    assert submitted_first.status_code == 200, submitted_first.payload
    assert submitted_second.status_code == 200, submitted_second.payload
    assert submitted_second.payload == submitted_first.payload
    assert _count_successors(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="planning.driver_shift_preferences.workbook",
        base_artifact_version_id=base_artifact_version_id,
    ) == 1


def test_workpage_mutation_smoke_weekly_publish_happy_path_promotes_official_pointer(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpage-smoke:weekly-publish",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    draft_artifact_version_id = str(
        seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"]
    )
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage05",
        task_kind="final_review",
        activation_key="api:workpage-smoke:weekly-publish:final-review",
        actor_role="operations_manager",
    )
    review_task_id = str(created["human_task"]["human_task_id"])
    manager_client = _client(
        db_url=db_url,
        actor_id="human:operations-manager-1",
        actor_roles=["operations_manager"],
    )
    _claim_human_task(
        manager_client,
        review_task_id,
        idempotency_key="api:workpage-smoke:weekly-publish:claim-review",
    )

    assignment_rows, reserve_rows = _schedule_submit_rows(
        manager_client,
        workflow_run_id,
        draft_artifact_version_id,
    )
    assignment_rows[0]["assigned_driver_id"] = "DRV-SMOKE-0152"
    assignment_rows[0]["assignment_status"] = "manual_override"
    submitted = manager_client.post(
        _schedule_submit_path(workflow_run_id, draft_artifact_version_id),
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "action_ref": _action_ref(
                action_id="workpage.schedule-v0.save_draft",
                workpage_kind="schedule-v0",
                workflow_run_id=workflow_run_id,
                artifact_version_id=draft_artifact_version_id,
                subject_kind="human_task",
                subject_id=review_task_id,
            ),
            "idempotency_key": "api:workpage-smoke:weekly-publish:submit-draft",
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
        idempotency_key="api:workpage-smoke:weekly-publish:upload-manager-review",
    )
    confirmed = manager_client.post(
        f"/api/v1/human-tasks/{review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [latest_draft_artifact_id],
            "idempotency_key": "api:workpage-smoke:weekly-publish:confirm-review",
        },
    )
    assert confirmed.status_code == 200, confirmed.payload
    completed = manager_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:workpage-smoke:weekly-publish:complete-review",
        },
    )
    assert completed.status_code == 200, completed.payload
    approval_id = str(completed.payload["result"]["requested_approvals"][0]["approval_id"])

    approved = manager_client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "response_reason": "publish the reviewed weekly schedule",
            "idempotency_key": "api:workpage-smoke:weekly-publish:approve",
        },
    )
    assert approved.status_code == 200, approved.payload

    published_rows = _query_rows(
        db_url,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind = 'planning.published_weekly_schedule.workbook'
        """,
        (workflow_run_id,),
    )
    assert len(published_rows) == 1

    pointer_rows = _query_rows(
        db_url,
        """
        SELECT pointer_key, artifact_kind, approved_by_approval_id
        FROM artifact_pointers
        WHERE workflow_run_id = ?
          AND pointer_key = 'official:planning.published_weekly_schedule.workbook'
        """,
        (workflow_run_id,),
    )
    assert pointer_rows == [
        {
            "pointer_key": "official:planning.published_weekly_schedule.workbook",
            "artifact_kind": "planning.published_weekly_schedule.workbook",
            "approved_by_approval_id": approval_id,
        }
    ]


def test_workpage_mutation_smoke_weekly_publish_dependency_drift_fails_closed(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpage-smoke:weekly-drift",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    draft_artifact_version_id = str(
        seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"]
    )
    route_requirements_artifact = seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage05",
        task_kind="final_review",
        activation_key="api:workpage-smoke:weekly-drift:final-review",
        actor_role="operations_manager",
    )
    review_task_id = str(created["human_task"]["human_task_id"])
    manager_client = _client(
        db_url=db_url,
        actor_id="human:operations-manager-3",
        actor_roles=["operations_manager"],
    )
    _claim_human_task(
        manager_client,
        review_task_id,
        idempotency_key="api:workpage-smoke:weekly-drift:claim-review",
    )
    _upload_json_artifact(
        manager_client,
        human_task_id=review_task_id,
        artifact_kind="planning.manager_review.doc",
        artifact_role="evidence",
        metadata_json={"review_status": "approved_pending_publish"},
        idempotency_key="api:workpage-smoke:weekly-drift:upload-manager-review",
    )
    confirmed = manager_client.post(
        f"/api/v1/human-tasks/{review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [draft_artifact_version_id],
            "idempotency_key": "api:workpage-smoke:weekly-drift:confirm-review",
        },
    )
    assert confirmed.status_code == 200, confirmed.payload
    completed = manager_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:workpage-smoke:weekly-drift:complete-review",
        },
    )
    assert completed.status_code == 200, completed.payload
    approval_id = str(completed.payload["result"]["requested_approvals"][0]["approval_id"])

    _create_artifact_version(
        db_url,
        workflow_run_id=workflow_run_id,
        artifact_kind="planning.route_slot_requirements.workbook",
        artifact_role="official_input",
        metadata_json=dict(route_requirements_artifact["metadata_json"]),
        idempotency_key="api:workpage-smoke:weekly-drift:new-route-requirements",
    )

    denied = manager_client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "response_reason": "attempt publish after route demand drifted",
            "idempotency_key": "api:workpage-smoke:weekly-drift:approve",
        },
    )
    assert denied.status_code == 400, denied.payload
    assert denied.payload["error"]["code"] == "dependency_drift_detected"

    published_rows = _query_rows(
        db_url,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind = 'planning.published_weekly_schedule.workbook'
        """,
        (workflow_run_id,),
    )
    assert published_rows == []

    pointer_rows = _query_rows(
        db_url,
        """
        SELECT pointer_key
        FROM artifact_pointers
        WHERE workflow_run_id = ?
          AND pointer_key = 'official:planning.published_weekly_schedule.workbook'
        """,
        (workflow_run_id,),
    )
    assert pointer_rows == []
