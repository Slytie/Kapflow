from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from typing import Any, Mapping, Sequence

from .bundle_builder import WeeklyScheduleControlBundle


DRIVER_PREFERENCES_DATASET_KEY = "planning.driver_shift_preferences.workbook"
DRIVER_PREFERENCE_WEEKDAY_KEYS = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")
_ALLOWED_PREFERENCE_VALUES = frozenset(
    {
        "definitely_can_not_work",
        "open_to_work",
        "prefer_not_to_work",
        None,
    }
)


def build_initial_driver_preferences_workbook(
    *,
    bundle: WeeklyScheduleControlBundle,
) -> dict[str, Any]:
    availability_by_driver = bundle.availability_by_driver
    service_dates = _service_dates_for_bundle(bundle)
    return {
        "schema_version": "1.0",
        "kind": "driver_shift_preferences",
        "planning_week_id": bundle.planning_week_id,
        "weekdays": list(DRIVER_PREFERENCE_WEEKDAY_KEYS),
        "service_dates": service_dates,
        "drivers": [
            {
                "driver_id": driver.driver_id,
                "driver_name": driver.driver_name or driver.driver_id,
                "employment_type": driver.employment_type,
                "on_call_eligible": bool(
                    getattr(availability_by_driver.get(driver.driver_id), "on_call_eligible", False)
                ),
                "preferences_by_weekday": _seed_driver_preferences_by_weekday(
                    bundle=bundle,
                    driver_id=driver.driver_id,
                    service_dates=service_dates,
                ),
            }
            for driver in sorted(
                bundle.drivers,
                key=lambda item: (str(item.driver_name or item.driver_id).lower(), item.driver_id),
            )
        ],
    }


def project_driver_preferences_workbook(workbook_bytes: bytes) -> dict[str, Any]:
    payload = _load_payload(workbook_bytes)
    weekdays = _require_weekdays(payload.get("weekdays"))
    service_dates = _normalize_service_dates(payload.get("service_dates"))
    drivers = _normalize_driver_rows(payload.get("drivers"), weekdays=weekdays)
    return {
        "weekdays": weekdays,
        "service_dates": service_dates,
        "drivers": drivers,
    }


def materialize_driver_preferences_workbook(
    base_workbook_bytes: bytes,
    *,
    driver_rows: Any,
) -> bytes:
    base_payload = _load_payload(base_workbook_bytes)
    weekdays = _require_weekdays(base_payload.get("weekdays"))
    base_drivers = _normalize_driver_rows(base_payload.get("drivers"), weekdays=weekdays)
    submitted_rows = _normalize_submitted_driver_rows(driver_rows, weekdays=weekdays)
    next_drivers = _validated_merged_driver_rows(
        base_drivers=base_drivers,
        submitted_rows=submitted_rows,
        weekdays=weekdays,
    )

    next_payload = dict(base_payload)
    next_payload["weekdays"] = list(weekdays)
    next_payload["drivers"] = next_drivers
    return json.dumps(next_payload, indent=2, sort_keys=True).encode("utf-8")


def driver_preferences_workbook_bytes_from_metadata_json(metadata_json: object) -> bytes:
    if not isinstance(metadata_json, Mapping):
        raise ValueError("driver preferences workbook metadata must be an object")
    try:
        return json.dumps(dict(metadata_json), indent=2, sort_keys=True).encode("utf-8")
    except TypeError as exc:
        raise ValueError("driver preferences workbook metadata must be JSON-serializable") from exc


def driver_preference_value_for_service_date(
    *,
    projection: Mapping[str, Any] | None,
    driver_id: str,
    service_date: str,
) -> str:
    if projection is None:
        return "unset"
    by_driver = projection.get("drivers_by_id")
    if not isinstance(by_driver, Mapping):
        by_driver = {
            str(row.get("driver_id") or ""): row
            for row in _projection_driver_rows(projection)
        }
    row = by_driver.get(driver_id)
    if not isinstance(row, Mapping):
        return "unset"
    preferences = row.get("preferences_by_weekday")
    if not isinstance(preferences, Mapping):
        return "unset"
    value = preferences.get(_weekday_key(service_date))
    text = str(value).strip() if value is not None else ""
    return text or "unset"


def annotate_driver_preferences_projection(projection: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if projection is None:
        return None
    drivers = _projection_driver_rows(projection)
    return {
        "weekdays": _require_weekdays(projection.get("weekdays")),
        "service_dates": _normalize_service_dates(projection.get("service_dates")),
        "drivers": drivers,
        "drivers_by_id": {
            str(row.get("driver_id") or ""): row
            for row in drivers
            if str(row.get("driver_id") or "").strip()
        },
    }


def _projection_driver_rows(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = projection.get("drivers")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return []
    return [
        dict(row)
        for row in rows
        if isinstance(row, Mapping)
    ]


def _load_payload(workbook_bytes: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(workbook_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("driver preferences workbook must decode as UTF-8 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("driver preferences workbook payload must decode to an object")
    return dict(decoded)


def _require_weekdays(raw_weekdays: Any) -> list[str]:
    if not isinstance(raw_weekdays, Sequence) or isinstance(raw_weekdays, (str, bytes, bytearray)):
        raise ValueError("driver preferences workbook weekdays must be a list")
    weekdays = [str(value or "").strip().lower() for value in raw_weekdays]
    if weekdays != list(DRIVER_PREFERENCE_WEEKDAY_KEYS):
        raise ValueError("driver preferences workbook weekdays must be sun..sat in canonical order")
    return weekdays


def _normalize_service_dates(raw_service_dates: Any) -> list[dict[str, str]]:
    if raw_service_dates is None:
        return []
    if not isinstance(raw_service_dates, Sequence) or isinstance(
        raw_service_dates,
        (str, bytes, bytearray),
    ):
        raise ValueError("driver preferences workbook service_dates must be a list")
    normalized: list[dict[str, str]] = []
    seen_service_dates: set[str] = set()
    for index, entry in enumerate(raw_service_dates):
        if not isinstance(entry, Mapping):
            raise ValueError(f"driver preferences workbook service_dates[{index}] must be an object")
        service_date = str(entry.get("service_date") or "").strip()
        if not service_date:
            raise ValueError(f"driver preferences workbook service_dates[{index}].service_date is required")
        if service_date in seen_service_dates:
            raise ValueError(
                f"driver preferences workbook service_dates contains duplicate service_date: {service_date}"
            )
        seen_service_dates.add(service_date)
        normalized.append(
            {
                "service_date": service_date,
                "label": str(entry.get("label") or service_date).strip() or service_date,
                "weekday_label": (
                    str(entry.get("weekday_label") or _weekday_label(service_date)).strip()
                    or _weekday_label(service_date)
                ),
            }
        )
    if normalized:
        weekday_keys = [_weekday_key(entry["service_date"]) for entry in normalized]
        if weekday_keys != list(DRIVER_PREFERENCE_WEEKDAY_KEYS):
            raise ValueError(
                "driver preferences workbook service_dates must align with sun..sat in canonical order"
            )
    return normalized


def _normalize_driver_rows(raw_rows: Any, *, weekdays: Sequence[str]) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes, bytearray)):
        raise ValueError("driver preferences workbook drivers must be a list")
    rows: list[dict[str, Any]] = []
    seen_driver_ids: set[str] = set()
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"driver preferences workbook drivers[{index}] must be an object")
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            raise ValueError(f"driver preferences workbook drivers[{index}].driver_id is required")
        if driver_id in seen_driver_ids:
            raise ValueError(f"driver preferences workbook contains duplicate driver_id: {driver_id}")
        seen_driver_ids.add(driver_id)
        preferences = _normalize_preferences_map(
            row.get("preferences_by_weekday"),
            weekdays=weekdays,
            label=f"drivers[{index}].preferences_by_weekday",
        )
        rows.append(
            {
                "driver_id": driver_id,
                "driver_name": str(row.get("driver_name") or driver_id).strip(),
                "employment_type": str(row.get("employment_type") or "").strip(),
                "on_call_eligible": bool(row.get("on_call_eligible")),
                "preferences_by_weekday": preferences,
            }
        )
    return rows


def _normalize_submitted_driver_rows(raw_rows: Any, *, weekdays: Sequence[str]) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes, bytearray)):
        raise ValueError("driver_rows must be a list")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"driver_rows[{index}] must be an object")
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            raise ValueError(f"driver_rows[{index}].driver_id is required")
        rows.append(
            {
                "driver_id": driver_id,
                "preferences_by_weekday": _normalize_preferences_map(
                    row.get("preferences_by_weekday"),
                    weekdays=weekdays,
                    label=f"driver_rows[{index}].preferences_by_weekday",
                ),
            }
        )
    return rows


def _validated_merged_driver_rows(
    *,
    base_drivers: list[dict[str, Any]],
    submitted_rows: list[dict[str, Any]],
    weekdays: Sequence[str],
) -> list[dict[str, Any]]:
    if len(base_drivers) != len(submitted_rows):
        raise ValueError("driver_rows must keep the same row count as the base artifact")
    merged: list[dict[str, Any]] = []
    for index, (base_row, submitted_row) in enumerate(zip(base_drivers, submitted_rows, strict=True)):
        base_driver_id = str(base_row.get("driver_id") or "").strip()
        submitted_driver_id = str(submitted_row.get("driver_id") or "").strip()
        if base_driver_id != submitted_driver_id:
            raise ValueError(
                f"driver_rows[{index}] driver_id changed from {base_driver_id} to {submitted_driver_id}"
            )
        merged.append(
            {
                **base_row,
                "preferences_by_weekday": _normalize_preferences_map(
                    submitted_row.get("preferences_by_weekday"),
                    weekdays=weekdays,
                    label=f"driver_rows[{index}].preferences_by_weekday",
                ),
            }
        )
    return merged


def _normalize_preferences_map(
    raw_preferences: Any,
    *,
    weekdays: Sequence[str],
    label: str,
) -> dict[str, str | None]:
    if not isinstance(raw_preferences, Mapping):
        raise ValueError(f"{label} must be an object")
    normalized: dict[str, str | None] = {}
    extra_keys = {str(key).strip().lower() for key in raw_preferences.keys()} - set(weekdays)
    if extra_keys:
        raise ValueError(f"{label} contains unsupported weekday keys: {sorted(extra_keys)}")
    for weekday in weekdays:
        value = raw_preferences.get(weekday)
        text = str(value).strip() if value is not None else ""
        normalized_value = text or None
        if normalized_value not in _ALLOWED_PREFERENCE_VALUES:
            raise ValueError(
                f"{label}.{weekday} must be one of definitely_can_not_work, open_to_work, prefer_not_to_work, or null"
            )
        normalized[weekday] = normalized_value
    return normalized


def _service_dates_for_bundle(
    bundle: WeeklyScheduleControlBundle,
) -> list[dict[str, str]]:
    start_year, start_month, start_day = (int(part) for part in bundle.scope_start.split("-"))
    start_date = date(start_year, start_month, start_day)
    return [
        _service_date_payload(start_date + timedelta(days=index))
        for index in range(len(DRIVER_PREFERENCE_WEEKDAY_KEYS))
    ]


def _service_date_payload(service_day: date) -> dict[str, str]:
    service_date = service_day.isoformat()
    return {
        "service_date": service_date,
        "label": service_date,
        "weekday_label": service_day.strftime("%a"),
    }


def _seed_driver_preferences_by_weekday(
    *,
    bundle: WeeklyScheduleControlBundle,
    driver_id: str,
    service_dates: Sequence[Mapping[str, str]],
) -> dict[str, str]:
    seed_scope = f"{bundle.planning_week_id}:{bundle.workflow_run_id}:{driver_id}"
    open_target = 4 + (_stable_int(f"{seed_scope}:open-target") % 3)
    unavailable_like_dates = _unavailable_like_service_dates(
        bundle=bundle,
        driver_id=driver_id,
        service_dates=service_dates,
    )
    ranked_dates = sorted(
        (str(entry.get("service_date") or "").strip() for entry in service_dates),
        key=lambda service_date: (
            1 if service_date in unavailable_like_dates else 0,
            _stable_int(f"{seed_scope}:rank:{service_date}"),
        ),
    )
    open_dates = set(ranked_dates[:open_target])
    closed_dates = [service_date for service_date in ranked_dates if service_date not in open_dates]
    hard_closed_dates = [service_date for service_date in closed_dates if service_date in unavailable_like_dates]
    soft_closed_dates = [service_date for service_date in closed_dates if service_date not in unavailable_like_dates]
    extra_hard_closed_dates: set[str] = set()
    if not hard_closed_dates and len(closed_dates) >= 2 and soft_closed_dates:
        extra_hard_closed_dates.add(
            min(
                soft_closed_dates,
                key=lambda service_date: _stable_int(f"{seed_scope}:extra-hard:{service_date}"),
            )
        )

    preferences_by_weekday: dict[str, str] = {}
    for entry in service_dates:
        service_date = str(entry.get("service_date") or "").strip()
        weekday = _weekday_key(service_date)
        if service_date in open_dates:
            preferences_by_weekday[weekday] = "open_to_work"
        elif service_date in unavailable_like_dates or service_date in extra_hard_closed_dates:
            preferences_by_weekday[weekday] = "definitely_can_not_work"
        else:
            preferences_by_weekday[weekday] = "prefer_not_to_work"
    return preferences_by_weekday


def _unavailable_like_service_dates(
    *,
    bundle: WeeklyScheduleControlBundle,
    driver_id: str,
    service_dates: Sequence[Mapping[str, str]],
) -> set[str]:
    availability = bundle.availability_by_driver.get(driver_id)
    if availability is None:
        return set()
    blocked_dates = {
        service_date
        for service_date in availability.approved_unavailable_dates
        if service_date
    }
    if availability.emergency_only:
        blocked_dates.update(
            str(entry.get("service_date") or "").strip()
            for entry in service_dates
            if str(entry.get("service_date") or "").strip()
        )
    for day_state in availability.daily_states:
        normalized_state = str(day_state.normalized_state or day_state.state or "").strip().lower()
        if normalized_state in {"approved_unavailable", "pattern_off", "emergency_only"}:
            blocked_dates.add(str(day_state.service_date or "").strip())
    return {service_date for service_date in blocked_dates if service_date}


def _stable_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16], 16)


def _weekday_key(service_date: str) -> str:
    year, month, day = (int(part) for part in service_date.split("-"))
    weekday_index = date(year, month, day).weekday()
    return DRIVER_PREFERENCE_WEEKDAY_KEYS[(weekday_index + 1) % 7]


def _weekday_label(service_date: str) -> str:
    year, month, day = (int(part) for part in service_date.split("-"))
    return date(year, month, day).strftime("%a")
