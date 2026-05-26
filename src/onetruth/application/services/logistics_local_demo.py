from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.artifacts import (
    create_artifact_version_command,
    ingest_artifact_document_command,
)
from onetruth.application.handlers.logistics_handoff import notify_only_handoff_command
from onetruth.application.handlers.pointers import promote_pointer_command
from onetruth.application.handlers.schedule_control import (
    build_weekly_schedule_control_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    claim_human_task_command,
    complete_human_task_command,
    create_task_run_command,
    create_workflow_run_command,
)
from onetruth.application.handlers.workpage_weekly_control_commands import (
    create_workflow_run_driver_preferences_snapshot_command,
)
from onetruth.application.services.dispatch_reporting_build import EOS_RAW_ARTIFACT_KIND
from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_actual_ops_weekly_stage04_fixture_payloads,
)
from onetruth.application.services.logistics_workpages import (
    canonical_driver_preferences_artifact_route,
    canonical_eod_artifact_route,
    canonical_route_demand_artifact_route,
    canonical_schedule_artifact_route,
    canonical_workflow_run_workpage_route,
    latest_compatible_eod_draft_artifact,
    latest_driver_preferences_artifact,
    latest_route_demand_artifact,
    latest_schedule_draft_artifact,
)
from onetruth.application.services.workpage_descriptors import (
    DRIVER_PREFERENCES_ARTIFACT_KIND,
    DRIVER_PREFERENCES_WORKPAGE_KIND,
    EOD_WORKPAGE_KIND,
    ROUTE_DEMAND_ARTIFACT_KIND,
    ROUTE_DEMAND_WORKPAGE_KIND,
    SCHEDULE_DRAFT_ARTIFACT_KIND,
    SCHEDULE_WORKPAGE_KIND,
    canonical_schedule_previous_week_reality_route,
)
from onetruth.infrastructure.artifacts.storage import (
    ARTIFACT_ROOT_ENV_VAR,
    ArtifactIngressDescriptor,
    default_storage_root_for_db_url,
)
from onetruth.infrastructure.repositories.artifact_pointers import get_pointer
from onetruth.infrastructure.repositories.artifact_versions import (
    get_artifact_version,
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.human_tasks import (
    get_human_task,
    get_human_task_by_task_run_id,
)
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
_DEMO_ACTOR_ID = "human:demo-operator"
_DEMO_ACTOR_TYPE = "human"
_DEMO_ACTOR_ROLES: tuple[str, ...] = (
    "dispatch_supervisor",
    "schedule_planner",
    "operations_manager",
)
_WEEKLY_STAGE04_INPUT_SPECS: tuple[tuple[str, str, str], ...] = (
    ("route_slot_requirements", "planning.route_slot_requirements.workbook", "route-slot-requirements"),
    ("driver_capabilities", "planning.driver_capabilities.workbook", "driver-capabilities"),
    ("approved_availability", "planning.approved_availability.workbook", "approved-availability"),
    ("actual_hours", "planning.actual_hours_snapshot.workbook", "actual-hours"),
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
    prior_service_date_id = _prior_feedback_service_date_id(planning_week_id)
    prior_reporting_run_id = _stable_id("wr-demo-reporting-feedback", prior_service_date_id)
    prior_reporting_normalized_artifact_id = _stable_id(
        "av-demo-reporting-normalized",
        prior_service_date_id,
    )
    prior_reporting_final_artifact_id = _stable_id("av-demo-reporting-final", prior_service_date_id)

    weekly_run = _ensure_workflow_run(
        connection,
        workflow_run_id=weekly_run_id,
        workflow_id=CURRENT_WEEKLY_WORKFLOW_ID,
        partition_key=planning_week_id,
        logical_date=_planning_week_start(planning_week_id),
        activation_key=f"logistics-demo:weekly:current:{planning_week_id}",
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
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
    )
    ensure_demo_weekly_stage04_input_artifacts(
        connection,
        workflow_run_id=weekly_run_id,
        idempotency_prefix=f"demo:weekly-scratch:{weekly_run_id}",
        artifact_version_prefix="av-demo-weekly-scratch-input",
    )

    prior_reporting_run = _ensure_workflow_run(
        connection,
        workflow_run_id=prior_reporting_run_id,
        workflow_id=REPORTING_WORKFLOW_ID,
        partition_key=prior_service_date_id,
        logical_date=prior_service_date_id.removeprefix("SD-"),
        activation_key=f"logistics-demo:reporting:feedback:{prior_service_date_id}",
    )
    prior_reporting_normalized = _ensure_metadata_artifact(
        connection,
        artifact_version_id=prior_reporting_normalized_artifact_id,
        workflow_run_id=prior_reporting_run_id,
        artifact_kind="reporting.actuals_normalized.workbook",
        artifact_role="official_input",
        media_type="application/json",
        metadata_json=_demo_normalized_reporting_payload(prior_service_date_id),
        idempotency_key=f"demo:{planning_week_id}:{service_date_id}:prior-reporting-normalized",
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
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
            "normalized_artifact_version_id": str(
                prior_reporting_normalized["artifact_version_id"]
            ),
        },
        idempotency_key=f"demo:{planning_week_id}:{service_date_id}:prior-reporting-final",
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
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
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
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
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
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


def seed_combined_logistics_local_demo(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    planning_week_id: str = DEFAULT_PLANNING_WEEK_ID,
    service_date_id: str = DEFAULT_SERVICE_DATE_ID,
) -> dict[str, Any]:
    seeded = seed_weekly_first_logistics_local_demo(
        connection,
        db_url=db_url,
        planning_week_id=planning_week_id,
        service_date_id=service_date_id,
    )
    weekly_companion = _seed_review_ready_weekly_companion_run(
        connection,
        db_url=db_url,
        planning_week_id=planning_week_id,
    )
    reporting_companion = _seed_review_ready_reporting_companion_run(
        connection,
        db_url=db_url,
        service_date_id=service_date_id,
    )
    return {
        **seeded,
        **weekly_companion,
        **reporting_companion,
    }


def ensure_demo_weekly_stage04_input_artifacts(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    idempotency_prefix: str,
    artifact_version_prefix: str,
    actor_id: str = _DEMO_ACTOR_ID,
    actor_type: str = _DEMO_ACTOR_TYPE,
    attachment_human_task_id: str | None = None,
) -> dict[str, dict[str, Any]]:
    payloads = build_actual_ops_weekly_stage04_fixture_payloads()
    created: dict[str, dict[str, Any]] = {}
    links = (
        [_artifact_attachment_link(human_task_id=attachment_human_task_id)]
        if attachment_human_task_id is not None
        else None
    )
    for payload_key, artifact_kind, suffix in _WEEKLY_STAGE04_INPUT_SPECS:
        artifact_version_id = _stable_id(artifact_version_prefix, workflow_run_id, suffix)
        existing = get_artifact_version(connection, artifact_version_id)
        if existing is not None:
            created[artifact_kind] = existing
            continue
        payload: dict[str, Any] = {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": "official_input",
            "media_type": "application/json",
            "storage_uri": f"inmem://logistics-demo/{workflow_run_id}/{suffix}.json",
            "content_digest": _content_digest(payloads[payload_key]),
            "metadata_json": payloads[payload_key],
            "idempotency_key": f"{idempotency_prefix}:artifacts.create:{suffix}",
            "actor_id": actor_id,
            "actor_type": actor_type,
        }
        if links is not None:
            payload["links"] = links
        created[artifact_kind] = create_artifact_version_command(connection, payload)
    return created


def ensure_demo_driver_preferences_snapshot(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    workflow_run: dict[str, Any],
    idempotency_key: str,
    actor_id: str = _DEMO_ACTOR_ID,
    actor_type: str = _DEMO_ACTOR_TYPE,
) -> str:
    workflow_run_id = str(workflow_run["workflow_run_id"])
    try:
        created = create_workflow_run_driver_preferences_snapshot_command(
            connection,
            workflow_run,
            {
                "tenant_id": DEMO_TENANT_ID,
                "domain_id": DEMO_DOMAIN_ID,
                "actor_id": actor_id,
                "actor_type": actor_type,
                "idempotency_key": idempotency_key,
            },
            storage_root=_storage_root_for_demo(db_url),
        )
    except CommandError as exc:
        if exc.code != "driver_preferences_snapshot_exists":
            raise
        artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
        existing = latest_driver_preferences_artifact(artifacts)
        return require_artifact_version_id(
            existing,
            field_name="driver_preferences_artifact_version_id",
        )
    return str(created["created"]["artifact_version_id"])


def materialize_demo_weekly_review_state(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    workflow_run: dict[str, Any],
    idempotency_prefix: str,
    artifact_version_prefix: str,
    include_driver_preferences: bool = True,
    attachment_human_task_id: str | None = None,
) -> dict[str, Any]:
    workflow_run_id = str(workflow_run["workflow_run_id"])
    input_artifacts = ensure_demo_weekly_stage04_input_artifacts(
        connection,
        workflow_run_id=workflow_run_id,
        idempotency_prefix=idempotency_prefix,
        artifact_version_prefix=artifact_version_prefix,
        attachment_human_task_id=attachment_human_task_id,
    )
    build_weekly_schedule_control_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "route_slot_requirements_artifact_version_id": str(
                input_artifacts["planning.route_slot_requirements.workbook"]["artifact_version_id"]
            ),
            "driver_capabilities_artifact_version_id": str(
                input_artifacts["planning.driver_capabilities.workbook"]["artifact_version_id"]
            ),
            "approved_availability_artifact_version_id": str(
                input_artifacts["planning.approved_availability.workbook"]["artifact_version_id"]
            ),
            "actual_hours_artifact_version_id": str(
                input_artifacts["planning.actual_hours_snapshot.workbook"]["artifact_version_id"]
            ),
            "idempotency_key": f"{idempotency_prefix}:schedule-control.build-weekly",
        },
    )

    driver_preferences_artifact_version_id: str | None = None
    if include_driver_preferences:
        driver_preferences_artifact_version_id = ensure_demo_driver_preferences_snapshot(
            connection,
            db_url=db_url,
            workflow_run=workflow_run,
            idempotency_key=f"{idempotency_prefix}:driver-preferences.create",
        )

    artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    schedule_artifact = latest_schedule_draft_artifact(artifacts)
    route_demand_artifact = latest_route_demand_artifact(artifacts)
    driver_preferences_artifact = (
        latest_driver_preferences_artifact(artifacts) if include_driver_preferences else None
    )
    schedule_artifact_version_id = require_artifact_version_id(
        schedule_artifact,
        field_name="schedule_artifact_version_id",
    )
    route_demand_artifact_version_id = require_artifact_version_id(
        route_demand_artifact,
        field_name="route_demand_artifact_version_id",
    )
    if include_driver_preferences:
        driver_preferences_artifact_version_id = require_artifact_version_id(
            driver_preferences_artifact,
            field_name="driver_preferences_artifact_version_id",
        )

    return {
        "workflow_run_id": workflow_run_id,
        "input_artifacts": input_artifacts,
        "schedule_artifact_version_id": schedule_artifact_version_id,
        "route_demand_artifact_version_id": route_demand_artifact_version_id,
        "driver_preferences_artifact_version_id": driver_preferences_artifact_version_id,
    }


def require_artifact_version_id(
    artifact: dict[str, Any] | None,
    *,
    field_name: str,
) -> str:
    if artifact is None:
        raise RuntimeError(f"{field_name} could not be resolved")
    artifact_version_id = str(artifact.get("artifact_version_id") or "").strip()
    if not artifact_version_id:
        raise RuntimeError(f"{field_name} is missing")
    return artifact_version_id


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
            "actor_id": _DEMO_ACTOR_ID,
            "actor_type": _DEMO_ACTOR_TYPE,
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
    links: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    existing = get_artifact_version(connection, artifact_version_id)
    if existing is not None:
        return existing
    payload: dict[str, Any] = {
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
    }
    if links is not None:
        payload["links"] = links
    created = ingest_artifact_document_command(
        connection,
        payload,
        storage_root=_storage_root_for_demo(db_url),
        ingress_descriptor=ArtifactIngressDescriptor.local_source_path(source_path=str(source_path)),
        include_receipt=True,
    )
    return created["result"]["artifact_version"]


def _ensure_metadata_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    workflow_run_id: str,
    artifact_kind: str,
    artifact_role: str,
    media_type: str,
    metadata_json: dict[str, Any],
    idempotency_key: str,
    actor_id: str,
    actor_type: str,
) -> dict[str, Any]:
    existing = get_artifact_version(connection, artifact_version_id)
    if existing is not None:
        return existing
    created = create_artifact_version_command(
        connection,
        {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": artifact_role,
            "media_type": media_type,
            "storage_uri": f"inmem://logistics-demo/{workflow_run_id}/{artifact_kind}",
            "content_digest": _content_digest(metadata_json),
            "metadata_json": metadata_json,
            "idempotency_key": idempotency_key,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        include_receipt=True,
    )
    return created["result"]


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


def _seed_review_ready_weekly_companion_run(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    planning_week_id: str,
) -> dict[str, Any]:
    workflow_run_id = _stable_id("wr-demo-weekly-review", planning_week_id)
    workflow_run = _ensure_workflow_run(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=CURRENT_WEEKLY_WORKFLOW_ID,
        partition_key=planning_week_id,
        logical_date=_planning_week_start(planning_week_id),
        activation_key=f"logistics-demo:weekly:review-ready:{planning_week_id}",
    )
    intake_activation_key = f"logistics-demo:weekly:review-ready:stage04:intake:{planning_week_id}"
    intake_task = _ensure_human_task(
        connection,
        workflow_run_id=workflow_run_id,
        task_run_id=_stable_id("tr-demo-weekly-review-intake", planning_week_id),
        human_task_id=_stable_id("ht-demo-weekly-review-intake", planning_week_id),
        stage_id="Stage04",
        task_kind="weekly_input_intake",
        activation_key=intake_activation_key,
        candidate_roles=["schedule_planner"],
        owner_role="schedule_planner",
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
    )
    intake_human_task = intake_task["human_task"]
    idempotency_prefix = f"demo:weekly-review-ready:{workflow_run_id}"
    input_artifacts = ensure_demo_weekly_stage04_input_artifacts(
        connection,
        workflow_run_id=workflow_run_id,
        idempotency_prefix=idempotency_prefix,
        artifact_version_prefix="av-demo-weekly-review-ready-input",
        attachment_human_task_id=str(intake_human_task["human_task_id"]),
    )
    if str(intake_human_task.get("state") or "") != "COMPLETED":
        _ensure_demo_task_claimed(
            connection,
            human_task_id=str(intake_human_task["human_task_id"]),
            idempotency_key=f"{idempotency_prefix}:weekly-intake-claim",
        )
        _ensure_demo_task_completed(
            connection,
            db_url=db_url,
            human_task_id=str(intake_human_task["human_task_id"]),
            idempotency_key=f"{idempotency_prefix}:weekly-intake-complete",
        )

    build_task = _ensure_human_task(
        connection,
        workflow_run_id=workflow_run_id,
        task_run_id=_stable_id("tr-demo-weekly-review-build", planning_week_id),
        human_task_id=_stable_id("ht-demo-weekly-review-build", planning_week_id),
        stage_id="Stage04",
        task_kind="work_item",
        activation_key=f"weekly:{workflow_run_id}:stage04:build",
        candidate_roles=["schedule_planner"],
        owner_role="schedule_planner",
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
    )
    build_human_task = build_task["human_task"]
    weekly_state = materialize_demo_weekly_review_state(
        connection,
        db_url=db_url,
        workflow_run=workflow_run,
        idempotency_prefix=idempotency_prefix,
        artifact_version_prefix="av-demo-weekly-review-ready-input",
        include_driver_preferences=True,
        attachment_human_task_id=str(intake_human_task["human_task_id"]),
    )
    if str(build_human_task.get("state") or "") != "COMPLETED":
        _ensure_demo_task_claimed(
            connection,
            human_task_id=str(build_human_task["human_task_id"]),
            idempotency_key=f"{idempotency_prefix}:weekly-build-claim",
        )
        _ensure_demo_task_completed(
            connection,
            db_url=db_url,
            human_task_id=str(build_human_task["human_task_id"]),
            idempotency_key=f"{idempotency_prefix}:weekly-build-complete",
        )
    schedule_artifact_version_id = str(weekly_state["schedule_artifact_version_id"])
    route_demand_artifact_version_id = str(weekly_state["route_demand_artifact_version_id"])
    driver_preferences_artifact_version_id = str(
        weekly_state["driver_preferences_artifact_version_id"]
    )
    _ensure_human_task(
        connection,
        workflow_run_id=workflow_run_id,
        task_run_id=_stable_id("tr-demo-weekly-review-final", planning_week_id),
        human_task_id=_stable_id("ht-demo-weekly-review-final", planning_week_id),
        stage_id="Stage05",
        task_kind="final_review",
        activation_key=f"weekly:{workflow_run_id}:stage05:final-review:{schedule_artifact_version_id}",
        candidate_roles=["operations_manager"],
        owner_role="operations_manager",
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
    )
    return {
        "review_ready_weekly_run_id": workflow_run_id,
        "review_ready_weekly_workspace_url": f"/runs/{workflow_run_id}/workspace",
        "review_ready_schedule_workpage_url": canonical_workflow_run_workpage_route(
            workflow_run_id=workflow_run_id,
            workpage_kind=SCHEDULE_WORKPAGE_KIND,
        ),
        "review_ready_schedule_artifact_version_id": schedule_artifact_version_id,
        "review_ready_schedule_artifact_url": canonical_schedule_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=schedule_artifact_version_id,
        ),
        "review_ready_schedule_previous_week_reality_url": canonical_schedule_previous_week_reality_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=schedule_artifact_version_id,
        ),
        "review_ready_route_demand_workpage_url": canonical_workflow_run_workpage_route(
            workflow_run_id=workflow_run_id,
            workpage_kind=ROUTE_DEMAND_WORKPAGE_KIND,
        ),
        "review_ready_route_demand_artifact_version_id": route_demand_artifact_version_id,
        "review_ready_route_demand_artifact_url": canonical_route_demand_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=route_demand_artifact_version_id,
        ),
        "review_ready_driver_preferences_workpage_url": canonical_workflow_run_workpage_route(
            workflow_run_id=workflow_run_id,
            workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
        ),
        "review_ready_driver_preferences_artifact_version_id": (
            driver_preferences_artifact_version_id
        ),
        "review_ready_driver_preferences_artifact_url": canonical_driver_preferences_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=driver_preferences_artifact_version_id,
        ),
    }


def _seed_review_ready_reporting_companion_run(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    service_date_id: str,
) -> dict[str, Any]:
    workflow_run_id = _stable_id("wr-demo-reporting-review", service_date_id)
    workflow_run = _ensure_workflow_run(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=REPORTING_WORKFLOW_ID,
        partition_key=service_date_id,
        logical_date=service_date_id.removeprefix("SD-"),
        activation_key=f"logistics-demo:reporting:review-ready:{service_date_id}",
    )
    intake_task = _ensure_human_task(
        connection,
        workflow_run_id=workflow_run_id,
        task_run_id=_stable_id("tr-demo-reporting-review-intake", service_date_id),
        human_task_id=_stable_id("ht-demo-reporting-review-intake", service_date_id),
        stage_id="Stage01",
        task_kind="eos_input_intake",
        activation_key=f"logistics-demo:reporting:review-ready:stage01:intake:{service_date_id}",
        candidate_roles=["dispatch_supervisor"],
        owner_role="dispatch_supervisor",
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
    )
    intake_human_task = intake_task["human_task"]
    idempotency_prefix = f"demo:reporting-review-ready:{workflow_run_id}"
    _ensure_ingested_artifact(
        connection,
        db_url=db_url,
        artifact_version_id=_stable_id("av-demo-reporting-review-input", service_date_id),
        workflow_run_id=workflow_run_id,
        artifact_kind=EOS_RAW_ARTIFACT_KIND,
        artifact_role="official_input",
        file_name=f"demo-reporting-eos-{service_date_id.removeprefix('SD-')}.xlsx",
        source_path=REPORTING_EOS_EXAMPLE_PATH,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        metadata_json={
            "demo_seed": "combined_local_demo",
            "file_name": f"demo-reporting-eos-{service_date_id.removeprefix('SD-')}.xlsx",
            "service_date": service_date_id.removeprefix("SD-"),
        },
        idempotency_key=f"{idempotency_prefix}:reporting-eos-upload",
        actor_id=_DEMO_ACTOR_ID,
        actor_type=_DEMO_ACTOR_TYPE,
        links=[_artifact_attachment_link(human_task_id=str(intake_human_task["human_task_id"]))],
    )
    if str(intake_human_task.get("state") or "") != "COMPLETED":
        _ensure_demo_task_claimed(
            connection,
            human_task_id=str(intake_human_task["human_task_id"]),
            idempotency_key=f"{idempotency_prefix}:reporting-intake-claim",
        )
        _ensure_demo_task_completed(
            connection,
            db_url=db_url,
            human_task_id=str(intake_human_task["human_task_id"]),
            idempotency_key=f"{idempotency_prefix}:reporting-intake-complete",
        )

    artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    latest_draft = latest_compatible_eod_draft_artifact(artifacts)
    eod_artifact_version_id = require_artifact_version_id(
        latest_draft,
        field_name="review_ready_eod_artifact_version_id",
    )
    _require_human_task_for_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=(
            f"dispatch:{workflow_run_id}:stage04:final-packet-review:{eod_artifact_version_id}"
        ),
        field_name="reporting_final_review_task",
    )
    return {
        "review_ready_reporting_run_id": workflow_run_id,
        "review_ready_reporting_workspace_url": f"/runs/{workflow_run_id}/workspace",
        "review_ready_eod_workpage_url": canonical_workflow_run_workpage_route(
            workflow_run_id=workflow_run_id,
            workpage_kind=EOD_WORKPAGE_KIND,
        ),
        "review_ready_eod_artifact_version_id": eod_artifact_version_id,
        "review_ready_eod_artifact_url": canonical_eod_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=eod_artifact_version_id,
        ),
    }


def _require_human_task_for_activation_key(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    activation_key: str,
    field_name: str,
) -> dict[str, Any]:
    task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if task_run is None:
        raise RuntimeError(f"{field_name} could not be resolved")
    human_task = get_human_task_by_task_run_id(connection, str(task_run["task_run_id"]))
    if human_task is None:
        raise RuntimeError(f"{field_name} is missing")
    return human_task


def _ensure_demo_task_claimed(
    connection: sqlite3.Connection,
    *,
    human_task_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    human_task = get_human_task(connection, human_task_id)
    if human_task is None:
        raise RuntimeError(f"human task missing: {human_task_id}")
    state = str(human_task.get("state") or "")
    if state == "COMPLETED":
        return human_task
    if (
        state == "CLAIMED"
        and str(human_task.get("assignee_actor_id") or "") == _DEMO_ACTOR_ID
        and str(human_task.get("assignee_actor_type") or "") == _DEMO_ACTOR_TYPE
    ):
        return human_task
    claim_human_task_command(
        connection,
        {
            "human_task_id": human_task_id,
            "actor_id": _DEMO_ACTOR_ID,
            "actor_type": _DEMO_ACTOR_TYPE,
            "actor_roles": list(_DEMO_ACTOR_ROLES),
            "lease_seconds": 300,
            "idempotency_key": idempotency_key,
        },
    )
    claimed = get_human_task(connection, human_task_id)
    if claimed is None:
        raise RuntimeError(f"human task missing after claim: {human_task_id}")
    return claimed


def _ensure_demo_task_completed(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    human_task_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    human_task = get_human_task(connection, human_task_id)
    if human_task is None:
        raise RuntimeError(f"human task missing: {human_task_id}")
    if str(human_task.get("state") or "") == "COMPLETED":
        return {"result": {"spawned_children": [], "requested_approvals": []}}
    complete_human_task_command(
        connection,
        {
            "human_task_id": human_task_id,
            "actor_id": _DEMO_ACTOR_ID,
            "actor_type": _DEMO_ACTOR_TYPE,
            "outcome": "complete",
            "idempotency_key": idempotency_key,
        },
        storage_root=_storage_root_for_demo(db_url),
    )
    return {"result": {"spawned_children": [], "requested_approvals": []}}


def _artifact_attachment_link(*, human_task_id: str) -> dict[str, str]:
    return {
        "subject_kind": "human_task",
        "subject_id": human_task_id,
        "relation_kind": "attachment",
    }


def _storage_root_for_demo(db_url: str) -> Path:
    return default_storage_root_for_db_url(
        db_url,
        override=os.environ.get(ARTIFACT_ROOT_ENV_VAR),
    )


def _content_digest(metadata_json: dict[str, Any]) -> str:
    payload = json.dumps(metadata_json, separators=(",", ":"), sort_keys=True)
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _prior_feedback_service_date_id(planning_week_id: str) -> str:
    planning_week_start = date.fromisoformat(_planning_week_start(planning_week_id))
    prior_feedback_date = planning_week_start - timedelta(days=2)
    return f"SD-{prior_feedback_date.isoformat()}"


def _demo_normalized_reporting_payload(service_date_id: str) -> dict[str, Any]:
    service_date = service_date_id.removeprefix("SD-")
    return {
        "schema_version": "1.0",
        "kind": "dispatch_reporting.actuals_normalized",
        "service_date": service_date,
        "station_code": "DVC4",
        "dsp_name": "QDCI",
        "rows": [
            {
                "row_id": f"demo-{service_date}",
                "service_date": service_date,
                "route_id": "DEMO-001",
                "driver_id": "D-DEMO-001",
                "driver_name": "Demo Driver",
                "actual_minutes": 540,
                "returned_packages": 0,
                "return_reasons": "",
                "upd_candidate": False,
                "formula_integrity_warning": "",
            }
        ],
        "quality_warnings": [],
        "break_tracker": {"sheet_present": False, "rows": []},
        "route_adherence": {"sheet_present": False, "cycles": []},
        "totals": {"route_count": 1, "upd_candidate_count": 0},
    }


def _planning_week_start(planning_week_id: str) -> str:
    token = planning_week_id.removeprefix("PW-")
    year_text, week_text = token.split("-W", maxsplit=1)
    return date.fromisocalendar(int(year_text), int(week_text), 1).isoformat()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"
