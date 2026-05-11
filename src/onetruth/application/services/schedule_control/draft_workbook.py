from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


SCHEDULE_DRAFT_DATASET_KEY = "planning.draft_weekly_schedule.workbook"
SCHEDULE_WORKFLOW_ID = "weekly_schedule_planning.v1"
EDITABLE_SCHEDULE_DRAFT_FIELDS = frozenset({"assigned_driver_id", "assignment_status"})


def project_stage04_draft_weekly_schedule_workbook(workbook_bytes: bytes) -> dict[str, Any]:
    payload = _load_payload(workbook_bytes)
    columns = _require_columns(payload.get("columns"))
    return {
        "columns": columns,
        "rows": _decode_assignment_rows(payload.get("rows"), columns),
        "reserve_rows": _normalize_mapping_rows(payload.get("reserve_rows"), label="reserve_rows"),
        "iteration_deltas": _normalize_mapping_rows(
            payload.get("iteration_deltas"),
            label="iteration_deltas",
        ),
    }


def materialize_stage04_draft_weekly_schedule_workbook(
    base_workbook_bytes: bytes,
    *,
    rows: Any,
    reserve_rows: Any,
) -> bytes:
    base_payload = _load_payload(base_workbook_bytes)
    columns = _require_columns(base_payload.get("columns"))
    base_assignment_rows = _decode_assignment_rows(base_payload.get("rows"), columns)
    base_reserve_rows = _normalize_mapping_rows(base_payload.get("reserve_rows"), label="reserve_rows")
    submitted_assignment_rows = _normalize_submitted_rows(rows, label="rows")
    submitted_reserve_rows = _normalize_submitted_rows(reserve_rows, label="reserve_rows")

    next_assignment_rows = _validated_merged_rows(
        base_rows=base_assignment_rows,
        submitted_rows=submitted_assignment_rows,
        label="rows",
    )
    next_reserve_rows = _validated_merged_rows(
        base_rows=base_reserve_rows,
        submitted_rows=submitted_reserve_rows,
        label="reserve_rows",
    )

    next_payload = dict(base_payload)
    next_payload["columns"] = list(columns)
    next_payload["rows"] = [
        [row[column] for column in columns]
        for row in next_assignment_rows
    ]
    next_payload["reserve_rows"] = next_reserve_rows
    next_payload["iteration_deltas"] = _normalize_mapping_rows(
        base_payload.get("iteration_deltas"),
        label="iteration_deltas",
    )
    return json.dumps(next_payload, indent=2, sort_keys=True).encode("utf-8")


def append_stage04_draft_weekly_schedule_assignment_rows(
    base_workbook_bytes: bytes,
    *,
    rows: Any,
    reserve_rows: Any,
    appended_rows: Sequence[Mapping[str, Any]],
) -> bytes:
    validated_bytes = materialize_stage04_draft_weekly_schedule_workbook(
        base_workbook_bytes,
        rows=rows,
        reserve_rows=reserve_rows,
    )
    payload = _load_payload(validated_bytes)
    columns = _require_columns(payload.get("columns"))
    assignment_rows = _decode_assignment_rows(payload.get("rows"), columns)
    reserve_payload_rows = _normalize_mapping_rows(payload.get("reserve_rows"), label="reserve_rows")
    next_appended_rows = _normalize_appended_rows(
        appended_rows=appended_rows,
        base_rows=assignment_rows,
        columns=columns,
    )
    payload["rows"] = [
        [row[column] for column in columns]
        for row in [*assignment_rows, *next_appended_rows]
    ]
    payload["reserve_rows"] = reserve_payload_rows
    payload["iteration_deltas"] = _normalize_mapping_rows(
        payload.get("iteration_deltas"),
        label="iteration_deltas",
    )
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def draft_workbook_bytes_from_metadata_json(metadata_json: object) -> bytes:
    if not isinstance(metadata_json, Mapping):
        raise ValueError("schedule draft workbook metadata must be an object")
    try:
        return json.dumps(dict(metadata_json), indent=2, sort_keys=True).encode("utf-8")
    except TypeError as exc:
        raise ValueError("schedule draft workbook metadata must be JSON-serializable") from exc


def _load_payload(workbook_bytes: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(workbook_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("schedule draft workbook must decode as UTF-8 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("schedule draft workbook payload must decode to an object")
    return dict(decoded)


def _require_columns(raw_columns: Any) -> list[str]:
    if not isinstance(raw_columns, Sequence) or isinstance(raw_columns, (str, bytes, bytearray)):
        raise ValueError("schedule draft workbook columns must be a list")
    columns: list[str] = []
    for index, value in enumerate(raw_columns):
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"schedule draft workbook columns[{index}] must be a non-empty string")
        columns.append(text)
    if not columns:
        raise ValueError("schedule draft workbook columns must not be empty")
    return columns


def _decode_assignment_rows(raw_rows: Any, columns: list[str]) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes, bytearray)):
        raise ValueError("schedule draft workbook rows must be a list")
    decoded: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes, bytearray)):
            raise ValueError(f"schedule draft workbook rows[{index}] must be a list")
        if len(row) != len(columns):
            raise ValueError(
                f"schedule draft workbook rows[{index}] must contain {len(columns)} columns"
            )
        decoded.append({column: row[column_index] for column_index, column in enumerate(columns)})
    return decoded


def _normalize_mapping_rows(raw_rows: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes, bytearray)):
        raise ValueError(f"{label} must be a list")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"{label}[{index}] must be an object")
        rows.append(dict(row))
    return rows


def _normalize_submitted_rows(raw_rows: Any, *, label: str) -> list[dict[str, Any]]:
    rows = _normalize_mapping_rows(raw_rows, label=label)
    for index, row in enumerate(rows):
        for key in ("service_date", "route_slot_id"):
            value = str(row.get(key) or "").strip()
            if not value:
                raise ValueError(f"{label}[{index}].{key} is required")
            row[key] = value
        for key in EDITABLE_SCHEDULE_DRAFT_FIELDS:
            row[key] = _normalize_editable_value(row.get(key))
    return rows


def _normalize_appended_rows(
    *,
    appended_rows: Sequence[Mapping[str, Any]],
    base_rows: list[dict[str, Any]],
    columns: list[str],
) -> list[dict[str, Any]]:
    existing_identities = {_row_identity(row) for row in base_rows}
    appended_identities: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    for index, appended_row in enumerate(appended_rows):
        if not isinstance(appended_row, Mapping):
            raise ValueError(f"appended_rows[{index}] must be an object")
        service_date = str(appended_row.get("service_date") or "").strip()
        route_slot_id = str(appended_row.get("route_slot_id") or "").strip()
        if not service_date:
            raise ValueError(f"appended_rows[{index}].service_date is required")
        if not route_slot_id:
            raise ValueError(f"appended_rows[{index}].route_slot_id is required")
        identity = (service_date, route_slot_id)
        if identity in existing_identities or identity in appended_identities:
            raise ValueError(
                f"appended_rows[{index}] duplicates existing row identity {identity}"
            )
        appended_identities.add(identity)
        full_row = {
            column: appended_row.get(column, "")
            for column in columns
        }
        for key in ("service_date", "route_slot_id"):
            full_row[key] = str(full_row.get(key) or "").strip()
        for key in EDITABLE_SCHEDULE_DRAFT_FIELDS:
            full_row[key] = _normalize_editable_value(full_row.get(key))
        normalized.append(full_row)
    return normalized


def _validated_merged_rows(
    *,
    base_rows: list[dict[str, Any]],
    submitted_rows: list[dict[str, Any]],
    label: str,
) -> list[dict[str, Any]]:
    if len(submitted_rows) != len(base_rows):
        raise ValueError(f"{label} must keep the same row count as the base artifact")

    merged_rows: list[dict[str, Any]] = []
    for index, (base_row, submitted_row) in enumerate(zip(base_rows, submitted_rows, strict=True)):
        base_identity = _row_identity(base_row)
        submitted_identity = _row_identity(submitted_row)
        if submitted_identity != base_identity:
            raise ValueError(
                f"{label}[{index}] identity changed from {base_identity} to {submitted_identity}"
            )
        if set(submitted_row.keys()) != set(base_row.keys()):
            raise ValueError(f"{label}[{index}] must preserve the same field set as the base artifact")

        merged_row = dict(base_row)
        for key in base_row:
            if key in EDITABLE_SCHEDULE_DRAFT_FIELDS:
                merged_row[key] = _normalize_editable_value(submitted_row.get(key))
                continue
            if submitted_row.get(key) != base_row.get(key):
                raise ValueError(f"{label}[{index}] changed immutable field '{key}'")
        merged_rows.append(merged_row)
    return merged_rows


def _row_identity(row: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("service_date") or "").strip(),
        str(row.get("route_slot_id") or "").strip(),
    )


def _normalize_editable_value(value: Any) -> str:
    return str(value or "").strip()
