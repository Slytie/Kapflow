from __future__ import annotations

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
    return {
        "schema_version": "1.0",
        "kind": "driver_shift_preferences",
        "planning_week_id": bundle.planning_week_id,
        "weekdays": list(DRIVER_PREFERENCE_WEEKDAY_KEYS),
        "drivers": [
            {
                "driver_id": driver.driver_id,
                "driver_name": driver.driver_name or driver.driver_id,
                "employment_type": driver.employment_type,
                "on_call_eligible": bool(
                    getattr(availability_by_driver.get(driver.driver_id), "on_call_eligible", False)
                ),
                "preferences_by_weekday": {
                    weekday: None for weekday in DRIVER_PREFERENCE_WEEKDAY_KEYS
                },
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
    drivers = _normalize_driver_rows(payload.get("drivers"), weekdays=weekdays)
    return {
        "weekdays": weekdays,
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


def _weekday_key(service_date: str) -> str:
    year, month, day = (int(part) for part in service_date.split("-"))
    import datetime as _datetime

    weekday_index = _datetime.date(year, month, day).weekday()
    return DRIVER_PREFERENCE_WEEKDAY_KEYS[(weekday_index + 1) % 7]
