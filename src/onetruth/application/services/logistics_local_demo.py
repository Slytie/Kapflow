from __future__ import annotations

from datetime import date, timedelta
import hashlib
import os
from pathlib import Path
import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.artifacts import ingest_artifact_document_command
from onetruth.application.handlers.logistics_handoff import notify_only_handoff_command
from onetruth.application.handlers.pointers import promote_pointer_command
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_task_run_command,
    create_workflow_run_command,
)
from onetruth.infrastructure.artifacts.storage import ArtifactIngressDescriptor, default_storage_root_for_db_url
from onetruth.infrastructure.repositories.artifact_pointers import get_pointer
from onetruth.infrastructure.repositories.artifact_versions import get_artifact_version
from onetruth.infrastructure.repositories.human_tasks import get_human_task_by_task_run_id
from onetruth.infrastructure.repositories.task_runs import get_task_run_by_activation_key
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run, list_workflow_runs

DEMO_TENANT_ID = "tenant-logistics"
DEMO_DOMAIN_ID = "domain-hub"
DEFAULT_PLANNING_WEEK_ID = "PW-2026-W10"
DEFAULT_SERVICE_DATE_ID = "SD-2026-03-06"
CURRENT_WEEKLY_WORKFLOW_ID = "weekly_schedule_planning.v1"
REPORTING_WORKFLOW_ID = "dispatch_reporting.v1"
REPORTING_FINAL_PACKET_ARTIFACT_KIND = "reporting.final_packet.workbook"
REPORTING_FINAL_PACKET_POINTER_KEY = "official:reporting.final_packet.workbook"
REPORTING_TO_PLANNING_EDGE_ID = "reporting_actuals_to_future_planning"
UPLOAD_PACK_ROOT = Path(__file__).resolve().parents[4] / "fixtures" / "logistics" / "local_demo_upload_pack"
REPORTING_EOS_EXAMPLE_PATH = (
    Path(__file__).resolve().parents[4]
    / "fixtures"
    / "workflows"
    / "dispatch_reporting"
    / "template_pack"
    / "Stage01_EOS_Intake"
    / "Stage01_EOS_Intake_eos_raw_Spreadsheet_Example_COMPLETED.xlsx"
)


def seed_weekly_first_logistics_local_demo(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    planning_week_id: str = DEFAULT_PLANNING_WEEK_ID,
    service_date_id: str = DEFAULT_SERVICE_DATE_ID,
) -> dict[str, Any]:
    weekly_run_id = _stable_id("wr-demo-weekly", planning_week_id)
    current_reporting_run_id = _stable_id("wr-demo-reporting-current", service_date_id)
    prior_service_date_id = _prior_service_date_id(service_date_id)
    prior_reporting_run_id = _stable_id("wr-demo-reporting-feedback", prior_service_date_id)
    prior_reporting_final_artifact_id = _stable_id("av-demo-reporting-final", prior_service_date_id)

    weekly_run = _ensure_workflow_run(
        connection,
        workflow_run_id=weekly_run_id,
        workflow_id=CURRENT_WEEKLY_WORKFLOW_ID,
        partition_key=planning_week_id,
        logical_date=_planning_week_start(planning_week_id),
        activation_key=f"logistics-demo:weekly:{planning_week_id}",
    )
    _ensure_human_task(
        connection,
        workflow_run_id=weekly_run_id,
        task_run_id=_stable_id("tr-demo-weekly-intake", planning_week_id),
        human_task_id=_stable_id("ht-demo-weekly-intake", planning_week_id),
        stage_id="Stage04",
        task_kind="weekly_input_intake",
        activation_key=f"logistics-demo:weekly:stage04:intake:{planning_week_id}",
        candidate_roles=["schedule_planner"],
        owner_role="schedule_planner",
        actor_id="human:demo-operator",
        actor_type="human",
    )

    prior_reporting_run = _ensure_workflow_run(
        connection,
        workflow_run_id=prior_reporting_run_id,
        workflow_id=REPORTING_WORKFLOW_ID,
        partition_key=prior_service_date_id,
        logical_date=prior_service_date_id.removeprefix("SD-"),
        activation_key=f"logistics-demo:reporting:feedback:{prior_service_date_id}",
    )
    prior_reporting_final_packet = _ensure_ingested_artifact(
        connection,
        db_url=db_url,
        artifact_version_id=prior_reporting_final_artifact_id,
        workflow_run_id=prior_reporting_run_id,
        artifact_kind=REPORTING_FINAL_PACKET_ARTIFACT_KIND,
        artifact_role="official_output",
        file_name=f"demo-reporting-final-{prior_service_date_id}.xlsx",
        source_path=REPORTING_EOS_EXAMPLE_PATH,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        metadata_json={
            "demo_seed": "weekly_first_local_demo",
            "file_name": f"demo-reporting-final-{prior_service_date_id}.xlsx",
            "service_date_id": prior_service_date_id,
        },
        idempotency_key=f"demo:{planning_week_id}:{service_date_id}:prior-reporting-final",
        actor_id="human:demo-operator",
        actor_type="human",
    )
    _ensure_pointer(
        connection,
        workflow_run_id=prior_reporting_run_id,
        scope_kind="stage",
        scope_ref="Stage04",
        pointer_key=REPORTING_FINAL_PACKET_POINTER_KEY,
        artifact_kind=REPORTING_FINAL_PACKET_ARTIFACT_KIND,
        artifact_version_id=str(prior_reporting_final_packet["artifact_version_id"]),
        promotion_reason="official_finalize",
        idempotency_key=f"demo:{planning_week_id}:{service_date_id}:prior-reporting-pointer",
        actor_id="human:demo-operator",
        actor_type="human",
    )
    notify_only_handoff_command(
        connection,
        {
            "edge_id": REPORTING_TO_PLANNING_EDGE_ID,
            "source_workflow_run_id": prior_reporting_run_id,
            "source_artifact_version_id": str(prior_reporting_final_packet["artifact_version_id"]),
            "idempotency_key": f"demo:{planning_week_id}:{service_date_id}:reporting-feedback-handoff",
        },
    )

    current_reporting_run = _ensure_workflow_run(
        connection,
        workflow_run_id=current_reporting_run_id,
        workflow_id=REPORTING_WORKFLOW_ID,
        partition_key=service_date_id,
        logical_date=service_date_id.removeprefix("SD-"),
        activation_key=f"logistics-demo:reporting:current:{service_date_id}",
    )
    _ensure_human_task(
        connection,
        workflow_run_id=current_reporting_run_id,
        task_run_id=_stable_id("tr-demo-reporting-intake", service_date_id),
        human_task_id=_stable_id("ht-demo-reporting-intake", service_date_id),
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key=f"logistics-demo:reporting:stage01:intake:{service_date_id}",
        candidate_roles=["dispatch_supervisor"],
        owner_role="dispatch_supervisor",
        actor_id="human:demo-operator",
        actor_type="human",
    )

    return {
        "planning_week_id": planning_week_id,
        "service_date_id": service_date_id,
        "prior_feedback_service_date_id": prior_service_date_id,
        "weekly_run_id": str(weekly_run["workflow_run_id"]),
        "reporting_run_id": str(current_reporting_run["workflow_run_id"]),
        "prior_reporting_run_id": str(prior_reporting_run["workflow_run_id"]),
        "recommended_story_url": (
            f"/demo/logistics?planning_week_id={planning_week_id}&service_date_id={service_date_id}"
        ),
        "weekly_workspace_url": f"/runs/{weekly_run['workflow_run_id']}/workspace",
        "reporting_workspace_url": f"/runs/{current_reporting_run['workflow_run_id']}/workspace",
        "live_workspace_url": None,
        "prepare_live_dispatch_path": (
            f"/api/v1/workflow-runs/{weekly_run['workflow_run_id']}/prepare-live-dispatch-day"
        ),
        "upload_pack_root": str(UPLOAD_PACK_ROOT),
        "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
    }


def _ensure_workflow_run(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str,
    partition_key: str,
    logical_date: str,
    activation_key: str,
) -> dict[str, Any]:
    existing = get_workflow_run(connection, workflow_run_id)
    if existing is not None:
        return existing
    for run in list_workflow_runs(
        connection,
        workflow_id=workflow_id,
        tenant_id=DEMO_TENANT_ID,
        domain_id=DEMO_DOMAIN_ID,
        state=None,
    ):
        if str(run.get("activation_key") or "") == activation_key:
            return run
    created = create_workflow_run_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "workflow_id": workflow_id,
            "workflow_version": "v1",
            "tenant_id": DEMO_TENANT_ID,
            "domain_id": DEMO_DOMAIN_ID,
            "partition_key": partition_key,
            "logical_date": logical_date,
            "activation_key": activation_key,
            "idempotency_key": f"demo:runs.create:{workflow_run_id}",
            "actor_id": "human:demo-operator",
            "actor_type": "human",
        },
        include_receipt=True,
    )
    return created["result"]


def _ensure_human_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    task_run_id: str,
    human_task_id: str,
    stage_id: str,
    task_kind: str,
    activation_key: str,
    candidate_roles: list[str],
    owner_role: str | None,
    actor_id: str,
    actor_type: str,
) -> dict[str, Any]:
    existing_task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if existing_task_run is not None:
        existing_human_task = get_human_task_by_task_run_id(
            connection,
            str(existing_task_run["task_run_id"]),
        )
        if existing_human_task is not None:
            return {
                "task_run": existing_task_run,
                "human_task": existing_human_task,
            }
    created = create_task_run_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "human_task_id": human_task_id,
            "stage_id": stage_id,
            "task_kind": task_kind,
            "activation_key": activation_key,
            "candidate_roles": candidate_roles,
            "owner_role": owner_role,
            "create_human_task": True,
            "idempotency_key": f"demo:tasks.create:{task_run_id}",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        include_receipt=True,
    )
    return created["result"]


def _ensure_ingested_artifact(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    artifact_version_id: str,
    workflow_run_id: str,
    artifact_kind: str,
    artifact_role: str,
    file_name: str,
    source_path: Path,
    media_type: str,
    metadata_json: dict[str, Any],
    idempotency_key: str,
    actor_id: str,
    actor_type: str,
) -> dict[str, Any]:
    existing = get_artifact_version(connection, artifact_version_id)
    if existing is not None:
        return existing
    created = ingest_artifact_document_command(
        connection,
        {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": artifact_role,
            "file_name": file_name,
            "media_type": media_type,
            "metadata_json": metadata_json,
            "idempotency_key": idempotency_key,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        storage_root=default_storage_root_for_db_url(db_url),
        ingress_descriptor=ArtifactIngressDescriptor.local_source_path(source_path=str(source_path)),
        include_receipt=True,
    )
    return created["result"]["artifact_version"]


def _ensure_pointer(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    scope_kind: str,
    scope_ref: str,
    pointer_key: str,
    artifact_kind: str,
    artifact_version_id: str,
    promotion_reason: str,
    idempotency_key: str,
    actor_id: str,
    actor_type: str,
) -> dict[str, Any]:
    existing = get_pointer(connection, workflow_run_id=workflow_run_id, pointer_key=pointer_key)
    if existing is not None and str(existing.get("artifact_version_id") or "") == artifact_version_id:
        return existing
    created = promote_pointer_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "scope_kind": scope_kind,
            "scope_ref": scope_ref,
            "pointer_key": pointer_key,
            "artifact_kind": artifact_kind,
            "artifact_version_id": artifact_version_id,
            "promotion_reason": promotion_reason,
            "idempotency_key": idempotency_key,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        include_receipt=True,
    )
    return created["result"]


def _prior_service_date_id(service_date_id: str) -> str:
    current = date.fromisoformat(service_date_id.removeprefix("SD-"))
    return f"SD-{(current - timedelta(days=1)).isoformat()}"


def _planning_week_start(planning_week_id: str) -> str:
    token = planning_week_id.removeprefix("PW-")
    year_text, week_text = token.split("-W", maxsplit=1)
    return date.fromisocalendar(int(year_text), int(week_text), 1).isoformat()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"
