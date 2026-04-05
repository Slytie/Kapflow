from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


ROUTE_DEMAND_DATASET_KEY = "planning.route_slot_requirements.workbook"
_STANDARD_BAND_KEYS = ("standard_early_slot_count", "standard_late_slot_count")


def project_route_demand_workbook(workbook_bytes: bytes) -> dict[str, Any]:
    payload = _load_payload(workbook_bytes)
    columns = _require_columns(payload.get("columns"), label="columns")
    daily_demand_columns = _require_columns(
        payload.get("daily_demand_columns"),
        label="daily_demand_columns",
    )
    return {
        "columns": columns,
        "rows": _decode_table_rows(payload.get("rows"), columns, label="rows"),
        "daily_demand_columns": daily_demand_columns,
        "daily_demand_rows": _decode_table_rows(
            payload.get("daily_demand_rows"),
            daily_demand_columns,
            label="daily_demand_rows",
        ),
    }


def materialize_route_demand_workbook(
    base_workbook_bytes: bytes,
    *,
    daily_demand_rows: Any,
) -> bytes:
    base_payload = _load_payload(base_workbook_bytes)
    columns = _require_columns(base_payload.get("columns"), label="columns")
    daily_demand_columns = _require_columns(
        base_payload.get("daily_demand_columns"),
        label="daily_demand_columns",
    )
    base_rows = _decode_table_rows(base_payload.get("rows"), columns, label="rows")
    base_daily_rows = _decode_table_rows(
        base_payload.get("daily_demand_rows"),
        daily_demand_columns,
        label="daily_demand_rows",
    )
    submitted_daily_rows = _normalize_submitted_daily_demand_rows(daily_demand_rows)
    next_daily_rows = _validated_merged_daily_rows(
        base_daily_rows=base_daily_rows,
        submitted_daily_rows=submitted_daily_rows,
    )
    next_rows = _apply_daily_route_demand_to_slot_rows(
        base_rows=base_rows,
        next_daily_rows=next_daily_rows,
    )

    next_payload = dict(base_payload)
    next_payload["columns"] = list(columns)
    next_payload["rows"] = [
        [row.get(column) for column in columns]
        for row in next_rows
    ]
    next_payload["daily_demand_columns"] = list(daily_demand_columns)
    next_payload["daily_demand_rows"] = [
        [row.get(column) for column in daily_demand_columns]
        for row in next_daily_rows
    ]
    return json.dumps(next_payload, indent=2, sort_keys=True).encode("utf-8")


def route_demand_workbook_bytes_from_metadata_json(metadata_json: object) -> bytes:
    if not isinstance(metadata_json, Mapping):
        raise ValueError("route demand workbook metadata must be an object")
    try:
        return json.dumps(dict(metadata_json), indent=2, sort_keys=True).encode("utf-8")
    except TypeError as exc:
        raise ValueError("route demand workbook metadata must be JSON-serializable") from exc


def _load_payload(workbook_bytes: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(workbook_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("route demand workbook must decode as UTF-8 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("route demand workbook payload must decode to an object")
    return dict(decoded)


def _require_columns(raw_columns: Any, *, label: str) -> list[str]:
    if not isinstance(raw_columns, Sequence) or isinstance(raw_columns, (str, bytes, bytearray)):
        raise ValueError(f"route demand workbook {label} must be a list")
    columns: list[str] = []
    for index, value in enumerate(raw_columns):
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"route demand workbook {label}[{index}] must be a non-empty string")
        columns.append(text)
    if not columns:
        raise ValueError(f"route demand workbook {label} must not be empty")
    return columns


def _decode_table_rows(raw_rows: Any, columns: list[str], *, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes, bytearray)):
        raise ValueError(f"route demand workbook {label} must be a list")
    decoded: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        if isinstance(row, Mapping):
            decoded.append({column: row.get(column) for column in columns})
            continue
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes, bytearray)):
            raise ValueError(f"route demand workbook {label}[{index}] must be a list")
        if len(row) != len(columns):
            raise ValueError(
                f"route demand workbook {label}[{index}] must contain {len(columns)} columns"
            )
        decoded.append({column: row[column_index] for column_index, column in enumerate(columns)})
    return decoded


def _normalize_submitted_daily_demand_rows(raw_rows: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes, bytearray)):
        raise ValueError("daily_demand_rows must be a list")
    normalized: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"daily_demand_rows[{index}] must be an object")
        service_date = str(row.get("service_date") or "").strip()
        if not service_date:
            raise ValueError(f"daily_demand_rows[{index}].service_date is required")
        if service_date in seen_dates:
            raise ValueError(f"daily_demand_rows contains duplicate service_date: {service_date}")
        seen_dates.add(service_date)
        planned_route_count = _coerce_int(row.get("planned_route_count"), default=-1)
        if planned_route_count < 0:
            raise ValueError(
                f"daily_demand_rows[{index}].planned_route_count must be a non-negative integer"
            )
        normalized.append(
            {
                "service_date": service_date,
                "planned_route_count": planned_route_count,
            }
        )
    return normalized


def _validated_merged_daily_rows(
    *,
    base_daily_rows: list[dict[str, Any]],
    submitted_daily_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(base_daily_rows) != len(submitted_daily_rows):
        raise ValueError("daily_demand_rows must keep the same row count as the base artifact")
    submitted_by_date = {
        str(row.get("service_date") or ""): row
        for row in submitted_daily_rows
    }
    next_daily_rows: list[dict[str, Any]] = []
    for index, base_row in enumerate(base_daily_rows):
        service_date = str(base_row.get("service_date") or "").strip()
        submitted_row = submitted_by_date.get(service_date)
        if submitted_row is None:
            raise ValueError(
                f"daily_demand_rows is missing service_date from the base artifact: {service_date}"
            )
        next_row = dict(base_row)
        planned_route_count = int(submitted_row["planned_route_count"])
        rescue_slot_count = max(_coerce_int(base_row.get("rescue_slot_count"), default=0), 0)
        overflow_slot_count = max(_coerce_int(base_row.get("overflow_slot_count"), default=0), 0)
        standard_total = max(planned_route_count - rescue_slot_count - overflow_slot_count, 0)
        next_row["planned_route_count"] = planned_route_count
        if "standard_slot_count" in next_row:
            next_row["standard_slot_count"] = standard_total
        if any(key in next_row for key in _STANDARD_BAND_KEYS):
            standard_by_band = _split_standard_total_by_ratio(base_row, standard_total)
            for key, value in standard_by_band.items():
                if key in next_row:
                    next_row[key] = value
        next_daily_rows.append(next_row)
    return next_daily_rows


def _apply_daily_route_demand_to_slot_rows(
    *,
    base_rows: list[dict[str, Any]],
    next_daily_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    next_standard_by_date = {
        str(row.get("service_date") or ""): max(
            _coerce_int(row.get("standard_slot_count"), default=_coerce_int(row.get("planned_route_count"), default=0)),
            0,
        )
        for row in next_daily_rows
    }
    grouped_rows: dict[str, list[dict[str, Any]]] = {}
    for row in base_rows:
        service_date = str(row.get("service_date") or "").strip()
        grouped_rows.setdefault(service_date, []).append(dict(row))

    next_rows: list[dict[str, Any]] = []
    for service_date in [str(row.get("service_date") or "").strip() for row in next_daily_rows]:
        day_rows = grouped_rows.get(service_date, [])
        standard_rows = [row for row in day_rows if _is_standard_row(row)]
        rescue_rows = [row for row in day_rows if _is_rescue_row(row)]
        overflow_rows = [row for row in day_rows if _is_overflow_row(row)]
        other_rows = [
            row
            for row in day_rows
            if row not in standard_rows and row not in rescue_rows and row not in overflow_rows
        ]
        if not standard_rows:
            next_rows.extend(day_rows)
            continue
        standard_total = max(
            next_standard_by_date.get(service_date, 0),
            0,
        )
        if len(standard_rows) == 1:
            row = dict(standard_rows[0])
            row["required_count"] = standard_total
            next_rows.extend([row, *rescue_rows, *overflow_rows, *other_rows])
            continue
        split = _split_standard_total_by_ratio_from_rows(standard_rows, standard_total)
        updated_standard_rows: list[dict[str, Any]] = []
        for row in standard_rows:
            updated = dict(row)
            updated["required_count"] = split.get(_standard_band_key(row), 0)
            updated_standard_rows.append(updated)
        next_rows.extend([*updated_standard_rows, *rescue_rows, *overflow_rows, *other_rows])
    return next_rows


def _split_standard_total_by_ratio(base_row: Mapping[str, Any], standard_total: int) -> dict[str, int]:
    explicit = {
        key: max(_coerce_int(base_row.get(key), default=0), 0)
        for key in _STANDARD_BAND_KEYS
        if key in base_row
    }
    if not explicit:
        return {}
    return _ratio_split(
        total=standard_total,
        weights=explicit,
        order=[key for key in _STANDARD_BAND_KEYS if key in explicit],
    )


def _split_standard_total_by_ratio_from_rows(
    standard_rows: list[Mapping[str, Any]],
    standard_total: int,
) -> dict[str, int]:
    weights = {
        _standard_band_key(row): max(_coerce_int(row.get("required_count"), default=0), 0)
        for row in standard_rows
    }
    order = sorted(weights.keys())
    return _ratio_split(total=standard_total, weights=weights, order=order)


def _ratio_split(
    *,
    total: int,
    weights: Mapping[str, int],
    order: list[str],
) -> dict[str, int]:
    if total <= 0:
        return {key: 0 for key in order}
    weight_sum = sum(max(value, 0) for value in weights.values())
    if weight_sum <= 0:
        base = total // max(len(order), 1)
        remainder = total - (base * len(order))
        result = {key: base for key in order}
        for key in order:
            if remainder <= 0:
                break
            result[key] += 1
            remainder -= 1
        return result

    allocations: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    allocated = 0
    for key in order:
        weight = max(weights.get(key, 0), 0)
        exact = (total * weight) / weight_sum
        whole = int(exact)
        allocations[key] = whole
        allocated += whole
        remainders.append((exact - whole, key))
    remaining = total - allocated
    for _fraction, key in sorted(remainders, key=lambda item: (-item[0], item[1])):
        if remaining <= 0:
            break
        allocations[key] += 1
        remaining -= 1
    return allocations


def _is_standard_row(row: Mapping[str, Any]) -> bool:
    if _is_rescue_row(row) or _is_overflow_row(row):
        return False
    route_slot_class = str(row.get("route_slot_class") or "").strip().lower()
    demand_kind = str(row.get("demand_kind") or "route").strip().lower()
    return "standard" in route_slot_class and demand_kind == "route"


def _is_rescue_row(row: Mapping[str, Any]) -> bool:
    return _band_contains(row, "rescue")


def _is_overflow_row(row: Mapping[str, Any]) -> bool:
    return _band_contains(row, "overflow")


def _band_contains(row: Mapping[str, Any], token: str) -> bool:
    token = token.lower()
    for field in ("route_slot_class", "slot_band", "preferred_shift_band", "demand_kind"):
        value = str(row.get(field) or "").strip().lower()
        if token in value:
            return True
    return False


def _standard_band_key(row: Mapping[str, Any]) -> str:
    route_slot_class = str(row.get("route_slot_class") or "").strip().lower()
    slot_band = str(row.get("slot_band") or row.get("preferred_shift_band") or "").strip().lower()
    if "early" in route_slot_class or slot_band == "early":
        return "standard_early_slot_count"
    if "late" in route_slot_class or slot_band == "late":
        return "standard_late_slot_count"
    return str(row.get("route_slot_id") or "").strip() or "standard_slot_count"


def _coerce_int(value: Any, *, default: int) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)
