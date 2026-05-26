from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.services.logistics_local_demo import (
    DEFAULT_PLANNING_WEEK_ID,
    DEFAULT_SERVICE_DATE_ID,
    DEMO_DOMAIN_ID,
    DEMO_TENANT_ID,
    materialize_demo_weekly_review_state,
    require_artifact_version_id,
    seed_weekly_first_logistics_local_demo,
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
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run


_FRONTEND_ACTOR_ID = "human:frontend-operator"
_FRONTEND_ACTOR_TYPE = "human"
_FRONTEND_ACTOR_ROLES: tuple[str, ...] = (
    "dispatch_supervisor",
    "schedule_planner",
    "fleet_coordinator",
    "operations_manager",
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

    weekly_state = materialize_demo_weekly_review_state(
        connection,
        db_url=db_url,
        workflow_run=weekly_run,
        idempotency_prefix=f"demo:workpage-prep:{weekly_run_id}",
        artifact_version_prefix="av-demo-workpage-prep",
        include_driver_preferences=include_driver_preferences,
    )

    artifacts = list_artifact_versions_for_workflow_run(connection, weekly_run_id)
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
    driver_preferences_artifact_version_id: str | None = None
    if include_driver_preferences:
        driver_preferences_artifact_version_id = require_artifact_version_id(
            driver_preferences_artifact,
            field_name="driver_preferences_artifact_version_id",
        )
    else:
        driver_preferences_artifact_version_id = None

    return {
        "planning_week_id": planning_week_id,
        "service_date_id": service_date_id,
        "weekly_run_id": weekly_run_id,
        "reporting_run_id": reporting_run_id,
        "recommended_story_url": str(seeded["recommended_story_url"]),
        "weekly_workspace_url": str(seeded["weekly_workspace_url"]),
        "reporting_workspace_url": str(seeded["reporting_workspace_url"]),
        "frontend_request_context": {
            "tenant_id": DEMO_TENANT_ID,
            "domain_id": DEMO_DOMAIN_ID,
            "actor_id": _FRONTEND_ACTOR_ID,
            "actor_type": _FRONTEND_ACTOR_TYPE,
            "actor_roles": list(_FRONTEND_ACTOR_ROLES),
        },
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
        "driver_preferences_artifact_version_id": (
            str(weekly_state["driver_preferences_artifact_version_id"])
            if weekly_state["driver_preferences_artifact_version_id"] is not None
            else None
        ),
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
