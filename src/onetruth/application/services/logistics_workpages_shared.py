from __future__ import annotations

from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
import sqlite3
from typing import Any, Mapping

import yaml

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.services.availability_exceptions import (
    driver_availability_exceptions_for_workflow_run,
)
from onetruth.application.services.schedule_control import (
    WeeklyScheduleControlBundle,
    build_weekly_schedule_control_bundle,
    run_weekly_stage04_deterministic_build,
)
from onetruth.application.services.schedule_control.draft_workbook import (
    SCHEDULE_DRAFT_DATASET_KEY,
    draft_workbook_bytes_from_metadata_json,
    project_stage04_draft_weekly_schedule_workbook,
)
from onetruth.application.services.schedule_control.driver_preferences_workbook import (
    DRIVER_PREFERENCES_DATASET_KEY,
    annotate_driver_preferences_projection,
    build_initial_driver_preferences_workbook,
    driver_preference_value_for_service_date,
    driver_preferences_workbook_bytes_from_metadata_json,
    project_driver_preferences_workbook,
)
from onetruth.application.services.schedule_control.route_demand_workbook import (
    ROUTE_DEMAND_DATASET_KEY,
    route_demand_workbook_bytes_from_metadata_json,
    project_route_demand_workbook,
)
from onetruth.application.services.schedule_control.workpage_calculations import (
    SCHEDULE_CALCULATION_SNAPSHOT_DATASET_KEY,
    build_schedule_bundle_from_dependencies,
    build_schedule_calculations,
    normalize_schedule_dependency_manifest,
    project_schedule_dependency_state,
    resolve_schedule_dependency_artifacts,
    schedule_preview_disabled_reason,
    schedule_save_disabled_reason,
)
from onetruth.application.services.schedule_control.stage04_input_registry import (
    resolve_weekly_stage04_input_artifacts,
)
from onetruth.application.services.workpage_descriptors import (
    DRIVER_PREFERENCES_ARTIFACT_KIND,
    DRIVER_PREFERENCES_WORKPAGE_KIND,
    EOD_WORKPAGE_KIND,
    EOD_DRAFT_ARTIFACT_KIND,
    ROUTE_DEMAND_WORKPAGE_KIND,
    ROUTE_DEMAND_ARTIFACT_KIND,
    SCHEDULE_WORKPAGE_KIND,
    SCHEDULE_PUBLISHED_ARTIFACT_KIND,
    WEEKLY_SCHEDULE_WORKFLOW_ID,
    build_schedule_accepted_series_key,
    canonical_driver_preferences_artifact_path,
    canonical_driver_preferences_artifact_route as descriptor_driver_preferences_artifact_route,
    canonical_driver_preferences_artifact_submit_path,
    canonical_driver_preferences_snapshot_create_path as descriptor_driver_preferences_snapshot_create_path,
    canonical_eod_artifact_route as descriptor_eod_artifact_route,
    canonical_eod_artifact_submit_path,
    canonical_eod_draft_create_path as descriptor_eod_draft_create_path,
    canonical_route_demand_artifact_route as descriptor_route_demand_artifact_route,
    canonical_route_demand_artifact_submit_path,
    canonical_schedule_artifact_route as descriptor_schedule_artifact_route,
    canonical_schedule_artifact_preview_path,
    canonical_schedule_artifact_submit_path,
    canonical_workflow_run_workpage_route as descriptor_workflow_run_workpage_route,
    get_workpage_descriptor,
)
from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.artifacts.storage import read_blob
from onetruth.infrastructure.repositories.artifact_versions import (
    get_artifact_version,
    get_latest_artifact_version_in_chain,
    list_artifact_versions_for_scope_and_kind,
)
from onetruth.infrastructure.repositories.human_tasks import (
    list_human_tasks_for_workflow_run,
)
from onetruth.infrastructure.repositories.task_runs import (
    get_task_run,
)


REPO_ROOT = Path(__file__).resolve().parents[4]

_SCHEDULE_WORKFLOW_ID = WEEKLY_SCHEDULE_WORKFLOW_ID
_EOD_WORKFLOW_ID = "dispatch_reporting.v1"
_PREVIEW_SERVICE_DATE = "2026-03-24"
_PLANNER_NOTE = (
    "Holdout schedule contributed route totals only; staffing cells were intentionally "
    "excluded from the normalized example package."
)
_SELECTED_DAY_OPEN_QUESTION = (
    "Confirm late requests and final on-call posture before day-of handoff."
)
_EOD_SERVICE_DATE = "2026-03-16"
_EOD_STATION_CODE = "DVC4"
_EOD_DSP_NAME = "QDCI"
_EOD_WARNING_NOTE = (
    "This EOD projection is built from canonical dispatch-reporting artifacts sourced from an "
    "intentionally partial 2026-03-16 QDCI / DVC4 example family. Row-level actuals remain the primary truth "
    "because the source workbook summary tabs contained broken formulas."
)
_EOD_NOTE_PANEL_BODY = (
    "This run-backed EOD landing is generated from canonical dispatch-reporting artifacts sourced "
    "from intentionally partial 2026-03-16 example material. Source workbook summary tabs showed "
    "formula failures, so row-level actuals remain the primary truth and the landing surfaces a "
    "warning instead of reproducing broken formulas."
)

_ROUTE_SLOT_DATASET_KEY = "planning.route_slot_requirements.workbook"
_APPROVED_AVAILABILITY_DATASET_KEY = "planning.approved_availability.workbook"
_DRIVER_CAPABILITIES_DATASET_KEY = "planning.driver_capabilities.workbook"
_ACTUAL_HOURS_DATASET_KEY = "planning.actual_hours_snapshot.workbook"
_INPUT_BUNDLE_DATASET_KEY = "planning.input_bundle.doc"
_SCHEDULE_DRAFT_DOC_DATASET_KEY = "planning.draft_weekly_schedule.doc"
_SCHEDULE_VALIDATION_SUMMARY_DATASET_KEY = "planning.validation_summary.doc"
_EOD_RAW_DATASET_KEY = "reporting.eos_raw.workbook"
_EOD_NORMALIZED_DATASET_KEY = "reporting.actuals_normalized.workbook"
_EOD_DRAFT_DATASET_KEY = EOD_DRAFT_ARTIFACT_KIND
ROUTE_DEMAND_REFRESH_TASK_ACTIVATION_PREFIX = "workpage.route-demand-v0.schedule-refresh"

_SOURCE_DATASETS: tuple[tuple[str, str], ...] = (
    ("route_slot_requirements", _ROUTE_SLOT_DATASET_KEY),
    ("approved_availability", _APPROVED_AVAILABILITY_DATASET_KEY),
    ("driver_capabilities", _DRIVER_CAPABILITIES_DATASET_KEY),
    ("actual_hours_snapshot", _ACTUAL_HOURS_DATASET_KEY),
    ("stage04_input_bundle", _INPUT_BUNDLE_DATASET_KEY),
)

_EOD_SOURCE_DATASETS: tuple[tuple[str, str], ...] = (
    ("eos_route_rows", _EOD_RAW_DATASET_KEY),
    ("normalized_actuals", _EOD_NORMALIZED_DATASET_KEY),
    ("upd_candidates", _EOD_DRAFT_DATASET_KEY),
)

_EOD_SOURCE_EXAMPLES = {
    "eos_route_rows": (
        "docs/workflows/dispatch_reporting/v1/examples/"
        "eos_route_rows_2026_03_16_qdci_partial_example.yaml"
    ),
    "normalized_actuals": (
        "docs/workflows/dispatch_reporting/v1/examples/"
        "normalized_actuals_2026_03_16_qdci_partial_example.yaml"
    ),
    "upd_candidates": (
        "docs/workflows/dispatch_reporting/v1/examples/"
        "upd_candidate_2026_03_16_qdci_partial_example.yaml"
    ),
}

_EOD_VALIDATION_WARNINGS = [
    "This run-backed EOD landing is generated from canonical dispatch-reporting artifacts sourced from an intentionally partial 2026-03-16 example family.",
    "Workbook summary formulas were broken in the source material, so row-level actuals remain the primary truth for this projection.",
    "Create draft opens the immutable reporting workbook edit lane, and submit creates a new superseding workbook artifact version.",
]

_ROSTER_TARGET_NAMES = (
    "Parampreet Singh",
    "Balwinder Singh",
    "Navjot Singh",
)

_FORM_ON_CALL_OPTIONS = (
    "Parampreet Singh",
    "Brahmvir Singh",
    "Sachin Goyal",
)


class WorkpageProjectionUnavailableError(RuntimeError):
    def __init__(
        self,
        *,
        workflow_run_id: str,
        workpage_id: str,
        message: str,
        missing_dataset_keys: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.workflow_run_id = workflow_run_id
        self.workpage_id = workpage_id
        self.missing_dataset_keys = list(missing_dataset_keys or [])


def canonical_schedule_artifact_route(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return descriptor_schedule_artifact_route(
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )


def canonical_workflow_run_workpage_route(*, workflow_run_id: str, workpage_kind: str) -> str:
    return descriptor_workflow_run_workpage_route(
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
    )


def canonical_eod_artifact_route(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return descriptor_eod_artifact_route(
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )


def canonical_route_demand_artifact_route(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return descriptor_route_demand_artifact_route(
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )


def canonical_driver_preferences_artifact_route(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return descriptor_driver_preferences_artifact_route(
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )


def canonical_eod_draft_create_path(*, workflow_run_id: str) -> str:
    return descriptor_eod_draft_create_path(workflow_run_id=workflow_run_id)


def canonical_driver_preferences_snapshot_create_path(*, workflow_run_id: str) -> str:
    return descriptor_driver_preferences_snapshot_create_path(
        workflow_run_id=workflow_run_id
    )


def canonical_driver_availability_exception_create_path(*, workflow_run_id: str) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{DRIVER_PREFERENCES_WORKPAGE_KIND}/availability-exceptions"
    )


def canonical_schedule_sick_no_show_path(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return (
        f"/api/v1/workpages/workflow-runs/{workflow_run_id}/"
        f"{SCHEDULE_WORKPAGE_KIND}/artifacts/{artifact_version_id}/sick-no-show"
    )


def build_workpage_action_ref(
    *,
    action_id: str,
    workpage_kind: str,
    workflow_run_id: str,
    artifact_version_id: str | None,
    subject_kind: str | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    subject: dict[str, str] | None = None
    if subject_kind and subject_id:
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


def build_route_demand_refresh_activation_key(*, artifact_version_id: str) -> str:
    return f"{ROUTE_DEMAND_REFRESH_TASK_ACTIVATION_PREFIX}:{artifact_version_id}"


def latest_schedule_draft_artifact(
    artifacts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return _latest_artifact_for_dataset_key(
        artifacts,
        dataset_key=SCHEDULE_DRAFT_DATASET_KEY,
    )


def latest_route_demand_artifact(
    artifacts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return _latest_artifact_for_dataset_key(
        artifacts,
        dataset_key=ROUTE_DEMAND_DATASET_KEY,
    )


def latest_driver_preferences_artifact(
    artifacts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return _latest_artifact_for_dataset_key(
        artifacts,
        dataset_key=DRIVER_PREFERENCES_DATASET_KEY,
    )


def latest_compatible_eod_draft_artifact(
    artifacts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return _latest_compatible_eod_draft_artifact(artifacts)


def build_schedule_workflow_run_workpage_contract(
    connection: sqlite3.Connection,
    *,
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    try:
        resolved_inputs = resolve_weekly_stage04_input_artifacts(
            artifacts=artifacts,
            stage_spec={"required_evidence_keys": [_ROUTE_SLOT_DATASET_KEY, _DRIVER_CAPABILITIES_DATASET_KEY]},
        )
        bundle = build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=_require_mapping(
                resolved_inputs.get("route_slot_requirements"),
                field_name="route_slot_requirements",
            ),
            driver_capabilities_artifact=_require_mapping(
                resolved_inputs.get("driver_capabilities"),
                field_name="driver_capabilities",
            ),
            approved_availability_artifact=_optional_mapping(
                resolved_inputs.get("approved_availability")
            ),
            actual_hours_artifact=_optional_mapping(resolved_inputs.get("actual_hours")),
            route_horizon_artifact=None,
        )
    except CommandError as exc:
        if exc.code != "stage04_input_artifact_missing":
            raise
        missing_slots = exc.details.get("missing_slots", [])
        missing_dataset_keys = [
            _require_text(slot.get("dataset_key"))
            for slot in missing_slots
            if isinstance(slot, dict) and slot.get("dataset_key") is not None
        ]
        raise WorkpageProjectionUnavailableError(
            workflow_run_id=workflow_run_id,
            workpage_id=SCHEDULE_WORKPAGE_KIND,
            message="workflow-run-backed schedule workpage is unavailable until the weekly Stage04 inputs exist for this run",
            missing_dataset_keys=missing_dataset_keys,
        ) from exc
    except ValueError as exc:
        raise WorkpageProjectionUnavailableError(
            workflow_run_id=workflow_run_id,
            workpage_id=SCHEDULE_WORKPAGE_KIND,
            message=f"workflow-run-backed schedule workpage is unavailable: {exc}",
        ) from exc

    latest_schedule_draft = latest_schedule_draft_artifact(artifacts)
    latest_route_demand = latest_route_demand_artifact(artifacts)
    latest_driver_preferences = latest_driver_preferences_artifact(artifacts)
    driver_preferences_projection = _driver_preferences_projection_from_artifact(
        latest_driver_preferences
    )
    source_refs = _schedule_runtime_source_refs(
        resolved_inputs=resolved_inputs,
        input_bundle_artifact=_latest_artifact_for_dataset_key(
            artifacts,
            dataset_key=_INPUT_BUNDLE_DATASET_KEY,
        ),
        latest_driver_preferences=latest_driver_preferences,
    )
    accepted_series = _build_schedule_accepted_series(
        connection,
        workflow_run=workflow_run,
        accepted_series_key=_bundle_schedule_accepted_series_key(bundle),
        current_partition_key=_require_text(workflow_run.get("partition_key")),
        current_workflow_run_id=None,
        current_artifact_version_id=None,
    )
    contract = {
        **_build_schedule_workpage_contract(
            bundle=bundle,
            latest_schedule_draft=latest_schedule_draft_artifact(artifacts),
            source_examples={},
            source_mode="run_projection",
            source_refs=source_refs,
            freshness_source_kind="workflow_run_projection",
            freshness_source_version=bundle.bundle_id,
            validation_warnings=[
                "This workflow-run-backed schedule projection is built from canonical weekly-planning input artifacts for the selected run.",
                "Selected-day controls are local what-if inputs only and do not claim ownership of live dispatch truth.",
            ],
            driver_preferences_projection=driver_preferences_projection,
        ),
        "run_context": _workflow_run_context(workflow_run),
        "draft_resolution": None,
    }
    schedule_projection = _schedule_run_projection(
        bundle=bundle,
        latest_schedule_draft=latest_schedule_draft,
    )
    assignment_rows = _projection_rows(schedule_projection, "rows")
    reserve_rows = _projection_rows(schedule_projection, "reserve_rows")
    contract.update(
        {
            "artifact_state": _schedule_run_artifact_state(
                latest_schedule_draft=latest_schedule_draft,
                accepted_artifact_version_id=_accepted_series_anchor_artifact_id(accepted_series),
            ),
            "dependencies": _schedule_dependency_rows_for_run(
                resolved_inputs=resolved_inputs,
                source_refs=source_refs,
                latest_driver_preferences=latest_driver_preferences,
            ),
            "calculations": build_schedule_calculations(
                bundle=bundle,
                assignment_rows=assignment_rows,
                reserve_rows=reserve_rows,
                driver_preferences_projection=driver_preferences_projection,
            ),
            "artifact_history": None,
            "draft_lineage": _empty_draft_lineage(),
            "accepted_series": accepted_series,
            "actions": _schedule_run_contract_actions(
                workflow_run_id=workflow_run_id,
                latest_schedule_draft=latest_schedule_draft,
                latest_route_demand=latest_route_demand,
                latest_driver_preferences=latest_driver_preferences,
            ),
        }
    )
    return contract


def build_route_demand_workflow_run_workpage_contract(
    connection: sqlite3.Connection,
    *,
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    latest_artifact = latest_route_demand_artifact(artifacts)
    if latest_artifact is None:
        raise WorkpageProjectionUnavailableError(
            workflow_run_id=workflow_run_id,
            workpage_id=ROUTE_DEMAND_WORKPAGE_KIND,
            message="workflow-run-backed route demand workpage is unavailable until the Stage04 route demand artifact exists for this run",
            missing_dataset_keys=[ROUTE_DEMAND_DATASET_KEY],
        )
    projection = _route_demand_projection_from_artifact(latest_artifact)
    day_cards = _route_demand_day_cards(
        projection=projection,
        previous_projection=None,
    )
    latest_schedule_draft = latest_schedule_draft_artifact(artifacts)
    schedule_impact = _route_demand_schedule_impact(
        connection,
        workflow_run_id=workflow_run_id,
        artifacts=artifacts,
        latest_route_demand_artifact_version_id=_require_text(
            latest_artifact.get("artifact_version_id")
        ),
        latest_schedule_draft=latest_schedule_draft,
    )
    contract = {
        "workpage": _build_route_demand_workpage_view_model(
            workflow_run=workflow_run,
            projection=projection,
            artifact_version_id=None,
            supersedes_artifact_version_id=None,
            latest_in_chain_artifact_version_id=_require_text(latest_artifact.get("artifact_version_id")),
            editable=False,
            validation_warnings=[
                "This workflow-run-backed route demand page is built from the latest canonical Stage04 route-demand artifact for the selected run.",
                "Route-demand edits stay on a separate truth surface from schedule reassignment and recalculation.",
            ],
        ),
        "source": {
            "mode": "run_projection",
            "primary_dataset_key": ROUTE_DEMAND_DATASET_KEY,
            "source_dataset_keys": [ROUTE_DEMAND_DATASET_KEY],
            "source_artifact_version_id": None,
            "source_refs": [
                _artifact_source_ref(latest_artifact),
            ],
        },
        "freshness": {
            "generated_at": utc_now_iso(),
            "source_kind": "workflow_run_projection",
            "source_version": _require_text(latest_artifact.get("artifact_version_id")),
        },
        "run_context": _workflow_run_context(workflow_run),
        "draft_resolution": None,
        "artifact_state": _route_demand_run_artifact_state(latest_artifact=latest_artifact),
        "calculations": {"day_cards": day_cards},
        "schedule_impact": schedule_impact,
        "artifact_history": None,
        "actions": [
            _route_demand_open_latest_contract_action(
                workflow_run_id=workflow_run_id,
                latest_artifact=latest_artifact,
            )
        ],
    }
    return contract


def build_driver_preferences_workflow_run_workpage_contract(
    connection: sqlite3.Connection,
    *,
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    bundle = _build_driver_preferences_bundle_for_run(
        workflow_run=workflow_run,
        artifacts=artifacts,
    )
    latest_artifact = latest_driver_preferences_artifact(artifacts)
    projection = (
        _driver_preferences_projection_from_artifact(latest_artifact)
        if latest_artifact is not None
        else _initial_driver_preferences_projection(bundle)
    )
    contract = {
        "workpage": _build_driver_preferences_workpage_view_model(
            workflow_run=workflow_run,
            projection=projection,
            artifact_version_id=None,
            supersedes_artifact_version_id=None,
            latest_in_chain_artifact_version_id=(
                _require_text_or_default(
                    latest_artifact.get("artifact_version_id"),
                    default="",
                )
                or None
                if latest_artifact is not None
                else None
            ),
            editable=False,
            validation_warnings=[
                "This workflow-run-backed driver preferences page uses the latest immutable weekly snapshot when one exists.",
                "Preference snapshots stay advisory only and do not become hard schedule truth or refresh tasks.",
            ],
        ),
        "source": {
            "mode": "run_projection",
            "primary_dataset_key": DRIVER_PREFERENCES_DATASET_KEY,
            "source_dataset_keys": [
                DRIVER_PREFERENCES_DATASET_KEY,
                _DRIVER_CAPABILITIES_DATASET_KEY,
            ],
            "source_artifact_version_id": None,
            "source_refs": _driver_preferences_runtime_source_refs(
                latest_artifact=latest_artifact,
                artifacts=artifacts,
            ),
        },
        "freshness": {
            "generated_at": utc_now_iso(),
            "source_kind": "workflow_run_projection",
            "source_version": (
                _require_text_or_default(latest_artifact.get("artifact_version_id"), default="")
                if latest_artifact is not None
                else bundle.bundle_id
            ),
        },
        "run_context": _workflow_run_context(workflow_run),
        "draft_resolution": None,
        "artifact_state": _driver_preferences_run_artifact_state(
            latest_artifact=latest_artifact,
        ),
        "preference_grid": _driver_preferences_grid(
            workflow_run=workflow_run,
            projection=projection,
        ),
        "driver_availability_exceptions": driver_availability_exceptions_for_workflow_run(
            connection,
            workflow_run=workflow_run,
        ),
        "schedule_impact": _driver_preferences_schedule_impact(
            artifacts=artifacts,
            latest_driver_preferences=latest_artifact,
        ),
        "artifact_history": None,
        "actions": _driver_preferences_run_contract_actions(
            workflow_run_id=workflow_run_id,
            latest_artifact=latest_artifact,
        ),
    }
    return contract


def _build_schedule_workpage_contract(
    *,
    bundle: WeeklyScheduleControlBundle,
    latest_schedule_draft: Mapping[str, Any] | None,
    source_examples: Mapping[str, str],
    source_mode: str,
    source_refs: list[str],
    freshness_source_kind: str,
    freshness_source_version: str,
    validation_warnings: list[str],
    driver_preferences_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_version = freshness_source_version
    if latest_schedule_draft is not None:
        latest_artifact_version_id = _require_text_or_default(
            latest_schedule_draft.get("artifact_version_id"),
            default="",
        )
        if latest_artifact_version_id:
            source_version = latest_artifact_version_id
    return {
        "workpage": _build_schedule_workpage_view_model(
            bundle=bundle,
            latest_schedule_draft=latest_schedule_draft,
            source_examples=source_examples,
            validation_warnings=validation_warnings,
            driver_preferences_projection=driver_preferences_projection,
        ),
        "source": {
            "mode": source_mode,
            "primary_dataset_key": None,
            "source_dataset_keys": [dataset_key for _, dataset_key in _SOURCE_DATASETS],
            "source_artifact_version_id": None,
            "source_refs": source_refs,
        },
        "freshness": {
            "generated_at": utc_now_iso(),
            "source_kind": freshness_source_kind,
            "source_version": source_version,
        },
    }

def _schedule_run_artifact_state(
    *,
    latest_schedule_draft: Mapping[str, Any] | None,
    accepted_artifact_version_id: str | None,
) -> dict[str, Any]:
    latest_artifact_version_id = (
        _require_text_or_default(
            latest_schedule_draft.get("artifact_version_id"),
            default="",
        )
        if latest_schedule_draft is not None
        else ""
    )
    return {
        "state_kind": "run_projection",
        "artifact_kind": SCHEDULE_DRAFT_DATASET_KEY,
        "editable": False,
        "current_artifact_version_id": None,
        "latest_artifact_version_id": latest_artifact_version_id or None,
        "accepted_artifact_version_id": accepted_artifact_version_id,
    }


def _schedule_artifact_state(
    *,
    artifact_kind: str,
    artifact_version_id: str,
    latest_in_chain_artifact_version_id: str,
    accepted_artifact_version_id: str | None,
    editable: bool,
) -> dict[str, Any]:
    return {
        "state_kind": "draft" if editable else "accepted",
        "artifact_kind": artifact_kind,
        "editable": editable,
        "current_artifact_version_id": artifact_version_id,
        "latest_artifact_version_id": latest_in_chain_artifact_version_id,
        "accepted_artifact_version_id": accepted_artifact_version_id,
    }

def _schedule_dependency_rows_for_run(
    *,
    resolved_inputs: Mapping[str, Mapping[str, Any] | None],
    source_refs: list[str],
    latest_driver_preferences: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    refs_by_key = {
        "route_slot_requirements": _artifact_source_ref(resolved_inputs.get("route_slot_requirements")),
        "approved_availability": _artifact_source_ref(resolved_inputs.get("approved_availability")),
        "driver_capabilities": _artifact_source_ref(resolved_inputs.get("driver_capabilities")),
        "actual_hours": _artifact_source_ref(resolved_inputs.get("actual_hours")),
        "driver_preferences": _artifact_source_ref(latest_driver_preferences),
    }
    if not refs_by_key["route_slot_requirements"] and source_refs:
        refs_by_key["route_slot_requirements"] = source_refs[0]
    return _schedule_dependency_rows(
        artifacts_by_key={
            "route_slot_requirements": resolved_inputs.get("route_slot_requirements"),
            "approved_availability": resolved_inputs.get("approved_availability"),
            "driver_capabilities": resolved_inputs.get("driver_capabilities"),
            "actual_hours": resolved_inputs.get("actual_hours"),
            "driver_preferences": latest_driver_preferences,
        },
        refs_by_key=refs_by_key,
    )


def _schedule_dependency_rows_for_artifact(
    *,
    dependencies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [dict(row) for row in dependencies]


def _schedule_dependency_rows(
    *,
    artifacts_by_key: Mapping[str, Mapping[str, Any] | None],
    refs_by_key: Mapping[str, str | None],
) -> list[dict[str, Any]]:
    dependency_specs = (
        ("route_slot_requirements", _ROUTE_SLOT_DATASET_KEY, "hard"),
        ("approved_availability", _APPROVED_AVAILABILITY_DATASET_KEY, "hard"),
        ("driver_capabilities", _DRIVER_CAPABILITIES_DATASET_KEY, "hard"),
        ("actual_hours", _ACTUAL_HOURS_DATASET_KEY, "hard"),
        ("driver_preferences", DRIVER_PREFERENCES_ARTIFACT_KIND, "soft"),
    )
    rows: list[dict[str, Any]] = []
    for dependency_key, artifact_kind, impact_class in dependency_specs:
        artifact = artifacts_by_key.get(dependency_key)
        artifact_version_id = (
            _require_text_or_default(artifact.get("artifact_version_id"), default="")
            if artifact is not None
            else ""
        )
        source_ref = refs_by_key.get(dependency_key)
        rows.append(
            {
                "dependency_key": dependency_key,
                "artifact_kind": artifact_kind,
                "artifact_version_id": artifact_version_id or None,
                "impact_class": impact_class,
                "state": "resolved" if artifact_version_id or source_ref else "not_available",
                "source_ref": source_ref,
            }
        )
    return rows


def _schedule_calculations(
    *,
    day_demand_rows: list[dict[str, Any]],
    selected_day_row: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "top_bar": {
            "days": [
                {
                    "service_date": _require_text_or_default(row.get("service_date"), default=""),
                    "weekday_label": _weekday_label(
                        _require_text_or_default(row.get("service_date"), default="")
                    ),
                    "routes_required": _int_or_zero(row.get("planned_route_count")),
                    "on_call_target": _int_or_zero(row.get("on_call_target")),
                    "excess_capacity_target": _int_or_zero(row.get("excess_capacity_target")),
                }
                for row in day_demand_rows
            ]
        },
        "selected_day": {
            "service_date": _require_text_or_default(selected_day_row.get("service_date"), default=""),
            "routes_required": _int_or_zero(selected_day_row.get("routes_required")),
            "drivers_available": _int_or_zero(selected_day_row.get("drivers_available")),
            "projected_on_call_needed": _int_or_zero(
                selected_day_row.get("projected_on_call_needed")
            ),
            "available_driver_ids": [],
            "available_preference_buckets": {
                "open_to_work": [],
                "prefer_not_to_work": [],
                "definitely_can_not_work": [],
                "unset": [],
            },
            "open_questions": _require_text_or_default(
                selected_day_row.get("open_questions"),
                default="",
            ),
        },
        "driver_metrics": [],
        "checks": [],
    }


def _empty_draft_lineage() -> dict[str, Any]:
    return {
        "current_artifact_version_id": None,
        "latest_artifact_version_id": None,
        "previous_artifact_version_id": None,
        "recent_versions": [],
    }


def _empty_artifact_history() -> dict[str, Any]:
    return {
        "current_artifact_version_id": None,
        "latest_artifact_version_id": None,
        "previous_artifact_version_id": None,
        "next_artifact_version_id": None,
        "entries": [],
    }


def _artifact_history_route(
    *,
    artifact_kind: str,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    if artifact_kind in {SCHEDULE_DRAFT_DATASET_KEY, SCHEDULE_PUBLISHED_ARTIFACT_KIND}:
        return canonical_schedule_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        )
    if artifact_kind == _EOD_DRAFT_DATASET_KEY:
        return canonical_eod_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        )
    if artifact_kind == ROUTE_DEMAND_DATASET_KEY:
        return canonical_route_demand_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        )
    if artifact_kind == DRIVER_PREFERENCES_DATASET_KEY:
        return canonical_driver_preferences_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        )
    raise ValueError(f"unsupported artifact history kind: {artifact_kind}")


def _artifact_history_entry(artifact: Mapping[str, Any]) -> dict[str, Any]:
    artifact_version_id = _require_text(artifact.get("artifact_version_id"))
    workflow_run_id = _require_text(artifact.get("workflow_run_id"))
    artifact_kind = _require_text(artifact.get("artifact_kind") or artifact.get("dataset_key"))
    return {
        "artifact_version_id": artifact_version_id,
        "workflow_run_id": workflow_run_id,
        "artifact_kind": artifact_kind,
        "created_at": _require_text_or_default(artifact.get("created_at"), default=""),
        "lineage_note": _require_text_or_default(artifact.get("lineage_note"), default="") or None,
        "supersedes_artifact_version_id": _require_text_or_default(
            artifact.get("supersedes_artifact_version_id"),
            default="",
        )
        or None,
        "route": _artifact_history_route(
            artifact_kind=artifact_kind,
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
        ),
    }


def _artifact_history_for_chain(
    connection: sqlite3.Connection,
    *,
    current_artifact: Mapping[str, Any] | None,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    if current_artifact is None:
        return _empty_artifact_history()

    artifact_kind = _require_text(
        current_artifact.get("artifact_kind") or current_artifact.get("dataset_key")
    )
    artifact_map: dict[str, Mapping[str, Any]] = {
        _require_text(item.get("artifact_version_id")): item
        for item in artifacts
        if item.get("artifact_version_id") is not None
        and _require_text(item.get("artifact_kind") or item.get("dataset_key")) == artifact_kind
    }
    current_artifact_version_id = _require_text(current_artifact.get("artifact_version_id"))
    artifact_map.setdefault(current_artifact_version_id, current_artifact)

    latest_artifact_version_id = _latest_chain_artifact_version_id(
        connection,
        artifact_version_id=current_artifact_version_id,
        default=current_artifact_version_id,
    )
    latest_artifact = artifact_map.get(latest_artifact_version_id)
    if latest_artifact is None:
        latest_artifact = get_artifact_version(connection, latest_artifact_version_id)
        if latest_artifact is None:
            latest_artifact = current_artifact
        artifact_map[latest_artifact_version_id] = latest_artifact

    entries: list[dict[str, Any]] = []
    cursor: Mapping[str, Any] | None = latest_artifact
    seen_ids: set[str] = set()
    while cursor is not None:
        cursor_artifact_version_id = _require_text_or_default(
            cursor.get("artifact_version_id"),
            default="",
        )
        if not cursor_artifact_version_id or cursor_artifact_version_id in seen_ids:
            break
        seen_ids.add(cursor_artifact_version_id)
        entries.append(_artifact_history_entry(cursor))
        parent_artifact_version_id = _require_text_or_default(
            cursor.get("supersedes_artifact_version_id"),
            default="",
        )
        if not parent_artifact_version_id:
            break
        next_cursor = artifact_map.get(parent_artifact_version_id)
        if next_cursor is None:
            next_cursor = get_artifact_version(connection, parent_artifact_version_id)
            if next_cursor is None:
                break
            if _require_text(next_cursor.get("artifact_kind") or next_cursor.get("dataset_key")) != artifact_kind:
                break
            artifact_map[parent_artifact_version_id] = next_cursor
        cursor = next_cursor

    current_index = next(
        (
            index
            for index, entry in enumerate(entries)
            if entry["artifact_version_id"] == current_artifact_version_id
        ),
        None,
    )
    if current_index is None:
        entries.insert(0, _artifact_history_entry(current_artifact))
        current_index = 0

    previous_artifact_version_id = (
        entries[current_index + 1]["artifact_version_id"]
        if current_index + 1 < len(entries)
        else None
    )
    next_artifact_version_id = (
        entries[current_index - 1]["artifact_version_id"] if current_index > 0 else None
    )
    return {
        "current_artifact_version_id": current_artifact_version_id,
        "latest_artifact_version_id": latest_artifact_version_id,
        "previous_artifact_version_id": previous_artifact_version_id,
        "next_artifact_version_id": next_artifact_version_id,
        "entries": entries,
    }


def _draft_lineage_from_artifact_history(artifact_history: Mapping[str, Any]) -> dict[str, Any]:
    current_artifact_version_id = _require_text_or_default(
        artifact_history.get("current_artifact_version_id"),
        default="",
    )
    if not current_artifact_version_id:
        return _empty_draft_lineage()
    entries = artifact_history.get("entries")
    if not isinstance(entries, list):
        return _empty_draft_lineage()
    current_index = next(
        (
            index
            for index, entry in enumerate(entries)
            if isinstance(entry, Mapping)
            and _require_text_or_default(entry.get("artifact_version_id"), default="")
            == current_artifact_version_id
        ),
        None,
    )
    if current_index is None:
        return _empty_draft_lineage()
    current_to_older = entries[current_index:]
    recent_versions = [
        {
            "artifact_version_id": _require_text(entry.get("artifact_version_id")),
            "supersedes_artifact_version_id": _require_text_or_default(
                entry.get("supersedes_artifact_version_id"),
                default="",
            )
            or None,
        }
        for entry in current_to_older[:5]
        if isinstance(entry, Mapping)
    ]
    return {
        "current_artifact_version_id": current_artifact_version_id,
        "latest_artifact_version_id": _require_text_or_default(
            artifact_history.get("latest_artifact_version_id"),
            default="",
        )
        or None,
        "previous_artifact_version_id": _require_text_or_default(
            artifact_history.get("previous_artifact_version_id"),
            default="",
        )
        or None,
        "recent_versions": recent_versions,
    }


def _schedule_draft_history_artifact(
    connection: sqlite3.Connection,
    *,
    artifact: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
    artifact_kind: str,
) -> Mapping[str, Any] | None:
    if artifact_kind == SCHEDULE_DRAFT_DATASET_KEY:
        return artifact
    if artifact_kind != SCHEDULE_PUBLISHED_ARTIFACT_KIND:
        return None
    metadata_json = artifact.get("metadata_json")
    if not isinstance(metadata_json, Mapping):
        return None
    anchor_artifact_version_id = _require_text_or_default(
        metadata_json.get("published_from_artifact_version_id"),
        default="",
    )
    if not anchor_artifact_version_id:
        return None
    artifact_map = {
        _require_text(item.get("artifact_version_id")): item
        for item in artifacts
        if item.get("artifact_version_id") is not None
    }
    current = artifact_map.get(anchor_artifact_version_id)
    if current is not None:
        return current
    return get_artifact_version(connection, anchor_artifact_version_id)


def _schedule_artifact_history(
    connection: sqlite3.Connection,
    *,
    artifact: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
    artifact_kind: str,
) -> dict[str, Any]:
    current = _schedule_draft_history_artifact(
        connection,
        artifact=artifact,
        artifacts=artifacts,
        artifact_kind=artifact_kind,
    )
    if current is None:
        return _empty_artifact_history()
    return _artifact_history_for_chain(
        connection,
        current_artifact=current,
        artifacts=artifacts,
    )


def _build_schedule_accepted_series(
    connection: sqlite3.Connection,
    *,
    workflow_run: Mapping[str, Any],
    accepted_series_key: str | None,
    current_partition_key: str | None,
    current_workflow_run_id: str | None,
    current_artifact_version_id: str | None,
) -> dict[str, Any]:
    series_key = _require_text_or_default(accepted_series_key, default="") or None
    if not series_key:
        return _empty_accepted_series()
    rows = list_artifact_versions_for_scope_and_kind(
        connection,
        tenant_id=_require_text(workflow_run.get("tenant_id")),
        domain_id=_require_text(workflow_run.get("domain_id")),
        artifact_kind=SCHEDULE_PUBLISHED_ARTIFACT_KIND,
        workflow_id=_SCHEDULE_WORKFLOW_ID,
    )
    entries = [
        {
            "artifact_version_id": _require_text(row.get("artifact_version_id")),
            "workflow_run_id": _require_text(row.get("workflow_run_id")),
            "partition_key": _require_text_or_default(
                row.get("workflow_partition_key"),
                default="",
            ),
            "logical_date": _require_text_or_default(
                row.get("workflow_logical_date"),
                default="",
            ),
            "artifact_kind": _require_text(row.get("artifact_kind")),
            "route": canonical_schedule_artifact_route(
                workflow_run_id=_require_text(row.get("workflow_run_id")),
                artifact_version_id=_require_text(row.get("artifact_version_id")),
            ),
        }
        for row in rows
        if _schedule_artifact_accepted_series_key(row.get("metadata_json")) == series_key
    ]
    if not entries:
        return _empty_accepted_series(series_key=series_key)
    current_index: int | None = None
    if current_artifact_version_id:
        for index, entry in enumerate(entries):
            if entry["artifact_version_id"] == current_artifact_version_id:
                current_index = index
                break
    if current_index is None and current_partition_key:
        for index, entry in enumerate(entries):
            if entry["partition_key"] != current_partition_key:
                continue
            if current_workflow_run_id and entry["workflow_run_id"] == current_workflow_run_id:
                current_index = index
                break
            if current_index is None:
                current_index = index
    previous_artifact_version_id = (
        entries[current_index - 1]["artifact_version_id"]
        if current_index is not None and current_index > 0
        else None
    )
    next_artifact_version_id = (
        entries[current_index + 1]["artifact_version_id"]
        if current_index is not None and current_index + 1 < len(entries)
        else None
    )
    return {
        "series_key": series_key,
        "current_artifact_version_id": (
            entries[current_index]["artifact_version_id"] if current_index is not None else None
        ),
        "previous_artifact_version_id": previous_artifact_version_id,
        "next_artifact_version_id": next_artifact_version_id,
        "entries": entries,
    }


def _empty_accepted_series(*, series_key: str | None = None) -> dict[str, Any]:
    return {
        "series_key": series_key,
        "current_artifact_version_id": None,
        "previous_artifact_version_id": None,
        "next_artifact_version_id": None,
        "entries": [],
    }


def _accepted_series_anchor_artifact_id(
    accepted_series: Mapping[str, Any],
) -> str | None:
    return _require_text_or_default(
        accepted_series.get("current_artifact_version_id"),
        default="",
    ) or None


def _bundle_schedule_accepted_series_key(bundle: WeeklyScheduleControlBundle) -> str:
    return build_schedule_accepted_series_key(
        station_code=_first_non_empty(slot.station_code for slot in bundle.route_slots),
        service_area=_first_non_empty(slot.service_area for slot in bundle.route_slots),
    )


def _schedule_artifact_accepted_series_key(metadata_json: object) -> str | None:
    if not isinstance(metadata_json, Mapping):
        return None
    value = _require_text_or_default(metadata_json.get("accepted_series_key"), default="")
    return value or None


def _schedule_open_latest_draft_contract_action(
    *,
    workflow_run_id: str,
    latest_schedule_draft: Mapping[str, Any] | None,
) -> dict[str, Any]:
    route: str | None = None
    state = "unavailable"
    artifact_version_id = None
    if latest_schedule_draft is not None:
        artifact_version_id = _require_text_or_default(
            latest_schedule_draft.get("artifact_version_id"),
            default="",
        )
        if artifact_version_id:
            route = canonical_schedule_artifact_route(
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            )
            state = "available"
    return {
        "action_id": "workpage.schedule-v0.open_latest_draft",
        "kind": "open_latest_draft",
        "label": "Open schedule draft",
        "state": state,
        "workpage_kind": SCHEDULE_WORKPAGE_KIND,
        "artifact_version_id": artifact_version_id or None,
        "route": route,
        "action_ref": build_workpage_action_ref(
            action_id="workpage.schedule-v0.open_latest_draft",
            workpage_kind=SCHEDULE_WORKPAGE_KIND,
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id or None,
        ),
    }


def _schedule_route_demand_contract_action(
    *,
    workflow_run_id: str,
    latest_route_demand: Mapping[str, Any] | None,
) -> dict[str, Any]:
    route: str | None = None
    state = "unavailable"
    artifact_version_id = None
    if latest_route_demand is not None:
        artifact_version_id = _require_text_or_default(
            latest_route_demand.get("artifact_version_id"),
            default="",
        )
        if artifact_version_id:
            route = canonical_route_demand_artifact_route(
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            )
            state = "available"
    return {
        "action_id": "workpage.route-demand-v0.open_latest",
        "kind": "open_latest",
        "label": "Open route demand",
        "state": state,
        "workpage_kind": ROUTE_DEMAND_WORKPAGE_KIND,
        "artifact_version_id": artifact_version_id or None,
        "route": route,
        "action_ref": build_workpage_action_ref(
            action_id="workpage.route-demand-v0.open_latest",
            workpage_kind=ROUTE_DEMAND_WORKPAGE_KIND,
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id or None,
        ),
    }


def _schedule_driver_preferences_contract_action(
    *,
    workflow_run_id: str,
    latest_driver_preferences: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if latest_driver_preferences is not None:
        artifact_version_id = _require_text_or_default(
            latest_driver_preferences.get("artifact_version_id"),
            default="",
        )
        if artifact_version_id:
            return {
                "action_id": "workpage.driver-preferences-v0.open_latest",
                "kind": "open_latest",
                "label": "Open driver preferences",
                "state": "available",
                "workpage_kind": DRIVER_PREFERENCES_WORKPAGE_KIND,
                "artifact_version_id": artifact_version_id,
                "route": canonical_driver_preferences_artifact_route(
                    workflow_run_id=workflow_run_id,
                    artifact_version_id=artifact_version_id,
                ),
                "action_ref": build_workpage_action_ref(
                    action_id="workpage.driver-preferences-v0.open_latest",
                    workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
                    workflow_run_id=workflow_run_id,
                    artifact_version_id=artifact_version_id,
                ),
            }
    return {
        "action_id": "workpage.driver-preferences-v0.create_snapshot",
        "kind": "create_snapshot",
        "label": "Create preferences snapshot",
        "state": "available",
        "workpage_kind": DRIVER_PREFERENCES_WORKPAGE_KIND,
        "artifact_version_id": None,
        "route": None,
        "create_path": canonical_driver_preferences_snapshot_create_path(
            workflow_run_id=workflow_run_id
        ),
        "action_ref": build_workpage_action_ref(
            action_id="workpage.driver-preferences-v0.create_snapshot",
            workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
            workflow_run_id=workflow_run_id,
            artifact_version_id=None,
        ),
    }


def _schedule_run_contract_actions(
    *,
    workflow_run_id: str,
    latest_schedule_draft: Mapping[str, Any] | None,
    latest_route_demand: Mapping[str, Any] | None,
    latest_driver_preferences: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    actions = [
        _schedule_open_latest_draft_contract_action(
            workflow_run_id=workflow_run_id,
            latest_schedule_draft=latest_schedule_draft,
        )
    ]
    if latest_route_demand is not None:
        actions.append(
            _schedule_route_demand_contract_action(
                workflow_run_id=workflow_run_id,
                latest_route_demand=latest_route_demand,
            )
        )
    actions.append(
        _schedule_driver_preferences_contract_action(
            workflow_run_id=workflow_run_id,
            latest_driver_preferences=latest_driver_preferences,
        )
    )
    return actions


def _schedule_artifact_contract_actions(
    *,
    workflow_run_id: str,
    artifact_kind: str,
    artifact_version_id: str,
    editable: bool,
    dependencies: list[dict[str, Any]],
    latest_route_demand: Mapping[str, Any] | None,
    latest_driver_preferences: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if editable and artifact_kind == SCHEDULE_DRAFT_DATASET_KEY:
        descriptor = get_workpage_descriptor(SCHEDULE_WORKPAGE_KIND)
        preview_disabled_reason = schedule_preview_disabled_reason(dependencies)
        save_disabled_reason = schedule_save_disabled_reason(dependencies)
        actions.extend(
            [
                {
                    "action_id": str(descriptor.preview_action_id if descriptor is not None else "workpage.schedule-v0.preview_recalc"),
                    "kind": "preview_recalc",
                    "label": str(descriptor.preview_action_label if descriptor is not None else "Preview recalculation"),
                    "state": "blocked" if preview_disabled_reason else "available",
                    "workpage_kind": SCHEDULE_WORKPAGE_KIND,
                    "artifact_version_id": artifact_version_id,
                    "preview_path": canonical_schedule_artifact_preview_path(
                        workflow_run_id=workflow_run_id,
                        artifact_version_id=artifact_version_id,
                    ),
                    "action_ref": build_workpage_action_ref(
                        action_id=str(descriptor.preview_action_id if descriptor is not None else "workpage.schedule-v0.preview_recalc"),
                        workpage_kind=SCHEDULE_WORKPAGE_KIND,
                        workflow_run_id=workflow_run_id,
                        artifact_version_id=artifact_version_id,
                    ),
                    "disabled_reason": preview_disabled_reason,
                },
                {
                    "action_id": "workpage.schedule-v0.save_draft",
                    "kind": "submit_artifact",
                    "label": "Save draft",
                    "state": "blocked" if save_disabled_reason else "available",
                    "workpage_kind": SCHEDULE_WORKPAGE_KIND,
                    "artifact_version_id": artifact_version_id,
                    "submit_path": canonical_schedule_artifact_submit_path(
                        workflow_run_id=workflow_run_id,
                        artifact_version_id=artifact_version_id,
                    ),
                    "action_ref": build_workpage_action_ref(
                        action_id="workpage.schedule-v0.save_draft",
                        workpage_kind=SCHEDULE_WORKPAGE_KIND,
                        workflow_run_id=workflow_run_id,
                        artifact_version_id=artifact_version_id,
                    ),
                    "disabled_reason": save_disabled_reason,
                },
                {
                    "action_id": "workpage.schedule-v0.mark_sick_no_show",
                    "kind": "mark_sick_no_show",
                    "label": "Mark Sick / No Show",
                    "state": "blocked" if preview_disabled_reason else "available",
                    "workpage_kind": SCHEDULE_WORKPAGE_KIND,
                    "artifact_version_id": artifact_version_id,
                    "sick_no_show_path": canonical_schedule_sick_no_show_path(
                        workflow_run_id=workflow_run_id,
                        artifact_version_id=artifact_version_id,
                    ),
                    "action_ref": build_workpage_action_ref(
                        action_id="workpage.schedule-v0.mark_sick_no_show",
                        workpage_kind=SCHEDULE_WORKPAGE_KIND,
                        workflow_run_id=workflow_run_id,
                        artifact_version_id=artifact_version_id,
                    ),
                    "disabled_reason": preview_disabled_reason,
                },
            ]
        )
    if latest_route_demand is not None:
        actions.append(
            _schedule_route_demand_contract_action(
                workflow_run_id=workflow_run_id,
                latest_route_demand=latest_route_demand,
            )
        )
    actions.append(
        _schedule_driver_preferences_contract_action(
            workflow_run_id=workflow_run_id,
            latest_driver_preferences=latest_driver_preferences,
        )
    )
    return actions


def _schedule_artifact_note_body(*, editable: bool) -> str:
    if editable:
        return (
            "This page edits the immutable Stage04 draft weekly schedule workbook only. "
            "It does not claim published weekly truth, does not replace manager-review "
            "evidence, and does not reach into live_dispatch.v1 day-of control."
        )
    return (
        "This page shows the accepted weekly schedule artifact as a read-only view. "
        "Accepted-history navigation remains separate from draft lineage, and saving a new "
        "draft still happens on the Stage04 draft workbook lane."
    )


def _schedule_artifact_source_dataset_keys(*, artifact_kind: str) -> list[str]:
    if artifact_kind in {SCHEDULE_DRAFT_DATASET_KEY, SCHEDULE_PUBLISHED_ARTIFACT_KIND}:
        return [
            artifact_kind,
            _SCHEDULE_DRAFT_DOC_DATASET_KEY,
            _SCHEDULE_VALIDATION_SUMMARY_DATASET_KEY,
            SCHEDULE_CALCULATION_SNAPSHOT_DATASET_KEY,
        ]
    return [artifact_kind]


def _build_schedule_workpage_view_model(
    *,
    bundle: WeeklyScheduleControlBundle,
    latest_schedule_draft: Mapping[str, Any] | None,
    source_examples: Mapping[str, str],
    validation_warnings: list[str],
    driver_preferences_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    primary_demand = _sorted_daily_demand(bundle)[0]
    schedule_projection = _schedule_run_projection(
        bundle=bundle,
        latest_schedule_draft=latest_schedule_draft,
    )
    assignment_rows = _projection_rows(schedule_projection, "rows")
    reserve_rows = _projection_rows(schedule_projection, "reserve_rows")
    return {
        "workpage_id": SCHEDULE_WORKPAGE_KIND,
        "version": 2,
        "title": "Weekly schedule review",
        "mode": "example",
        "workflow_id": _SCHEDULE_WORKFLOW_ID,
        "dataset_key": _INPUT_BUNDLE_DATASET_KEY,
        "source_artifact_version_id": None,
        "source_examples": dict(source_examples),
        "summary": {
            "planning_week_id": bundle.planning_week_id,
            "operational_week_start": bundle.scope_start,
            "service_area": _first_non_empty(slot.service_area for slot in bundle.route_slots),
            "station_code": _first_non_empty(slot.station_code for slot in bundle.route_slots),
            "total_routes_required": sum(
                item.planned_route_count for item in bundle.daily_demand_by_service_date.values()
            ),
            "drivers_in_scope": len(bundle.drivers),
            "on_call_target_per_day": primary_demand.on_call_target,
            "excess_capacity_target_per_day": primary_demand.excess_capacity_target,
            "planner_note": _PLANNER_NOTE,
        },
        "sections": [
            {
                "kind": "summary_cards",
                "title": "Week summary",
                "cards": [
                    {
                        "key": "planning_week",
                        "label": "Planning week",
                        "value": bundle.planning_week_id,
                    },
                    {
                        "key": "total_routes",
                        "label": "Required routes",
                        "value": sum(
                            item.planned_route_count
                            for item in bundle.daily_demand_by_service_date.values()
                        ),
                    },
                    {
                        "key": "drivers",
                        "label": "Drivers in scope",
                        "value": len(bundle.drivers),
                    },
                    {
                        "key": "on_call_target",
                        "label": "Daily on-call target",
                        "value": primary_demand.on_call_target,
                    },
                    {
                        "key": "excess_capacity_target",
                        "label": "Daily excess-capacity target",
                        "value": primary_demand.excess_capacity_target,
                    },
                ],
            },
            {
                "kind": "table",
                "title": "Daily demand and coverage posture",
                "table_id": "day_demand",
                "columns": [
                    {"key": "service_date", "label": "Service date"},
                    {"key": "planned_route_count", "label": "Planned routes"},
                    {"key": "on_call_target", "label": "On-call target"},
                    {"key": "excess_capacity_target", "label": "Excess-capacity target"},
                    {"key": "note", "label": "Note"},
                ],
                "rows": _day_demand_rows(bundle),
            },
            {
                "kind": "table",
                "title": "Selected-day preview",
                "table_id": "selected_day_preview",
                "columns": [
                    {"key": "service_date", "label": "Selected day"},
                    {"key": "routes_required", "label": "Routes required"},
                    {"key": "drivers_available", "label": "Drivers available"},
                    {"key": "projected_on_call_needed", "label": "On-call needed"},
                    {"key": "open_questions", "label": "Open questions"},
                ],
                "rows": [_selected_day_preview_row(bundle)],
            },
            {
                "kind": "table",
                "title": "Driver roster excerpt",
                "table_id": "driver_roster",
                "columns": [
                    {"key": "driver_name", "label": "Driver"},
                    {"key": "employment_type", "label": "Employment"},
                    {
                        "key": "preferred_route_slot_classes",
                        "label": "Preferred slot",
                    },
                    {"key": "target_shifts_per_week", "label": "Target shifts"},
                    {"key": "on_call_eligible", "label": "On-call eligible"},
                    {"key": "previous_week_minutes", "label": "Previous-week minutes"},
                    {"key": "availability_summary", "label": "Availability summary"},
                ],
                "rows": _driver_roster_rows(bundle),
            },
            {
                "kind": "schedule_heatmap",
                "title": "Planned schedule heatmap",
                **_schedule_heatmap_payload(
                    bundle=bundle,
                    assignment_rows=assignment_rows,
                    reserve_rows=reserve_rows,
                    driver_preferences_projection=driver_preferences_projection,
                ),
            },
            {
                "kind": "note_panel",
                "title": "Boundary note",
                "body": (
                    "This page is a weekly-planning review surface. Any selected-day "
                    "controls below are local what-if inputs for the prototype and do "
                    "not replace live_dispatch.v1 day-of truth."
                ),
            },
            {
                "kind": "form",
                "title": "Selected-day what-if inputs",
                "form_id": "selected_day_what_if",
                "fields": [
                    {
                        "key": "scenario_sick_calls",
                        "label": "Scenario sick calls",
                        "input": "multi_select",
                        "options": _multi_select_options(bundle),
                        "value": [],
                    },
                    {
                        "key": "scenario_on_call_assignments",
                        "label": "Scenario on-call assignments",
                        "input": "multi_select",
                        "options": [
                            name
                            for name in _FORM_ON_CALL_OPTIONS
                            if name in _available_driver_names(bundle)
                        ],
                        "value": [],
                    },
                    {
                        "key": "scenario_added_routes",
                        "label": "Scenario added routes",
                        "input": "integer",
                        "value": 0,
                    },
                    {
                        "key": "scenario_dropped_routes",
                        "label": "Scenario dropped routes",
                        "input": "integer",
                        "value": 0,
                    },
                    {
                        "key": "scenario_note",
                        "label": "Planner note",
                        "input": "textarea",
                        "value": "",
                    },
                ],
            },
            {
                "kind": "table",
                "title": "Route assignments",
                "table_id": "assignment_rows",
                "columns": _schedule_table_columns(
                    assignment_rows,
                    preferred_order=[
                        "service_date",
                        "route_slot_id",
                        "assigned_driver_id",
                        "assignment_status",
                        "projected_minutes",
                        "baseline_template_state",
                        "planned_driver_day_state",
                        "new_agreement_required",
                        "new_agreement_trigger_reason",
                        "template_state_preservation_fit",
                        "candidate_delta_id",
                        "source_bundle_id",
                        "iteration_index",
                        "delta_kind",
                        "previous_week_stability",
                    ],
                ),
                "rows": _schedule_scalar_rows(assignment_rows),
            },
            {
                "kind": "table",
                "title": "Reserve posture",
                "table_id": "reserve_rows",
                "columns": _schedule_table_columns(
                    reserve_rows,
                    preferred_order=[
                        "service_date",
                        "route_slot_id",
                        "route_id",
                        "assigned_driver_id",
                        "assignment_status",
                        "phase",
                        "projected_minutes",
                        "availability_state",
                        "baseline_template_state",
                        "planned_driver_day_state",
                        "new_agreement_required",
                        "new_agreement_trigger_reason",
                        "template_state_preservation_fit",
                        "iteration_index",
                        "rationale_code",
                        "assignment_action",
                    ],
                ),
                "rows": _schedule_scalar_rows(reserve_rows),
            },
            {
                "kind": "history_stub",
                "title": "History",
                "entries": [
                    {
                        "label": "Previous week actual-hours snapshot",
                        "value": "available for comparison",
                    },
                    {
                        "label": "Rescue / fairness trend",
                        "value": "future slice",
                    },
                ],
            },
        ],
        "validation": {
            "status": "informational",
            "warnings": validation_warnings,
        },
    }


def _workflow_run_context(workflow_run: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "workflow_run_id": _require_text(workflow_run.get("workflow_run_id")),
        "workflow_id": _require_text(workflow_run.get("workflow_id")),
        "workflow_version": _require_text(workflow_run.get("workflow_version")),
        "partition_key": _require_text(workflow_run.get("partition_key")),
        "logical_date": _require_text(workflow_run.get("logical_date")),
        "activation_key": _require_text(workflow_run.get("activation_key")),
        "state": _require_text(workflow_run.get("state")),
    }


def _schedule_run_projection(
    *,
    bundle: WeeklyScheduleControlBundle,
    latest_schedule_draft: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if latest_schedule_draft is not None:
        return project_stage04_draft_weekly_schedule_workbook(
            _schedule_draft_workbook_bytes_from_artifact(latest_schedule_draft)
        )
    deterministic_build = run_weekly_stage04_deterministic_build(bundle=bundle)
    return project_stage04_draft_weekly_schedule_workbook(
        draft_workbook_bytes_from_metadata_json(deterministic_build.draft_workbook_payload)
    )


def _schedule_draft_workbook_bytes_from_artifact(
    artifact: Mapping[str, Any],
) -> bytes:
    storage_uri = str(artifact.get("storage_uri") or "")
    if storage_uri.startswith("file:"):
        return read_blob(storage_uri)
    return draft_workbook_bytes_from_metadata_json(artifact.get("metadata_json"))


def _schedule_runtime_source_refs(
    *,
    resolved_inputs: Mapping[str, Mapping[str, Any] | None],
    input_bundle_artifact: Mapping[str, Any] | None,
    latest_driver_preferences: Mapping[str, Any] | None,
) -> list[str]:
    refs: list[str] = []
    for slot_key in (
        "route_slot_requirements",
        "approved_availability",
        "driver_capabilities",
        "actual_hours",
    ):
        artifact = resolved_inputs.get(slot_key)
        if artifact is None:
            continue
        ref = _artifact_detail_ref(artifact)
        if ref not in refs:
            refs.append(ref)
    if input_bundle_artifact is not None:
        input_bundle_ref = _artifact_detail_ref(input_bundle_artifact)
        if input_bundle_ref not in refs:
            refs.append(input_bundle_ref)
    if latest_driver_preferences is not None:
        preference_ref = _artifact_detail_ref(latest_driver_preferences)
        if preference_ref not in refs:
            refs.append(preference_ref)
    return refs


def _eod_runtime_source_refs(artifacts: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    latest_draft = _latest_compatible_eod_draft_artifact(artifacts)
    artifacts_by_dataset_key: dict[str, Mapping[str, Any] | None] = {
        _EOD_RAW_DATASET_KEY: _latest_artifact_for_dataset_key(
            artifacts,
            dataset_key=_EOD_RAW_DATASET_KEY,
        ),
        _EOD_NORMALIZED_DATASET_KEY: _latest_artifact_for_dataset_key(
            artifacts,
            dataset_key=_EOD_NORMALIZED_DATASET_KEY,
        ),
        _EOD_DRAFT_DATASET_KEY: latest_draft,
    }
    for _label, dataset_key in _EOD_SOURCE_DATASETS:
        artifact = artifacts_by_dataset_key.get(dataset_key)
        if artifact is None:
            continue
        ref = _artifact_detail_ref(artifact)
        if ref not in refs:
            refs.append(ref)
    return refs


def _eod_draft_resolution(
    *,
    workflow_run_id: str,
    latest_draft: Mapping[str, Any] | None,
) -> dict[str, Any]:
    descriptor = get_workpage_descriptor(EOD_WORKPAGE_KIND)
    create_action_id = (
        str(descriptor.create_action_id)
        if descriptor is not None and descriptor.create_action_id is not None
        else "workpage.eod-v0.create_draft"
    )
    open_action_id = (
        str(descriptor.open_action_id)
        if descriptor is not None and descriptor.open_action_id is not None
        else "workpage.eod-v0.open_latest_draft"
    )
    if latest_draft is None:
        return {
            "state": "no_draft",
            "latest_artifact_version_id": None,
            "artifact_route": None,
            "open_action_ref": None,
            "create_action_ref": build_workpage_action_ref(
                action_id=create_action_id,
                workpage_kind=EOD_WORKPAGE_KIND,
                workflow_run_id=workflow_run_id,
                artifact_version_id=None,
            ),
        }
    latest_artifact_version_id = _require_text(latest_draft.get("artifact_version_id"))
    return {
        "state": "latest_draft_available",
        "latest_artifact_version_id": latest_artifact_version_id,
        "artifact_route": canonical_eod_artifact_route(
            workflow_run_id=workflow_run_id,
            artifact_version_id=latest_artifact_version_id,
        ),
        "open_action_ref": build_workpage_action_ref(
            action_id=open_action_id,
            workpage_kind=EOD_WORKPAGE_KIND,
            workflow_run_id=workflow_run_id,
            artifact_version_id=latest_artifact_version_id,
        ),
        "create_action_ref": None,
    }


def _artifact_detail_ref(artifact: Mapping[str, Any]) -> str:
    return f"/api/v1/artifacts/{_require_text(artifact.get('artifact_version_id'))}"


def _artifact_source_ref(artifact: Mapping[str, Any] | None) -> str | None:
    if artifact is None:
        return None
    artifact_version_id = _require_text_or_default(
        artifact.get("artifact_version_id"),
        default="",
    )
    if not artifact_version_id:
        return None
    return _artifact_detail_ref(artifact)


def _latest_artifact_for_dataset_key(
    artifacts: list[dict[str, Any]],
    *,
    dataset_key: str,
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for artifact in artifacts:
        if str(artifact.get("dataset_key") or artifact.get("artifact_kind") or "") != dataset_key:
            continue
        latest = artifact
    return latest


def _latest_compatible_eod_draft_artifact(
    artifacts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for artifact in artifacts:
        if not _is_compatible_eod_draft_artifact(artifact):
            continue
        latest = artifact
    return latest


def _is_compatible_eod_draft_artifact(artifact: Mapping[str, Any]) -> bool:
    return (
        str(artifact.get("dataset_key") or artifact.get("artifact_kind") or "")
        == _EOD_DRAFT_DATASET_KEY
    )


def _require_mapping(
    value: Mapping[str, Any] | None,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    if value is None:
        raise ValueError(f"{field_name} artifact is required")
    return value


def _optional_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    return value


def build_eod_workflow_run_workpage_contract(
    *,
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    latest_draft = _latest_compatible_eod_draft_artifact(artifacts)

    return {
        **_build_eod_landing_contract(
            source_examples={},
            source_mode="run_projection",
            source_refs=_eod_runtime_source_refs(artifacts),
            freshness_source_kind="workflow_run_projection",
            freshness_source_version=(
                _require_text(latest_draft.get("artifact_version_id"))
                if latest_draft is not None
                else workflow_run_id
            ),
        ),
        "run_context": _workflow_run_context(workflow_run),
        "draft_resolution": _eod_draft_resolution(
            workflow_run_id=workflow_run_id,
            latest_draft=latest_draft,
        ),
        "artifact_history": None,
    }


def _build_eod_landing_contract(
    *,
    source_examples: Mapping[str, str],
    source_mode: str,
    source_refs: list[str],
    freshness_source_kind: str,
    freshness_source_version: str,
) -> dict[str, Any]:
    return {
        "workpage": _build_eod_landing_workpage_view_model(
            source_examples=source_examples,
        ),
        "source": {
            "mode": source_mode,
            "primary_dataset_key": _EOD_DRAFT_DATASET_KEY,
            "source_dataset_keys": [dataset_key for _, dataset_key in _EOD_SOURCE_DATASETS],
            "source_artifact_version_id": None,
            "source_refs": source_refs,
        },
        "freshness": {
            "generated_at": utc_now_iso(),
            "source_kind": freshness_source_kind,
            "source_version": freshness_source_version,
        },
    }


def _build_eod_landing_workpage_view_model(
    *,
    source_examples: Mapping[str, str],
) -> dict[str, Any]:
    route_rows = _load_eod_route_rows()
    normalized_rows = _load_eod_normalized_actuals()
    upd_rows = _load_eod_upd_candidates()
    return {
        "workpage_id": EOD_WORKPAGE_KIND,
        "version": 2,
        "title": "End-of-day report",
        "mode": "example",
        "workflow_id": _EOD_WORKFLOW_ID,
        "dataset_key": _EOD_DRAFT_DATASET_KEY,
        "source_artifact_version_id": None,
        "source_examples": dict(source_examples),
        "summary": _eod_summary(route_rows, normalized_rows),
        "sections": [
            {
                "kind": "summary_cards",
                "title": "Daily summary",
                "cards": _eod_summary_cards(route_rows, normalized_rows),
            },
            {
                "kind": "note_panel",
                "title": "Formula-integrity warning",
                "body": _EOD_NOTE_PANEL_BODY,
            },
            {
                "kind": "table",
                "title": "Route actuals",
                "table_id": "route_actuals",
                "columns": [
                    {"key": "route_id", "label": "Route"},
                    {"key": "driver_name", "label": "Driver"},
                    {"key": "packages_dispatched", "label": "Dispatched"},
                    {"key": "packages_delivered", "label": "Delivered"},
                    {"key": "planned_window", "label": "Planned"},
                    {"key": "actual_window", "label": "Actual"},
                    {"key": "actual_minutes", "label": "Minutes"},
                    {"key": "returns", "label": "Returns"},
                    {"key": "return_reasons", "label": "Return reasons"},
                    {"key": "upd_candidate", "label": "UPD?"},
                ],
                "rows": _eod_route_actual_rows(route_rows, normalized_rows),
            },
            {
                "kind": "form",
                "title": "Manual closeout",
                "form_id": "closeout_details",
                "fields": _eod_form_fields(route_rows),
            },
            {
                "kind": "checklist",
                "title": "UPD candidate review",
                "checklist_id": "upd_candidates",
                "items": _eod_checklist_items(upd_rows),
            },
            {
                "kind": "history_stub",
                "title": "History",
                "entries": [
                    {"label": "Previous daily reports", "value": "future slice"},
                    {"label": "Weekly / monthly summaries", "value": "future slice"},
                ],
            },
        ],
        "validation": {
            "status": "informational",
            "warnings": list(_EOD_VALIDATION_WARNINGS),
        },
    }


def _eod_artifact_contract_actions(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
    editable: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "action_id": "workpage.eod-v0.submit_draft",
            "kind": "submit_artifact",
            "label": "Submit draft",
            "state": "available" if editable else "blocked",
            "workpage_kind": EOD_WORKPAGE_KIND,
            "artifact_version_id": artifact_version_id,
            "submit_path": canonical_eod_artifact_submit_path(
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            ),
            "action_ref": build_workpage_action_ref(
                action_id="workpage.eod-v0.submit_draft",
                workpage_kind=EOD_WORKPAGE_KIND,
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            ),
            "disabled_reason": None if editable else "historical_artifact_read_only",
        }
    ]


def build_eod_artifact_workpage_contract(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    artifact: Mapping[str, Any],
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
    download_path: str,
    projection: Mapping[str, Any],
    source_refs: list[str],
    generated_at: str | None = None,
) -> dict[str, Any]:
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    supersedes_artifact_version_id = (
        _require_text_or_default(artifact.get("supersedes_artifact_version_id"), default="")
        or None
    )
    superseded_by_artifact_version_id = _latest_superseding_artifact_version_id(
        artifact=artifact,
        artifacts=artifacts,
    )
    latest_in_chain_artifact_version_id = _latest_chain_artifact_version_id(
        connection,
        artifact_version_id=artifact_version_id,
        default=artifact_version_id,
    )
    editable = artifact_version_id == latest_in_chain_artifact_version_id
    metadata_json = artifact.get("metadata_json")
    service_date = (
        _require_text_or_default(metadata_json.get("service_date"), default=_EOD_SERVICE_DATE)
        if isinstance(metadata_json, Mapping)
        else _EOD_SERVICE_DATE
    )
    station_code = (
        _require_text_or_default(metadata_json.get("station_code"), default=_EOD_STATION_CODE)
        if isinstance(metadata_json, Mapping)
        else _EOD_STATION_CODE
    )
    dsp_name = (
        _require_text_or_default(metadata_json.get("dsp_name"), default=_EOD_DSP_NAME)
        if isinstance(metadata_json, Mapping)
        else _EOD_DSP_NAME
    )
    route_rows = _projection_rows(projection, "route_actuals")
    manual_closeout_rows = _projection_rows(projection, "manual_closeout")
    checklist_rows = _projection_rows(projection, "upd_candidates")
    quality_warning_rows = _projection_rows(projection, "quality_warnings")

    summary = _artifact_eod_summary(
        route_rows=route_rows,
        quality_warning_rows=quality_warning_rows,
        service_date=service_date,
        station_code=station_code,
        dsp_name=dsp_name,
    )
    return {
        "workpage": {
            "workpage_id": EOD_WORKPAGE_KIND,
            "version": 2,
            "title": "End-of-day report",
            "mode": "example",
            "workflow_id": _EOD_WORKFLOW_ID,
            "dataset_key": _EOD_DRAFT_DATASET_KEY,
            "source_artifact_version_id": artifact_version_id,
            "source_examples": {},
            "summary": summary,
            "sections": [
                {
                    "kind": "summary_cards",
                    "title": "Daily summary",
                    "cards": _artifact_eod_summary_cards(summary),
                },
                {
                    "kind": "note_panel",
                    "title": "Artifact-backed projection note",
                    "body": _artifact_eod_note_body(quality_warning_rows),
                },
                {
                    "kind": "table",
                    "title": "Route actuals",
                    "table_id": "route_actuals",
                    "columns": [
                        {"key": "route_id", "label": "Route"},
                        {"key": "driver_name", "label": "Driver"},
                        {"key": "packages_dispatched", "label": "Dispatched"},
                        {"key": "packages_delivered", "label": "Delivered"},
                        {"key": "planned_window", "label": "Planned"},
                        {"key": "actual_window", "label": "Actual"},
                        {"key": "actual_minutes", "label": "Minutes"},
                        {"key": "returns", "label": "Returns"},
                        {"key": "return_reasons", "label": "Return reasons"},
                        {"key": "upd_candidate", "label": "UPD?"},
                    ],
                    "rows": _artifact_eod_route_actual_rows(route_rows),
                },
                {
                    "kind": "form",
                    "title": "Manual closeout",
                    "form_id": "closeout_details",
                    "fields": _artifact_eod_form_fields(
                        route_rows=route_rows,
                        manual_closeout_rows=manual_closeout_rows,
                    ),
                },
                {
                    "kind": "checklist",
                    "title": "UPD candidate review",
                    "checklist_id": "upd_candidates",
                    "items": _artifact_eod_checklist_items(checklist_rows),
                },
                {
                    "kind": "history_stub",
                    "title": "History",
                    "entries": [
                        {
                            "label": "Current artifact version",
                            "value": artifact_version_id,
                        },
                        {
                            "label": "Supersedes",
                            "value": supersedes_artifact_version_id or "Initial draft",
                        },
                        {
                            "label": "Latest draft in chain",
                            "value": latest_in_chain_artifact_version_id,
                        },
                    ],
                },
            ],
            "validation": {
                "status": "informational",
                "warnings": _artifact_eod_validation_warnings(quality_warning_rows),
            },
        },
        "source": {
            "mode": "artifact_projection",
            "primary_dataset_key": _EOD_DRAFT_DATASET_KEY,
            "source_dataset_keys": [_EOD_DRAFT_DATASET_KEY],
            "source_artifact_version_id": artifact_version_id,
            "source_refs": source_refs,
        },
        "freshness": {
            "generated_at": generated_at or utc_now_iso(),
            "source_kind": "artifact_version",
            "source_version": artifact_version_id,
        },
        "artifact_context": {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": _EOD_DRAFT_DATASET_KEY,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "superseded_by_artifact_version_id": superseded_by_artifact_version_id,
            "latest_in_chain_artifact_version_id": latest_in_chain_artifact_version_id,
            "download_path": download_path,
        },
        "actions": _eod_artifact_contract_actions(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
            editable=editable,
        ),
        "artifact_history": _artifact_history_for_chain(
            connection,
            current_artifact=artifact,
            artifacts=artifacts,
        ),
    }


def build_route_demand_artifact_workpage_contract(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    artifact: Mapping[str, Any],
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
    download_path: str,
    projection: Mapping[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    supersedes_artifact_version_id = (
        _require_text_or_default(artifact.get("supersedes_artifact_version_id"), default="")
        or None
    )
    latest_in_chain_artifact_version_id = _latest_chain_artifact_version_id(
        connection,
        artifact_version_id=artifact_version_id,
        default=artifact_version_id,
    )
    editable = artifact_version_id == latest_in_chain_artifact_version_id
    previous_projection = _route_demand_previous_projection(
        artifacts=artifacts,
        supersedes_artifact_version_id=supersedes_artifact_version_id,
    )
    latest_schedule_draft = latest_schedule_draft_artifact(artifacts)
    schedule_impact = _route_demand_schedule_impact(
        connection,
        workflow_run_id=workflow_run_id,
        artifacts=artifacts,
        latest_route_demand_artifact_version_id=latest_in_chain_artifact_version_id,
        latest_schedule_draft=latest_schedule_draft,
    )
    contract = {
        "workpage": _build_route_demand_workpage_view_model(
            workflow_run=workflow_run,
            projection=projection,
            artifact_version_id=artifact_version_id,
            supersedes_artifact_version_id=supersedes_artifact_version_id,
            latest_in_chain_artifact_version_id=latest_in_chain_artifact_version_id,
            editable=editable,
            validation_warnings=[
                (
                    "This artifact-backed route demand page edits daily route-demand truth only. "
                    "It does not mutate schedule assignments or auto-refresh schedule drafts."
                ),
            ],
        ),
        "source": {
            "mode": "artifact_projection",
            "primary_dataset_key": ROUTE_DEMAND_DATASET_KEY,
            "source_dataset_keys": [ROUTE_DEMAND_DATASET_KEY],
            "source_artifact_version_id": artifact_version_id,
            "source_refs": [f"/api/v1/artifacts/{artifact_version_id}"],
        },
        "freshness": {
            "generated_at": generated_at or utc_now_iso(),
            "source_kind": "artifact_version",
            "source_version": artifact_version_id,
        },
        "artifact_context": {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": ROUTE_DEMAND_ARTIFACT_KIND,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "superseded_by_artifact_version_id": _latest_superseding_artifact_version_id(
                artifact=artifact,
                artifacts=artifacts,
            ),
            "latest_in_chain_artifact_version_id": latest_in_chain_artifact_version_id,
            "download_path": download_path,
        },
        "artifact_state": _route_demand_artifact_state(
            artifact_version_id=artifact_version_id,
            latest_artifact_version_id=latest_in_chain_artifact_version_id,
            editable=editable,
        ),
        "calculations": {
            "day_cards": _route_demand_day_cards(
                projection=projection,
                previous_projection=previous_projection,
            )
        },
        "schedule_impact": schedule_impact,
        "artifact_history": _artifact_history_for_chain(
            connection,
            current_artifact=artifact,
            artifacts=artifacts,
        ),
        "actions": _route_demand_artifact_contract_actions(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
            editable=editable,
        ),
    }
    return contract


def build_driver_preferences_artifact_workpage_contract(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    artifact: Mapping[str, Any],
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
    download_path: str,
    projection: Mapping[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    supersedes_artifact_version_id = (
        _require_text_or_default(artifact.get("supersedes_artifact_version_id"), default="")
        or None
    )
    latest_in_chain_artifact_version_id = _latest_chain_artifact_version_id(
        connection,
        artifact_version_id=artifact_version_id,
        default=artifact_version_id,
    )
    editable = artifact_version_id == latest_in_chain_artifact_version_id
    contract = {
        "workpage": _build_driver_preferences_workpage_view_model(
            workflow_run=workflow_run,
            projection=projection,
            artifact_version_id=artifact_version_id,
            supersedes_artifact_version_id=supersedes_artifact_version_id,
            latest_in_chain_artifact_version_id=latest_in_chain_artifact_version_id,
            editable=editable,
            validation_warnings=[
                "This artifact-backed driver preferences page edits only the immutable weekly advisory snapshot for the selected run.",
                "Preference saves never create refresh tasks and never hard-block schedule preview, save, or publish.",
            ],
        ),
        "source": {
            "mode": "artifact_projection",
            "primary_dataset_key": DRIVER_PREFERENCES_DATASET_KEY,
            "source_dataset_keys": [DRIVER_PREFERENCES_DATASET_KEY],
            "source_artifact_version_id": artifact_version_id,
            "source_refs": [f"/api/v1/artifacts/{artifact_version_id}"],
        },
        "freshness": {
            "generated_at": generated_at or utc_now_iso(),
            "source_kind": "artifact_version",
            "source_version": artifact_version_id,
        },
        "artifact_context": {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": DRIVER_PREFERENCES_DATASET_KEY,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "superseded_by_artifact_version_id": _latest_superseding_artifact_version_id(
                artifact=artifact,
                artifacts=artifacts,
            ),
            "latest_in_chain_artifact_version_id": latest_in_chain_artifact_version_id,
            "download_path": download_path,
        },
        "artifact_state": _driver_preferences_artifact_state(
            artifact_version_id=artifact_version_id,
            latest_artifact_version_id=latest_in_chain_artifact_version_id,
            editable=editable,
        ),
        "preference_grid": _driver_preferences_grid(
            workflow_run=workflow_run,
            projection=projection,
        ),
        "driver_availability_exceptions": driver_availability_exceptions_for_workflow_run(
            connection,
            workflow_run=workflow_run,
        ),
        "schedule_impact": _driver_preferences_schedule_impact(
            artifacts=artifacts,
            latest_driver_preferences=latest_driver_preferences_artifact(artifacts),
        ),
        "artifact_history": _artifact_history_for_chain(
            connection,
            current_artifact=artifact,
            artifacts=artifacts,
        ),
        "actions": _driver_preferences_artifact_contract_actions(
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
            editable=editable,
        ),
    }
    return contract


def _route_demand_projection_from_artifact(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    return project_route_demand_workbook(
        _route_demand_workbook_bytes_from_artifact(artifact)
    )


def _route_demand_workbook_bytes_from_artifact(
    artifact: Mapping[str, Any],
) -> bytes:
    storage_uri = str(artifact.get("storage_uri") or "")
    if storage_uri.startswith("file:"):
        return read_blob(storage_uri)
    return route_demand_workbook_bytes_from_metadata_json(artifact.get("metadata_json"))


def _build_route_demand_workpage_view_model(
    *,
    workflow_run: Mapping[str, Any],
    projection: Mapping[str, Any],
    artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    latest_in_chain_artifact_version_id: str | None,
    editable: bool,
    validation_warnings: list[str],
) -> dict[str, Any]:
    summary = _route_demand_summary(
        workflow_run=workflow_run,
        projection=projection,
    )
    history_entries = [
        {
            "label": "Current artifact version",
            "value": artifact_version_id or "Run-backed latest artifact",
        },
        {
            "label": "Supersedes",
            "value": supersedes_artifact_version_id or "Initial route demand version",
        },
        {
            "label": "Latest route demand version",
            "value": latest_in_chain_artifact_version_id or "Unavailable",
        },
    ]
    return {
        "workpage_id": ROUTE_DEMAND_WORKPAGE_KIND,
        "version": 1,
        "title": (
            "Weekly route demand editor"
            if artifact_version_id
            else "Weekly route demand review"
        ),
        "mode": "example",
        "workflow_id": _SCHEDULE_WORKFLOW_ID,
        "dataset_key": ROUTE_DEMAND_DATASET_KEY,
        "source_artifact_version_id": artifact_version_id,
        "source_examples": {},
        "summary": summary,
        "sections": [
            {
                "kind": "summary_cards",
                "title": "Route demand summary",
                "cards": [
                    {
                        "key": "planning_week_id",
                        "label": "Planning week",
                        "value": summary["planning_week_id"],
                    },
                    {
                        "key": "service_day_count",
                        "label": "Service days",
                        "value": summary["service_day_count"],
                    },
                    {
                        "key": "planned_route_total",
                        "label": "Planned routes",
                        "value": summary["planned_route_total"],
                    },
                    {
                        "key": "station_code",
                        "label": "Station",
                        "value": summary["station_code"],
                    },
                    {
                        "key": "service_area",
                        "label": "Service area",
                        "value": summary["service_area"],
                    },
                ],
            },
            {
                "kind": "note_panel",
                "title": "Route demand boundary",
                "body": (
                    "This page edits route-demand truth only. Schedule reassignment, preview, and "
                    "save stay on schedule-v0, and route-demand saves never auto-refresh schedule artifacts."
                ),
            },
            {
                "kind": "table",
                "title": "Daily route demand",
                "table_id": "route_demand_daily_rows",
                "columns": [
                    {"key": "service_date", "label": "Service date"},
                    {"key": "planned_route_count", "label": "Planned routes"},
                    {"key": "standard_slot_count", "label": "Standard"},
                    {"key": "rescue_slot_count", "label": "Rescue"},
                    {"key": "overflow_slot_count", "label": "Overflow"},
                    {"key": "on_call_target", "label": "On-call target"},
                    {"key": "excess_capacity_target", "label": "Excess-capacity target"},
                ],
                "rows": [
                    {
                        "service_date": item["service_date"],
                        "planned_route_count": item["planned_route_count"],
                        "standard_slot_count": item["standard_slot_count"],
                        "rescue_slot_count": item["rescue_slot_count"],
                        "overflow_slot_count": item["overflow_slot_count"],
                        "on_call_target": item.get("on_call_target"),
                        "excess_capacity_target": item.get("excess_capacity_target"),
                    }
                    for item in _route_demand_day_cards(
                        projection=projection,
                        previous_projection=None,
                    )
                ],
            },
            {
                "kind": "history_stub",
                "title": "History",
                "entries": history_entries,
            },
        ],
        "validation": {
            "status": "informational",
            "warnings": validation_warnings,
        },
    }


def _route_demand_summary(
    *,
    workflow_run: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    day_cards = _route_demand_day_cards(
        projection=projection,
        previous_projection=None,
    )
    station_code = ""
    service_area = ""
    for row in _projection_rows(projection, "rows"):
        station_code = station_code or _require_text_or_default(row.get("station_code"), default="")
        service_area = service_area or _require_text_or_default(row.get("service_area"), default="")
        if station_code and service_area:
            break
    if not station_code or not service_area:
        for row in _projection_rows(projection, "daily_demand_rows"):
            station_code = station_code or _require_text_or_default(row.get("station_code"), default="")
            service_area = service_area or _require_text_or_default(row.get("service_area"), default="")
            if station_code and service_area:
                break
    return {
        "planning_week_id": _require_text_or_default(
            workflow_run.get("partition_key") or projection.get("planning_week_id"),
            default="unknown",
        ),
        "operational_week_start": (
            day_cards[0]["service_date"] if day_cards else _require_text_or_default(workflow_run.get("logical_date"), default="")
        ),
        "service_day_count": len(day_cards),
        "planned_route_total": sum(_require_int(item.get("planned_route_count")) for item in day_cards),
        "station_code": station_code or "unknown",
        "service_area": service_area or "unknown",
    }


def _route_demand_day_cards(
    *,
    projection: Mapping[str, Any],
    previous_projection: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    daily_rows = _projection_rows(projection, "daily_demand_rows")
    previous_by_date = {
        _require_text(row.get("service_date")): row
        for row in _projection_rows(previous_projection or {}, "daily_demand_rows")
        if str(row.get("service_date") or "").strip()
    }
    cards: list[dict[str, Any]] = []
    for row in daily_rows:
        service_date = _require_text(row.get("service_date"))
        previous_row = previous_by_date.get(service_date)
        current_planned = max(_require_int(row.get("planned_route_count")), 0)
        previous_planned = (
            max(_require_int(previous_row.get("planned_route_count")), 0)
            if previous_row is not None
            else None
        )
        cards.append(
            {
                "service_date": service_date,
                "weekday_label": _weekday_label(service_date),
                "planned_route_count": current_planned,
                "standard_slot_count": max(
                    _require_int_or_default(
                        row.get("standard_slot_count"),
                        default=current_planned,
                    ),
                    0,
                ),
                "standard_early_slot_count": _require_int_or_default(
                    row.get("standard_early_slot_count"),
                    default=0,
                ),
                "standard_late_slot_count": _require_int_or_default(
                    row.get("standard_late_slot_count"),
                    default=0,
                ),
                "rescue_slot_count": max(
                    _require_int_or_default(row.get("rescue_slot_count"), default=0),
                    0,
                ),
                "overflow_slot_count": max(
                    _require_int_or_default(row.get("overflow_slot_count"), default=0),
                    0,
                ),
                "on_call_target": _require_int_or_default(row.get("on_call_target"), default=0),
                "excess_capacity_target": _require_int_or_default(
                    row.get("excess_capacity_target"),
                    default=0,
                ),
                "delta_from_previous_version": (
                    {
                        "planned_route_count_delta": current_planned - previous_planned,
                    }
                    if previous_planned is not None
                    else None
                ),
            }
        )
    return cards


def _route_demand_previous_projection(
    *,
    artifacts: list[dict[str, Any]],
    supersedes_artifact_version_id: str | None,
) -> dict[str, Any] | None:
    if not supersedes_artifact_version_id:
        return None
    for artifact in artifacts:
        if _require_text_or_default(artifact.get("artifact_version_id"), default="") != supersedes_artifact_version_id:
            continue
        return _route_demand_projection_from_artifact(artifact)
    return None


def _route_demand_run_artifact_state(
    *,
    latest_artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    latest_artifact_version_id = (
        _require_text_or_default(latest_artifact.get("artifact_version_id"), default="")
        if latest_artifact is not None
        else ""
    )
    return {
        "state_kind": "run_projection",
        "artifact_kind": ROUTE_DEMAND_ARTIFACT_KIND,
        "editable": False,
        "current_artifact_version_id": None,
        "latest_artifact_version_id": latest_artifact_version_id or None,
        "accepted_artifact_version_id": None,
    }


def _route_demand_artifact_state(
    *,
    artifact_version_id: str,
    latest_artifact_version_id: str,
    editable: bool,
) -> dict[str, Any]:
    return {
        "state_kind": "artifact_projection",
        "artifact_kind": ROUTE_DEMAND_ARTIFACT_KIND,
        "editable": editable,
        "current_artifact_version_id": artifact_version_id,
        "latest_artifact_version_id": latest_artifact_version_id,
        "accepted_artifact_version_id": None,
    }


def _route_demand_open_latest_contract_action(
    *,
    workflow_run_id: str,
    latest_artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    route: str | None = None
    state = "unavailable"
    artifact_version_id = None
    if latest_artifact is not None:
        artifact_version_id = _require_text_or_default(
            latest_artifact.get("artifact_version_id"),
            default="",
        )
        if artifact_version_id:
            route = canonical_route_demand_artifact_route(
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            )
            state = "available"
    return {
        "action_id": "workpage.route-demand-v0.open_latest",
        "kind": "open_latest",
        "label": "Open route demand",
        "state": state,
        "workpage_kind": ROUTE_DEMAND_WORKPAGE_KIND,
        "artifact_version_id": artifact_version_id or None,
        "route": route,
        "action_ref": build_workpage_action_ref(
            action_id="workpage.route-demand-v0.open_latest",
            workpage_kind=ROUTE_DEMAND_WORKPAGE_KIND,
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id or None,
        ),
    }


def _route_demand_artifact_contract_actions(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
    editable: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "action_id": "workpage.route-demand-v0.save",
            "kind": "save",
            "label": "Save route demand",
            "state": "available" if editable else "blocked",
            "workpage_kind": ROUTE_DEMAND_WORKPAGE_KIND,
            "artifact_version_id": artifact_version_id,
            "submit_path": canonical_route_demand_artifact_submit_path(
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            ),
            "action_ref": build_workpage_action_ref(
                action_id="workpage.route-demand-v0.save",
                workpage_kind=ROUTE_DEMAND_WORKPAGE_KIND,
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            ),
            "disabled_reason": None if editable else "historical_artifact_read_only",
        }
    ]


def _build_driver_preferences_bundle_for_run(
    *,
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> WeeklyScheduleControlBundle:
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    try:
        resolved_inputs = resolve_weekly_stage04_input_artifacts(
            artifacts=artifacts,
            stage_spec={
                "required_evidence_keys": [
                    _ROUTE_SLOT_DATASET_KEY,
                    _DRIVER_CAPABILITIES_DATASET_KEY,
                ]
            },
        )
        return build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=_require_mapping(
                resolved_inputs.get("route_slot_requirements"),
                field_name="route_slot_requirements",
            ),
            driver_capabilities_artifact=_require_mapping(
                resolved_inputs.get("driver_capabilities"),
                field_name="driver_capabilities",
            ),
            approved_availability_artifact=_optional_mapping(
                resolved_inputs.get("approved_availability")
            ),
            actual_hours_artifact=_optional_mapping(resolved_inputs.get("actual_hours")),
            route_horizon_artifact=None,
        )
    except CommandError as exc:
        if exc.code != "stage04_input_artifact_missing":
            raise
        missing_slots = exc.details.get("missing_slots", [])
        missing_dataset_keys = [
            _require_text(slot.get("dataset_key"))
            for slot in missing_slots
            if isinstance(slot, dict) and slot.get("dataset_key") is not None
        ]
        raise WorkpageProjectionUnavailableError(
            workflow_run_id=workflow_run_id,
            workpage_id="driver-preferences-v0",
            message="driver-preferences workpage is unavailable until the weekly Stage04 roster inputs exist for this run",
            missing_dataset_keys=missing_dataset_keys,
        ) from exc
    except ValueError as exc:
        raise WorkpageProjectionUnavailableError(
            workflow_run_id=workflow_run_id,
            workpage_id="driver-preferences-v0",
            message=f"driver-preferences workpage is unavailable: {exc}",
        ) from exc


def _driver_preferences_projection_from_artifact(
    artifact: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if artifact is None:
        return None
    return project_driver_preferences_workbook(
        driver_preferences_workbook_bytes_from_metadata_json(artifact.get("metadata_json"))
    )


def _initial_driver_preferences_projection(
    bundle: WeeklyScheduleControlBundle,
) -> dict[str, Any]:
    payload = build_initial_driver_preferences_workbook(bundle=bundle)
    return {
        "weekdays": list(payload.get("weekdays") or []),
        "service_dates": [
            dict(item)
            for item in payload.get("service_dates", [])
            if isinstance(item, Mapping)
        ],
        "drivers": list(payload.get("drivers") or []),
    }


def _driver_preferences_runtime_source_refs(
    *,
    latest_artifact: Mapping[str, Any] | None,
    artifacts: list[dict[str, Any]],
) -> list[str]:
    refs: list[str] = []
    if latest_artifact is not None:
        refs.append(_artifact_detail_ref(latest_artifact))
    driver_capabilities = _latest_artifact_for_dataset_key(
        artifacts,
        dataset_key=_DRIVER_CAPABILITIES_DATASET_KEY,
    )
    if driver_capabilities is not None:
        ref = _artifact_detail_ref(driver_capabilities)
        if ref not in refs:
            refs.append(ref)
    return refs


def _build_driver_preferences_workpage_view_model(
    *,
    workflow_run: Mapping[str, Any],
    projection: Mapping[str, Any],
    artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    latest_in_chain_artifact_version_id: str | None,
    editable: bool,
    validation_warnings: list[str],
) -> dict[str, Any]:
    summary = _driver_preferences_summary(
        workflow_run=workflow_run,
        projection=projection,
    )
    history_entries = [
        {
            "label": "Current artifact version",
            "value": artifact_version_id or "Run-backed latest snapshot",
        },
        {
            "label": "Supersedes",
            "value": supersedes_artifact_version_id or "Initial preferences snapshot",
        },
        {
            "label": "Latest snapshot version",
            "value": latest_in_chain_artifact_version_id or "Unavailable",
        },
    ]
    return {
        "workpage_id": "driver-preferences-v0",
        "version": 1,
        "title": (
            "Weekly driver preferences snapshot"
            if artifact_version_id
            else "Weekly driver preferences"
        ),
        "mode": "example",
        "workflow_id": _SCHEDULE_WORKFLOW_ID,
        "dataset_key": DRIVER_PREFERENCES_DATASET_KEY,
        "source_artifact_version_id": artifact_version_id,
        "source_examples": {},
        "summary": summary,
        "sections": [
            {
                "kind": "summary_cards",
                "title": "Preferences summary",
                "cards": [
                    {
                        "key": "planning_week_id",
                        "label": "Planning week",
                        "value": summary["planning_week_id"],
                    },
                    {
                        "key": "driver_count",
                        "label": "Drivers in scope",
                        "value": summary["driver_count"],
                    },
                    {
                        "key": "on_call_eligible_count",
                        "label": "On-call eligible",
                        "value": summary["on_call_eligible_count"],
                    },
                    {
                        "key": "explicit_preference_count",
                        "label": "Recorded preferences",
                        "value": summary["explicit_preference_count"],
                    },
                    {
                        "key": "unset_preference_count",
                        "label": "Unset cells",
                        "value": summary["unset_preference_count"],
                    },
                ],
            },
            {
                "kind": "note_panel",
                "title": "Preferences boundary",
                "body": (
                    "This page stores a weekly Sunday-Saturday advisory snapshot only. "
                    "It informs schedule highlighting and soft drift cues without becoming hard scheduling truth."
                ),
            },
            {
                "kind": "history_stub",
                "title": "History",
                "entries": history_entries,
            },
        ],
        "validation": {
            "status": "informational",
            "warnings": validation_warnings,
        },
    }


def _driver_preferences_summary(
    *,
    workflow_run: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    drivers = [
        dict(item)
        for item in projection.get("drivers", [])
        if isinstance(item, Mapping)
    ]
    explicit_preference_count = 0
    unset_preference_count = 0
    on_call_eligible_count = 0
    for driver in drivers:
        if bool(driver.get("on_call_eligible")):
            on_call_eligible_count += 1
        preferences = driver.get("preferences_by_weekday")
        if not isinstance(preferences, Mapping):
            continue
        for value in preferences.values():
            if str(value or "").strip():
                explicit_preference_count += 1
            else:
                unset_preference_count += 1
    return {
        "planning_week_id": _require_text_or_default(
            workflow_run.get("partition_key") or projection.get("planning_week_id"),
            default="unknown",
        ),
        "driver_count": len(drivers),
        "on_call_eligible_count": on_call_eligible_count,
        "explicit_preference_count": explicit_preference_count,
        "unset_preference_count": unset_preference_count,
    }


def _driver_preferences_grid(
    *,
    workflow_run: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "weekdays": [
            str(value or "").strip()
            for value in projection.get("weekdays", [])
            if str(value or "").strip()
        ],
        "service_dates": _driver_preferences_service_dates(
            workflow_run=workflow_run,
            projection=projection,
        ),
        "drivers": [
            dict(item)
            for item in projection.get("drivers", [])
            if isinstance(item, Mapping)
        ],
    }


def _driver_preferences_service_dates(
    *,
    workflow_run: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> list[dict[str, str]]:
    projection_service_dates = [
        {
            "service_date": _require_text(item.get("service_date")),
            "label": _require_text_or_default(item.get("label"), default=_require_text(item.get("service_date"))),
            "weekday_label": _require_text_or_default(
                item.get("weekday_label"),
                default=_weekday_label(_require_text(item.get("service_date"))),
            ),
        }
        for item in projection.get("service_dates", [])
        if isinstance(item, Mapping) and str(item.get("service_date") or "").strip()
    ]
    if projection_service_dates:
        return projection_service_dates
    return _weekly_service_dates_from_start(
        _require_text_or_default(workflow_run.get("logical_date"), default="")
    )


def _driver_preferences_run_artifact_state(
    *,
    latest_artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    latest_artifact_version_id = (
        _require_text_or_default(latest_artifact.get("artifact_version_id"), default="")
        if latest_artifact is not None
        else ""
    )
    return {
        "state_kind": "run_projection",
        "artifact_kind": DRIVER_PREFERENCES_DATASET_KEY,
        "editable": False,
        "current_artifact_version_id": None,
        "latest_artifact_version_id": latest_artifact_version_id or None,
        "accepted_artifact_version_id": None,
    }


def _driver_preferences_artifact_state(
    *,
    artifact_version_id: str,
    latest_artifact_version_id: str,
    editable: bool,
) -> dict[str, Any]:
    return {
        "state_kind": "artifact_projection",
        "artifact_kind": DRIVER_PREFERENCES_DATASET_KEY,
        "editable": editable,
        "current_artifact_version_id": artifact_version_id,
        "latest_artifact_version_id": latest_artifact_version_id,
        "accepted_artifact_version_id": None,
    }


def _driver_preferences_run_contract_actions(
    *,
    workflow_run_id: str,
    latest_artifact: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    add_exception_action = _driver_preferences_add_exception_contract_action(
        workflow_run_id=workflow_run_id,
    )
    if latest_artifact is not None:
        artifact_version_id = _require_text_or_default(
            latest_artifact.get("artifact_version_id"),
            default="",
        )
        if artifact_version_id:
            return [
                {
                    "action_id": "workpage.driver-preferences-v0.open_latest",
                    "kind": "open_latest",
                    "label": "Open latest snapshot",
                    "state": "available",
                    "workpage_kind": DRIVER_PREFERENCES_WORKPAGE_KIND,
                    "artifact_version_id": artifact_version_id,
                    "route": canonical_driver_preferences_artifact_route(
                        workflow_run_id=workflow_run_id,
                        artifact_version_id=artifact_version_id,
                    ),
                    "action_ref": build_workpage_action_ref(
                        action_id="workpage.driver-preferences-v0.open_latest",
                        workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
                        workflow_run_id=workflow_run_id,
                        artifact_version_id=artifact_version_id,
                    ),
                },
                add_exception_action,
            ]
    return [
        {
            "action_id": "workpage.driver-preferences-v0.create_snapshot",
            "kind": "create_snapshot",
            "label": "Create preferences snapshot",
            "state": "available",
            "workpage_kind": DRIVER_PREFERENCES_WORKPAGE_KIND,
            "artifact_version_id": None,
            "route": None,
            "create_path": canonical_driver_preferences_snapshot_create_path(
                workflow_run_id=workflow_run_id
            ),
            "action_ref": build_workpage_action_ref(
                action_id="workpage.driver-preferences-v0.create_snapshot",
                workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
                workflow_run_id=workflow_run_id,
                artifact_version_id=None,
            ),
        },
        add_exception_action,
    ]


def _driver_preferences_artifact_contract_actions(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
    editable: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "action_id": "workpage.driver-preferences-v0.save",
            "kind": "save",
            "label": "Save preferences snapshot",
            "state": "available" if editable else "blocked",
            "workpage_kind": DRIVER_PREFERENCES_WORKPAGE_KIND,
            "artifact_version_id": artifact_version_id,
            "submit_path": canonical_driver_preferences_artifact_submit_path(
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            ),
            "action_ref": build_workpage_action_ref(
                action_id="workpage.driver-preferences-v0.save",
                workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
            ),
            "disabled_reason": None if editable else "historical_artifact_read_only",
        },
        _driver_preferences_add_exception_contract_action(
            workflow_run_id=workflow_run_id,
        ),
    ]


def _driver_preferences_add_exception_contract_action(
    *,
    workflow_run_id: str,
) -> dict[str, Any]:
    return {
        "action_id": "workpage.driver-preferences-v0.add_availability_exception",
        "kind": "add_availability_exception",
        "label": "Add availability exception",
        "state": "available",
        "workpage_kind": DRIVER_PREFERENCES_WORKPAGE_KIND,
        "artifact_version_id": None,
        "create_path": canonical_driver_availability_exception_create_path(
            workflow_run_id=workflow_run_id,
        ),
        "action_ref": build_workpage_action_ref(
            action_id="workpage.driver-preferences-v0.add_availability_exception",
            workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
            workflow_run_id=workflow_run_id,
            artifact_version_id=None,
        ),
        "disabled_reason": None,
    }


def _driver_preferences_schedule_impact(
    *,
    artifacts: list[dict[str, Any]],
    latest_driver_preferences: Mapping[str, Any] | None,
) -> dict[str, Any]:
    latest_schedule_draft = latest_schedule_draft_artifact(artifacts)
    latest_driver_preferences_artifact_version_id = (
        _require_text_or_default(latest_driver_preferences.get("artifact_version_id"), default="")
        or None
        if latest_driver_preferences is not None
        else None
    )
    if latest_schedule_draft is None:
        return {
            "latest_schedule_draft_artifact_version_id": None,
            "latest_driver_preferences_artifact_version_id": latest_driver_preferences_artifact_version_id,
            "dependency_state": "no_draft",
            "schedule_state": "no_draft",
        }
    if latest_driver_preferences is None:
        return {
            "latest_schedule_draft_artifact_version_id": _require_text(
                latest_schedule_draft.get("artifact_version_id")
            ),
            "latest_driver_preferences_artifact_version_id": None,
            "dependency_state": "no_snapshot",
            "schedule_state": "no_snapshot",
        }
    dependency_projection = project_schedule_dependency_state(
        dependency_manifest=_schedule_artifact_dependency_manifest(
            latest_schedule_draft.get("metadata_json")
        ),
        artifacts=artifacts,
    )
    driver_preferences_dependency = next(
        (
            row
            for row in dependency_projection.dependencies
            if _require_text(row.get("dependency_key")) == "driver_preferences"
        ),
        None,
    )
    dependency_state = (
        _require_text_or_default(
            driver_preferences_dependency.get("state"),
            default="aligned",
        )
        if driver_preferences_dependency is not None
        else "aligned"
    )
    return {
        "latest_schedule_draft_artifact_version_id": _require_text(
            latest_schedule_draft.get("artifact_version_id")
        ),
        "latest_driver_preferences_artifact_version_id": latest_driver_preferences_artifact_version_id,
        "dependency_state": dependency_state,
        "schedule_state": dependency_state,
    }


def _route_demand_schedule_impact(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    artifacts: list[dict[str, Any]],
    latest_route_demand_artifact_version_id: str,
    latest_schedule_draft: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if latest_schedule_draft is None:
        return {
            "latest_schedule_draft_artifact_version_id": None,
            "dependency_state": "no_draft",
            "schedule_state": "no_draft",
            "refresh_task": None,
        }
    dependency_projection = project_schedule_dependency_state(
        dependency_manifest=_schedule_artifact_dependency_manifest(
            latest_schedule_draft.get("metadata_json")
        ),
        artifacts=artifacts,
    )
    route_dependency = next(
        (
            row
            for row in dependency_projection.dependencies
            if _require_text(row.get("dependency_key")) == "route_slot_requirements"
        ),
        None,
    )
    dependency_state = (
        _require_text_or_default(route_dependency.get("state"), default="aligned")
        if route_dependency is not None
        else "aligned"
    )
    refresh_task = _route_demand_active_refresh_task_summary(
        connection,
        workflow_run_id=workflow_run_id,
    )
    schedule_state = dependency_state
    if dependency_state == "drifted" and refresh_task is not None:
        schedule_state = "awaiting_refresh"
    return {
        "latest_schedule_draft_artifact_version_id": _require_text(
            latest_schedule_draft.get("artifact_version_id")
        ),
        "dependency_state": dependency_state,
        "schedule_state": schedule_state,
        "refresh_task": refresh_task,
        "latest_route_demand_artifact_version_id": latest_route_demand_artifact_version_id,
    }


def _route_demand_active_refresh_task_summary(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    for task in reversed(list_human_tasks_for_workflow_run(connection, workflow_run_id)):
        task_run = get_task_run(connection, str(task.get("task_run_id") or ""))
        if task_run is None:
            continue
        activation_key = _require_text_or_default(task_run.get("activation_key"), default="")
        if not activation_key.startswith(ROUTE_DEMAND_REFRESH_TASK_ACTIVATION_PREFIX):
            continue
        if _require_text(task_run.get("stage_id")) != "Stage04":
            continue
        if _require_text(task.get("task_kind")) != "work_item":
            continue
        task_state = _require_text_or_default(task.get("state"), default="")
        if task_state not in {"OPEN", "CLAIMED"}:
            continue
        return {
            "human_task_id": _require_text(task.get("human_task_id")),
            "task_run_id": _require_text(task.get("task_run_id")),
            "state": task_state,
            "owner_role": _require_text_or_default(task.get("owner_role"), default="") or None,
            "activation_key": activation_key,
            "blocked_on_kind": _require_text_or_default(task_run.get("blocked_on_kind"), default="") or None,
            "blocked_on_ref": _require_text_or_default(task_run.get("blocked_on_ref"), default="") or None,
        }
    return None


def build_schedule_artifact_workpage_contract(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    artifact: Mapping[str, Any],
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
    download_path: str,
    projection: Mapping[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    assignment_rows = _projection_rows(projection, "rows")
    reserve_rows = _projection_rows(projection, "reserve_rows")
    iteration_rows = _projection_rows(projection, "iteration_deltas")
    summary = _schedule_artifact_summary(
        workflow_run=workflow_run,
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
        iteration_rows=iteration_rows,
    )
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    artifact_kind = _require_text(
        artifact.get("artifact_kind") or artifact.get("dataset_key")
    )
    editable = artifact_kind == SCHEDULE_DRAFT_DATASET_KEY
    supersedes_artifact_version_id = (
        _require_text_or_default(artifact.get("supersedes_artifact_version_id"), default="")
        or None
    )
    superseded_by_artifact_version_id = _latest_superseding_artifact_version_id(
        artifact=artifact,
        artifacts=artifacts,
    )
    latest_in_chain_artifact_version_id = _latest_chain_artifact_version_id(
        connection,
        artifact_version_id=artifact_version_id,
        default=artifact_version_id,
    )
    metadata_json = artifact.get("metadata_json")
    draft_anchor_artifact_version_id = _schedule_anchor_artifact_version_id(
        artifact=artifact,
        artifact_kind=artifact_kind,
    )
    dependency_projection = project_schedule_dependency_state(
        dependency_manifest=_schedule_artifact_dependency_manifest(metadata_json),
        artifacts=artifacts,
    )
    dependency_artifacts = resolve_schedule_dependency_artifacts(
        workflow_run_id=workflow_run_id,
        artifacts=artifacts,
        dependency_manifest=_schedule_artifact_dependency_manifest(metadata_json),
    )
    driver_preferences_projection = _driver_preferences_projection_from_artifact(
        dependency_artifacts.get("driver_preferences")
        or latest_driver_preferences_artifact(artifacts)
    )
    try:
        bundle = build_schedule_bundle_from_dependencies(
            workflow_run=workflow_run,
            dependency_artifacts_by_key=dependency_artifacts,
        )
    except ValueError:
        bundle = None
    companion_artifacts = _schedule_companion_artifacts_for_draft(
        artifacts=artifacts,
        draft_artifact_version_id=draft_anchor_artifact_version_id,
    )
    calculation_snapshot = _schedule_calculation_snapshot_payload(
        companion_artifacts.get(SCHEDULE_CALCULATION_SNAPSHOT_DATASET_KEY),
    )
    contract = {
        "workpage": {
            "workpage_id": SCHEDULE_WORKPAGE_KIND,
            "version": 2,
            "title": (
                "Weekly schedule draft artifact"
                if editable
                else "Weekly published schedule artifact"
            ),
            "mode": "example",
            "workflow_id": _SCHEDULE_WORKFLOW_ID,
            "dataset_key": artifact_kind,
            "source_artifact_version_id": artifact_version_id,
            "source_examples": {},
            "summary": summary,
            "sections": [
                {
                    "kind": "summary_cards",
                    "title": "Draft workbook summary",
                    "cards": [
                        {
                            "key": "planning_week_id",
                            "label": "Planning week",
                            "value": summary["planning_week_id"],
                        },
                        {
                            "key": "route_assignment_count",
                            "label": "Route assignments",
                            "value": summary["route_assignment_count"],
                        },
                        {
                            "key": "reserve_assignment_count",
                            "label": "Reserve rows",
                            "value": summary["reserve_assignment_count"],
                        },
                        {
                            "key": "iteration_count",
                            "label": "Iterations",
                            "value": summary["iteration_count"],
                        },
                        {
                            "key": "source_bundle_id",
                            "label": "Source bundle",
                            "value": summary["source_bundle_id"],
                        },
                    ],
                },
                {
                    "kind": "schedule_heatmap",
                    "title": "Planned schedule heatmap",
                    "subtitle": (
                        "Click a filled cell to arm it, then click another cell on the same day "
                        "to move or swap the planned state before saving a new draft."
                    ),
                    **_schedule_heatmap_payload(
                        bundle=bundle,
                        assignment_rows=assignment_rows,
                        reserve_rows=reserve_rows,
                        driver_preferences_projection=driver_preferences_projection,
                    ),
                },
                {
                    "kind": "table",
                    "title": "Daily demand and coverage posture",
                    "table_id": "day_demand",
                    "columns": [
                        {"key": "service_date", "label": "Service date"},
                        {"key": "planned_route_count", "label": "Planned routes"},
                        {"key": "on_call_target", "label": "On-call target"},
                        {"key": "excess_capacity_target", "label": "Excess-capacity target"},
                        {"key": "note", "label": "Note"},
                    ],
                    "rows": _artifact_day_demand_rows(
                        bundle=bundle,
                        assignment_rows=assignment_rows,
                        reserve_rows=reserve_rows,
                    ),
                },
                {
                    "kind": "table",
                    "title": "Selected-day preview",
                    "table_id": "selected_day_preview",
                    "columns": [
                        {"key": "service_date", "label": "Selected day"},
                        {"key": "routes_required", "label": "Routes required"},
                        {"key": "drivers_available", "label": "Drivers available"},
                        {"key": "projected_on_call_needed", "label": "On-call needed"},
                        {"key": "open_questions", "label": "Open questions"},
                    ],
                    "rows": [
                        _artifact_selected_day_preview_row(
                            bundle=bundle,
                            assignment_rows=assignment_rows,
                            reserve_rows=reserve_rows,
                        )
                    ],
                },
                {
                    "kind": "table",
                    "title": "Driver roster",
                    "table_id": "driver_roster",
                    "columns": [
                        {"key": "driver_name", "label": "Driver"},
                        {"key": "employment_type", "label": "Employment"},
                        {
                            "key": "preferred_route_slot_classes",
                            "label": "Preferred slot",
                        },
                        {"key": "target_shifts_per_week", "label": "Target shifts"},
                        {"key": "on_call_eligible", "label": "On-call eligible"},
                        {"key": "previous_week_minutes", "label": "Previous-week minutes"},
                        {"key": "availability_summary", "label": "Availability summary"},
                    ],
                    "rows": _artifact_driver_roster_rows(
                        bundle=bundle,
                        assignment_rows=assignment_rows,
                        reserve_rows=reserve_rows,
                    ),
                },
                {
                    "kind": "note_panel",
                    "title": (
                        "Stage04 draft boundary"
                        if editable
                        else "Accepted weekly boundary"
                    ),
                    "body": _schedule_artifact_note_body(editable=editable),
                },
                {
                    "kind": "table",
                    "title": "Route assignments",
                    "table_id": "assignment_rows",
                    "columns": _schedule_table_columns(
                        assignment_rows,
                        preferred_order=[
                            "service_date",
                            "route_slot_id",
                            "assigned_driver_id",
                            "assignment_status",
                            "projected_minutes",
                            "baseline_template_state",
                            "planned_driver_day_state",
                            "new_agreement_required",
                            "new_agreement_trigger_reason",
                            "template_state_preservation_fit",
                            "candidate_delta_id",
                            "source_bundle_id",
                            "iteration_index",
                            "delta_kind",
                            "previous_week_stability",
                        ],
                    ),
                    "rows": _schedule_scalar_rows(assignment_rows),
                },
                {
                    "kind": "table",
                    "title": "Reserve posture",
                    "table_id": "reserve_rows",
                    "columns": _schedule_table_columns(
                        reserve_rows,
                        preferred_order=[
                            "service_date",
                            "route_slot_id",
                            "route_id",
                            "assigned_driver_id",
                            "assignment_status",
                            "phase",
                            "projected_minutes",
                            "availability_state",
                            "baseline_template_state",
                            "planned_driver_day_state",
                            "new_agreement_required",
                            "new_agreement_trigger_reason",
                            "template_state_preservation_fit",
                            "iteration_index",
                            "rationale_code",
                            "assignment_action",
                        ],
                    ),
                    "rows": _schedule_scalar_rows(reserve_rows),
                },
                {
                    "kind": "table",
                    "title": "Iteration deltas",
                    "table_id": "iteration_deltas",
                    "columns": _schedule_table_columns(
                        iteration_rows,
                        preferred_order=[
                            "iteration_index",
                            "batch_id",
                            "planning_phase",
                            "pressure_group_id",
                            "batch_size",
                            "route_slot_ids",
                            "assigned_route_slot_ids",
                            "uncovered_route_slot_ids",
                            "moved_route_slot_ids",
                        ],
                    ),
                    "rows": _schedule_scalar_rows(iteration_rows),
                },
                {
                    "kind": "history_stub",
                    "title": "History",
                    "entries": [
                        {
                            "label": "Current artifact version",
                            "value": artifact_version_id,
                        },
                        {
                            "label": "Supersedes",
                            "value": supersedes_artifact_version_id or "Initial Stage04 draft",
                        },
                        {
                            "label": "Latest draft in chain",
                            "value": latest_in_chain_artifact_version_id,
                        },
                    ],
                },
            ],
            "validation": {
                "status": "informational",
                "warnings": [
                    "This artifact-backed schedule workpage edits only the Stage04 draft weekly schedule workbook for the selected run.",
                    "Published weekly truth still begins only at Stage06 pointer promotion, and live dispatch remains downstream.",
                ],
            },
        },
        "source": {
            "mode": "artifact_projection",
            "primary_dataset_key": artifact_kind,
            "source_dataset_keys": _schedule_artifact_source_dataset_keys(artifact_kind=artifact_kind),
            "source_artifact_version_id": artifact_version_id,
            "source_refs": _schedule_artifact_source_refs(
                artifact_version_id=artifact_version_id,
                artifact_kind=artifact_kind,
                companion_artifacts=companion_artifacts,
            ),
        },
        "freshness": {
            "generated_at": generated_at or utc_now_iso(),
            "source_kind": "artifact_version",
            "source_version": artifact_version_id,
        },
        "artifact_context": {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": artifact_kind,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "superseded_by_artifact_version_id": superseded_by_artifact_version_id,
            "latest_in_chain_artifact_version_id": latest_in_chain_artifact_version_id,
            "download_path": download_path,
        },
    }
    accepted_series = _build_schedule_accepted_series(
        connection,
        workflow_run=workflow_run,
        accepted_series_key=_schedule_artifact_accepted_series_key(metadata_json),
        current_partition_key=_require_text(workflow_run.get("partition_key")),
        current_workflow_run_id=workflow_run_id,
        current_artifact_version_id=(
            artifact_version_id if artifact_kind == SCHEDULE_PUBLISHED_ARTIFACT_KIND else None
        ),
    )
    artifact_history = _schedule_artifact_history(
        connection,
        artifact=artifact,
        artifacts=artifacts,
        artifact_kind=artifact_kind,
    )
    contract.update(
        {
            "artifact_state": _schedule_artifact_state(
                artifact_kind=artifact_kind,
                artifact_version_id=artifact_version_id,
                latest_in_chain_artifact_version_id=latest_in_chain_artifact_version_id,
                accepted_artifact_version_id=_accepted_series_anchor_artifact_id(accepted_series),
                editable=editable,
            ),
            "dependencies": _schedule_dependency_rows_for_artifact(
                dependencies=dependency_projection.dependencies,
            ),
            "calculations": (
                calculation_snapshot
                if calculation_snapshot is not None
                else (
                    build_schedule_calculations(
                        bundle=bundle,
                        assignment_rows=assignment_rows,
                        reserve_rows=reserve_rows,
                        driver_preferences_projection=driver_preferences_projection,
                    )
                    if bundle is not None
                    else _schedule_calculations(
                        day_demand_rows=_artifact_day_demand_rows(
                            bundle=bundle,
                            assignment_rows=assignment_rows,
                            reserve_rows=reserve_rows,
                        ),
                        selected_day_row=_artifact_selected_day_preview_row(
                            bundle=bundle,
                            assignment_rows=assignment_rows,
                            reserve_rows=reserve_rows,
                        ),
                    )
                )
            ),
            "artifact_history": artifact_history,
            "draft_lineage": _draft_lineage_from_artifact_history(artifact_history),
            "accepted_series": accepted_series,
            "actions": _schedule_artifact_contract_actions(
                workflow_run_id=workflow_run_id,
                artifact_kind=artifact_kind,
                artifact_version_id=artifact_version_id,
                editable=editable,
                dependencies=dependency_projection.dependencies,
                latest_route_demand=latest_route_demand_artifact(artifacts),
                latest_driver_preferences=latest_driver_preferences_artifact(artifacts),
            ),
        }
    )
    return contract

def _sorted_daily_demand(bundle: WeeklyScheduleControlBundle) -> list[Any]:
    return sorted(
        bundle.daily_demand_by_service_date.values(),
        key=lambda item: item.service_date,
    )


def _day_demand_rows(bundle: WeeklyScheduleControlBundle) -> list[dict[str, Any]]:
    daily_demand = _sorted_daily_demand(bundle)
    max_demand = max((item.planned_route_count for item in daily_demand), default=0)
    rows: list[dict[str, Any]] = []
    for item in daily_demand:
        notes = ["Holdout route total override"]
        if item.planned_route_count == max_demand and max_demand > 0:
            notes.append("Highest-demand day in the example week")
        if item.service_date == _PREVIEW_SERVICE_DATE:
            notes.append("Selected-day preview default")
        rows.append(
            {
                "service_date": item.service_date,
                "planned_route_count": item.planned_route_count,
                "on_call_target": item.on_call_target,
                "excess_capacity_target": item.excess_capacity_target,
                "note": "; ".join(notes),
            }
        )
    return rows


@lru_cache(maxsize=1)
def _load_eod_route_rows() -> tuple[dict[str, Any], ...]:
    return _load_tabular_example_rows(_EOD_SOURCE_EXAMPLES["eos_route_rows"])


@lru_cache(maxsize=1)
def _load_eod_normalized_actuals() -> tuple[dict[str, Any], ...]:
    return _load_tabular_example_rows(_EOD_SOURCE_EXAMPLES["normalized_actuals"])


@lru_cache(maxsize=1)
def _load_eod_upd_candidates() -> tuple[dict[str, Any], ...]:
    return _load_tabular_example_rows(_EOD_SOURCE_EXAMPLES["upd_candidates"])


def _load_tabular_example_rows(relative_path: str) -> tuple[dict[str, Any], ...]:
    loaded = yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"tabular example must decode to an object: {relative_path}")

    columns = loaded.get("columns")
    rows = loaded.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        raise ValueError(f"tabular example must define columns and rows: {relative_path}")

    column_names = [_require_text(column) for column in columns]
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != len(column_names):
            raise ValueError(f"tabular example row shape mismatch: {relative_path}")
        normalized_rows.append(dict(zip(column_names, row)))
    return tuple(normalized_rows)


def _eod_summary(
    route_rows: tuple[dict[str, Any], ...],
    normalized_rows: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    packages_dispatched = sum(_require_int(row.get("packages_dispatched")) for row in route_rows)
    packages_delivered = sum(_require_int(row.get("packages_delivered")) for row in route_rows)
    packages_returned = sum(_require_int(row.get("returned_packages")) for row in normalized_rows)
    actual_minutes = [_require_int(row.get("actual_minutes")) for row in normalized_rows]
    formula_warning = any(str(row.get("formula_integrity_warning") or "").strip() for row in normalized_rows)

    return {
        "service_date": _EOD_SERVICE_DATE,
        "station_code": _EOD_STATION_CODE,
        "dsp_name": _EOD_DSP_NAME,
        "total_routes_actual": len(route_rows),
        "packages_dispatched": packages_dispatched,
        "actual_dispatched": packages_dispatched,
        "packages_delivered": packages_delivered,
        "packages_returned": packages_returned,
        "delivered_pct": _percent(packages_delivered, packages_dispatched),
        "return_pct": _percent(packages_returned, packages_dispatched),
        "average_route_time": _format_average_minutes(actual_minutes),
        "formula_integrity_warning": formula_warning,
        "warning_note": _EOD_WARNING_NOTE,
    }


def _eod_summary_cards(
    route_rows: tuple[dict[str, Any], ...],
    normalized_rows: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    summary = _eod_summary(route_rows, normalized_rows)
    return [
        {
            "key": "total_routes",
            "label": "Total routes actual",
            "value": summary["total_routes_actual"],
        },
        {
            "key": "packages_dispatched",
            "label": "Packages dispatched",
            "value": summary["packages_dispatched"],
        },
        {
            "key": "packages_delivered",
            "label": "Packages delivered",
            "value": summary["packages_delivered"],
        },
        {
            "key": "packages_returned",
            "label": "Packages returned",
            "value": summary["packages_returned"],
        },
        {
            "key": "delivered_pct",
            "label": "Delivered %",
            "value": f"{summary['delivered_pct']:.2f}%",
        },
        {
            "key": "average_route_time",
            "label": "Average route time",
            "value": summary["average_route_time"],
        },
    ]


def _eod_route_actual_rows(
    route_rows: tuple[dict[str, Any], ...],
    normalized_rows: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    normalized_by_key = {
        _eod_row_identity(row): row for row in normalized_rows
    }
    rows: list[dict[str, Any]] = []
    for route_row in route_rows:
        identity = _eod_row_identity(route_row)
        normalized_row = normalized_by_key.get(identity)
        if normalized_row is None:
            raise ValueError(f"normalized actuals missing for EOD route row: {identity}")
        rows.append(
            {
                "route_id": _require_text(route_row.get("route_id")),
                "driver_name": _require_text(route_row.get("driver_name")),
                "packages_dispatched": _require_int(route_row.get("packages_dispatched")),
                "packages_delivered": _require_int(route_row.get("packages_delivered")),
                "planned_window": _time_window(
                    route_row.get("planned_start"),
                    route_row.get("planned_finish"),
                ),
                "actual_window": _time_window(
                    route_row.get("actual_start"),
                    route_row.get("actual_finish"),
                ),
                "actual_minutes": _require_int(normalized_row.get("actual_minutes")),
                "returns": _require_int(normalized_row.get("returned_packages")),
                "return_reasons": str(normalized_row.get("return_reasons") or ""),
                "upd_candidate": bool(normalized_row.get("upd_candidate")),
            }
        )
    return rows


def _eod_form_fields(route_rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    driver_options = _unique_driver_names(route_rows)
    last_clockout = max(_require_text(row.get("actual_finish")) for row in route_rows)
    return [
        {
            "key": "sick_calls",
            "label": "Sick calls",
            "input": "multi_select",
            "options": driver_options,
            "value": [],
        },
        {
            "key": "unavailable_drivers",
            "label": "Not available",
            "input": "multi_select",
            "options": driver_options,
            "value": [],
        },
        {
            "key": "working_devices",
            "label": "Working devices / rabbits",
            "input": "text",
            "value": "",
        },
        {
            "key": "rescues",
            "label": "Rescues",
            "input": "repeater",
            "value": [],
        },
        {
            "key": "incidents",
            "label": "Incidents",
            "input": "repeater",
            "value": [],
        },
        {
            "key": "last_driver_clockout",
            "label": "Last driver clock-out",
            "input": "time",
            "value": last_clockout,
        },
        {
            "key": "dispatcher_comment",
            "label": "Dispatcher comment",
            "input": "textarea",
            "value": "",
        },
        {
            "key": "manager_note",
            "label": "Manager note",
            "input": "textarea",
            "value": "",
        },
    ]


def _eod_checklist_items(upd_rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in upd_rows:
        route_id = _require_text(row.get("route_id"))
        items.append(
            {
                "item_id": f"upd-candidate-{route_id.lower()}",
                "title": f"{_require_text(row.get('driver_name'))} · {route_id}",
                "detail": _require_text(row.get("reason")),
                "selected": False,
                "note": "",
                "tags": [f"{_require_int(row.get('actual_minutes'))} minutes"],
            }
        )
    return items


def _projection_rows(projection: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    raw_rows = projection.get(key)
    if not isinstance(raw_rows, list):
        return []
    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        if isinstance(row, Mapping):
            rows.append(dict(row))
    return rows


def _build_schedule_artifact_bundle(
    *,
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> WeeklyScheduleControlBundle | None:
    try:
        resolved_inputs = resolve_weekly_stage04_input_artifacts(
            artifacts=artifacts,
            stage_spec={
                "required_evidence_keys": [
                    _ROUTE_SLOT_DATASET_KEY,
                    _DRIVER_CAPABILITIES_DATASET_KEY,
                ]
            },
        )
        return build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=_require_mapping(
                resolved_inputs.get("route_slot_requirements"),
                field_name="route_slot_requirements",
            ),
            driver_capabilities_artifact=_require_mapping(
                resolved_inputs.get("driver_capabilities"),
                field_name="driver_capabilities",
            ),
            approved_availability_artifact=_optional_mapping(
                resolved_inputs.get("approved_availability")
            ),
            actual_hours_artifact=_optional_mapping(resolved_inputs.get("actual_hours")),
            route_horizon_artifact=None,
        )
    except (CommandError, ValueError):
        return None


def _schedule_heatmap_payload(
    *,
    bundle: WeeklyScheduleControlBundle | None,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
    driver_preferences_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    preferences_projection = annotate_driver_preferences_projection(
        driver_preferences_projection
    )
    service_dates = _schedule_heatmap_service_dates(
        bundle=bundle,
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
    )
    people = _schedule_heatmap_people(
        bundle=bundle,
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
        service_dates=service_dates,
    )
    cell_map = _schedule_heatmap_cell_map(
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
    )
    return {
        "service_dates": service_dates,
        "people": [
            {
                **person,
                "cells": [
                    _schedule_heatmap_cell_payload(
                        driver_id=person["driver_id"],
                        service_date=item["service_date"],
                        row=cell_map.get((person["driver_id"], item["service_date"])),
                        bundle=bundle,
                        driver_preferences_projection=preferences_projection,
                    )
                    for item in service_dates
                ],
            }
            for person in people
        ],
    }


def _schedule_heatmap_service_dates(
    *,
    bundle: WeeklyScheduleControlBundle | None,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if bundle is not None:
        ordered_dates = sorted(bundle.daily_demand_by_service_date.keys())
    else:
        ordered_dates = sorted(
            {
                _require_text(row.get("service_date"))
                for row in [*assignment_rows, *reserve_rows]
                if str(row.get("service_date") or "").strip()
            }
        )
    selected_service_date = (
        _selected_day_service_date(bundle) if bundle is not None else (ordered_dates[0] if ordered_dates else "")
    )
    return [
        {
            "service_date": service_date,
            "label": service_date,
            "weekday_label": _weekday_label(service_date),
            "is_selected_day": service_date == selected_service_date,
        }
        for service_date in ordered_dates
    ]


def _schedule_heatmap_people(
    *,
    bundle: WeeklyScheduleControlBundle | None,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
    service_dates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    people: list[dict[str, Any]] = []
    seen_driver_ids: set[str] = set()

    if bundle is not None:
        for driver in sorted(
            bundle.drivers,
            key=lambda item: (
                str(item.driver_name or item.driver_id).lower(),
                item.driver_id,
            ),
        ):
            availability = bundle.availability_by_driver.get(driver.driver_id)
            people.append(
                {
                    "driver_id": driver.driver_id,
                    "driver_name": driver.driver_name or driver.driver_id,
                    "employment_type": (
                        driver.employment_type
                        or (availability.employment_type if availability is not None else "")
                    ),
                    "on_call_eligible": (
                        bool(availability.on_call_eligible)
                        if availability is not None
                        else False
                    ),
                    "previous_week_minutes": bundle.actual_minutes_by_driver.get(driver.driver_id, 0),
                    "availability_summary": _availability_summary(availability),
                }
            )
            seen_driver_ids.add(driver.driver_id)

    referenced_driver_ids = sorted(
        {
            _require_text(row.get("assigned_driver_id"))
            for row in [*assignment_rows, *reserve_rows]
            if str(row.get("assigned_driver_id") or "").strip()
        }
    )
    for driver_id in referenced_driver_ids:
        if driver_id in seen_driver_ids:
            continue
        people.append(
            {
                "driver_id": driver_id,
                "driver_name": driver_id,
                "employment_type": "",
                "on_call_eligible": False,
                "previous_week_minutes": 0,
                "availability_summary": "driver only present in the current draft rows",
            }
        )
        seen_driver_ids.add(driver_id)

    if people:
        return people

    fallback_people: list[dict[str, Any]] = []
    for index, service_date in enumerate(service_dates):
        fallback_people.append(
            {
                "driver_id": f"unassigned-{index + 1}",
                "driver_name": f"Unassigned {service_date['service_date']}",
                "employment_type": "",
                "on_call_eligible": False,
                "previous_week_minutes": 0,
                "availability_summary": "No driver rows available",
            }
        )
    return fallback_people


def _schedule_heatmap_cell_map(
    *,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    cell_map: dict[tuple[str, str], dict[str, Any]] = {}
    for row in assignment_rows:
        driver_id = str(row.get("assigned_driver_id") or "").strip()
        service_date = str(row.get("service_date") or "").strip()
        if not driver_id or not service_date:
            continue
        cell_map[(driver_id, service_date)] = {
            "row_kind": "assignment",
            "row": row,
        }
    for row in reserve_rows:
        driver_id = str(row.get("assigned_driver_id") or "").strip()
        service_date = str(row.get("service_date") or "").strip()
        if not driver_id or not service_date:
            continue
        cell_map.setdefault(
            (driver_id, service_date),
            {
                "row_kind": "reserve",
                "row": row,
            },
        )
    return cell_map


def _schedule_heatmap_cell_payload(
    *,
    driver_id: str,
    service_date: str,
    row: dict[str, Any] | None,
    bundle: WeeklyScheduleControlBundle | None,
    driver_preferences_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    preference_state = driver_preference_value_for_service_date(
        projection=driver_preferences_projection,
        driver_id=driver_id,
        service_date=service_date,
    )
    availability_metadata = _schedule_heatmap_availability_metadata(
        bundle=bundle,
        driver_id=driver_id,
        service_date=service_date,
    )
    if row is None:
        return {
            "service_date": service_date,
            "state": "empty",
            "row_kind": None,
            "route_slot_id": None,
            "projected_minutes": None,
            "assignment_status": None,
            "planned_driver_day_state": None,
            "manual_override": False,
            "preference_state": preference_state,
            **availability_metadata,
        }
    source_row = _require_mapping(row.get("row"), field_name="row")
    row_kind = str(row.get("row_kind") or "").strip() or None
    planned_state = str(source_row.get("planned_driver_day_state") or "").strip()
    if not planned_state:
        planned_state = "on_call" if row_kind == "reserve" else "assigned"
    assignment_status = str(source_row.get("assignment_status") or "").strip() or None
    return {
        "service_date": service_date,
        "state": planned_state or "empty",
        "row_kind": row_kind,
        "route_slot_id": str(source_row.get("route_slot_id") or "").strip() or None,
        "projected_minutes": _int_or_none(source_row.get("projected_minutes")),
        "assignment_status": assignment_status,
        "planned_driver_day_state": planned_state or None,
        "manual_override": assignment_status == "manual_override",
        "preference_state": preference_state,
        **availability_metadata,
    }


def _schedule_heatmap_availability_metadata(
    *,
    bundle: WeeklyScheduleControlBundle | None,
    driver_id: str,
    service_date: str,
) -> dict[str, str | None]:
    if bundle is None:
        return {
            "availability_state": None,
            "availability_reason_code": None,
            "availability_source_ref": None,
        }
    availability = bundle.availability_by_driver.get(driver_id)
    if availability is None:
        return {
            "availability_state": "unknown",
            "availability_reason_code": None,
            "availability_source_ref": None,
        }
    for day_state in availability.daily_states:
        if day_state.service_date != service_date:
            continue
        return {
            "availability_state": str(day_state.normalized_state or day_state.state or "").strip() or "unknown",
            "availability_reason_code": str(getattr(day_state, "reason_code", "") or "").strip() or None,
            "availability_source_ref": str(day_state.source_ref or "").strip() or None,
        }
    return {
        "availability_state": "unknown",
        "availability_reason_code": None,
        "availability_source_ref": None,
    }


def _artifact_day_demand_rows(
    *,
    bundle: WeeklyScheduleControlBundle | None,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if bundle is not None:
        return _day_demand_rows(bundle)

    counts = _schedule_daily_row_counts(
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
    )
    return [
        {
            "service_date": service_date,
            "planned_route_count": counts["assignment_count"],
            "on_call_target": counts["reserve_count"],
            "excess_capacity_target": 0,
            "note": "Derived from current draft rows only",
        }
        for service_date, counts in sorted(counts.items())
    ]


def _artifact_selected_day_preview_row(
    *,
    bundle: WeeklyScheduleControlBundle | None,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if bundle is not None:
        return _selected_day_preview_row(bundle)

    counts_by_date = _schedule_daily_row_counts(
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
    )
    if not counts_by_date:
        return {
            "service_date": "",
            "routes_required": 0,
            "drivers_available": 0,
            "projected_on_call_needed": 0,
            "open_questions": _SELECTED_DAY_OPEN_QUESTION,
        }
    service_date = next(iter(sorted(counts_by_date.keys())))
    counts = counts_by_date[service_date]
    return {
        "service_date": service_date,
        "routes_required": counts["assignment_count"],
        "drivers_available": counts["assignment_count"] + counts["reserve_count"],
        "projected_on_call_needed": counts["reserve_count"],
        "open_questions": _SELECTED_DAY_OPEN_QUESTION,
    }


def _artifact_driver_roster_rows(
    *,
    bundle: WeeklyScheduleControlBundle | None,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if bundle is not None:
        return _full_driver_roster_rows(bundle)

    driver_ids = sorted(
        {
            _require_text(row.get("assigned_driver_id"))
            for row in [*assignment_rows, *reserve_rows]
            if str(row.get("assigned_driver_id") or "").strip()
        }
    )
    return [
        {
            "driver_name": driver_id,
            "employment_type": "",
            "preferred_route_slot_classes": "",
            "target_shifts_per_week": 0,
            "on_call_eligible": False,
            "previous_week_minutes": 0,
            "availability_summary": "driver only present in the current draft rows",
        }
        for driver_id in driver_ids
    ]


def _schedule_artifact_summary(
    *,
    workflow_run: Mapping[str, Any],
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
    iteration_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    first_assignment = assignment_rows[0] if assignment_rows else {}
    source_bundle_id = _require_text_or_default(
        first_assignment.get("source_bundle_id"),
        default="unavailable",
    )
    candidate_delta_id = _require_text_or_default(
        first_assignment.get("candidate_delta_id"),
        default="unavailable",
    )
    return {
        "planning_week_id": _require_text(workflow_run.get("partition_key")),
        "operational_week_start": _require_text(workflow_run.get("logical_date")),
        "route_assignment_count": len(assignment_rows),
        "reserve_assignment_count": len(reserve_rows),
        "iteration_count": len(iteration_rows),
        "source_bundle_id": source_bundle_id,
        "candidate_delta_id": candidate_delta_id,
    }


def _schedule_artifact_source_refs(
    *,
    artifact_version_id: str,
    artifact_kind: str,
    companion_artifacts: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    refs = [f"/api/v1/artifacts/{artifact_version_id}"]
    for dataset_key in (
        _SCHEDULE_DRAFT_DOC_DATASET_KEY,
        _SCHEDULE_VALIDATION_SUMMARY_DATASET_KEY,
        SCHEDULE_CALCULATION_SNAPSHOT_DATASET_KEY,
    ):
        artifact = companion_artifacts.get(dataset_key)
        if artifact is None:
            continue
        ref = _artifact_detail_ref(artifact)
        if ref not in refs:
            refs.append(ref)
    return refs


def _schedule_anchor_artifact_version_id(
    *,
    artifact: Mapping[str, Any],
    artifact_kind: str,
) -> str:
    if artifact_kind == SCHEDULE_DRAFT_DATASET_KEY:
        return _require_text(artifact.get("artifact_version_id"))
    metadata_json = artifact.get("metadata_json")
    if isinstance(metadata_json, Mapping):
        anchored = _require_text_or_default(
            metadata_json.get("published_from_artifact_version_id"),
            default="",
        )
        if anchored:
            return anchored
    return _require_text(artifact.get("artifact_version_id"))


def _schedule_artifact_dependency_manifest(metadata_json: object) -> object:
    if isinstance(metadata_json, Mapping):
        return metadata_json.get("dependency_manifest")
    return None


def _schedule_companion_artifacts_for_draft(
    *,
    artifacts: list[dict[str, Any]],
    draft_artifact_version_id: str,
) -> dict[str, dict[str, Any]]:
    companion_artifacts: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        if _require_text_or_default(artifact.get("parent_artifact_version_id"), default="") != draft_artifact_version_id:
            continue
        artifact_kind = _require_text_or_default(
            artifact.get("artifact_kind") or artifact.get("dataset_key"),
            default="",
        )
        if artifact_kind not in {
            _SCHEDULE_DRAFT_DOC_DATASET_KEY,
            _SCHEDULE_VALIDATION_SUMMARY_DATASET_KEY,
            SCHEDULE_CALCULATION_SNAPSHOT_DATASET_KEY,
        }:
            continue
        companion_artifacts[artifact_kind] = artifact
    return companion_artifacts


def _schedule_calculation_snapshot_payload(
    artifact: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if artifact is None:
        return None
    metadata_json = artifact.get("metadata_json")
    if not isinstance(metadata_json, Mapping):
        return None
    calculations = metadata_json.get("calculations")
    if not isinstance(calculations, Mapping):
        return None
    return dict(calculations)


def _latest_superseding_artifact_version_id(
    *,
    artifact: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> str | None:
    artifact_version_id = _require_text_or_default(
        artifact.get("artifact_version_id"),
        default="",
    )
    if not artifact_version_id:
        return None
    latest: str | None = None
    for item in artifacts:
        supersedes_artifact_version_id = _require_text_or_default(
            item.get("supersedes_artifact_version_id"),
            default="",
        )
        if supersedes_artifact_version_id != artifact_version_id:
            continue
        latest = _require_text_or_default(item.get("artifact_version_id"), default="") or latest
    return latest


def _latest_chain_artifact_version_id(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    default: str,
) -> str:
    try:
        latest = get_latest_artifact_version_in_chain(connection, artifact_version_id)
    except ValueError:
        return default
    if latest is None:
        return default
    return _require_text_or_default(latest.get("artifact_version_id"), default=default)


def _schedule_table_columns(
    rows: list[dict[str, Any]],
    *,
    preferred_order: list[str],
) -> list[dict[str, str]]:
    if not rows:
        return [{"key": "empty", "label": "No rows"}]
    first_row = rows[0]
    ordered_keys = [key for key in preferred_order if key in first_row]
    ordered_keys.extend(
        key for key in first_row.keys() if key not in ordered_keys
    )
    return [
        {
            "key": key,
            "label": key.replace("_", " ").title(),
        }
        for key in ordered_keys
    ]


def _schedule_scalar_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: _schedule_scalar_value(value)
            for key, value in row.items()
        }
        for row in rows
    ]


def _schedule_scalar_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _artifact_eod_summary(
    *,
    route_rows: list[dict[str, Any]],
    quality_warning_rows: list[dict[str, Any]],
    service_date: str,
    station_code: str,
    dsp_name: str,
) -> dict[str, Any]:
    packages_dispatched = sum(_int_or_zero(row.get("packages_dispatched")) for row in route_rows)
    packages_delivered = sum(_int_or_zero(row.get("packages_delivered")) for row in route_rows)
    packages_returned = sum(_int_or_zero(row.get("returns")) for row in route_rows)
    actual_minutes = [_int_or_zero(row.get("actual_minutes")) for row in route_rows]
    formula_warning = len(quality_warning_rows) > 0

    return {
        "service_date": service_date,
        "station_code": station_code,
        "dsp_name": dsp_name,
        "total_routes_actual": len(route_rows),
        "packages_dispatched": packages_dispatched,
        "actual_dispatched": packages_dispatched,
        "packages_delivered": packages_delivered,
        "packages_returned": packages_returned,
        "delivered_pct": _percent(packages_delivered, packages_dispatched),
        "return_pct": _percent(packages_returned, packages_dispatched),
        "average_route_time": _format_average_minutes(actual_minutes),
        "formula_integrity_warning": formula_warning,
        "warning_note": _EOD_WARNING_NOTE,
    }


def _artifact_eod_summary_cards(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "key": "total_routes",
            "label": "Total routes actual",
            "value": summary["total_routes_actual"],
        },
        {
            "key": "packages_dispatched",
            "label": "Packages dispatched",
            "value": summary["packages_dispatched"],
        },
        {
            "key": "packages_delivered",
            "label": "Packages delivered",
            "value": summary["packages_delivered"],
        },
        {
            "key": "packages_returned",
            "label": "Packages returned",
            "value": summary["packages_returned"],
        },
        {
            "key": "delivered_pct",
            "label": "Delivered %",
            "value": f"{summary['delivered_pct']:.2f}%",
        },
        {
            "key": "average_route_time",
            "label": "Average route time",
            "value": summary["average_route_time"],
        },
    ]


def _artifact_eod_note_body(quality_warning_rows: list[dict[str, Any]]) -> str:
    if not quality_warning_rows:
        return (
            "This page is projected from an immutable Stage03 reporting workbook artifact. "
            "Quality warnings are surfaced from the workbook when present, and formulas are not recomputed."
        )

    warning_messages = [
        _require_text(row.get("message"))
        for row in quality_warning_rows
        if str(row.get("message") or "").strip()
    ]
    joined = "; ".join(warning_messages[:2])
    if joined:
        return (
            "This page is projected from an immutable Stage03 reporting workbook artifact. "
            f"Workbook warnings remain visible instead of being recomputed: {joined}"
        )
    return (
        "This page is projected from an immutable Stage03 reporting workbook artifact. "
        "Workbook warnings remain visible instead of being recomputed."
    )


def _artifact_eod_route_actual_rows(route_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in route_rows:
        rows.append(
            {
                "route_id": str(row.get("route_id") or ""),
                "driver_name": str(row.get("driver_name") or ""),
                "packages_dispatched": _int_or_zero(row.get("packages_dispatched")),
                "packages_delivered": _int_or_zero(row.get("packages_delivered")),
                "planned_window": _optional_time_window(
                    row.get("planned_start"),
                    row.get("planned_finish"),
                ),
                "actual_window": _optional_time_window(
                    row.get("actual_start"),
                    row.get("actual_finish"),
                ),
                "actual_minutes": _int_or_zero(row.get("actual_minutes")),
                "returns": _int_or_zero(row.get("returns")),
                "return_reasons": str(row.get("return_reasons") or ""),
                "upd_candidate": _truthy_bool(row.get("upd_candidate")),
            }
        )
    return rows


def _artifact_eod_form_fields(
    *,
    route_rows: list[dict[str, Any]],
    manual_closeout_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    driver_options = _unique_driver_names(tuple(route_rows))
    manual_closeout = manual_closeout_rows[0] if manual_closeout_rows else {}
    last_clockout = str(manual_closeout.get("last_driver_clockout") or "").strip()
    if not last_clockout:
        last_clockout = _artifact_last_clockout(route_rows)
    return [
        {
            "key": "sick_calls",
            "label": "Sick calls",
            "input": "multi_select",
            "options": driver_options,
            "value": _split_workbook_multivalue(manual_closeout.get("sick_calls")),
        },
        {
            "key": "unavailable_drivers",
            "label": "Not available",
            "input": "multi_select",
            "options": driver_options,
            "value": _split_workbook_multivalue(manual_closeout.get("unavailable_drivers")),
        },
        {
            "key": "working_devices",
            "label": "Working devices / rabbits",
            "input": "text",
            "value": str(manual_closeout.get("working_devices") or ""),
        },
        {
            "key": "rescues",
            "label": "Rescues",
            "input": "repeater",
            "value": _split_workbook_multivalue(manual_closeout.get("rescues")),
        },
        {
            "key": "incidents",
            "label": "Incidents",
            "input": "repeater",
            "value": _split_workbook_multivalue(manual_closeout.get("incidents")),
        },
        {
            "key": "last_driver_clockout",
            "label": "Last driver clock-out",
            "input": "time",
            "value": last_clockout,
        },
        {
            "key": "dispatcher_comment",
            "label": "Dispatcher comment",
            "input": "textarea",
            "value": str(manual_closeout.get("dispatcher_comment") or ""),
        },
        {
            "key": "manager_note",
            "label": "Manager note",
            "input": "textarea",
            "value": str(manual_closeout.get("manager_note") or ""),
        },
    ]


def _artifact_eod_checklist_items(upd_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in upd_rows:
        item_id = str(row.get("row_id") or "").strip()
        if not item_id:
            continue
        route_id = str(row.get("route_id") or "").strip()
        actual_minutes = _int_or_zero(row.get("actual_minutes"))
        items.append(
            {
                "item_id": item_id,
                "title": f"{str(row.get('driver_name') or '').strip()} · {route_id}".strip(" ·"),
                "detail": str(row.get("reason") or "Needs review"),
                "selected": _truthy_bool(row.get("selected")),
                "note": str(row.get("manager_note") or ""),
                "tags": [f"{actual_minutes} minutes"] if actual_minutes > 0 else [],
            }
        )
    return items


def _artifact_eod_validation_warnings(
    quality_warning_rows: list[dict[str, Any]],
) -> list[str]:
    warnings = [
        "This workpage is derived from an immutable reporting workbook artifact; the workbook remains authoritative truth.",
        "Submit creates a new superseding workbook artifact version; no in-place workbook mutation occurs.",
    ]
    if quality_warning_rows:
        warnings.append(
            "Workbook quality warnings are surfaced from the artifact directly; formulas are not recomputed in the workpage projection."
        )
    return warnings


def _eod_row_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _require_text(row.get("service_date")),
        _require_text(row.get("route_id")),
        _require_text(row.get("driver_name")),
    )


def _unique_driver_names(route_rows: tuple[dict[str, Any], ...]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in route_rows:
        name = _require_text(row.get("driver_name"))
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _time_window(start: Any, finish: Any) -> str:
    return f"{_require_text(start)} - {_require_text(finish)}"


def _optional_time_window(start: Any, finish: Any) -> str:
    start_text = str(start or "").strip()
    finish_text = str(finish or "").strip()
    if not start_text and not finish_text:
        return ""
    return f"{start_text} - {finish_text}".strip()


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _format_average_minutes(minutes: list[int]) -> str:
    if not minutes:
        return "0:00:00"
    average_minutes = round(sum(minutes) / len(minutes))
    hours, minute_remainder = divmod(average_minutes, 60)
    return f"{hours}:{minute_remainder:02d}:00"


def _selected_day_preview_row(bundle: WeeklyScheduleControlBundle) -> dict[str, Any]:
    selected_service_date = _selected_day_service_date(bundle)
    demand = bundle.daily_demand_by_service_date.get(selected_service_date)
    if demand is None:
        raise ValueError(
            "selected-day preview date is missing from schedule bundle"
        )
    return {
        "service_date": selected_service_date,
        "routes_required": demand.planned_route_count,
        "drivers_available": demand.planned_route_count + demand.on_call_target,
        "projected_on_call_needed": demand.on_call_target,
        "open_questions": _SELECTED_DAY_OPEN_QUESTION,
    }


def _driver_roster_rows(bundle: WeeklyScheduleControlBundle) -> list[dict[str, Any]]:
    capabilities_by_name = {
        capability.driver_name: capability
        for capability in bundle.drivers
        if capability.driver_name
    }
    selected_names = [name for name in _ROSTER_TARGET_NAMES if name in capabilities_by_name]
    remaining_names = sorted(
        name for name in capabilities_by_name if name not in selected_names
    )
    for name in remaining_names:
        if len(selected_names) >= len(_ROSTER_TARGET_NAMES):
            break
        selected_names.append(name)

    rows: list[dict[str, Any]] = []
    for name in selected_names:
        capability = capabilities_by_name[name]
        availability = bundle.availability_by_driver.get(capability.driver_id)
        rows.append(
            {
                "driver_name": name,
                "employment_type": (
                    capability.employment_type
                    or (availability.employment_type if availability is not None else "")
                ),
                "preferred_route_slot_classes": ", ".join(
                    capability.preferred_route_slot_classes
                ),
                "target_shifts_per_week": (
                    availability.target_shifts_per_week if availability is not None else 0
                ),
                "on_call_eligible": (
                    bool(availability.on_call_eligible)
                    if availability is not None
                    else False
                ),
                "previous_week_minutes": bundle.actual_minutes_by_driver.get(
                    capability.driver_id,
                    0,
                ),
                "availability_summary": _availability_summary(availability),
            }
        )
    return rows


def _full_driver_roster_rows(bundle: WeeklyScheduleControlBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for capability in sorted(
        bundle.drivers,
        key=lambda item: (
            str(item.driver_name or item.driver_id).lower(),
            item.driver_id,
        ),
    ):
        availability = bundle.availability_by_driver.get(capability.driver_id)
        rows.append(
            {
                "driver_name": capability.driver_name or capability.driver_id,
                "employment_type": (
                    capability.employment_type
                    or (availability.employment_type if availability is not None else "")
                ),
                "preferred_route_slot_classes": ", ".join(
                    capability.preferred_route_slot_classes
                ),
                "target_shifts_per_week": (
                    availability.target_shifts_per_week if availability is not None else 0
                ),
                "on_call_eligible": (
                    bool(availability.on_call_eligible)
                    if availability is not None
                    else False
                ),
                "previous_week_minutes": bundle.actual_minutes_by_driver.get(
                    capability.driver_id,
                    0,
                ),
                "availability_summary": _availability_summary(availability),
            }
        )
    return rows


def _availability_summary(availability: Any) -> str:
    if availability is None or not availability.daily_states:
        return "no planning-week availability recorded"
    counts = Counter(str(item.state or "").upper() for item in availability.daily_states)
    labels = (
        ("PREFERRED", "preferred"),
        ("AVAILABLE", "available"),
        ("ON_CALL_ONLY", "on-call-only"),
        ("AVOID_IF_POSSIBLE", "avoid-if-possible"),
        ("CANNOT", "cannot"),
    )
    parts = [
        f"{label} {count} {'day' if count == 1 else 'days'}"
        for key, label in labels
        for count in [counts.get(key, 0)]
        if count > 0
    ]
    return "; ".join(parts) if parts else "no planning-week availability recorded"


def _selected_day_service_date(bundle: WeeklyScheduleControlBundle) -> str:
    if _PREVIEW_SERVICE_DATE in bundle.daily_demand_by_service_date:
        return _PREVIEW_SERVICE_DATE
    ordered_dates = sorted(bundle.daily_demand_by_service_date.keys())
    if not ordered_dates:
        raise ValueError("schedule bundle does not contain any service dates")
    return ordered_dates[min(2, len(ordered_dates) - 1)]


def _schedule_daily_row_counts(
    *,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for row in assignment_rows:
        service_date = str(row.get("service_date") or "").strip()
        if not service_date:
            continue
        counts.setdefault(
            service_date,
            {"assignment_count": 0, "reserve_count": 0},
        )["assignment_count"] += 1
    for row in reserve_rows:
        service_date = str(row.get("service_date") or "").strip()
        if not service_date:
            continue
        counts.setdefault(
            service_date,
            {"assignment_count": 0, "reserve_count": 0},
        )["reserve_count"] += 1
    return counts


def _multi_select_options(bundle: WeeklyScheduleControlBundle) -> list[str]:
    available_names = _available_driver_names(bundle)
    return [name for name in _ROSTER_TARGET_NAMES if name in available_names]


def _available_driver_names(bundle: WeeklyScheduleControlBundle) -> set[str]:
    return {
        capability.driver_name
        for capability in bundle.drivers
        if capability.driver_name
    }


def _first_non_empty(values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _require_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("expected non-empty text value")
    return text


def _require_text_or_default(value: Any, *, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _require_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("expected integer value")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("expected integer value") from exc


def _require_int_or_default(value: Any, *, default: int) -> int:
    text = str(value or "").strip()
    if not text:
        return int(default)
    return _require_int(value)


def _truthy_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def _int_or_zero(value: Any) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    return _require_int(value)


def _int_or_none(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    return _require_int(value)


def _weekday_label(service_date: str) -> str:
    parts = service_date.split("-")
    if len(parts) != 3:
        return service_date
    try:
        year, month, day = (int(part) for part in parts)
    except ValueError:
        return service_date
    return date(year, month, day).strftime("%a")


def _weekly_service_dates_from_start(scope_start: str) -> list[dict[str, str]]:
    parts = scope_start.split("-")
    if len(parts) != 3:
        return []
    try:
        start_year, start_month, start_day = (int(part) for part in parts)
        start_date = date(start_year, start_month, start_day)
    except ValueError:
        return []
    return [
        {
            "service_date": service_day.isoformat(),
            "label": service_day.isoformat(),
            "weekday_label": service_day.strftime("%a"),
        }
        for service_day in (start_date.fromordinal(start_date.toordinal() + offset) for offset in range(7))
    ]


def _split_workbook_multivalue(value: Any) -> list[str]:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    return [part.strip() for part in text.split("\n") if part.strip()]


def _artifact_last_clockout(route_rows: list[dict[str, Any]]) -> str:
    finishes = [
        str(row.get("actual_finish") or "").strip()
        for row in route_rows
        if str(row.get("actual_finish") or "").strip()
    ]
    return max(finishes, default="")
