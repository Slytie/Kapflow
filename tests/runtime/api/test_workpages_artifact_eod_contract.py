from __future__ import annotations

import json
from pathlib import Path

import onetruth.application.handlers.workpage_reporting_commands as workpage_reporting_commands
from onetruth.application.handlers.artifacts import ingest_artifact_document_command
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_workflow_run_command,
)
from onetruth.application.services.dispatch_reporting_workbook import (
    project_upd_draft_workbook,
)
from onetruth.infrastructure.artifacts.storage import (
    default_storage_root_for_db_url,
    encode_base64_content,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from tests.runtime.helpers.dispatch_reporting import REALISTIC_REPORTING_SERVICE_DATE
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT, run_cli
from tests.runtime.helpers.workpage_runs import seed_dispatch_reporting_workpage_run


REPORTING_TEMPLATE_PATH = (
    REPO_ROOT
    / "fixtures/workflows/dispatch_reporting/template_pack/Stage03_Threshold_Detection_and_Draft_Packet/Stage03_Threshold_Detection_and_Draft_Packet_upd_draft_Spreadsheet_Template_EMPTY.xlsx"
)
SCHEDULE_TEMPLATE_PATH = (
    REPO_ROOT
    / "fixtures/workflows/schedule_planning/template_pack/Stage05_Draft_Schedule_Triage/Stage05_Draft_Schedule_Triage_Spreadsheet_Template_EMPTY.xlsx"
)
EXPECTED_TEMPLATE_REF = (
    "fixtures/workflows/dispatch_reporting/template_pack/"
    "Stage03_Threshold_Detection_and_Draft_Packet/"
    "Stage03_Threshold_Detection_and_Draft_Packet_upd_draft_Spreadsheet_Template_EMPTY.xlsx"
)


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'runtime.db'}"


def _client(tmp_path: Path) -> RuntimeApiClient:
    _init_db(tmp_path)
    return RuntimeApiClient(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager", "dispatch_supervisor", "schedule_planner"],
    )


def _other_scope_client(tmp_path: Path) -> RuntimeApiClient:
    _init_db(tmp_path)
    return RuntimeApiClient(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-b",
        domain_id="domain-y",
        actor_id="human:ops-manager-9",
        actor_type="human",
        actor_roles=["operations_manager"],
    )


def _init_db(tmp_path: Path) -> None:
    run_cli("--db-url", _db_url(tmp_path), "init-db")


def _draft_create_path(workflow_run_id: str) -> str:
    return f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts"


def _artifact_path(workflow_run_id: str, artifact_version_id: str) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"eod-v0/artifacts/{artifact_version_id}"
    )


def _submit_path(workflow_run_id: str, artifact_version_id: str) -> str:
    return f"{_artifact_path(workflow_run_id, artifact_version_id)}/submit"


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


def _request_approval(
    tmp_path: Path,
    *,
    workflow_run_id: str,
    approval_id: str,
    scope_ref: str,
) -> dict[str, object]:
    requested = run_cli(
        "--db-url",
        _db_url(tmp_path),
        "approvals",
        "request",
        "--json",
        json.dumps(
            {
                "approval_id": approval_id,
                "workflow_run_id": workflow_run_id,
                "approval_kind": "business_decision",
                "scope_kind": "stage",
                "scope_ref": scope_ref,
                "candidate_roles": ["operations_manager"],
                "required_role": "operations_manager",
                "action": "confirm_dispatch_reporting_packet",
                "idempotency_key": f"api:eod-draft:approval:{approval_id}",
            },
            separators=(",", ":"),
        ),
    )
    return json.loads(requested.stdout)["approval"]


def _request_review_task(
    tmp_path: Path,
    *,
    workflow_run_id: str,
    human_task_id: str,
    task_run_id: str,
) -> dict[str, object]:
    created = run_cli(
        "--db-url",
        _db_url(tmp_path),
        "tasks",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "task_run_id": task_run_id,
                "human_task_id": human_task_id,
                "stage_id": "Stage04",
                "task_kind": "final_packet_review",
                "activation_key": f"api:eod-draft:review-task:{human_task_id}",
                "candidate_roles": ["dispatch_supervisor"],
                "owner_role": "dispatch_supervisor",
                "create_human_task": True,
                "idempotency_key": f"api:eod-draft:review-task:{human_task_id}",
            },
            separators=(",", ":"),
        ),
    )
    return json.loads(created.stdout)["result"]["human_task"]


def test_canonical_eod_draft_create_creates_artifact_in_seeded_reporting_run(
    tmp_path: Path,
) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:create-001",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)

    response = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:create-001"},
    )
    assert response.status_code == 200
    assert response.payload["status"] == "ok"
    assert response.payload["command"] == "api.workpages.eod_drafts.create"

    draft = response.payload["draft"]
    artifact_version_id = str(draft["artifact_version_id"])
    assert str(draft["workflow_run_id"]) == workflow_run_id
    assert draft["route"] == f"/runs/{workflow_run_id}/workpages/eod-v0/artifacts/{artifact_version_id}"

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        run_rows = connection.execute(
            """
            SELECT workflow_id, partition_key, activation_key
            FROM workflow_runs
            ORDER BY created_at ASC
            """
        ).fetchall()
        assert [dict(row) for row in run_rows] == [
            {
                    "workflow_id": "dispatch_reporting.v1",
                    "partition_key": f"SD-{REALISTIC_REPORTING_SERVICE_DATE}",
                    "activation_key": "api:eod-draft:create-001:dispatch-reporting-workpage",
                }
            ]

        artifact_row = connection.execute(
            """
            SELECT workflow_run_id, artifact_kind, dataset_key, supersedes_artifact_version_id, metadata_json
            FROM artifact_versions
            WHERE artifact_version_id = ?
            """,
            (artifact_version_id,),
        ).fetchone()
        assert artifact_row is not None
        assert str(artifact_row["workflow_run_id"]) == workflow_run_id
        assert str(artifact_row["artifact_kind"]) == "reporting.upd_draft.workbook"
        assert str(artifact_row["dataset_key"]) == "reporting.upd_draft.workbook"
        assert artifact_row["supersedes_artifact_version_id"] is None

        metadata = json.loads(str(artifact_row["metadata_json"]))
        assert metadata["template_id"] == "dispatch_reporting.stage03.upd_draft.workbook.empty.v1"
        assert metadata["seed_source_path"] == EXPECTED_TEMPLATE_REF
        assert "demo_workpage_id" not in metadata
        assert metadata["service_date"] == REALISTIC_REPORTING_SERVICE_DATE
        assert metadata["station_code"] == "DVC4"
        assert metadata["dsp_name"] == "QDCI"


def test_canonical_eod_draft_create_replays_idempotently_without_duplicate_artifacts(
    tmp_path: Path,
) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:create-replay",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)

    first = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:create-replay"},
    )
    second = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:create-replay"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.payload == first.payload

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        artifact_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM artifact_versions
            WHERE workflow_run_id = ?
              AND dataset_key = 'reporting.upd_draft.workbook'
            """,
            (workflow_run_id,),
        ).fetchone()[0]
    assert artifact_count == 1


def test_canonical_eod_draft_create_links_supported_stage04_approval_as_draft(
    tmp_path: Path,
) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:canonical-subject-create",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    approval = _request_approval(
        tmp_path,
        workflow_run_id=workflow_run_id,
        approval_id="ap-dispatch-stage04",
        scope_ref="Stage04",
    )
    client = _client(tmp_path)

    response = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={
            "action_ref": _action_ref(
                action_id="workpage.eod-v0.create_draft",
                workflow_run_id=workflow_run_id,
                artifact_version_id=None,
                subject_kind="approval",
                subject_id=str(approval["approval_id"]),
            ),
            "idempotency_key": "api:eod-draft:canonical-subject-create",
        },
    )
    assert response.status_code == 200
    artifact_version_id = str(response.payload["draft"]["artifact_version_id"])

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        rows = connection.execute(
            """
            SELECT subject_kind, subject_id, relation_kind
            FROM artifact_links
            WHERE artifact_version_id = ?
            ORDER BY subject_kind ASC, subject_id ASC, relation_kind ASC
            """,
            (artifact_version_id,),
        ).fetchall()
    assert [dict(row) for row in rows] == [
        {
            "subject_kind": "approval",
            "subject_id": "ap-dispatch-stage04",
            "relation_kind": "draft",
        }
    ]


def test_canonical_eod_draft_create_links_supported_stage04_review_task_as_draft(
    tmp_path: Path,
) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:canonical-review-task-create",
        include_source_artifacts=False,
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    review_task = _request_review_task(
        tmp_path,
        workflow_run_id=workflow_run_id,
        human_task_id="ht-dispatch-stage04-review",
        task_run_id="tr-dispatch-stage04-review",
    )
    client = _client(tmp_path)

    response = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={
            "subject_link": {
                "subject_kind": "human_task",
                "subject_id": str(review_task["human_task_id"]),
            },
            "idempotency_key": "api:eod-draft:canonical-review-task-create",
        },
    )
    assert response.status_code == 200
    artifact_version_id = str(response.payload["draft"]["artifact_version_id"])

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        rows = connection.execute(
            """
            SELECT subject_kind, subject_id, relation_kind
            FROM artifact_links
            WHERE artifact_version_id = ?
            ORDER BY subject_kind ASC, subject_id ASC, relation_kind ASC
            """,
            (artifact_version_id,),
        ).fetchall()
    assert [dict(row) for row in rows] == [
        {
            "subject_kind": "human_task",
            "subject_id": "ht-dispatch-stage04-review",
            "relation_kind": "draft",
        }
    ]


def test_artifact_backed_eod_workpage_returns_projected_contract(tmp_path: Path) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:read-001",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)
    created = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:read-001"},
    )
    artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    response = client.get(_artifact_path(workflow_run_id, artifact_version_id))
    assert response.status_code == 200

    payload = response.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.workpages.artifact"

    workpage = payload["workpage"]
    assert workpage["workpage_id"] == "eod-v0"
    assert workpage["version"] == 2
    assert workpage["workflow_id"] == "dispatch_reporting.v1"
    assert workpage["dataset_key"] == "reporting.upd_draft.workbook"
    assert workpage["source_artifact_version_id"] == artifact_version_id
    assert workpage["source_examples"] == {}
    assert workpage["summary"] == {
        "service_date": REALISTIC_REPORTING_SERVICE_DATE,
        "station_code": "DVC4",
        "dsp_name": "QDCI",
        "total_routes_actual": 0,
        "packages_dispatched": 0,
        "actual_dispatched": 0,
        "packages_delivered": 0,
        "packages_returned": 0,
        "delivered_pct": 0.0,
        "return_pct": 0.0,
        "average_route_time": "0:00:00",
        "formula_integrity_warning": False,
        "warning_note": (
            "This EOD projection is built from canonical dispatch-reporting artifacts. "
            "Row-level route actuals remain the primary truth when summary sheets contain "
            "broken formulas."
        ),
    }

    sections = workpage["sections"]
    assert [section["kind"] for section in sections] == [
        "summary_cards",
        "note_panel",
        "table",
        "form",
        "checklist",
        "history_stub",
    ]

    route_actuals_section = next(
        section for section in sections if section.get("table_id") == "route_actuals"
    )
    assert route_actuals_section["rows"] == []

    form_section = next(section for section in sections if section["kind"] == "form")
    field_map = {field["key"]: field for field in form_section["fields"]}
    assert field_map["sick_calls"]["value"] == []
    assert field_map["unavailable_drivers"]["value"] == []
    assert field_map["rescues"]["value"] == []
    assert field_map["incidents"]["value"] == []
    assert field_map["last_driver_clockout"]["value"] == ""
    assert field_map["dispatcher_comment"]["value"] == ""
    assert field_map["manager_note"]["value"] == ""

    checklist_section = next(section for section in sections if section["kind"] == "checklist")
    assert checklist_section["items"] == []

    source = payload["source"]
    assert source == {
        "mode": "artifact_projection",
        "primary_dataset_key": "reporting.upd_draft.workbook",
        "source_dataset_keys": ["reporting.upd_draft.workbook"],
        "source_artifact_version_id": artifact_version_id,
        "source_refs": [EXPECTED_TEMPLATE_REF],
    }

    freshness = payload["freshness"]
    assert freshness["source_kind"] == "artifact_version"
    assert freshness["source_version"] == artifact_version_id
    assert freshness["generated_at"]

    artifact_context = payload["artifact_context"]
    assert artifact_context == {
        "artifact_version_id": artifact_version_id,
        "workflow_run_id": created.payload["draft"]["workflow_run_id"],
        "artifact_kind": "reporting.upd_draft.workbook",
        "supersedes_artifact_version_id": None,
        "superseded_by_artifact_version_id": None,
        "latest_in_chain_artifact_version_id": artifact_version_id,
        "download_path": f"/api/v1/artifacts/{artifact_version_id}/download.bin",
    }
    assert payload["artifact_history"]["current_artifact_version_id"] == artifact_version_id
    assert payload["artifact_history"]["latest_artifact_version_id"] == artifact_version_id
    assert payload["artifact_history"]["previous_artifact_version_id"] is None
    assert payload["artifact_history"]["next_artifact_version_id"] is None
    assert payload["artifact_history"]["entries"] == [
        {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": created.payload["draft"]["workflow_run_id"],
            "artifact_kind": "reporting.upd_draft.workbook",
            "created_at": payload["artifact_history"]["entries"][0]["created_at"],
            "lineage_note": "Initial artifact-backed EOD draft seeded from Stage03 template.",
            "supersedes_artifact_version_id": None,
            "route": (
                f"/runs/{created.payload['draft']['workflow_run_id']}/workpages/eod-v0/artifacts/"
                f"{artifact_version_id}"
            ),
        }
    ]
    assert payload["artifact_history"]["entries"][0]["created_at"]
    assert payload["actions"] == [
        {
            "action_id": "workpage.eod-v0.submit_draft",
            "kind": "submit_artifact",
            "label": "Submit draft",
            "state": "available",
            "workpage_kind": "eod-v0",
            "artifact_version_id": artifact_version_id,
            "submit_path": _submit_path(workflow_run_id, artifact_version_id),
            "action_ref": _action_ref(
                action_id="workpage.eod-v0.submit_draft",
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            ),
            "disabled_reason": None,
        }
    ]


def test_submit_artifact_workpage_creates_superseding_version_and_updates_projection(
    tmp_path: Path,
) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:submit-001",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)
    created = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:submit-001"},
    )
    base_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    submit_payload = {
        "form_values": {
            "sick_calls": ["Brahamvir Singh"],
            "unavailable_drivers": ["Tarandeep Singh"],
            "working_devices": "38",
            "rescues": ["CX100 assist", "CX95 assist"],
            "incidents": ["dock delay"],
            "last_driver_clockout": "22:27",
            "dispatcher_comment": "Draft closeout captured through artifact-backed workpage.",
            "manager_note": "Escalate next morning.",
        },
        "checklist_values": [],
        "idempotency_key": "api:eod-draft:submit-001",
    }
    submitted = client.post(
        _submit_path(workflow_run_id, base_artifact_version_id),
        payload=submit_payload,
    )
    assert submitted.status_code == 200
    assert submitted.payload["command"] == "api.workpages.artifact.submit"

    submitted_artifact_version_id = str(submitted.payload["submitted"]["artifact_version_id"])
    assert submitted_artifact_version_id != base_artifact_version_id
    assert submitted.payload["submitted"]["workflow_run_id"] == created.payload["draft"]["workflow_run_id"]
    assert (
        submitted.payload["submitted"]["supersedes_artifact_version_id"]
        == base_artifact_version_id
    )
    assert submitted.payload["submitted"]["route"] == (
        f"/runs/{created.payload['draft']['workflow_run_id']}/workpages/eod-v0/artifacts/{submitted_artifact_version_id}"
    )

    base_read = client.get(_artifact_path(workflow_run_id, base_artifact_version_id))
    assert base_read.status_code == 200
    assert (
        base_read.payload["artifact_context"]["superseded_by_artifact_version_id"]
        == submitted_artifact_version_id
    )
    assert (
        base_read.payload["artifact_context"]["latest_in_chain_artifact_version_id"]
        == submitted_artifact_version_id
    )

    latest_read = client.get(_artifact_path(workflow_run_id, submitted_artifact_version_id))
    assert latest_read.status_code == 200
    latest_form = {
        field["key"]: field["value"]
        for field in next(
            section
            for section in latest_read.payload["workpage"]["sections"]
            if section["kind"] == "form"
        )["fields"]
    }
    assert latest_form["sick_calls"] == ["Brahamvir Singh"]
    assert latest_form["unavailable_drivers"] == ["Tarandeep Singh"]
    assert latest_form["working_devices"] == "38"
    assert latest_form["rescues"] == ["CX100 assist", "CX95 assist"]
    assert latest_form["incidents"] == ["dock delay"]
    assert latest_form["last_driver_clockout"] == "22:27"
    assert latest_form["dispatcher_comment"] == (
        "Draft closeout captured through artifact-backed workpage."
    )
    assert latest_form["manager_note"] == "Escalate next morning."
    assert (
        latest_read.payload["artifact_context"]["supersedes_artifact_version_id"]
        == base_artifact_version_id
    )
    assert (
        latest_read.payload["artifact_context"]["latest_in_chain_artifact_version_id"]
        == submitted_artifact_version_id
    )


def test_submit_artifact_workpage_links_supported_stage04_approval_as_response(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        workpage_reporting_commands,
        "project_upd_draft_workbook",
        lambda _workbook_bytes: {
            "manual_closeout": [
                {
                    "sick_calls": "",
                    "unavailable_drivers": "",
                    "working_devices": "",
                    "rescues": "",
                    "incidents": "",
                    "last_driver_clockout": "",
                    "dispatcher_comment": "",
                    "manager_note": "",
                }
            ],
            "upd_candidates": [],
        },
    )
    monkeypatch.setattr(
        workpage_reporting_commands,
        "materialize_upd_draft_workbook",
        lambda workbook_bytes, edits, change_log_entry: workbook_bytes,
    )
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:subject-submit",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    approval = _request_approval(
        tmp_path,
        workflow_run_id=workflow_run_id,
        approval_id="ap-dispatch-stage04-submit",
        scope_ref="Stage04",
    )
    client = _client(tmp_path)
    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={"idempotency_key": "api:eod-draft:subject-submit:create"},
    )
    base_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    submitted = client.post(
        _submit_path(workflow_run_id, base_artifact_version_id),
        payload={
            "form_values": {"dispatcher_comment": "Linked to Stage04 approval."},
            "checklist_values": [],
            "action_ref": _action_ref(
                action_id="workpage.eod-v0.submit_draft",
                workflow_run_id=workflow_run_id,
                artifact_version_id=base_artifact_version_id,
                subject_kind="approval",
                subject_id=str(approval["approval_id"]),
            ),
            "idempotency_key": "api:eod-draft:subject-submit",
        },
    )
    assert submitted.status_code == 200
    submitted_artifact_version_id = str(submitted.payload["submitted"]["artifact_version_id"])

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        rows = connection.execute(
            """
            SELECT subject_kind, subject_id, relation_kind
            FROM artifact_links
            WHERE artifact_version_id = ?
            ORDER BY subject_kind ASC, subject_id ASC, relation_kind ASC
            """,
            (submitted_artifact_version_id,),
        ).fetchall()
    assert [dict(row) for row in rows] == [
        {
            "subject_kind": "approval",
            "subject_id": "ap-dispatch-stage04-submit",
            "relation_kind": "response",
        }
    ]


def test_submit_artifact_workpage_links_supported_stage04_review_task_as_response(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        workpage_reporting_commands,
        "materialize_upd_draft_workbook",
        lambda workbook_bytes, edits, change_log_entry: workbook_bytes,
    )
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:review-task-submit",
        include_source_artifacts=False,
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    review_task = _request_review_task(
        tmp_path,
        workflow_run_id=workflow_run_id,
        human_task_id="ht-dispatch-stage04-review-submit",
        task_run_id="tr-dispatch-stage04-review-submit",
    )
    client = _client(tmp_path)
    created = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts",
        payload={"idempotency_key": "api:eod-draft:review-task-submit:create"},
    )
    base_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    submitted = client.post(
        _submit_path(workflow_run_id, base_artifact_version_id),
        payload={
            "form_values": {"dispatcher_comment": "Linked to Stage04 review task."},
            "checklist_values": [],
            "subject_link": {
                "subject_kind": "human_task",
                "subject_id": str(review_task["human_task_id"]),
            },
            "idempotency_key": "api:eod-draft:review-task-submit",
        },
    )
    assert submitted.status_code == 200
    submitted_artifact_version_id = str(submitted.payload["submitted"]["artifact_version_id"])

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        rows = connection.execute(
            """
            SELECT subject_kind, subject_id, relation_kind
            FROM artifact_links
            WHERE artifact_version_id = ?
            ORDER BY subject_kind ASC, subject_id ASC, relation_kind ASC
            """,
            (submitted_artifact_version_id,),
        ).fetchall()
    assert [dict(row) for row in rows] == [
        {
            "subject_kind": "human_task",
            "subject_id": "ht-dispatch-stage04-review-submit",
            "relation_kind": "response",
        }
    ]


def test_workflow_run_artifact_list_includes_eod_draft_chain_versions(tmp_path: Path) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:history-001",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)
    created = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:history-001"},
    )
    base_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    submitted = client.post(
        _submit_path(workflow_run_id, base_artifact_version_id),
        payload={
            "form_values": {
                "working_devices": "37",
                "dispatcher_comment": "History list regression",
            },
            "checklist_values": [],
            "idempotency_key": "api:eod-draft:history-submit-001",
        },
    )
    submitted_artifact_version_id = str(submitted.payload["submitted"]["artifact_version_id"])

    listed = client.get(f"/api/v1/workflow-runs/{workflow_run_id}/artifacts")
    assert listed.status_code == 200
    assert listed.payload["status"] == "ok"
    assert listed.payload["command"] == "api.workflow_runs.artifacts.list"

    workbook_rows = [
        row
        for row in listed.payload["artifact_versions"]
        if row["artifact_kind"] == "reporting.upd_draft.workbook"
    ]
    assert [row["artifact_version_id"] for row in workbook_rows] == [
        base_artifact_version_id,
        submitted_artifact_version_id,
    ]
    assert all("demo_workpage_id" not in row["metadata_json"] for row in workbook_rows)

    second_workbook_page = client.get(
        "/api/v1/artifacts",
        query={
            "workflow_run_id": workflow_run_id,
            "artifact_kind": "reporting.upd_draft.workbook",
            "limit": "1",
            "offset": "1",
        },
    )
    assert second_workbook_page.status_code == 200
    assert second_workbook_page.payload["command"] == "api.artifacts.list"
    assert second_workbook_page.payload["page"] == {"limit": 1, "offset": 1}
    assert [
        row["artifact_version_id"]
        for row in second_workbook_page.payload["artifact_versions"]
        if row["artifact_kind"] == "reporting.upd_draft.workbook"
    ] == [submitted_artifact_version_id]


def test_submit_artifact_workpage_replays_idempotently_without_duplicate_versions(
    tmp_path: Path,
) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:submit-replay",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)
    created = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:submit-replay:create"},
    )
    base_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])
    payload = {
        "form_values": {"dispatcher_comment": "Replay-safe submit"},
        "checklist_values": [],
        "idempotency_key": "api:eod-draft:submit-replay",
    }

    first = client.post(
        _submit_path(workflow_run_id, base_artifact_version_id),
        payload=payload,
    )
    second = client.post(
        _submit_path(workflow_run_id, base_artifact_version_id),
        payload=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.payload == first.payload

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        artifact_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM artifact_versions
            WHERE workflow_run_id = ?
              AND dataset_key = 'reporting.upd_draft.workbook'
            """,
            (workflow_run_id,),
        ).fetchone()[0]
    assert artifact_count == 2


def test_canonical_eod_draft_create_rejects_invalid_subject_kind(tmp_path: Path) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:invalid-subject-link",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)

    response = client.post(
        _draft_create_path(workflow_run_id),
        payload={
            "subject_link": {
                "subject_kind": "workflow_run",
                "subject_id": workflow_run_id,
            },
            "idempotency_key": "api:eod-draft:invalid-subject-link",
        },
    )
    assert response.status_code == 400
    assert response.payload["error"]["code"] == "invalid_workpage_subject_link"


def test_canonical_eod_draft_create_rejects_mixed_action_ref_and_subject_link(
    tmp_path: Path,
) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:mixed-action-ref-subject-link",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)

    response = client.post(
        _draft_create_path(workflow_run_id),
        payload={
            "action_ref": _action_ref(
                action_id="workpage.eod-v0.create_draft",
                workflow_run_id=workflow_run_id,
                artifact_version_id=None,
                subject_kind="approval",
                subject_id="ap-stage04",
            ),
            "subject_link": {
                "subject_kind": "approval",
                "subject_id": "ap-stage04",
            },
            "idempotency_key": "api:eod-draft:mixed-action-ref-subject-link",
        },
    )
    assert response.status_code == 400
    assert response.payload["error"]["code"] == "invalid_payload"
    assert response.payload["error"]["details"] == {
        "field_names": ["action_ref", "subject_link"]
    }


def test_submit_artifact_workpage_rejects_action_ref_for_wrong_artifact(
    tmp_path: Path,
) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:invalid-action-ref-artifact",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)
    created = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:invalid-action-ref-artifact:create"},
    )
    base_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    response = client.post(
        _submit_path(workflow_run_id, base_artifact_version_id),
        payload={
            "form_values": {"dispatcher_comment": "Reject mismatched action ref."},
            "checklist_values": [],
            "action_ref": _action_ref(
                action_id="workpage.eod-v0.submit_draft",
                workflow_run_id=workflow_run_id,
                artifact_version_id="av-wrong-artifact",
            ),
            "idempotency_key": "api:eod-draft:invalid-action-ref-artifact",
        },
    )
    assert response.status_code == 400
    assert response.payload["error"]["code"] == "invalid_workpage_action_ref"
    assert response.payload["error"]["details"] == {
        "workpage_kind": "eod-v0",
        "flow_kind": "submit",
        "artifact_version_id": base_artifact_version_id,
        "action_artifact_version_id": "av-wrong-artifact",
    }


def test_canonical_eod_draft_create_rejects_cross_run_approval_subject_link(
    tmp_path: Path,
) -> None:
    first_run = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:cross-run:first",
    )
    second_run = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:cross-run:second",
        include_source_artifacts=False,
    )
    approval = _request_approval(
        tmp_path,
        workflow_run_id=str(second_run["workflow_run_id"]),
        approval_id="ap-cross-run-stage04",
        scope_ref="Stage04",
    )
    client = _client(tmp_path)

    response = client.post(
        f"/api/v1/workpages/workflow-runs/{first_run['workflow_run_id']}/eod-v0/drafts",
        payload={
            "subject_link": {
                "subject_kind": "approval",
                "subject_id": str(approval["approval_id"]),
            },
            "idempotency_key": "api:eod-draft:cross-run:create",
        },
    )
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "cross_workflow_link_reference"


def test_submit_artifact_workpage_returns_conflict_for_stale_base(tmp_path: Path) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:conflict",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)
    created = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:conflict:create"},
    )
    base_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    first_submit = client.post(
        _submit_path(workflow_run_id, base_artifact_version_id),
        payload={
            "form_values": {"dispatcher_comment": "First submit"},
            "checklist_values": [],
            "idempotency_key": "api:eod-draft:conflict:first",
        },
    )
    assert first_submit.status_code == 200
    latest_artifact_version_id = str(first_submit.payload["submitted"]["artifact_version_id"])

    conflict = client.post(
        _submit_path(workflow_run_id, base_artifact_version_id),
        payload={
            "form_values": {"dispatcher_comment": "Stale retry"},
            "checklist_values": [],
            "idempotency_key": "api:eod-draft:conflict:stale",
        },
    )
    assert conflict.status_code == 409
    assert conflict.payload["error"]["code"] == "workpage_artifact_conflict"
    assert conflict.payload["error"]["details"] == {
        "artifact_version_id": base_artifact_version_id,
        "latest_artifact_version_id": latest_artifact_version_id,
        "workflow_run_id": created.payload["draft"]["workflow_run_id"],
        "route": f"/runs/{created.payload['draft']['workflow_run_id']}/workpages/eod-v0/artifacts/{latest_artifact_version_id}",
    }


def test_artifact_backed_eod_routes_fail_closed_for_wrong_family_and_scope(tmp_path: Path) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:scope-closed",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)
    other_client = _other_scope_client(tmp_path)

    created = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:scope-closed"},
    )
    artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    scope_denied = other_client.get(_artifact_path(workflow_run_id, artifact_version_id))
    assert scope_denied.status_code == 404
    assert scope_denied.payload["error"]["code"] == "workpage_artifact_not_found"

    wrong_family_artifact_version_id = _seed_schedule_artifact(_db_url(tmp_path))
    wrong_family = client.get(_artifact_path(workflow_run_id, wrong_family_artifact_version_id))
    assert wrong_family.status_code == 404
    assert wrong_family.payload["error"]["code"] == "workpage_artifact_not_found"


def test_created_and_submitted_workpage_artifacts_download_through_normal_binary_route(
    tmp_path: Path,
) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:eod-draft:download",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    client = _client(tmp_path)
    created = client.post(
        _draft_create_path(workflow_run_id),
        payload={"idempotency_key": "api:eod-draft:download:create"},
    )
    created_artifact_version_id = str(created.payload["draft"]["artifact_version_id"])

    created_binary = client.get_raw(f"/api/v1/artifacts/{created_artifact_version_id}/download.bin")
    assert created_binary.status_code == 200
    assert created_binary.body == REPORTING_TEMPLATE_PATH.read_bytes()
    assert created_binary.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    submitted = client.post(
        _submit_path(workflow_run_id, created_artifact_version_id),
        payload={
            "form_values": {
                "dispatcher_comment": "Downloaded after submit",
                "manager_note": "Binary route stays canonical.",
            },
            "checklist_values": [],
            "idempotency_key": "api:eod-draft:download:submit",
        },
    )
    submitted_artifact_version_id = str(submitted.payload["submitted"]["artifact_version_id"])

    submitted_binary = client.get_raw(
        f"/api/v1/artifacts/{submitted_artifact_version_id}/download.bin"
    )
    assert submitted_binary.status_code == 200
    projected = project_upd_draft_workbook(submitted_binary.body)
    assert projected["manual_closeout"] == [
        {
            "row_id": "manual-closeout",
            "sick_calls": "",
            "unavailable_drivers": "",
            "working_devices": "",
            "rescues": "",
            "incidents": "",
            "last_driver_clockout": "",
            "dispatcher_comment": "Downloaded after submit",
            "manager_note": "Binary route stays canonical.",
        }
    ]
    assert len(projected["change_log_stage03_upd_draft"]) == 1


def _seed_schedule_artifact(db_url: str) -> str:
    with open_sqlite_connection(db_url) as connection:
        created_run = create_workflow_run_command(
            connection,
            {
                "workflow_id": "schedule_planning.v1",
                "workflow_version": "v1",
                "tenant_id": "tenant-a",
                "domain_id": "domain-x",
                "partition_key": "PW-2026-W10",
                "logical_date": "2026-03-09",
                "activation_key": "tests:workpages-artifact-eod:wrong-family",
            },
        )
        artifact = ingest_artifact_document_command(
            connection,
            {
                "workflow_run_id": str(created_run["workflow_run_id"]),
                "artifact_kind": "schedule.draft_schedule.workbook",
                "file_name": SCHEDULE_TEMPLATE_PATH.name,
                "media_type": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                "content_base64": encode_base64_content(SCHEDULE_TEMPLATE_PATH.read_bytes()),
                "metadata_json": {"file_name": SCHEDULE_TEMPLATE_PATH.name},
                "idempotency_key": "tests:workpages-artifact-eod:wrong-family-artifact",
            },
            storage_root=default_storage_root_for_db_url(db_url),
        )
    return str(artifact["artifact_version"]["artifact_version_id"])
