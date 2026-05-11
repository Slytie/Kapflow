from __future__ import annotations

import base64
import json
from pathlib import Path
import sqlite3

from onetruth.application.services.dispatch_reporting_workbook import (
    WorkbookRuntimeDependencyError,
)
from tests.runtime.helpers.dispatch_reporting import (
    REALISTIC_REPORTING_SERVICE_DATE,
    SUPPORTED_REPORTING_WORKBOOK_PATH,
    XLSX_MEDIA_TYPE,
    reporting_workbook_upload_metadata,
)
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import run_cli, stdout_json


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
    tenant_id: str = "tenant-a",
    domain_id: str = "domain-x",
    actor_roles: list[str],
) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_id=actor_id,
        actor_type="human",
        actor_roles=actor_roles,
    )


def _create_dispatch_run(
    db_url: str,
    *,
    run_tag: str,
    service_date: str = REALISTIC_REPORTING_SERVICE_DATE,
    tenant_id: str = "tenant-a",
    domain_id: str = "domain-x",
) -> dict[str, object]:
    run_cli("--db-url", db_url, "init-db")
    created = run_cli(
        "--db-url",
        db_url,
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": "dispatch_reporting.v1",
                "workflow_version": "v1",
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "partition_key": f"SD-{service_date}",
                "logical_date": service_date,
                "activation_key": f"{run_tag}:dispatch-run",
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


def _claim_human_task(client: RuntimeApiClient, human_task_id: str, *, idempotency_key: str) -> None:
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": idempotency_key},
    )
    assert claimed.status_code == 200, claimed.payload


def _upload_binary_artifact(
    client: RuntimeApiClient,
    *,
    human_task_id: str,
    artifact_kind: str,
    artifact_role: str,
    content: bytes,
    file_name: str,
    media_type: str,
    metadata_json: dict[str, object] | None,
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


def _action_ref(
    *,
    action_id: str,
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
        "workpage_kind": "eod-v0",
        "workflow_run_id": workflow_run_id,
        "artifact_version_id": artifact_version_id,
        "subject": subject,
    }


def _latest_artifact_id(db_path: Path, *, workflow_run_id: str, artifact_kind: str) -> str:
    rows = _query_rows(
        db_path,
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_kind = ?
        ORDER BY created_at DESC
        """,
        (workflow_run_id, artifact_kind),
    )
    assert rows, artifact_kind
    return str(rows[0]["artifact_version_id"])


def _review_approval_id(db_path: Path, *, workflow_run_id: str) -> str:
    rows = _query_rows(
        db_path,
        """
        SELECT approval_id
        FROM approvals
        WHERE workflow_run_id = ? AND scope_ref = 'Stage04'
        ORDER BY requested_at DESC
        """,
        (workflow_run_id,),
    )
    assert rows
    return str(rows[0]["approval_id"])


def _upload_supported_eos_workbook(
    client: RuntimeApiClient,
    *,
    human_task_id: str,
    service_date: str = REALISTIC_REPORTING_SERVICE_DATE,
    idempotency_key: str,
) -> dict[str, object]:
    return _upload_binary_artifact(
        client,
        human_task_id=human_task_id,
        artifact_kind="reporting.eos_raw.workbook",
        artifact_role="official_input",
        content=SUPPORTED_REPORTING_WORKBOOK_PATH.read_bytes(),
        file_name=SUPPORTED_REPORTING_WORKBOOK_PATH.name,
        media_type=XLSX_MEDIA_TYPE,
        metadata_json=reporting_workbook_upload_metadata(service_date),
        idempotency_key=idempotency_key,
    )


def test_dispatch_eos_intake_contract_uses_official_input_role_and_blocks_completion(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    workflow_run = _create_dispatch_run(db_url, run_tag="api:dispatch-intake-contract")
    created = _create_human_task(
        db_url,
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key="api:dispatch-intake-contract:stage01-intake",
        actor_role="dispatch_supervisor",
    )
    human_task_id = str(created["human_task"]["human_task_id"])
    client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_human_task(
        client,
        human_task_id,
        idempotency_key="api:dispatch-intake-contract:claim",
    )

    workspace = client.get(f"/api/v1/workflow-runs/{workflow_run['workflow_run_id']}/workspace")
    assert workspace.status_code == 200
    item = _workspace_item(
        workspace.payload,
        subject_kind="human_task",
        subject_id=human_task_id,
    )
    assert item["required_uploads"] == [
        {
            "dataset_key": "reporting.eos_raw.workbook",
            "template_id": None,
            "artifact_kind": "reporting.eos_raw.workbook",
            "artifact_role": "official_input",
            "required": True,
            "required_count": 1,
            "current_count": 0,
            "linked_count": 0,
            "status": "missing",
        },
        {
            "dataset_key": "reporting.eos_raw.doc",
            "template_id": None,
            "artifact_kind": "reporting.eos_raw.doc",
            "artifact_role": "evidence",
            "required": False,
            "required_count": 1,
            "current_count": 0,
            "linked_count": 0,
            "status": "optional",
        },
    ]
    assert item["missing_required_inputs"] == ["reporting.eos_raw.workbook"]
    assert "complete" not in item["available_actions"]

    denied = client.post(
        f"/api/v1/human-tasks/{human_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-intake-contract:complete",
        },
    )
    assert denied.status_code == 400
    assert denied.payload["error"]["code"] == "task_requirements_not_satisfied"


def test_eod_intake_task_endpoint_reuses_open_task_and_creates_new_generation_after_completion(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    workflow_run = _create_dispatch_run(db_url, run_tag="api:dispatch-intake-ensure")
    workflow_run_id = str(workflow_run["workflow_run_id"])
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key="api:dispatch-intake-ensure:stage01-intake",
        actor_role="dispatch_supervisor",
    )
    human_task_id = str(created["human_task"]["human_task_id"])
    client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )

    first = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/intake-task",
        payload={"idempotency_key": "api:dispatch-intake-ensure:first"},
    )
    assert first.status_code == 200, first.payload
    assert first.payload["intake_task"] == {
        "workflow_run_id": workflow_run_id,
        "task_run_id": str(created["task_run"]["task_run_id"]),
        "human_task_id": human_task_id,
        "stage_id": "Stage01",
        "task_kind": "eos_input_intake",
        "task_run_state": "READY",
        "human_task_state": "OPEN",
        "activation_key": "api:dispatch-intake-ensure:stage01-intake",
        "generation": 0,
        "created": False,
        "service_date": REALISTIC_REPORTING_SERVICE_DATE,
        "target_workflow_run_id": workflow_run_id,
        "target_route": f"/runs/{workflow_run_id}/workpages/eod-v0",
        "created_workflow_run": False,
    }

    _claim_human_task(
        client,
        human_task_id,
        idempotency_key="api:dispatch-intake-ensure:claim",
    )
    _upload_supported_eos_workbook(
        client,
        human_task_id=human_task_id,
        idempotency_key="api:dispatch-intake-ensure:upload",
    )
    completed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-intake-ensure:complete",
        },
    )
    assert completed.status_code == 200, completed.payload

    second = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/intake-task",
        payload={"idempotency_key": "api:dispatch-intake-ensure:second"},
    )
    assert second.status_code == 200, second.payload
    intake_task = second.payload["intake_task"]
    assert intake_task["workflow_run_id"] == workflow_run_id
    assert intake_task["human_task_id"] != human_task_id
    assert intake_task["stage_id"] == "Stage01"
    assert intake_task["task_kind"] == "eos_input_intake"
    assert intake_task["task_run_state"] == "READY"
    assert intake_task["human_task_state"] == "OPEN"
    assert intake_task["generation"] == 1
    assert intake_task["created"] is True
    assert str(intake_task["activation_key"]).endswith(":generation:1")
    assert intake_task["service_date"] == REALISTIC_REPORTING_SERVICE_DATE
    assert intake_task["target_workflow_run_id"] == workflow_run_id
    assert intake_task["target_route"] == f"/runs/{workflow_run_id}/workpages/eod-v0"
    assert intake_task["created_workflow_run"] is False


def test_eod_intake_task_endpoint_resolves_existing_matching_service_date_run(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    source_run = _create_dispatch_run(db_url, run_tag="api:dispatch-intake-target-source")
    target_run = _create_dispatch_run(
        db_url,
        run_tag="api:dispatch-intake-target-existing",
        service_date="2026-03-25",
    )
    target_created = _create_human_task(
        db_url,
        workflow_run_id=str(target_run["workflow_run_id"]),
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key="api:dispatch-intake-target-existing:stage01-intake",
        actor_role="dispatch_supervisor",
    )
    client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )

    response = client.post(
        f"/api/v1/workpages/workflow-runs/{source_run['workflow_run_id']}/eod-v0/intake-task",
        payload={
            "service_date": "2026-03-25",
            "idempotency_key": "api:dispatch-intake-target-existing:ensure",
        },
    )
    assert response.status_code == 200, response.payload
    assert response.payload["intake_task"] == {
        "workflow_run_id": str(target_run["workflow_run_id"]),
        "task_run_id": str(target_created["task_run"]["task_run_id"]),
        "human_task_id": str(target_created["human_task"]["human_task_id"]),
        "stage_id": "Stage01",
        "task_kind": "eos_input_intake",
        "task_run_state": "READY",
        "human_task_state": "OPEN",
        "activation_key": "api:dispatch-intake-target-existing:stage01-intake",
        "generation": 0,
        "created": False,
        "service_date": "2026-03-25",
        "target_workflow_run_id": str(target_run["workflow_run_id"]),
        "target_route": f"/runs/{target_run['workflow_run_id']}/workpages/eod-v0",
        "created_workflow_run": False,
    }


def test_eod_intake_task_endpoint_creates_matching_service_date_run_when_missing(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    source_run = _create_dispatch_run(db_url, run_tag="api:dispatch-intake-target-create")
    client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )

    response = client.post(
        f"/api/v1/workpages/workflow-runs/{source_run['workflow_run_id']}/eod-v0/intake-task",
        payload={
            "service_date": "2026-03-25",
            "idempotency_key": "api:dispatch-intake-target-create:ensure",
        },
    )
    assert response.status_code == 200, response.payload
    intake_task = response.payload["intake_task"]
    assert intake_task["workflow_run_id"] != str(source_run["workflow_run_id"])
    assert intake_task["workflow_run_id"] == intake_task["target_workflow_run_id"]
    assert intake_task["service_date"] == "2026-03-25"
    assert intake_task["created"] is True
    assert intake_task["created_workflow_run"] is True
    assert intake_task["target_route"] == (
        f"/runs/{intake_task['target_workflow_run_id']}/workpages/eod-v0"
    )

    created_runs = _query_rows(
        db_path,
        """
        SELECT workflow_run_id, workflow_id, tenant_id, domain_id, partition_key, logical_date
        FROM workflow_runs
        WHERE partition_key = 'SD-2026-03-25'
        """,
    )
    assert created_runs == [
        {
            "workflow_run_id": intake_task["target_workflow_run_id"],
            "workflow_id": "dispatch_reporting.v1",
            "tenant_id": "tenant-a",
            "domain_id": "domain-x",
            "partition_key": "SD-2026-03-25",
            "logical_date": "2026-03-25",
        }
    ]


def test_eod_intake_task_endpoint_rejects_invalid_service_date(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    source_run = _create_dispatch_run(db_url, run_tag="api:dispatch-intake-invalid-date")
    client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )

    response = client.post(
        f"/api/v1/workpages/workflow-runs/{source_run['workflow_run_id']}/eod-v0/intake-task",
        payload={
            "service_date": "03/25/2026",
            "idempotency_key": "api:dispatch-intake-invalid-date:ensure",
        },
    )
    assert response.status_code == 400
    assert response.payload["error"]["code"] == "invalid_service_date"
    assert response.payload["error"]["details"]["service_date"] == "03/25/2026"


def test_eod_intake_task_endpoint_respects_scope_when_resolving_service_date_runs(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "runtime.db"
    db_url = f"sqlite:///{db_path}"
    source_run = _create_dispatch_run(db_url, run_tag="api:dispatch-intake-scope-source")
    _create_dispatch_run(
        db_url,
        run_tag="api:dispatch-intake-scope-other",
        service_date="2026-03-25",
        tenant_id="tenant-b",
        domain_id="domain-y",
    )
    client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )

    response = client.post(
        f"/api/v1/workpages/workflow-runs/{source_run['workflow_run_id']}/eod-v0/intake-task",
        payload={
            "service_date": "2026-03-25",
            "idempotency_key": "api:dispatch-intake-scope-source:ensure",
        },
    )
    assert response.status_code == 200, response.payload
    target_workflow_run_id = str(response.payload["intake_task"]["target_workflow_run_id"])

    created_rows = _query_rows(
        db_path,
        """
        SELECT tenant_id, domain_id, workflow_run_id
        FROM workflow_runs
        WHERE partition_key = 'SD-2026-03-25' AND tenant_id = 'tenant-a' AND domain_id = 'domain-x'
        """,
    )
    assert len(created_rows) == 1
    assert str(created_rows[0]["workflow_run_id"]) == target_workflow_run_id


def test_eod_intake_task_endpoint_rejects_task_claimed_by_other_actor(
    tmp_path: Path,
) -> None:
    db_url = _db_url(tmp_path)
    workflow_run = _create_dispatch_run(db_url, run_tag="api:dispatch-intake-ensure-claimed")
    workflow_run_id = str(workflow_run["workflow_run_id"])
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key="api:dispatch-intake-ensure-claimed:stage01-intake",
        actor_role="dispatch_supervisor",
    )
    human_task_id = str(created["human_task"]["human_task_id"])
    claimant = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )
    other_actor = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-2",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_human_task(
        claimant,
        human_task_id,
        idempotency_key="api:dispatch-intake-ensure-claimed:claim",
    )

    response = other_actor.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/intake-task",
        payload={"idempotency_key": "api:dispatch-intake-ensure-claimed:ensure"},
    )
    assert response.status_code == 409
    assert response.payload["error"]["code"] == "task_not_claimable"


def test_dispatch_reporting_happy_path_builds_review_finalizes_and_handoffs(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "happy-runtime.db"
    db_url = f"sqlite:///{db_path}"
    workflow_run = _create_dispatch_run(db_url, run_tag="api:dispatch-happy")
    workflow_run_id = str(workflow_run["workflow_run_id"])
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key="api:dispatch-happy:stage01-intake",
        actor_role="dispatch_supervisor",
    )
    intake_task_id = str(created["human_task"]["human_task_id"])
    dispatcher_client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-2",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_human_task(
        dispatcher_client,
        intake_task_id,
        idempotency_key="api:dispatch-happy:claim-intake",
    )
    _upload_supported_eos_workbook(
        dispatcher_client,
        human_task_id=intake_task_id,
        idempotency_key="api:dispatch-happy:upload-eos",
    )

    completed_intake = dispatcher_client.post(
        f"/api/v1/human-tasks/{intake_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-happy:complete-intake",
        },
    )
    assert completed_intake.status_code == 200, completed_intake.payload
    spawned_children = completed_intake.payload["result"]["spawned_children"]
    assert len(spawned_children) == 1
    review_task_id = str(spawned_children[0]["human_task_id"])

    artifact_kinds = [
        str(row["artifact_kind"])
        for row in _query_rows(
            db_path,
            """
            SELECT artifact_kind
            FROM artifact_versions
            WHERE workflow_run_id = ?
            ORDER BY created_at ASC
            """,
            (workflow_run_id,),
        )
    ]
    assert "reporting.actuals_normalized.workbook" in artifact_kinds
    assert "reporting.upd_draft.workbook" in artifact_kinds
    initial_draft_artifact_id = _latest_artifact_id(
        db_path,
        workflow_run_id=workflow_run_id,
        artifact_kind="reporting.upd_draft.workbook",
    )

    workspace = dispatcher_client.get(f"/api/v1/workflow-runs/{workflow_run_id}/workspace")
    assert workspace.status_code == 200
    review_item = _workspace_item(
        workspace.payload,
        subject_kind="human_task",
        subject_id=review_task_id,
    )
    assert review_item["workpage_actions"] == [
        {
            "action_id": "workpage.eod-v0.open_latest_draft",
            "workpage_kind": "eod-v0",
            "label": "Open EOD draft",
            "presentation": "open_route",
            "state": "available",
            "route": f"/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{initial_draft_artifact_id}",
            "create_path": None,
            "subject_context": {
                "subject_kind": "human_task",
                "subject_id": review_task_id,
                "workflow_run_id": workflow_run_id,
            },
            "action_ref": _action_ref(
                action_id="workpage.eod-v0.open_latest_draft",
                workflow_run_id=workflow_run_id,
                artifact_version_id=initial_draft_artifact_id,
                subject_kind="human_task",
                subject_id=review_task_id,
            ),
            "link_policy": {
                "create_relation_kind": "draft",
                "submit_relation_kind": "response",
            },
            "disabled_reason": None,
        }
    ]

    _claim_human_task(
        dispatcher_client,
        review_task_id,
        idempotency_key="api:dispatch-happy:claim-review",
    )
    submitted = dispatcher_client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"eod-v0/artifacts/{initial_draft_artifact_id}/submit",
        payload={
            "form_values": {
                "dispatcher_comment": "Reviewed Stage03 draft before manager confirmation.",
            },
            "checklist_values": [],
            "action_ref": _action_ref(
                action_id="workpage.eod-v0.submit_draft",
                workflow_run_id=workflow_run_id,
                artifact_version_id=initial_draft_artifact_id,
                subject_kind="human_task",
                subject_id=review_task_id,
            ),
            "idempotency_key": "api:dispatch-happy:submit-review-edits",
        },
    )
    assert submitted.status_code == 200, submitted.payload
    latest_draft_artifact_id = str(submitted.payload["submitted"]["artifact_version_id"])

    confirmed = dispatcher_client.post(
        f"/api/v1/human-tasks/{review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [latest_draft_artifact_id],
            "idempotency_key": "api:dispatch-happy:confirm-review",
        },
    )
    assert confirmed.status_code == 200, confirmed.payload

    completed_review = dispatcher_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-happy:complete-review",
        },
    )
    assert completed_review.status_code == 200, completed_review.payload
    approval_id = _review_approval_id(db_path, workflow_run_id=workflow_run_id)

    manager_client = _client(
        db_url=db_url,
        actor_id="human:operations-manager-1",
        actor_roles=["operations_manager"],
    )
    approved = manager_client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "idempotency_key": "api:dispatch-happy:approve",
        },
    )
    assert approved.status_code == 200, approved.payload

    finalized_artifact_rows = _query_rows(
        db_path,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_kind = 'reporting.final_packet.workbook'
        """,
        (workflow_run_id,),
    )
    assert len(finalized_artifact_rows) == 1

    pointer_rows = _query_rows(
        db_path,
        """
        SELECT pointer_key, artifact_kind, promotion_reason, approved_by_approval_id
        FROM artifact_pointers
        WHERE workflow_run_id = ? AND pointer_key = 'official:reporting.final_packet.workbook'
        """,
        (workflow_run_id,),
    )
    assert pointer_rows == [
        {
            "pointer_key": "official:reporting.final_packet.workbook",
            "artifact_kind": "reporting.final_packet.workbook",
            "promotion_reason": "official_finalize",
            "approved_by_approval_id": approval_id,
        }
    ]

    edge_rows = _query_rows(
        db_path,
        """
        SELECT edge_id, status, target_workflow_run_id
        FROM edge_executions
        WHERE source_workflow_run_id = ? AND edge_id = 'reporting_actuals_to_future_planning'
        ORDER BY created_at ASC
        """,
        (workflow_run_id,),
    )
    assert len(edge_rows) == 1
    assert str(edge_rows[0]["status"]) == "prepared"

    target_input_rows = _query_rows(
        db_path,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE artifact_kind = 'planning.actual_hours_snapshot.workbook'
        ORDER BY created_at ASC
        """,
    )
    assert len(target_input_rows) == 1

    unexpected_seed_rows = _query_rows(
        db_path,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE artifact_kind LIKE 'planning.daily_dispatch_seed.%'
        """,
    )
    assert unexpected_seed_rows == []

    workspace_after_approve = manager_client.get(f"/api/v1/workflow-runs/{workflow_run_id}/workspace")
    assert workspace_after_approve.status_code == 200
    assert any(
        output["artifact_version"]["artifact_kind"] == "reporting.final_packet.workbook"
        for output in workspace_after_approve.payload["official_outputs"]["outputs"]
        if isinstance(output.get("artifact_version"), dict)
    )


def test_dispatch_reporting_date_selected_import_runs_finalize_loop_on_target_service_date_run(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "target-date-runtime.db"
    db_url = f"sqlite:///{db_path}"
    source_run = _create_dispatch_run(
        db_url,
        run_tag="api:dispatch-target-date-source",
        service_date="2026-03-24",
    )
    dispatcher_client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-2",
        actor_roles=["dispatch_supervisor"],
    )

    ensured = dispatcher_client.post(
        f"/api/v1/workpages/workflow-runs/{source_run['workflow_run_id']}/eod-v0/intake-task",
        payload={
            "service_date": "2026-03-25",
            "idempotency_key": "api:dispatch-target-date:ensure",
        },
    )
    assert ensured.status_code == 200, ensured.payload
    intake_task = ensured.payload["intake_task"]
    target_workflow_run_id = str(intake_task["target_workflow_run_id"])
    assert target_workflow_run_id != str(source_run["workflow_run_id"])
    assert intake_task["service_date"] == "2026-03-25"

    _claim_human_task(
        dispatcher_client,
        str(intake_task["human_task_id"]),
        idempotency_key="api:dispatch-target-date:claim-intake",
    )
    _upload_supported_eos_workbook(
        dispatcher_client,
        human_task_id=str(intake_task["human_task_id"]),
        service_date="2026-03-25",
        idempotency_key="api:dispatch-target-date:upload-eos",
    )

    completed_intake = dispatcher_client.post(
        f"/api/v1/human-tasks/{intake_task['human_task_id']}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-target-date:complete-intake",
        },
    )
    assert completed_intake.status_code == 200, completed_intake.payload
    review_task_id = str(completed_intake.payload["result"]["spawned_children"][0]["human_task_id"])
    latest_draft_artifact_id = _latest_artifact_id(
        db_path,
        workflow_run_id=target_workflow_run_id,
        artifact_kind="reporting.upd_draft.workbook",
    )

    _claim_human_task(
        dispatcher_client,
        review_task_id,
        idempotency_key="api:dispatch-target-date:claim-review",
    )
    confirmed = dispatcher_client.post(
        f"/api/v1/human-tasks/{review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [latest_draft_artifact_id],
            "idempotency_key": "api:dispatch-target-date:confirm-review",
        },
    )
    assert confirmed.status_code == 200, confirmed.payload
    completed_review = dispatcher_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-target-date:complete-review",
        },
    )
    assert completed_review.status_code == 200, completed_review.payload
    approval_id = _review_approval_id(db_path, workflow_run_id=target_workflow_run_id)

    manager_client = _client(
        db_url=db_url,
        actor_id="human:operations-manager-1",
        actor_roles=["operations_manager"],
    )
    approved = manager_client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "idempotency_key": "api:dispatch-target-date:approve",
        },
    )
    assert approved.status_code == 200, approved.payload

    target_final_rows = _query_rows(
        db_path,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_kind = 'reporting.final_packet.workbook'
        """,
        (target_workflow_run_id,),
    )
    assert len(target_final_rows) == 1

    source_final_rows = _query_rows(
        db_path,
        """
        SELECT artifact_kind
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_kind = 'reporting.final_packet.workbook'
        """,
        (str(source_run["workflow_run_id"]),),
    )
    assert source_final_rows == []

    target_edge_rows = _query_rows(
        db_path,
        """
        SELECT edge_id, status
        FROM edge_executions
        WHERE source_workflow_run_id = ? AND edge_id = 'reporting_actuals_to_future_planning'
        """,
        (target_workflow_run_id,),
    )
    assert target_edge_rows == [
        {
            "edge_id": "reporting_actuals_to_future_planning",
            "status": "prepared",
        }
    ]

    source_edge_rows = _query_rows(
        db_path,
        """
        SELECT edge_id
        FROM edge_executions
        WHERE source_workflow_run_id = ? AND edge_id = 'reporting_actuals_to_future_planning'
        """,
        (str(source_run["workflow_run_id"]),),
    )
    assert source_edge_rows == []


def test_dispatch_eos_intake_rejects_unsupported_workbook_shape_without_review_task(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "unsupported-runtime.db"
    db_url = f"sqlite:///{db_path}"
    workflow_run = _create_dispatch_run(db_url, run_tag="api:dispatch-unsupported")
    created = _create_human_task(
        db_url,
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key="api:dispatch-unsupported:stage01-intake",
        actor_role="dispatch_supervisor",
    )
    intake_task_id = str(created["human_task"]["human_task_id"])
    dispatcher_client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-3",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_human_task(
        dispatcher_client,
        intake_task_id,
        idempotency_key="api:dispatch-unsupported:claim-intake",
    )
    _upload_binary_artifact(
        dispatcher_client,
        human_task_id=intake_task_id,
        artifact_kind="reporting.eos_raw.workbook",
        artifact_role="official_input",
        content=b"not-a-valid-workbook",
        file_name="unsupported-eos.xlsx",
        media_type=XLSX_MEDIA_TYPE,
        metadata_json={"service_date": REALISTIC_REPORTING_SERVICE_DATE},
        idempotency_key="api:dispatch-unsupported:upload-eos",
    )

    completed = dispatcher_client.post(
        f"/api/v1/human-tasks/{intake_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-unsupported:complete-intake",
        },
    )
    assert completed.status_code == 400
    assert completed.payload["error"]["code"] == "unsupported_eos_workbook_shape"

    review_task_rows = _query_rows(
        db_path,
        """
        SELECT human_task_id
        FROM human_tasks
        WHERE workflow_run_id = ? AND task_kind = 'final_packet_review'
        """,
        (str(workflow_run["workflow_run_id"]),),
    )
    assert review_task_rows == []


def test_dispatch_eos_intake_reports_missing_runtime_dependency_without_review_task(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "dependency-missing-runtime.db"
    db_url = f"sqlite:///{db_path}"
    workflow_run = _create_dispatch_run(db_url, run_tag="api:dispatch-dependency-missing")
    created = _create_human_task(
        db_url,
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key="api:dispatch-dependency-missing:stage01-intake",
        actor_role="dispatch_supervisor",
    )
    intake_task_id = str(created["human_task"]["human_task_id"])
    dispatcher_client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-4",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_human_task(
        dispatcher_client,
        intake_task_id,
        idempotency_key="api:dispatch-dependency-missing:claim-intake",
    )
    _upload_supported_eos_workbook(
        dispatcher_client,
        human_task_id=intake_task_id,
        idempotency_key="api:dispatch-dependency-missing:upload-eos",
    )
    monkeypatch.setattr(
        "onetruth.application.services.dispatch_reporting_build.project_raw_eos_workbook",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            WorkbookRuntimeDependencyError("openpyxl")
        ),
    )

    completed = dispatcher_client.post(
        f"/api/v1/human-tasks/{intake_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-dependency-missing:complete-intake",
        },
    )
    assert completed.status_code == 500
    assert completed.payload["error"]["code"] == "runtime_dependency_missing"
    assert completed.payload["error"]["details"]["dependency"] == "openpyxl"

    review_task_rows = _query_rows(
        db_path,
        """
        SELECT human_task_id
        FROM human_tasks
        WHERE workflow_run_id = ? AND task_kind = 'final_packet_review'
        """,
        (str(workflow_run["workflow_run_id"]),),
    )
    assert review_task_rows == []


def test_dispatch_review_completion_requires_manager_review_and_latest_confirmation(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "review-requirements-runtime.db"
    db_url = f"sqlite:///{db_path}"
    workflow_run = _create_dispatch_run(db_url, run_tag="api:dispatch-review-requirements")
    workflow_run_id = str(workflow_run["workflow_run_id"])
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key="api:dispatch-review-requirements:stage01-intake",
        actor_role="dispatch_supervisor",
    )
    intake_task_id = str(created["human_task"]["human_task_id"])
    dispatcher_client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-4",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_human_task(
        dispatcher_client,
        intake_task_id,
        idempotency_key="api:dispatch-review-requirements:claim-intake",
    )
    _upload_supported_eos_workbook(
        dispatcher_client,
        human_task_id=intake_task_id,
        idempotency_key="api:dispatch-review-requirements:upload-eos",
    )
    completed_intake = dispatcher_client.post(
        f"/api/v1/human-tasks/{intake_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-review-requirements:complete-intake",
        },
    )
    assert completed_intake.status_code == 200, completed_intake.payload
    review_task_id = str(completed_intake.payload["result"]["spawned_children"][0]["human_task_id"])

    _claim_human_task(
        dispatcher_client,
        review_task_id,
        idempotency_key="api:dispatch-review-requirements:claim-review",
    )
    denied = dispatcher_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-review-requirements:complete-review",
        },
    )
    assert denied.status_code == 400
    assert denied.payload["error"]["code"] == "task_requirements_not_satisfied"
    assert denied.payload["error"]["details"]["blocking_reason_codes"] == [
        "required_review_confirmation_missing:reporting.upd_draft.workbook",
    ]


def test_dispatch_finalize_fails_closed_when_reviewed_draft_is_stale(tmp_path: Path) -> None:
    db_path = tmp_path / "stale-runtime.db"
    db_url = f"sqlite:///{db_path}"
    workflow_run = _create_dispatch_run(db_url, run_tag="api:dispatch-stale")
    workflow_run_id = str(workflow_run["workflow_run_id"])
    created = _create_human_task(
        db_url,
        workflow_run_id=workflow_run_id,
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key="api:dispatch-stale:stage01-intake",
        actor_role="dispatch_supervisor",
    )
    intake_task_id = str(created["human_task"]["human_task_id"])
    dispatcher_client = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-5",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_human_task(
        dispatcher_client,
        intake_task_id,
        idempotency_key="api:dispatch-stale:claim-intake",
    )
    _upload_supported_eos_workbook(
        dispatcher_client,
        human_task_id=intake_task_id,
        idempotency_key="api:dispatch-stale:upload-eos",
    )
    completed_intake = dispatcher_client.post(
        f"/api/v1/human-tasks/{intake_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-stale:complete-intake",
        },
    )
    assert completed_intake.status_code == 200, completed_intake.payload
    review_task_id = str(completed_intake.payload["result"]["spawned_children"][0]["human_task_id"])
    initial_draft_artifact_id = _latest_artifact_id(
        db_path,
        workflow_run_id=workflow_run_id,
        artifact_kind="reporting.upd_draft.workbook",
    )

    _claim_human_task(
        dispatcher_client,
        review_task_id,
        idempotency_key="api:dispatch-stale:claim-review",
    )
    confirmed = dispatcher_client.post(
        f"/api/v1/human-tasks/{review_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [initial_draft_artifact_id],
            "idempotency_key": "api:dispatch-stale:confirm-review",
        },
    )
    assert confirmed.status_code == 200, confirmed.payload
    completed_review = dispatcher_client.post(
        f"/api/v1/human-tasks/{review_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": "api:dispatch-stale:complete-review",
        },
    )
    assert completed_review.status_code == 200, completed_review.payload
    approval_id = _review_approval_id(db_path, workflow_run_id=workflow_run_id)

    newer_draft = dispatcher_client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"eod-v0/artifacts/{initial_draft_artifact_id}/submit",
        payload={
            "form_values": {"dispatcher_comment": "Create a newer draft before approval."},
            "checklist_values": [],
            "action_ref": _action_ref(
                action_id="workpage.eod-v0.submit_draft",
                workflow_run_id=workflow_run_id,
                artifact_version_id=initial_draft_artifact_id,
                subject_kind="human_task",
                subject_id=review_task_id,
            ),
            "idempotency_key": "api:dispatch-stale:create-newer-draft",
        },
    )
    assert newer_draft.status_code == 200, newer_draft.payload
    latest_draft_artifact_id = str(newer_draft.payload["submitted"]["artifact_version_id"])
    assert latest_draft_artifact_id != initial_draft_artifact_id

    manager_client = _client(
        db_url=db_url,
        actor_id="human:operations-manager-2",
        actor_roles=["operations_manager"],
    )
    approved = manager_client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "idempotency_key": "api:dispatch-stale:approve",
        },
    )
    assert approved.status_code == 400
    assert approved.payload["error"]["code"] == "stable_base_schedule_required"

    finalized_rows = _query_rows(
        db_path,
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_kind = 'reporting.final_packet.workbook'
        """,
        (workflow_run_id,),
    )
    assert finalized_rows == []

    pointer_rows = _query_rows(
        db_path,
        """
        SELECT pointer_key
        FROM artifact_pointers
        WHERE workflow_run_id = ? AND pointer_key = 'official:reporting.final_packet.workbook'
        """,
        (workflow_run_id,),
    )
    assert pointer_rows == []

    edge_rows = _query_rows(
        db_path,
        """
        SELECT edge_execution_id
        FROM edge_executions
        WHERE source_workflow_run_id = ? AND edge_id = 'reporting_actuals_to_future_planning'
        """,
        (workflow_run_id,),
    )
    assert edge_rows == []
