from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.artifacts import create_artifact_version_command
from onetruth.application.handlers.schedule_control import (
    build_weekly_schedule_control_command,
)
from onetruth.application.handlers.workpage_weekly_control_commands import (
    create_workflow_run_driver_preferences_snapshot_command,
)
from onetruth.application.services.logistics_local_demo import (
    DEFAULT_PLANNING_WEEK_ID,
    DEFAULT_SERVICE_DATE_ID,
    DEMO_DOMAIN_ID,
    DEMO_TENANT_ID,
    seed_weekly_first_logistics_local_demo,
)
from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_actual_ops_weekly_stage04_fixture_payloads,
)
from onetruth.application.services.logistics_workpages import (
    canonical_driver_preferences_artifact_route,
    canonical_route_demand_artifact_route,
    canonical_schedule_artifact_route,
    canonical_workflow_run_workpage_route,
    latest_driver_preferences_artifact,
    latest_route_demand_artifact,
    latest_schedule_draft_artifact,
)
from onetruth.application.services.workpage_descriptors import (
    DRIVER_PREFERENCES_WORKPAGE_KIND,
    EOD_WORKPAGE_KIND,
    ROUTE_DEMAND_WORKPAGE_KIND,
    SCHEDULE_WORKPAGE_KIND,
)
from onetruth.infrastructure.artifacts.storage import (
    ARTIFACT_ROOT_ENV_VAR,
    default_storage_root_for_db_url,
)
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run


_PREP_ACTOR_ID = "system:logistics-workpage-demo-prep"
_PREP_ACTOR_TYPE = "system"

_STAGE04_INPUT_SPECS: tuple[tuple[str, str, str], ...] = (
    ("route_slot_requirements", "planning.route_slot_requirements.workbook", "route-slot-requirements"),
    ("driver_capabilities", "planning.driver_capabilities.workbook", "driver-capabilities"),
    ("approved_availability", "planning.approved_availability.workbook", "approved-availability"),
    ("actual_hours", "planning.actual_hours_snapshot.workbook", "actual-hours"),
)


def prepare_logistics_workpage_demo(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    planning_week_id: str = DEFAULT_PLANNING_WEEK_ID,
    service_date_id: str = DEFAULT_SERVICE_DATE_ID,
    include_driver_preferences: bool = True,
) -> dict[str, Any]:
    seeded = seed_weekly_first_logistics_local_demo(
        connection,
        db_url=db_url,
        planning_week_id=planning_week_id,
        service_date_id=service_date_id,
    )
    weekly_run_id = str(seeded["weekly_run_id"])
    reporting_run_id = str(seeded["reporting_run_id"])
    weekly_run = get_workflow_run(connection, weekly_run_id)
    if weekly_run is None:
        raise RuntimeError(f"weekly run missing after demo seed: {weekly_run_id}")

    input_artifacts = _ensure_weekly_stage04_input_artifacts(
        connection,
        workflow_run_id=weekly_run_id,
    )
    build_weekly_schedule_control_command(
        connection,
        {
            "workflow_run_id": weekly_run_id,
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
            "idempotency_key": _idempotency_key(
                weekly_run_id,
                "schedule-control.build-weekly",
            ),
        },
    )

    driver_preferences_artifact_version_id: str | None = None
    if include_driver_preferences:
        driver_preferences_artifact_version_id = _ensure_driver_preferences_snapshot(
            connection,
            db_url=db_url,
            workflow_run=weekly_run,
        )

    artifacts = list_artifact_versions_for_workflow_run(connection, weekly_run_id)
    schedule_artifact = latest_schedule_draft_artifact(artifacts)
    route_demand_artifact = latest_route_demand_artifact(artifacts)
    driver_preferences_artifact = (
        latest_driver_preferences_artifact(artifacts) if include_driver_preferences else None
    )
    schedule_artifact_version_id = _require_artifact_version_id(
        schedule_artifact,
        field_name="schedule_artifact_version_id",
    )
    route_demand_artifact_version_id = _require_artifact_version_id(
        route_demand_artifact,
        field_name="route_demand_artifact_version_id",
    )
    if include_driver_preferences:
        driver_preferences_artifact_version_id = _require_artifact_version_id(
            driver_preferences_artifact,
            field_name="driver_preferences_artifact_version_id",
        )

    return {
        "planning_week_id": planning_week_id,
        "service_date_id": service_date_id,
        "weekly_run_id": weekly_run_id,
        "reporting_run_id": reporting_run_id,
        "recommended_story_url": str(seeded["recommended_story_url"]),
        "weekly_workspace_url": str(seeded["weekly_workspace_url"]),
        "reporting_workspace_url": str(seeded["reporting_workspace_url"]),
        "schedule_workpage_url": canonical_workflow_run_workpage_route(
            workflow_run_id=weekly_run_id,
            workpage_kind=SCHEDULE_WORKPAGE_KIND,
        ),
        "schedule_artifact_version_id": schedule_artifact_version_id,
        "schedule_artifact_url": canonical_schedule_artifact_route(
            workflow_run_id=weekly_run_id,
            artifact_version_id=schedule_artifact_version_id,
        ),
        "route_demand_workpage_url": canonical_workflow_run_workpage_route(
            workflow_run_id=weekly_run_id,
            workpage_kind=ROUTE_DEMAND_WORKPAGE_KIND,
        ),
        "route_demand_artifact_version_id": route_demand_artifact_version_id,
        "route_demand_artifact_url": canonical_route_demand_artifact_route(
            workflow_run_id=weekly_run_id,
            artifact_version_id=route_demand_artifact_version_id,
        ),
        "driver_preferences_workpage_url": canonical_workflow_run_workpage_route(
            workflow_run_id=weekly_run_id,
            workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
        ),
        "driver_preferences_artifact_version_id": driver_preferences_artifact_version_id,
        "driver_preferences_artifact_url": (
            canonical_driver_preferences_artifact_route(
                workflow_run_id=weekly_run_id,
                artifact_version_id=driver_preferences_artifact_version_id,
            )
            if driver_preferences_artifact_version_id is not None
            else None
        ),
        "eod_workpage_url": canonical_workflow_run_workpage_route(
            workflow_run_id=reporting_run_id,
            workpage_kind=EOD_WORKPAGE_KIND,
        ),
    }


def _ensure_weekly_stage04_input_artifacts(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
) -> dict[str, dict[str, Any]]:
    payloads = build_actual_ops_weekly_stage04_fixture_payloads()
    created: dict[str, dict[str, Any]] = {}
    for payload_key, artifact_kind, suffix in _STAGE04_INPUT_SPECS:
        metadata_json = payloads[payload_key]
        content_digest = _content_digest(metadata_json)
        result = create_artifact_version_command(
            connection,
            {
                "artifact_version_id": _stable_id("av-demo-workpage-prep", workflow_run_id, suffix),
                "workflow_run_id": workflow_run_id,
                "artifact_kind": artifact_kind,
                "artifact_role": "official_input",
                "media_type": "application/json",
                "storage_uri": (
                    f"inmem://logistics-workpage-demo-prep/{workflow_run_id}/{suffix}.json"
                ),
                "content_digest": content_digest,
                "metadata_json": metadata_json,
                "idempotency_key": _idempotency_key(
                    workflow_run_id,
                    f"artifacts.create:{suffix}",
                ),
                "actor_id": _PREP_ACTOR_ID,
                "actor_type": _PREP_ACTOR_TYPE,
            },
        )
        created[artifact_kind] = result
    return created


def _ensure_driver_preferences_snapshot(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    workflow_run: dict[str, Any],
) -> str:
    workflow_run_id = str(workflow_run["workflow_run_id"])
    storage_root = default_storage_root_for_db_url(
        db_url,
        override=os.environ.get(ARTIFACT_ROOT_ENV_VAR),
    )
    try:
        created = create_workflow_run_driver_preferences_snapshot_command(
            connection,
            workflow_run,
            {
                "tenant_id": DEMO_TENANT_ID,
                "domain_id": DEMO_DOMAIN_ID,
                "actor_id": _PREP_ACTOR_ID,
                "actor_type": _PREP_ACTOR_TYPE,
                "idempotency_key": _idempotency_key(
                    workflow_run_id,
                    "driver-preferences.create",
                ),
            },
            storage_root=storage_root,
        )
    except CommandError as exc:
        if exc.code != "driver_preferences_snapshot_exists":
            raise
        artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
        existing = latest_driver_preferences_artifact(artifacts)
        return _require_artifact_version_id(
            existing,
            field_name="driver_preferences_artifact_version_id",
        )
    return str(created["created"]["artifact_version_id"])


def _require_artifact_version_id(
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


def _content_digest(metadata_json: dict[str, Any]) -> str:
    payload = json.dumps(metadata_json, separators=(",", ":"), sort_keys=True)
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _idempotency_key(workflow_run_id: str, suffix: str) -> str:
    return f"demo:workpage-prep:{workflow_run_id}:{suffix}"


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"
