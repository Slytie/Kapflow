from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
from typing import Any, Iterable, Mapping

from .route_slot_requirements import RouteSlotRequirement, parse_route_slot_requirements


@dataclass(frozen=True)
class DriverCapability:
    driver_id: str
    skills: tuple[str, ...]
    vehicle_certifications: tuple[str, ...]
    eligible_route_slot_classes: tuple[str, ...]
    approved_restrictions: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class DriverAvailability:
    driver_id: str
    target_shifts_per_week: int
    on_call_eligible: bool
    approved_unavailable_dates: tuple[str, ...]
    regular_pattern: tuple[str, ...]


@dataclass(frozen=True)
class WeeklyScheduleControlBundle:
    bundle_id: str
    workflow_run_id: str
    planning_week_id: str
    trigger_type: str
    scope_start: str
    scope_end_exclusive: str
    route_slots: tuple[RouteSlotRequirement, ...]
    drivers: tuple[DriverCapability, ...]
    availability_by_driver: dict[str, DriverAvailability]
    actual_minutes_by_driver: dict[str, int]
    referenced_artifacts: tuple[dict[str, str], ...]
    planner_notes: tuple[str, ...]
    external_evidence_refs: tuple[str, ...]


def build_weekly_schedule_control_bundle(
    *,
    workflow_run: Mapping[str, Any],
    route_slot_requirements_artifact: Mapping[str, Any],
    driver_capabilities_artifact: Mapping[str, Any],
    approved_availability_artifact: Mapping[str, Any] | None = None,
    actual_hours_artifact: Mapping[str, Any] | None = None,
    route_horizon_artifact: Mapping[str, Any] | None = None,
    trigger_type: str = "weekly_build",
) -> WeeklyScheduleControlBundle:
    planning_week_id = str(workflow_run.get("partition_key") or "")
    workflow_run_id = str(workflow_run.get("workflow_run_id") or "")
    if not workflow_run_id:
        raise ValueError("workflow_run_id is required for weekly schedule-control bundle")
    if not planning_week_id.startswith("PW-"):
        raise ValueError(
            "weekly schedule-control bundle requires PlanningWeekID partition key "
            f"(got {planning_week_id!r})"
        )

    route_slots = _parse_route_slots(route_slot_requirements_artifact)
    if not route_slots:
        raise ValueError("route_slot_requirements artifact does not contain any route slots")

    drivers = _parse_driver_capabilities(driver_capabilities_artifact)
    if not drivers:
        raise ValueError("driver_capabilities artifact does not contain any drivers")

    availability_by_driver = _parse_approved_availability(approved_availability_artifact)
    actual_minutes_by_driver = _parse_actual_hours(actual_hours_artifact)

    scope_start_date, scope_end_exclusive_date = _planning_week_bounds(planning_week_id)
    referenced_artifacts = _referenced_artifacts(
        route_horizon_artifact=route_horizon_artifact,
        approved_availability_artifact=approved_availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
        route_slot_requirements_artifact=route_slot_requirements_artifact,
        driver_capabilities_artifact=driver_capabilities_artifact,
    )

    bundle_id = _stable_bundle_id(
        planning_week_id=planning_week_id,
        route_slot_requirements_artifact_version_id=str(
            route_slot_requirements_artifact.get("artifact_version_id") or ""
        ),
        driver_capabilities_artifact_version_id=str(
            driver_capabilities_artifact.get("artifact_version_id") or ""
        ),
        approved_availability_artifact_version_id=(
            str(approved_availability_artifact.get("artifact_version_id") or "")
            if approved_availability_artifact is not None
            else ""
        ),
        actual_hours_artifact_version_id=(
            str(actual_hours_artifact.get("artifact_version_id") or "")
            if actual_hours_artifact is not None
            else ""
        ),
    )

    planner_notes, external_evidence_refs = _bundle_notes(
        route_horizon_artifact=route_horizon_artifact,
        approved_availability_artifact=approved_availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
    )

    return WeeklyScheduleControlBundle(
        bundle_id=bundle_id,
        workflow_run_id=workflow_run_id,
        planning_week_id=planning_week_id,
        trigger_type=str(trigger_type),
        scope_start=scope_start_date.isoformat(),
        scope_end_exclusive=scope_end_exclusive_date.isoformat(),
        route_slots=route_slots,
        drivers=drivers,
        availability_by_driver=availability_by_driver,
        actual_minutes_by_driver=actual_minutes_by_driver,
        referenced_artifacts=referenced_artifacts,
        planner_notes=planner_notes,
        external_evidence_refs=external_evidence_refs,
    )


def _parse_route_slots(artifact: Mapping[str, Any]) -> tuple[RouteSlotRequirement, ...]:
    metadata = _metadata_json(artifact)
    columns, rows = _extract_table(columns_key="columns", rows_key="rows", metadata=metadata)
    return parse_route_slot_requirements(columns=columns, rows=rows)


def _parse_driver_capabilities(artifact: Mapping[str, Any]) -> tuple[DriverCapability, ...]:
    metadata = _metadata_json(artifact)
    columns, rows = _extract_table(columns_key="columns", rows_key="rows", metadata=metadata)
    parsed: list[DriverCapability] = []
    for row in _rows_to_dicts(columns=columns, rows=rows):
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            continue
        parsed.append(
            DriverCapability(
                driver_id=driver_id,
                skills=_csv_tokens(row.get("skills")),
                vehicle_certifications=_csv_tokens(row.get("vehicle_certifications")),
                eligible_route_slot_classes=_csv_tokens(row.get("eligible_route_slot_classes")),
                approved_restrictions=_csv_tokens(row.get("approved_restrictions")),
                notes=str(row.get("notes") or "").strip(),
            )
        )

    return tuple(sorted(parsed, key=lambda item: item.driver_id))


def _parse_approved_availability(
    artifact: Mapping[str, Any] | None,
) -> dict[str, DriverAvailability]:
    if artifact is None:
        return {}
    metadata = _metadata_json(artifact)
    columns, rows = _extract_table(columns_key="columns", rows_key="rows", metadata=metadata)
    parsed: dict[str, DriverAvailability] = {}
    for row in _rows_to_dicts(columns=columns, rows=rows):
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            continue
        target_shifts_per_week = _coerce_int(row.get("target_shifts_per_week"), default=4)
        on_call_eligible = str(row.get("on_call_eligible") or "").strip().lower() in {
            "true",
            "yes",
            "1",
        }
        parsed[driver_id] = DriverAvailability(
            driver_id=driver_id,
            target_shifts_per_week=max(target_shifts_per_week, 1),
            on_call_eligible=on_call_eligible,
            approved_unavailable_dates=_csv_tokens(row.get("approved_unavailable_dates")),
            regular_pattern=_csv_tokens(row.get("regular_pattern")),
        )
    return parsed


def _parse_actual_hours(
    artifact: Mapping[str, Any] | None,
) -> dict[str, int]:
    if artifact is None:
        return {}
    metadata = _metadata_json(artifact)
    columns, rows = _extract_table(columns_key="columns", rows_key="rows", metadata=metadata)
    totals: dict[str, int] = {}
    for row in _rows_to_dicts(columns=columns, rows=rows):
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            continue
        actual_minutes = _coerce_int(row.get("actual_minutes"), default=0)
        totals[driver_id] = totals.get(driver_id, 0) + max(actual_minutes, 0)
    return totals


def _bundle_notes(
    *,
    route_horizon_artifact: Mapping[str, Any] | None,
    approved_availability_artifact: Mapping[str, Any] | None,
    actual_hours_artifact: Mapping[str, Any] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    evidence_refs: list[str] = []
    notes: list[str] = []
    for artifact in (
        route_horizon_artifact,
        approved_availability_artifact,
        actual_hours_artifact,
    ):
        if artifact is None:
            continue
        metadata = _metadata_json(artifact)
        external_refs = metadata.get("external_evidence_refs")
        if isinstance(external_refs, list):
            evidence_refs.extend(str(item) for item in external_refs if str(item).strip())
        planner_notes = metadata.get("planner_notes")
        if isinstance(planner_notes, list):
            notes.extend(str(item) for item in planner_notes if str(item).strip())

    if not notes:
        notes = [
            "Deterministic Stage04 build generated from canonical route-slot and driver-capability artifacts."
        ]
    return tuple(dict.fromkeys(notes)), tuple(dict.fromkeys(evidence_refs))


def _referenced_artifacts(
    *,
    route_horizon_artifact: Mapping[str, Any] | None,
    approved_availability_artifact: Mapping[str, Any] | None,
    actual_hours_artifact: Mapping[str, Any] | None,
    route_slot_requirements_artifact: Mapping[str, Any],
    driver_capabilities_artifact: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    ordered = [
        route_horizon_artifact,
        approved_availability_artifact,
        actual_hours_artifact,
        route_slot_requirements_artifact,
        driver_capabilities_artifact,
    ]
    refs: list[dict[str, str]] = []
    for artifact in ordered:
        if artifact is None:
            continue
        artifact_version_id = str(artifact.get("artifact_version_id") or "").strip()
        if not artifact_version_id:
            continue
        dataset_key = str(
            artifact.get("dataset_key")
            or artifact.get("artifact_kind")
            or ""
        ).strip()
        if not dataset_key:
            continue
        refs.append(
            {
                "dataset_key": dataset_key,
                "artifact_version_id": artifact_version_id,
            }
        )
    return tuple(refs)


def _stable_bundle_id(
    *,
    planning_week_id: str,
    route_slot_requirements_artifact_version_id: str,
    driver_capabilities_artifact_version_id: str,
    approved_availability_artifact_version_id: str,
    actual_hours_artifact_version_id: str,
) -> str:
    digest = hashlib.sha256(
        "|".join(
            [
                "weekly_stage04_bundle",
                planning_week_id,
                route_slot_requirements_artifact_version_id,
                driver_capabilities_artifact_version_id,
                approved_availability_artifact_version_id,
                actual_hours_artifact_version_id,
            ]
        ).encode("utf-8")
    ).hexdigest()[:10]
    return f"bundle-{planning_week_id.lower()}-stage04-{digest}"


def _planning_week_bounds(planning_week_id: str) -> tuple[date, date]:
    week_token = planning_week_id.removeprefix("PW-")
    year_text, week_text = week_token.split("-W", maxsplit=1)
    start = date.fromisocalendar(int(year_text), int(week_text), 1)
    end_exclusive = start + timedelta(days=7)
    return start, end_exclusive


def _metadata_json(artifact: Mapping[str, Any]) -> dict[str, Any]:
    metadata = artifact.get("metadata_json")
    if isinstance(metadata, dict):
        return metadata
    raise ValueError(
        "artifact metadata_json must be a JSON object "
        f"(artifact_version_id={artifact.get('artifact_version_id')})"
    )


def _extract_table(
    *,
    columns_key: str,
    rows_key: str,
    metadata: Mapping[str, Any],
) -> tuple[list[str], list[Any]]:
    columns = metadata.get(columns_key)
    rows = metadata.get(rows_key)

    if isinstance(columns, list) and isinstance(rows, list):
        return [str(item) for item in columns], list(rows)

    nested_bundle = metadata.get("bundle")
    if isinstance(nested_bundle, Mapping):
        columns = nested_bundle.get(columns_key)
        rows = nested_bundle.get(rows_key)
        if isinstance(columns, list) and isinstance(rows, list):
            return [str(item) for item in columns], list(rows)

    return [], []


def _rows_to_dicts(*, columns: list[str], rows: Iterable[Any]) -> list[dict[str, Any]]:
    normalized_columns = [str(column).strip() for column in columns]
    result: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            item = {str(key).strip(): value for key, value in row.items()}
        elif isinstance(row, (list, tuple)):
            item = {
                normalized_columns[index]: value
                for index, value in enumerate(row)
                if index < len(normalized_columns)
            }
        else:
            continue
        result.append(item)
    return result


def _csv_tokens(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        tokens = [str(item).strip() for item in value if str(item).strip()]
    else:
        tokens = [part.strip() for part in str(value).split(",") if part.strip()]
    return tuple(tokens)


def _coerce_int(value: Any, *, default: int) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)
