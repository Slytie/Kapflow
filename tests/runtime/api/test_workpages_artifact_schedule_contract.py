from __future__ import annotations

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


SCHEDULE_DATASET_KEY = "planning.draft_weekly_schedule.workbook"
PUBLISHED_SCHEDULE_DATASET_KEY = "planning.published_weekly_schedule.workbook"
_UNSET = object()


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


def _action_by_id(
    actions: list[dict[str, object]],
    action_id: str,
) -> dict[str, object]:
    return next(action for action in actions if action["action_id"] == action_id)


def _create_human_task(
    tmp_path: Path,
    *,
    workflow_run_id: str,
    task_run_id: str,
    human_task_id: str,
    stage_id: str,
    task_kind: str,
    activation_key: str,
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
                "stage_id": stage_id,
                "task_kind": task_kind,
                "activation_key": activation_key,
                "create_human_task": True,
                "candidate_roles": ["schedule_planner", "operations_manager"],
                "owner_role": "operations_manager",
                "idempotency_key": f"api:workpages:artifact-schedule:task:{human_task_id}",
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(created)["result"]["human_task"]


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
                "action": "publish_weekly_base_schedule",
                "idempotency_key": f"api:workpages:artifact-schedule:approval:{approval_id}",
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(requested)["approval"]


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


def _load_artifact_version(
    tmp_path: Path,
    *,
    artifact_version_id: str,
) -> dict[str, Any]:
    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        row = connection.execute(
            """
            SELECT
                artifact_version_id,
                workflow_run_id,
                tenant_id,
                domain_id,
                artifact_kind,
                artifact_role,
                media_type,
                metadata_json,
                supersedes_artifact_version_id
            FROM artifact_versions
            WHERE artifact_version_id = ?
            """,
            (artifact_version_id,),
        ).fetchone()
    assert row is not None
    artifact = dict(row)
    artifact["metadata_json"] = json.loads(str(artifact["metadata_json"] or "{}"))
    return artifact


def _create_published_schedule_artifact(
    tmp_path: Path,
    *,
    workflow_run_id: str,
    draft_artifact_version_id: str,
    idempotency_key: str,
    accepted_series_key: str | None | object = _UNSET,
) -> dict[str, Any]:
    draft_artifact = _load_artifact_version(
        tmp_path,
        artifact_version_id=draft_artifact_version_id,
    )
    metadata_json = dict(draft_artifact["metadata_json"])
    metadata_json["published_from_artifact_version_id"] = draft_artifact_version_id
    if accepted_series_key is _UNSET:
        pass
    elif accepted_series_key is None:
        metadata_json.pop("accepted_series_key", None)
    else:
        metadata_json["accepted_series_key"] = accepted_series_key

    created = run_cli(
        "--db-url",
        _db_url(tmp_path),
        "artifacts",
        "create-version",
        "--json",
        json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "artifact_kind": PUBLISHED_SCHEDULE_DATASET_KEY,
                "artifact_role": "official_output",
                "media_type": str(draft_artifact["media_type"] or "application/json"),
                "storage_uri": (
                    f"inmem://workpages/{idempotency_key}/"
                    "planning.published_weekly_schedule.workbook"
                ),
                "content_digest": (
                    f"sha256:{idempotency_key}:planning.published_weekly_schedule.workbook"
                ),
                "metadata_json": metadata_json,
                "idempotency_key": idempotency_key,
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(created)["artifact_version"]


def _create_artifact_version(
    tmp_path: Path,
    *,
    workflow_run_id: str,
    artifact_kind: str,
    metadata_json: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    created = run_cli(
        "--db-url",
        _db_url(tmp_path),
        "artifacts",
        "create-version",
        "--json",
        json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "artifact_kind": artifact_kind,
                "artifact_role": "official_input",
                "media_type": "application/json",
                "storage_uri": f"inmem://workpages/{idempotency_key}/{artifact_kind}",
                "content_digest": f"sha256:{idempotency_key}:{artifact_kind}",
                "metadata_json": metadata_json,
                "idempotency_key": idempotency_key,
            },
            separators=(",", ":"),
        ),
    )
    return stdout_json(created)["artifact_version"]


def _update_artifact_metadata_json(
    tmp_path: Path,
    *,
    artifact_version_id: str,
    metadata_json: dict[str, Any],
) -> None:
    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        connection.execute(
            """
            UPDATE artifact_versions
            SET metadata_json = ?
            WHERE artifact_version_id = ?
            """,
            (json.dumps(metadata_json, separators=(",", ":")), artifact_version_id),
        )
        connection.commit()


def test_artifact_backed_schedule_workpage_returns_projected_contract(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:read",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(tmp_path)

    response = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}")
    assert response.status_code == 200

    payload = response.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.workpages.artifact"

    workpage = payload["workpage"]
    assert workpage["workpage_id"] == "schedule-v0"
    assert workpage["version"] == 2
    assert workpage["title"] == "Weekly schedule draft artifact"
    assert workpage["mode"] == "example"
    assert workpage["workflow_id"] == "weekly_schedule_planning.v1"
    assert workpage["dataset_key"] == SCHEDULE_DATASET_KEY
    assert workpage["source_artifact_version_id"] == artifact_version_id
    summary = workpage["summary"]
    assert summary["planning_week_id"] == "PW-2026-W13"
    assert summary["operational_week_start"] == "2026-03-22"
    assert summary["route_assignment_count"] > 0
    assert summary["reserve_assignment_count"] > 0
    assert summary["iteration_count"] > 0
    assert str(summary["source_bundle_id"]).startswith("bundle-")
    assert str(summary["candidate_delta_id"]).startswith("cand-")
    assert [section["kind"] for section in workpage["sections"]] == [
        "summary_cards",
        "schedule_heatmap",
        "table",
        "table",
        "table",
        "note_panel",
        "table",
        "table",
        "table",
        "history_stub",
    ]
    assert [section["table_id"] for section in workpage["sections"] if section["kind"] == "table"] == [
        "day_demand",
        "selected_day_preview",
        "driver_roster",
        "assignment_rows",
        "reserve_rows",
        "iteration_deltas",
    ]
    heatmap_section = next(
        section for section in workpage["sections"] if section["kind"] == "schedule_heatmap"
    )
    assignment_rows = next(
        section["rows"]
        for section in workpage["sections"]
        if section.get("table_id") == "assignment_rows"
    )
    reserve_rows = next(
        section["rows"]
        for section in workpage["sections"]
        if section.get("table_id") == "reserve_rows"
    )
    assert heatmap_section["service_dates"]
    assert heatmap_section["people"]
    assert heatmap_section["people"][0]["driver_name"]
    assert len(heatmap_section["people"][0]["cells"]) == len(heatmap_section["service_dates"])
    assert assignment_rows[0]["assigned_driver_id"]
    assert assignment_rows[0]["assignment_status"]
    assert reserve_rows[0]["assignment_status"]

    source = payload["source"]
    assert source == {
        "mode": "artifact_projection",
        "primary_dataset_key": SCHEDULE_DATASET_KEY,
        "source_dataset_keys": [
            "planning.draft_weekly_schedule.workbook",
            "planning.draft_weekly_schedule.doc",
            "planning.validation_summary.doc",
            "planning.schedule_calculation_snapshot.json",
        ],
        "source_artifact_version_id": artifact_version_id,
        "source_refs": [
            f"/api/v1/artifacts/{artifact_version_id}",
            f"/api/v1/artifacts/{seeded['stage04_outputs']['draft_doc']['artifact_version_id']}",
            f"/api/v1/artifacts/{seeded['stage04_outputs']['validation_summary']['artifact_version_id']}",
            f"/api/v1/artifacts/{seeded['stage04_outputs']['calculation_snapshot']['artifact_version_id']}",
        ],
    }

    freshness = payload["freshness"]
    assert freshness["source_kind"] == "artifact_version"
    assert freshness["source_version"] == artifact_version_id
    assert freshness["generated_at"]

    artifact_context = payload["artifact_context"]
    assert artifact_context == {
        "artifact_version_id": artifact_version_id,
        "workflow_run_id": workflow_run_id,
        "artifact_kind": SCHEDULE_DATASET_KEY,
        "supersedes_artifact_version_id": None,
        "superseded_by_artifact_version_id": None,
        "latest_in_chain_artifact_version_id": artifact_version_id,
        "download_path": f"/api/v1/artifacts/{artifact_version_id}/download.bin",
    }
    assert payload["artifact_state"] == {
        "state_kind": "draft",
        "artifact_kind": SCHEDULE_DATASET_KEY,
        "editable": True,
        "current_artifact_version_id": artifact_version_id,
        "latest_artifact_version_id": artifact_version_id,
        "accepted_artifact_version_id": None,
    }
    dependencies = {row["dependency_key"]: row for row in payload["dependencies"]}
    assert dependencies["route_slot_requirements"]["state"] == "aligned"
    assert dependencies["approved_availability"]["state"] == "aligned"
    assert dependencies["driver_capabilities"]["state"] == "aligned"
    assert dependencies["actual_hours"]["state"] == "aligned"
    assert dependencies["driver_preferences"]["state"] == "aligned"
    assert dependencies["route_slot_requirements"]["artifact_version_id"] == str(
        seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]["artifact_version_id"]
    )
    calculations = payload["calculations"]
    assert calculations["top_bar"]["days"]
    assert calculations["selected_day"]["service_date"]
    assert calculations["driver_metrics"]
    assert calculations["checks"]
    assert payload["draft_lineage"] == {
        "current_artifact_version_id": artifact_version_id,
        "latest_artifact_version_id": artifact_version_id,
        "previous_artifact_version_id": None,
        "recent_versions": [
            {
                "artifact_version_id": artifact_version_id,
                "supersedes_artifact_version_id": None,
            }
        ],
    }
    assert payload["accepted_series"] == {
        "series_key": "weekly_schedule_planning.v1:dvc4:pitt-meadows",
        "current_artifact_version_id": None,
        "previous_artifact_version_id": None,
        "next_artifact_version_id": None,
        "entries": [],
    }
    actions = payload["actions"]
    assert _action_by_id(actions, "workpage.schedule-v0.preview_recalc") == {
        "action_id": "workpage.schedule-v0.preview_recalc",
        "kind": "preview_recalc",
        "label": "Preview recalculation",
        "state": "available",
        "workpage_kind": "schedule-v0",
        "artifact_version_id": artifact_version_id,
        "preview_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"schedule-v0/artifacts/{artifact_version_id}/preview"
        ),
        "disabled_reason": None,
    }
    assert _action_by_id(actions, "workpage.schedule-v0.save_draft") == {
        "action_id": "workpage.schedule-v0.save_draft",
        "kind": "submit_artifact",
        "label": "Save draft",
        "state": "available",
        "workpage_kind": "schedule-v0",
        "artifact_version_id": artifact_version_id,
        "submit_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"schedule-v0/artifacts/{artifact_version_id}/submit"
        ),
        "disabled_reason": None,
    }
    assert _action_by_id(actions, "workpage.route-demand-v0.open_latest") == {
        "action_id": "workpage.route-demand-v0.open_latest",
        "kind": "open_latest",
        "label": "Open route demand",
        "state": "available",
        "workpage_kind": "route-demand-v0",
        "artifact_version_id": seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]["artifact_version_id"],
        "route": (
            f"/runs/{workflow_run_id}/workpages/route-demand-v0/artifacts/"
            f"{seeded['artifacts_by_kind']['planning.route_slot_requirements.workbook']['artifact_version_id']}"
        ),
    }

    downloaded = client.get_raw(f"/api/v1/artifacts/{artifact_version_id}/download.bin")
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/json"
    parsed_download = json.loads(downloaded.body.decode("utf-8"))
    assert parsed_download["columns"]
    assert parsed_download["rows"]
    assert parsed_download["dependency_manifest"]


def test_artifact_backed_schedule_workpage_reads_are_stable_except_for_generated_at(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:stable",
    )
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(tmp_path)
    path = f"/api/v1/workpages/artifacts/{artifact_version_id}"

    first = client.get(path)
    second = client.get(path)

    assert first.status_code == 200
    assert second.status_code == 200
    assert _without_generated_at(first.payload) == _without_generated_at(second.payload)


def test_artifact_backed_schedule_workpage_canonical_route_matches_alias(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:canonical-read",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(tmp_path)

    alias_response = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}")
    canonical_response = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{artifact_version_id}"
    )

    assert alias_response.status_code == 200
    assert canonical_response.status_code == 200
    assert _without_generated_at(alias_response.payload) == _without_generated_at(
        canonical_response.payload
    )


def test_schedule_artifact_route_rejects_wrong_artifact_family(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:wrong-kind",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    wrong_artifact_id = str(
        seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]["artifact_version_id"]
    )
    client = _client(tmp_path)

    response = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{wrong_artifact_id}"
    )
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "workpage_artifact_not_found"
    assert response.payload["error"]["details"] == {"artifact_version_id": wrong_artifact_id}


def test_artifact_backed_schedule_workpage_cross_scope_access_fails_closed(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:cross-scope",
    )
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _other_scope_client(tmp_path)

    response = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}")
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "workpage_artifact_not_found"
    assert response.payload["error"]["details"] == {"artifact_version_id": artifact_version_id}


def test_published_schedule_artifact_reads_under_schedule_workpage_kind(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:published-read",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    draft_artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    published = _create_published_schedule_artifact(
        tmp_path,
        workflow_run_id=workflow_run_id,
        draft_artifact_version_id=draft_artifact_version_id,
        idempotency_key="api:workpages:artifact-schedule:published-read:create",
    )
    published_artifact_version_id = str(published["artifact_version_id"])
    client = _client(tmp_path)

    response = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{published_artifact_version_id}"
    )
    assert response.status_code == 200

    payload = response.payload
    assert payload["workpage"]["title"] == "Weekly published schedule artifact"
    assert payload["workpage"]["dataset_key"] == PUBLISHED_SCHEDULE_DATASET_KEY
    assert payload["source"] == {
        "mode": "artifact_projection",
        "primary_dataset_key": PUBLISHED_SCHEDULE_DATASET_KEY,
        "source_dataset_keys": [
            PUBLISHED_SCHEDULE_DATASET_KEY,
            "planning.draft_weekly_schedule.doc",
            "planning.validation_summary.doc",
            "planning.schedule_calculation_snapshot.json",
        ],
        "source_artifact_version_id": published_artifact_version_id,
        "source_refs": [
            f"/api/v1/artifacts/{published_artifact_version_id}",
            f"/api/v1/artifacts/{seeded['stage04_outputs']['draft_doc']['artifact_version_id']}",
            f"/api/v1/artifacts/{seeded['stage04_outputs']['validation_summary']['artifact_version_id']}",
            f"/api/v1/artifacts/{seeded['stage04_outputs']['calculation_snapshot']['artifact_version_id']}",
        ],
    }
    assert payload["artifact_context"]["artifact_kind"] == PUBLISHED_SCHEDULE_DATASET_KEY
    assert payload["artifact_state"] == {
        "state_kind": "accepted",
        "artifact_kind": PUBLISHED_SCHEDULE_DATASET_KEY,
        "editable": False,
        "current_artifact_version_id": published_artifact_version_id,
        "latest_artifact_version_id": published_artifact_version_id,
        "accepted_artifact_version_id": published_artifact_version_id,
    }
    assert payload["draft_lineage"]["current_artifact_version_id"] == draft_artifact_version_id
    assert payload["draft_lineage"]["latest_artifact_version_id"] == draft_artifact_version_id
    assert payload["draft_lineage"]["previous_artifact_version_id"] is None
    assert payload["draft_lineage"]["recent_versions"] == [
        {
            "artifact_version_id": draft_artifact_version_id,
            "supersedes_artifact_version_id": None,
        }
    ]
    assert payload["accepted_series"]["series_key"]
    assert payload["accepted_series"]["current_artifact_version_id"] == published_artifact_version_id
    assert payload["accepted_series"]["entries"] == [
        {
            "artifact_version_id": published_artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "partition_key": "PW-2026-W13",
            "logical_date": "2026-03-22",
            "artifact_kind": PUBLISHED_SCHEDULE_DATASET_KEY,
        }
    ]
    assert payload["actions"] == [
        {
            "action_id": "workpage.route-demand-v0.open_latest",
            "kind": "open_latest",
            "label": "Open route demand",
            "state": "available",
            "workpage_kind": "route-demand-v0",
            "artifact_version_id": seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]["artifact_version_id"],
            "route": (
                f"/runs/{workflow_run_id}/workpages/route-demand-v0/artifacts/"
                f"{seeded['artifacts_by_kind']['planning.route_slot_requirements.workbook']['artifact_version_id']}"
            ),
        }
    ]


def test_published_schedule_accepted_series_groups_same_key_only_with_scope_isolation(
    tmp_path: Path,
) -> None:
    older = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:accepted-series:older",
    )
    current = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:accepted-series:current",
    )
    newer = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:accepted-series:newer",
    )
    other_scope = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-b",
        domain_id="domain-y",
        run_tag="api:workpages:artifact-schedule:accepted-series:other-scope",
    )

    older_published = _create_published_schedule_artifact(
        tmp_path,
        workflow_run_id=str(older["workflow_run_id"]),
        draft_artifact_version_id=str(older["stage04_outputs"]["draft_workbook"]["artifact_version_id"]),
        idempotency_key="api:workpages:artifact-schedule:accepted-series:older:create",
    )
    current_published = _create_published_schedule_artifact(
        tmp_path,
        workflow_run_id=str(current["workflow_run_id"]),
        draft_artifact_version_id=str(current["stage04_outputs"]["draft_workbook"]["artifact_version_id"]),
        idempotency_key="api:workpages:artifact-schedule:accepted-series:current:create",
    )
    newer_published = _create_published_schedule_artifact(
        tmp_path,
        workflow_run_id=str(newer["workflow_run_id"]),
        draft_artifact_version_id=str(newer["stage04_outputs"]["draft_workbook"]["artifact_version_id"]),
        idempotency_key="api:workpages:artifact-schedule:accepted-series:newer:create",
    )
    _create_published_schedule_artifact(
        tmp_path,
        workflow_run_id=str(current["workflow_run_id"]),
        draft_artifact_version_id=str(current["stage04_outputs"]["draft_workbook"]["artifact_version_id"]),
        idempotency_key="api:workpages:artifact-schedule:accepted-series:other-key:create",
        accepted_series_key="weekly_schedule_planning.v1:different-station:different-area",
    )
    _create_published_schedule_artifact(
        tmp_path,
        workflow_run_id=str(other_scope["workflow_run_id"]),
        draft_artifact_version_id=str(other_scope["stage04_outputs"]["draft_workbook"]["artifact_version_id"]),
        idempotency_key="api:workpages:artifact-schedule:accepted-series:other-scope:create",
    )
    client = _client(tmp_path)
    current_published_artifact_version_id = str(current_published["artifact_version_id"])

    response = client.get(
        f"/api/v1/workpages/workflow-runs/{current['workflow_run_id']}/"
        f"schedule-v0/artifacts/{current_published_artifact_version_id}"
    )
    assert response.status_code == 200

    accepted_series = response.payload["accepted_series"]
    assert accepted_series["current_artifact_version_id"] == current_published_artifact_version_id
    assert accepted_series["previous_artifact_version_id"] == str(
        older_published["artifact_version_id"]
    )
    assert accepted_series["next_artifact_version_id"] == str(newer_published["artifact_version_id"])
    assert accepted_series["entries"] == [
        {
            "artifact_version_id": str(older_published["artifact_version_id"]),
            "workflow_run_id": str(older["workflow_run_id"]),
            "partition_key": "PW-2026-W13",
            "logical_date": "2026-03-22",
            "artifact_kind": PUBLISHED_SCHEDULE_DATASET_KEY,
        },
        {
            "artifact_version_id": current_published_artifact_version_id,
            "workflow_run_id": str(current["workflow_run_id"]),
            "partition_key": "PW-2026-W13",
            "logical_date": "2026-03-22",
            "artifact_kind": PUBLISHED_SCHEDULE_DATASET_KEY,
        },
        {
            "artifact_version_id": str(newer_published["artifact_version_id"]),
            "workflow_run_id": str(newer["workflow_run_id"]),
            "partition_key": "PW-2026-W13",
            "logical_date": "2026-03-22",
            "artifact_kind": PUBLISHED_SCHEDULE_DATASET_KEY,
        },
    ]


def test_published_schedule_without_accepted_series_key_returns_empty_series(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:accepted-series:missing-key",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    draft_artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    published = _create_published_schedule_artifact(
        tmp_path,
        workflow_run_id=workflow_run_id,
        draft_artifact_version_id=draft_artifact_version_id,
        idempotency_key="api:workpages:artifact-schedule:accepted-series:missing-key:create",
        accepted_series_key=None,
    )
    client = _client(tmp_path)

    response = client.get(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{published['artifact_version_id']}"
    )
    assert response.status_code == 200
    assert response.payload["accepted_series"] == {
        "series_key": None,
        "current_artifact_version_id": None,
        "previous_artifact_version_id": None,
        "next_artifact_version_id": None,
        "entries": [],
    }


def test_schedule_artifact_submit_canonical_route_matches_alias(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:canonical-submit",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(tmp_path)
    assignment_rows, reserve_rows = _schedule_submit_rows(client, artifact_version_id)

    canonical = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "api:workpages:artifact-schedule:canonical-submit:001",
        },
    )
    alias = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "api:workpages:artifact-schedule:canonical-submit:001",
        },
    )

    assert canonical.status_code == 200
    assert alias.status_code == 200
    assert alias.payload == canonical.payload


def test_schedule_artifact_preview_canonical_route_matches_alias(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:canonical-preview",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(tmp_path)
    assignment_rows, reserve_rows = _schedule_submit_rows(client, artifact_version_id)

    canonical = client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"schedule-v0/artifacts/{artifact_version_id}/preview",
        payload={"rows": assignment_rows, "reserve_rows": reserve_rows},
    )
    alias = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/preview",
        payload={"rows": assignment_rows, "reserve_rows": reserve_rows},
    )

    assert canonical.status_code == 200
    assert alias.status_code == 200
    assert alias.payload == canonical.payload


def test_schedule_artifact_preview_recalculates_without_creating_artifacts(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:preview",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(tmp_path)
    assignment_rows, reserve_rows = _schedule_submit_rows(client, artifact_version_id)
    assignment_rows[0]["assigned_driver_id"] = "DRV-PREVIEW-77"
    assignment_rows[0]["assignment_status"] = "manual_override"

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        before_count = connection.execute(
            "SELECT COUNT(*) AS count FROM artifact_versions WHERE workflow_run_id = ?",
            (workflow_run_id,),
        ).fetchone()["count"]

    response = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/preview",
        payload={"rows": assignment_rows, "reserve_rows": reserve_rows},
    )
    assert response.status_code == 200
    preview = response.payload["preview"]
    assert preview["artifact_version_id"] == artifact_version_id
    assert preview["workflow_run_id"] == workflow_run_id
    assert preview["dirty"] is True
    assert preview["dependency_state"] == "aligned"
    assert preview["dependencies"]
    assert preview["calculations"]["top_bar"]["days"]
    assert preview["calculations"]["driver_metrics"]
    assert preview["calculations"]["checks"]

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        after_count = connection.execute(
            "SELECT COUNT(*) AS count FROM artifact_versions WHERE workflow_run_id = ?",
            (workflow_run_id,),
        ).fetchone()["count"]
    assert after_count == before_count


def test_schedule_artifact_submit_creates_superseding_version_and_replays_idempotently(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:submit",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(tmp_path)

    base = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}").payload
    assignment_rows = deepcopy(
        next(
            section["rows"]
            for section in base["workpage"]["sections"]
            if section.get("table_id") == "assignment_rows"
        )
    )
    reserve_rows = deepcopy(
        next(
            section["rows"]
            for section in base["workpage"]["sections"]
            if section.get("table_id") == "reserve_rows"
        )
    )
    assignment_rows[0]["assigned_driver_id"] = "DRV-MANUAL-77"
    assignment_rows[0]["assignment_status"] = "manual_override"
    reserve_rows[0]["assigned_driver_id"] = "DRV-MANUAL-88"
    reserve_rows[0]["assignment_status"] = "manual_override"

    first = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "api:workpages:artifact-schedule:submit:001",
        },
    )
    second = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "api:workpages:artifact-schedule:submit:001",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.payload == first.payload

    submitted = first.payload["submitted"]
    submitted_artifact_version_id = str(submitted["artifact_version_id"])
    assert submitted["workflow_run_id"] == workflow_run_id
    assert submitted["supersedes_artifact_version_id"] == artifact_version_id
    assert submitted["route"] == (
        f"/runs/{workflow_run_id}/workpages/schedule-v0/artifacts/{submitted_artifact_version_id}"
    )

    refreshed = client.get(f"/api/v1/workpages/artifacts/{submitted_artifact_version_id}")
    assert refreshed.status_code == 200
    refreshed_assignment_rows = next(
        section["rows"]
        for section in refreshed.payload["workpage"]["sections"]
        if section.get("table_id") == "assignment_rows"
    )
    refreshed_reserve_rows = next(
        section["rows"]
        for section in refreshed.payload["workpage"]["sections"]
        if section.get("table_id") == "reserve_rows"
    )
    assert refreshed_assignment_rows[0]["assigned_driver_id"] == "DRV-MANUAL-77"
    assert refreshed_assignment_rows[0]["assignment_status"] == "manual_override"
    assert refreshed_reserve_rows[0]["assigned_driver_id"] == "DRV-MANUAL-88"
    assert refreshed_reserve_rows[0]["assignment_status"] == "manual_override"
    assert refreshed.payload["source"]["source_refs"][0] == (
        f"/api/v1/artifacts/{submitted_artifact_version_id}"
    )
    assert refreshed.payload["source"]["source_dataset_keys"] == [
        "planning.draft_weekly_schedule.workbook",
        "planning.draft_weekly_schedule.doc",
        "planning.validation_summary.doc",
        "planning.schedule_calculation_snapshot.json",
    ]

    with open_sqlite_connection(_db_url(tmp_path)) as connection:
        companion_rows = connection.execute(
            """
            SELECT artifact_kind
            FROM artifact_versions
            WHERE parent_artifact_version_id = ?
            ORDER BY artifact_kind ASC
            """,
            (submitted_artifact_version_id,),
        ).fetchall()
    assert [str(row["artifact_kind"]) for row in companion_rows] == [
        "planning.draft_weekly_schedule.doc",
        "planning.schedule_calculation_snapshot.json",
        "planning.validation_summary.doc",
    ]


def test_schedule_artifact_submit_links_response_to_supported_human_task_surface(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:subject-human-task",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    task = _create_human_task(
        tmp_path,
        workflow_run_id=workflow_run_id,
        task_run_id="tr-stage05-info",
        human_task_id="ht-stage05-info",
        stage_id="Stage05",
        task_kind="information_request",
        activation_key="stage05-information-request",
    )
    client = _client(tmp_path)
    assignment_rows, reserve_rows = _schedule_submit_rows(client, artifact_version_id)

    response = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "subject_link": {
                "subject_kind": "human_task",
                "subject_id": str(task["human_task_id"]),
            },
            "idempotency_key": "api:workpages:artifact-schedule:subject-human-task",
        },
    )
    assert response.status_code == 200
    submitted_artifact_version_id = str(response.payload["submitted"]["artifact_version_id"])

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
            "subject_id": "ht-stage05-info",
            "relation_kind": "response",
        }
    ]


def test_schedule_artifact_submit_links_response_to_supported_stage06_approval_surface(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:subject-approval",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    approval = _request_approval(
        tmp_path,
        workflow_run_id=workflow_run_id,
        approval_id="ap-stage06-publish",
        scope_ref="Stage06",
    )
    client = _client(tmp_path)
    assignment_rows, reserve_rows = _schedule_submit_rows(client, artifact_version_id)

    response = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "subject_link": {
                "subject_kind": "approval",
                "subject_id": str(approval["approval_id"]),
            },
            "idempotency_key": "api:workpages:artifact-schedule:subject-approval",
        },
    )
    assert response.status_code == 200
    submitted_artifact_version_id = str(response.payload["submitted"]["artifact_version_id"])

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
            "subject_id": "ap-stage06-publish",
            "relation_kind": "response",
        }
    ]


def test_schedule_artifact_submit_rejects_stale_base_versions(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:stale",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    client = _client(tmp_path)

    base = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}").payload
    assignment_rows = deepcopy(
        next(
            section["rows"]
            for section in base["workpage"]["sections"]
            if section.get("table_id") == "assignment_rows"
        )
    )
    reserve_rows = deepcopy(
        next(
            section["rows"]
            for section in base["workpage"]["sections"]
            if section.get("table_id") == "reserve_rows"
        )
    )
    assignment_rows[0]["assigned_driver_id"] = "DRV-MANUAL-77"
    assignment_rows[0]["assignment_status"] = "manual_override"

    created = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "api:workpages:artifact-schedule:stale:create",
        },
    )
    latest_artifact_version_id = str(created.payload["submitted"]["artifact_version_id"])

    stale = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "api:workpages:artifact-schedule:stale:retry",
        },
    )
    assert stale.status_code == 409
    assert stale.payload["error"]["code"] == "workpage_artifact_conflict"
    assert stale.payload["error"]["details"] == {
        "artifact_version_id": artifact_version_id,
        "latest_artifact_version_id": latest_artifact_version_id,
        "workflow_run_id": workflow_run_id,
        "route": f"/runs/{workflow_run_id}/workpages/schedule-v0/artifacts/{latest_artifact_version_id}",
    }


def test_schedule_artifact_hard_dependency_drift_surfaces_and_blocks_save(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:dependency-drift",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    route_artifact_id = str(
        seeded["artifacts_by_kind"]["planning.route_slot_requirements.workbook"]["artifact_version_id"]
    )
    route_artifact = _load_artifact_version(tmp_path, artifact_version_id=route_artifact_id)
    _create_artifact_version(
        tmp_path,
        workflow_run_id=workflow_run_id,
        artifact_kind="planning.route_slot_requirements.workbook",
        metadata_json=dict(route_artifact["metadata_json"]),
        idempotency_key="api:workpages:artifact-schedule:dependency-drift:new-route-demand",
    )
    client = _client(tmp_path)

    payload = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}").payload
    dependencies = {row["dependency_key"]: row for row in payload["dependencies"]}
    assert dependencies["route_slot_requirements"]["state"] == "drifted"
    actions = payload["actions"]
    assert _action_by_id(actions, "workpage.schedule-v0.preview_recalc") == {
        "action_id": "workpage.schedule-v0.preview_recalc",
        "kind": "preview_recalc",
        "label": "Preview recalculation",
        "state": "available",
        "workpage_kind": "schedule-v0",
        "artifact_version_id": artifact_version_id,
        "preview_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"schedule-v0/artifacts/{artifact_version_id}/preview"
        ),
        "disabled_reason": None,
    }
    assert _action_by_id(actions, "workpage.schedule-v0.save_draft") == {
        "action_id": "workpage.schedule-v0.save_draft",
        "kind": "submit_artifact",
        "label": "Save draft",
        "state": "blocked",
        "workpage_kind": "schedule-v0",
        "artifact_version_id": artifact_version_id,
        "submit_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"schedule-v0/artifacts/{artifact_version_id}/submit"
        ),
        "disabled_reason": "dependency_drift_detected",
    }
    assert _action_by_id(actions, "workpage.route-demand-v0.open_latest")["state"] == "available"

    assignment_rows, reserve_rows = _schedule_submit_rows(client, artifact_version_id)
    preview = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/preview",
        payload={"rows": assignment_rows, "reserve_rows": reserve_rows},
    )
    assert preview.status_code == 200
    assert preview.payload["preview"]["dependency_state"] == "drifted"

    denied = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "api:workpages:artifact-schedule:dependency-drift:submit",
        },
    )
    assert denied.status_code == 400
    assert denied.payload["error"]["code"] == "dependency_drift_detected"


def test_schedule_artifact_without_pinned_manifest_remains_readable_but_blocks_preview_and_save(
    tmp_path: Path,
) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:not-pinned",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    base_artifact = _load_artifact_version(tmp_path, artifact_version_id=artifact_version_id)
    metadata_json = dict(base_artifact["metadata_json"])
    metadata_json.pop("dependency_manifest", None)
    _update_artifact_metadata_json(
        tmp_path,
        artifact_version_id=artifact_version_id,
        metadata_json=metadata_json,
    )
    client = _client(tmp_path)

    payload = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}").payload
    dependencies = {row["dependency_key"]: row for row in payload["dependencies"]}
    assert dependencies["route_slot_requirements"]["state"] == "not_pinned"
    assert dependencies["approved_availability"]["state"] == "not_pinned"
    assert dependencies["driver_capabilities"]["state"] == "not_pinned"
    assert dependencies["actual_hours"]["state"] == "not_pinned"
    actions = payload["actions"]
    assert _action_by_id(actions, "workpage.schedule-v0.preview_recalc") == {
        "action_id": "workpage.schedule-v0.preview_recalc",
        "kind": "preview_recalc",
        "label": "Preview recalculation",
        "state": "blocked",
        "workpage_kind": "schedule-v0",
        "artifact_version_id": artifact_version_id,
        "preview_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"schedule-v0/artifacts/{artifact_version_id}/preview"
        ),
        "disabled_reason": "dependency_baseline_unavailable",
    }
    assert _action_by_id(actions, "workpage.schedule-v0.save_draft") == {
        "action_id": "workpage.schedule-v0.save_draft",
        "kind": "submit_artifact",
        "label": "Save draft",
        "state": "blocked",
        "workpage_kind": "schedule-v0",
        "artifact_version_id": artifact_version_id,
        "submit_path": (
            f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
            f"schedule-v0/artifacts/{artifact_version_id}/submit"
        ),
        "disabled_reason": "dependency_baseline_unavailable",
    }
    assert _action_by_id(actions, "workpage.route-demand-v0.open_latest")["state"] == "available"

    assignment_rows, reserve_rows = _schedule_submit_rows(client, artifact_version_id)
    preview = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/preview",
        payload={"rows": assignment_rows, "reserve_rows": reserve_rows},
    )
    assert preview.status_code == 400
    assert preview.payload["error"]["code"] == "dependency_baseline_unavailable"

    denied = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "idempotency_key": "api:workpages:artifact-schedule:not-pinned:submit",
        },
    )
    assert denied.status_code == 400
    assert denied.payload["error"]["code"] == "dependency_baseline_unavailable"


def test_schedule_artifact_submit_cross_scope_denial_fails_closed(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:cross-scope-submit",
    )
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    other_scope_client = _other_scope_client(tmp_path)

    response = other_scope_client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": [],
            "reserve_rows": [],
            "idempotency_key": "api:workpages:artifact-schedule:cross-scope-submit",
        },
    )
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "workpage_artifact_not_found"
    assert response.payload["error"]["details"] == {"artifact_version_id": artifact_version_id}


def test_schedule_artifact_submit_rejects_unsupported_subject_surface(tmp_path: Path) -> None:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:unsupported-subject",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])
    task = _create_human_task(
        tmp_path,
        workflow_run_id=workflow_run_id,
        task_run_id="tr-stage06-final-review",
        human_task_id="ht-stage06-final-review",
        stage_id="Stage06",
        task_kind="final_review",
        activation_key="stage06-final-review",
    )
    client = _client(tmp_path)
    assignment_rows, reserve_rows = _schedule_submit_rows(client, artifact_version_id)

    response = client.post(
        f"/api/v1/workpages/artifacts/{artifact_version_id}/submit",
        payload={
            "rows": assignment_rows,
            "reserve_rows": reserve_rows,
            "subject_link": {
                "subject_kind": "human_task",
                "subject_id": str(task["human_task_id"]),
            },
            "idempotency_key": "api:workpages:artifact-schedule:unsupported-subject",
        },
    )
    assert response.status_code == 400
    assert response.payload["error"]["code"] == "invalid_workpage_subject_link"
    assert response.payload["error"]["details"]["stage_id"] == "Stage06"
    assert response.payload["error"]["details"]["task_kind"] == "final_review"


def test_schedule_artifact_route_rejects_non_weekly_schedule_artifacts(tmp_path: Path) -> None:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=_db_url(tmp_path),
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="api:workpages:artifact-schedule:wrong-workflow",
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    run_cli("--db-url", _db_url(tmp_path), "init-db")
    created_artifact = run_cli(
        "--db-url",
        _db_url(tmp_path),
        "artifacts",
        "create-version",
        "--json",
        json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "artifact_kind": "planning.draft_weekly_schedule.workbook",
                "artifact_role": "official_input",
                "media_type": "application/json",
                "storage_uri": "inmem://wrong-workflow/schedule-draft",
                "content_digest": "sha256:wrong-workflow:schedule-draft",
                "metadata_json": {
                    "columns": ["service_date", "route_slot_id", "assigned_driver_id", "assignment_status"],
                    "rows": [["2026-03-16", "slot-001", "DRV-01", "assigned"]],
                    "reserve_rows": [],
                    "iteration_deltas": [],
                },
                "idempotency_key": "api:workpages:artifact-schedule:wrong-workflow:create",
            },
            separators=(",", ":"),
        ),
    )
    artifact_version_id = str(stdout_json(created_artifact)["artifact_version"]["artifact_version_id"])
    client = _client(tmp_path)

    response = client.get(f"/api/v1/workpages/artifacts/{artifact_version_id}")
    assert response.status_code == 404
    assert response.payload["error"]["code"] == "workpage_artifact_not_found"
    assert response.payload["error"]["details"] == {"artifact_version_id": artifact_version_id}


def _without_generated_at(payload: dict[str, object]) -> dict[str, object]:
    copied = deepcopy(payload)
    freshness = copied.get("freshness")
    if isinstance(freshness, dict):
        freshness.pop("generated_at", None)
    return copied
