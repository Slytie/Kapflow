from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable


SCHEDULE_WORKPAGE_KIND = "schedule-v0"
EOD_WORKPAGE_KIND = "eod-v0"
ROUTE_DEMAND_WORKPAGE_KIND = "route-demand-v0"
DRIVER_PREFERENCES_WORKPAGE_KIND = "driver-preferences-v0"

WEEKLY_SCHEDULE_WORKFLOW_ID = "weekly_schedule_planning.v1"
DISPATCH_REPORTING_WORKFLOW_ID = "dispatch_reporting.v1"
SCHEDULE_WORKFLOW_ID = WEEKLY_SCHEDULE_WORKFLOW_ID

SCHEDULE_DRAFT_ARTIFACT_KIND = "planning.draft_weekly_schedule.workbook"
SCHEDULE_PUBLISHED_ARTIFACT_KIND = "planning.published_weekly_schedule.workbook"
EOD_DRAFT_ARTIFACT_KIND = "reporting.upd_draft.workbook"
ROUTE_DEMAND_ARTIFACT_KIND = "planning.route_slot_requirements.workbook"
DRIVER_PREFERENCES_ARTIFACT_KIND = "planning.driver_shift_preferences.workbook"


ArtifactRouteBuilder = Callable[[str, str], str]
CreatePathBuilder = Callable[[str], str]

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class WorkpageDescriptor:
    kind: str
    workflow_id: str
    run_enabled: bool
    artifact_enabled: bool
    submit_enabled: bool
    artifact_kinds: frozenset[str]
    editable_artifact_kinds: frozenset[str]
    frontend_artifact_route_builder: ArtifactRouteBuilder
    backend_artifact_route_builder: ArtifactRouteBuilder
    backend_artifact_submit_path_builder: ArtifactRouteBuilder | None
    backend_artifact_preview_path_builder: ArtifactRouteBuilder | None
    create_path_builder: CreatePathBuilder | None
    open_action_id: str | None
    open_action_label: str | None
    create_action_id: str | None
    create_action_label: str | None
    submit_action_id: str | None
    submit_action_label: str | None
    preview_action_id: str | None
    preview_action_label: str | None
    create_relation_kind: str | None
    submit_relation_kind: str | None

    def supports_workflow(self, workflow_id: str) -> bool:
        return workflow_id == self.workflow_id

    def supports_artifact_kind(self, artifact_kind: str) -> bool:
        return artifact_kind in self.artifact_kinds

    def supports_editable_artifact_kind(self, artifact_kind: str) -> bool:
        return artifact_kind in self.editable_artifact_kinds


def canonical_schedule_artifact_route(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return (
        f"/runs/{workflow_run_id}/workpages/"
        f"{SCHEDULE_WORKPAGE_KIND}/artifacts/{artifact_version_id}"
    )


def canonical_schedule_previous_week_reality_route(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/runs/{workflow_run_id}/workpages/"
        f"{SCHEDULE_WORKPAGE_KIND}/artifacts/{artifact_version_id}/reality/previous-week"
    )


def canonical_workflow_run_workpage_route(*, workflow_run_id: str, workpage_kind: str) -> str:
    return f"/runs/{workflow_run_id}/workpages/{workpage_kind}"


def canonical_eod_artifact_route(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return f"/runs/{workflow_run_id}/workpages/{EOD_WORKPAGE_KIND}/artifacts/{artifact_version_id}"


def canonical_route_demand_artifact_route(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/runs/{workflow_run_id}/workpages/"
        f"{ROUTE_DEMAND_WORKPAGE_KIND}/artifacts/{artifact_version_id}"
    )


def canonical_driver_preferences_artifact_route(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/runs/{workflow_run_id}/workpages/"
        f"{DRIVER_PREFERENCES_WORKPAGE_KIND}/artifacts/{artifact_version_id}"
    )


def canonical_schedule_artifact_path(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{SCHEDULE_WORKPAGE_KIND}/artifacts/{artifact_version_id}"
    )


def canonical_schedule_previous_week_reality_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{SCHEDULE_WORKPAGE_KIND}/artifacts/{artifact_version_id}/reality/previous-week"
    )


def canonical_eod_artifact_path(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{EOD_WORKPAGE_KIND}/artifacts/{artifact_version_id}"
    )


def canonical_route_demand_artifact_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{ROUTE_DEMAND_WORKPAGE_KIND}/artifacts/{artifact_version_id}"
    )


def canonical_driver_preferences_artifact_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{DRIVER_PREFERENCES_WORKPAGE_KIND}/artifacts/{artifact_version_id}"
    )


def canonical_schedule_artifact_submit_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{SCHEDULE_WORKPAGE_KIND}/artifacts/{artifact_version_id}/submit"
    )


def canonical_schedule_artifact_preview_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{SCHEDULE_WORKPAGE_KIND}/artifacts/{artifact_version_id}/preview"
    )


def canonical_schedule_route_demand_coverage_candidates_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{SCHEDULE_WORKPAGE_KIND}/artifacts/{artifact_version_id}/"
        "route-demand-coverage-candidates"
    )


def canonical_schedule_route_demand_coverage_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{SCHEDULE_WORKPAGE_KIND}/artifacts/{artifact_version_id}/route-demand-coverage"
    )


def canonical_schedule_route_demand_coverage_apply_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return canonical_schedule_route_demand_coverage_path(
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )


def canonical_eod_artifact_submit_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{EOD_WORKPAGE_KIND}/artifacts/{artifact_version_id}/submit"
    )


def canonical_route_demand_artifact_submit_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{ROUTE_DEMAND_WORKPAGE_KIND}/artifacts/{artifact_version_id}/submit"
    )


def canonical_route_demand_next_week_create_path(*, workflow_run_id: str) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{ROUTE_DEMAND_WORKPAGE_KIND}/next-week"
    )


def canonical_route_demand_artifact_save_and_run_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{ROUTE_DEMAND_WORKPAGE_KIND}/artifacts/{artifact_version_id}/save-and-run"
    )


def canonical_driver_preferences_artifact_submit_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{DRIVER_PREFERENCES_WORKPAGE_KIND}/artifacts/{artifact_version_id}/submit"
    )


def canonical_eod_draft_create_path(*, workflow_run_id: str) -> str:
    return f"/api/v1/workpages/workflow-runs/{workflow_run_id}/{EOD_WORKPAGE_KIND}/drafts"


def canonical_driver_preferences_snapshot_create_path(*, workflow_run_id: str) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{DRIVER_PREFERENCES_WORKPAGE_KIND}/snapshots"
    )


def build_schedule_accepted_series_key(
    *,
    station_code: str,
    service_area: str,
) -> str:
    return (
        f"{WEEKLY_SCHEDULE_WORKFLOW_ID}:"
        f"{_normalize_scope_token(station_code)}:"
        f"{_normalize_scope_token(service_area)}"
    )


def default_workpage_descriptor_registry():
    from onetruth.application.services.workpage_descriptor_registry_defaults import (
        DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY,
    )

    return DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY


def get_workpage_descriptor(workpage_kind: str) -> WorkpageDescriptor | None:
    return default_workpage_descriptor_registry().get_descriptor(workpage_kind)


def require_workpage_descriptor(workpage_kind: str) -> WorkpageDescriptor:
    return default_workpage_descriptor_registry().require_descriptor(workpage_kind)


def descriptor_for_public_run(
    *,
    workpage_kind: str,
    workflow_id: str,
) -> WorkpageDescriptor | None:
    return default_workpage_descriptor_registry().descriptor_for_public_run(
        workpage_kind=workpage_kind,
        workflow_id=workflow_id,
    )


def _normalize_scope_token(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"
    normalized = _NON_ALNUM.sub("-", text).strip("-")
    return normalized or "unknown"
