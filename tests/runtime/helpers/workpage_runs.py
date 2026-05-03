from __future__ import annotations

import base64
import json
import sqlite3
from typing import Any

import yaml

from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_actual_ops_weekly_stage04_fixture_payloads,
)

from .dispatch_reporting import (
    REALISTIC_REPORTING_SERVICE_DATE,
    SUPPORTED_REPORTING_WORKBOOK_PATH,
    XLSX_MEDIA_TYPE,
    reporting_workbook_upload_metadata,
)
from .runtime_api import RuntimeApiClient
from .runtime_cli import REPO_ROOT, run_cli, stdout_json


_ACTUAL_OPS_SOURCE_MATERIAL_PATH = (
    REPO_ROOT / "fixtures" / "logistics" / "weekly_stage04_actual_ops_lab_source_material_v3.yaml"
)

_DATASET_PAYLOAD_KEYS: tuple[tuple[str, str], ...] = (
    ("planning.route_slot_requirements.workbook", "route_slot_requirements"),
    ("planning.driver_capabilities.workbook", "driver_capabilities"),
    ("planning.approved_availability.workbook", "approved_availability"),
    ("planning.actual_hours_snapshot.workbook", "actual_hours"),
)

_REPORTING_SOURCE_DATASET_KEYS: tuple[str, ...] = (
    "reporting.eos_raw.workbook",
    "reporting.actuals_normalized.workbook",
)


def seed_actual_ops_weekly_schedule_run(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
) -> dict[str, Any]:
    source_material = _load_actual_ops_source_material()
    fixture_payloads = build_actual_ops_weekly_stage04_fixture_payloads()

    run_cli("--db-url", db_url, "init-db")
    created_run = run_cli(
        "--db-url",
        db_url,
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": "weekly_schedule_planning.v1",
                "workflow_version": "v1",
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "partition_key": str(source_material["planning_week_id"]),
                "logical_date": str(source_material["scope_start"]),
                "activation_key": f"{run_tag}:weekly-schedule-workpage",
                "idempotency_key": f"{run_tag}:runs.create",
            },
            separators=(",", ":"),
        ),
    )
    workflow_run = stdout_json(created_run)["workflow_run"]
    workflow_run_id = str(workflow_run["workflow_run_id"])

    artifacts_by_kind: dict[str, dict[str, Any]] = {}
    for artifact_kind, payload_key in _DATASET_PAYLOAD_KEYS:
        created_artifact = run_cli(
            "--db-url",
            db_url,
            "artifacts",
            "create-version",
            "--json",
            json.dumps(
                {
                    "workflow_run_id": workflow_run_id,
                    "artifact_kind": artifact_kind,
                    "artifact_role": "official_input",
                    "media_type": "application/json",
                    "storage_uri": f"inmem://workpages/{run_tag}/{artifact_kind}",
                    "content_digest": f"sha256:{run_tag}:{artifact_kind}",
                    "metadata_json": fixture_payloads[payload_key],
                    "idempotency_key": f"{run_tag}:artifacts.create:{artifact_kind}",
                },
                separators=(",", ":"),
            ),
        )
        artifacts_by_kind[artifact_kind] = stdout_json(created_artifact)["artifact_version"]

    return {
        "workflow_run": workflow_run,
        "workflow_run_id": workflow_run_id,
        "artifacts_by_kind": artifacts_by_kind,
        "fixture_contract": str(source_material["fixture_contract"]),
    }


def seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
) -> dict[str, Any]:
    seeded = seed_actual_ops_weekly_schedule_run(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        run_tag=run_tag,
    )
    workflow_run_id = str(seeded["workflow_run_id"])
    artifacts_by_kind = seeded["artifacts_by_kind"]
    payload = {
        "workflow_run_id": workflow_run_id,
        "route_slot_requirements_artifact_version_id": str(
            artifacts_by_kind["planning.route_slot_requirements.workbook"]["artifact_version_id"]
        ),
        "driver_capabilities_artifact_version_id": str(
            artifacts_by_kind["planning.driver_capabilities.workbook"]["artifact_version_id"]
        ),
        "approved_availability_artifact_version_id": str(
            artifacts_by_kind["planning.approved_availability.workbook"]["artifact_version_id"]
        ),
        "actual_hours_artifact_version_id": str(
            artifacts_by_kind["planning.actual_hours_snapshot.workbook"]["artifact_version_id"]
        ),
        "idempotency_key": f"{run_tag}:schedule-control.build-weekly",
    }
    built = run_cli(
        "--db-url",
        db_url,
        "schedule-control",
        "build-weekly",
        "--json",
        json.dumps(payload, separators=(",", ":")),
    )
    seeded["stage04_outputs"] = stdout_json(built)["result"]["artifacts"]
    return seeded


def create_driver_preferences_snapshot(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    workflow_run_id: str,
    run_tag: str,
) -> dict[str, Any]:
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )
    return client.post(
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/driver-preferences-v0/snapshots",
        payload={"idempotency_key": f"{run_tag}:driver-preferences:create"},
    ).payload


def seed_dispatch_reporting_workpage_run(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
    include_source_artifacts: bool = True,
) -> dict[str, Any]:
    run_cli("--db-url", db_url, "init-db")
    created_run = run_cli(
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
                "partition_key": f"SD-{REALISTIC_REPORTING_SERVICE_DATE}",
                "logical_date": REALISTIC_REPORTING_SERVICE_DATE,
                "activation_key": f"{run_tag}:dispatch-reporting-workpage",
                "idempotency_key": f"{run_tag}:runs.create",
            },
            separators=(",", ":"),
        ),
    )
    workflow_run = stdout_json(created_run)["workflow_run"]
    workflow_run_id = str(workflow_run["workflow_run_id"])

    artifacts_by_kind: dict[str, dict[str, Any]] = {}
    if include_source_artifacts:
        for artifact_kind in _REPORTING_SOURCE_DATASET_KEYS:
            created_artifact = run_cli(
                "--db-url",
                db_url,
                "artifacts",
                "create-version",
                "--json",
                json.dumps(
                    {
                        "workflow_run_id": workflow_run_id,
                        "artifact_kind": artifact_kind,
                        "artifact_role": "official_input",
                        "media_type": "application/json",
                        "storage_uri": f"inmem://workpages/{run_tag}/{artifact_kind}",
                        "content_digest": f"sha256:{run_tag}:{artifact_kind}",
                        "metadata_json": {
                            "service_date": REALISTIC_REPORTING_SERVICE_DATE,
                            "workpage_seed": "dispatch-reporting-run",
                        },
                        "idempotency_key": f"{run_tag}:artifacts.create:{artifact_kind}",
                    },
                    separators=(",", ":"),
                ),
            )
            artifacts_by_kind[artifact_kind] = stdout_json(created_artifact)["artifact_version"]

    return {
        "workflow_run": workflow_run,
        "workflow_run_id": workflow_run_id,
        "artifacts_by_kind": artifacts_by_kind,
    }


def seed_imported_dispatch_reporting_workpage_run(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
    service_date: str = REALISTIC_REPORTING_SERVICE_DATE,
) -> dict[str, Any]:
    run_cli("--db-url", db_url, "init-db")
    created_run = run_cli(
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
                "activation_key": f"{run_tag}:dispatch-reporting-imported",
                "idempotency_key": f"{run_tag}:runs.create",
            },
            separators=(",", ":"),
        ),
    )
    workflow_run = stdout_json(created_run)["workflow_run"]
    workflow_run_id = str(workflow_run["workflow_run_id"])
    created_task = run_cli(
        "--db-url",
        db_url,
        "tasks",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "stage_id": "Stage01",
                "task_kind": "eos_input_intake",
                "activation_key": f"{run_tag}:stage01:eos_input_intake",
                "create_human_task": True,
                "candidate_roles": ["dispatch_supervisor"],
                "owner_role": "dispatch_supervisor",
                "idempotency_key": f"{run_tag}:tasks.create",
            },
            separators=(",", ":"),
        ),
    )
    intake_human_task_id = str(
        stdout_json(created_task)["result"]["human_task"]["human_task_id"]
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_id="human:dispatch-supervisor-seed",
        actor_type="human",
        actor_roles=["dispatch_supervisor", "operations_manager", "schedule_planner"],
    )
    claimed = client.post(
        f"/api/v1/human-tasks/{intake_human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"{run_tag}:claim",
        },
    )
    assert claimed.status_code == 200, claimed.payload
    uploaded = client.post(
        f"/api/v1/human-tasks/{intake_human_task_id}/artifacts/upload",
        payload={
            "artifact_kind": "reporting.eos_raw.workbook",
            "artifact_role": "official_input",
            "media_type": XLSX_MEDIA_TYPE,
            "file_name": f"{service_date}.xlsx",
            "metadata_json": reporting_workbook_upload_metadata(service_date),
            "content_base64": base64.b64encode(
                SUPPORTED_REPORTING_WORKBOOK_PATH.read_bytes()
            ).decode("ascii"),
            "idempotency_key": f"{run_tag}:upload",
        },
    )
    assert uploaded.status_code == 200, uploaded.payload
    completed = client.post(
        f"/api/v1/human-tasks/{intake_human_task_id}/complete",
        payload={
            "outcome": "complete",
            "idempotency_key": f"{run_tag}:complete",
        },
    )
    assert completed.status_code == 200, completed.payload

    connection = sqlite3.connect(db_url.removeprefix("sqlite:///"))
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT artifact_version_id, artifact_kind
            FROM artifact_versions
            WHERE workflow_run_id = ?
            ORDER BY created_at ASC, artifact_version_id ASC
            """,
            (workflow_run_id,),
        ).fetchall()
        artifacts_by_kind = {
            str(row["artifact_kind"]): {
                "artifact_version_id": str(row["artifact_version_id"]),
                "artifact_kind": str(row["artifact_kind"]),
            }
            for row in rows
        }
    finally:
        connection.close()

    return {
        "workflow_run": workflow_run,
        "workflow_run_id": workflow_run_id,
        "artifacts_by_kind": artifacts_by_kind,
        "intake_human_task_id": intake_human_task_id,
    }


def seed_weekly_workspace_supported_task_surface_with_draft(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
) -> dict[str, Any]:
    seeded = seed_actual_ops_weekly_schedule_run_with_stage04_outputs(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        run_tag=run_tag,
    )
    result = run_cli(
        "--db-url",
        db_url,
        "tasks",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_run_id": seeded["workflow_run_id"],
                "stage_id": "Stage05",
                "task_kind": "information_request",
                "activation_key": f"{run_tag}:task:create",
                "candidate_roles": ["schedule_planner"],
                "owner_role": "schedule_planner",
                "create_human_task": True,
                "idempotency_key": f"{run_tag}:task:create",
            },
            separators=(",", ":"),
        ),
    )
    seeded["workspace_surface"] = stdout_json(result)["result"]
    return seeded


def seed_weekly_workspace_stage04_task_surface_without_draft(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
) -> dict[str, Any]:
    seeded = seed_actual_ops_weekly_schedule_run(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        run_tag=run_tag,
    )
    result = run_cli(
        "--db-url",
        db_url,
        "tasks",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_run_id": seeded["workflow_run_id"],
                "stage_id": "Stage04",
                "task_kind": "work_item",
                "activation_key": f"{run_tag}:task:create",
                "candidate_roles": ["schedule_planner"],
                "owner_role": "schedule_planner",
                "create_human_task": True,
                "idempotency_key": f"{run_tag}:task:create",
            },
            separators=(",", ":"),
        ),
    )
    seeded["workspace_surface"] = stdout_json(result)["result"]
    return seeded


def seed_dispatch_workspace_stage04_approval_without_draft(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
) -> dict[str, Any]:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        run_tag=run_tag,
    )
    result = run_cli(
        "--db-url",
        db_url,
        "approvals",
        "request",
        "--json",
        json.dumps(
            {
                "workflow_run_id": seeded["workflow_run_id"],
                "approval_kind": "business_decision",
                "scope_kind": "stage",
                "scope_ref": "Stage04",
                "candidate_roles": ["dispatch_supervisor"],
                "required_role": "dispatch_supervisor",
                "action": "review_eod_draft",
                "idempotency_key": f"{run_tag}:approval:request",
            },
            separators=(",", ":"),
        ),
    )
    seeded["workspace_surface"] = {"approval": stdout_json(result)["approval"]}
    return seeded


def seed_dispatch_workspace_stage04_approval_with_draft(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
) -> dict[str, Any]:
    seeded = seed_dispatch_workspace_stage04_approval_without_draft(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        run_tag=run_tag,
    )
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_id="human:frontend-snapshot-exporter",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )
    seeded["draft"] = client.post(
        f"/api/v1/workpages/workflow-runs/{seeded['workflow_run_id']}/eod-v0/drafts",
        payload={"idempotency_key": f"{run_tag}:eod-draft:create"},
    ).payload
    return seeded


def seed_dispatch_workspace_stage04_review_task_with_draft(
    *,
    db_url: str,
    tenant_id: str,
    domain_id: str,
    run_tag: str,
) -> dict[str, Any]:
    seeded = seed_dispatch_reporting_workpage_run(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        run_tag=run_tag,
        include_source_artifacts=False,
    )
    result = run_cli(
        "--db-url",
        db_url,
        "tasks",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_run_id": seeded["workflow_run_id"],
                "stage_id": "Stage04",
                "task_kind": "final_packet_review",
                "activation_key": f"{run_tag}:task:create",
                "candidate_roles": ["dispatch_supervisor"],
                "owner_role": "dispatch_supervisor",
                "create_human_task": True,
                "idempotency_key": f"{run_tag}:task:create",
            },
            separators=(",", ":"),
        ),
    )
    seeded["workspace_surface"] = stdout_json(result)["result"]
    human_task_id = str(seeded["workspace_surface"]["human_task"]["human_task_id"])
    client = RuntimeApiClient(
        db_url=db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_id="human:dispatch-supervisor-seed",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )
    seeded["draft"] = client.post(
        f"/api/v1/workpages/workflow-runs/{seeded['workflow_run_id']}/eod-v0/drafts",
        payload={
            "subject_link": {
                "subject_kind": "human_task",
                "subject_id": human_task_id,
            },
            "idempotency_key": f"{run_tag}:eod-draft:create",
        },
    ).payload
    return seeded


def _load_actual_ops_source_material() -> dict[str, Any]:
    loaded = yaml.safe_load(_ACTUAL_OPS_SOURCE_MATERIAL_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError("weekly Stage04 actual-ops source material must decode to an object")
    return loaded
