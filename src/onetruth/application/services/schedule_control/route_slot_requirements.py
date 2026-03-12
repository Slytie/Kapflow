from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class RouteSlotRequirement:
    service_date: str
    route_slot_id: str
    route_slot_class: str
    required_skill: str
    vehicle_type: str
    shift_start: str
    shift_end: str
    estimated_hours: float
    source_snapshot_row_ref: str

    @property
    def projected_minutes(self) -> int:
        return int(round(self.estimated_hours * 60.0))


def parse_route_slot_requirements(*, columns: list[str], rows: Iterable[Any]) -> tuple[RouteSlotRequirement, ...]:
    parsed: list[RouteSlotRequirement] = []
    for raw in _rows_to_dicts(columns=columns, rows=rows):
        route_slot_id = str(raw.get("route_slot_id") or "").strip()
        service_date = str(raw.get("service_date") or "").strip()
        if not route_slot_id or not service_date:
            continue
        parsed.append(
            RouteSlotRequirement(
                service_date=service_date,
                route_slot_id=route_slot_id,
                route_slot_class=str(raw.get("route_slot_class") or "").strip(),
                required_skill=str(raw.get("required_skill") or "").strip(),
                vehicle_type=str(raw.get("vehicle_type") or "").strip(),
                shift_start=str(raw.get("shift_start") or "").strip(),
                shift_end=str(raw.get("shift_end") or "").strip(),
                estimated_hours=_coerce_float(raw.get("estimated_hours"), default=0.0),
                source_snapshot_row_ref=str(raw.get("source_snapshot_row_ref") or "").strip(),
            )
        )

    return tuple(
        sorted(
            parsed,
            key=lambda item: (
                item.service_date,
                item.route_slot_id,
                item.shift_start,
            ),
        )
    )


def expand_route_slot_requirements(
    route_slots: Iterable[RouteSlotRequirement],
    *,
    default_required_count: int = 1,
) -> tuple[RouteSlotRequirement, ...]:
    expanded: list[RouteSlotRequirement] = []
    for slot in sorted(
        route_slots,
        key=lambda item: (
            item.service_date,
            item.route_slot_id,
            item.shift_start,
        ),
    ):
        required_count = _required_count_for_slot(slot, default_required_count=default_required_count)
        if required_count == 1:
            expanded.append(slot)
            continue
        base_route_slot_id = slot.route_slot_id.split("*", maxsplit=1)[0]
        for index in range(required_count):
            expanded.append(
                RouteSlotRequirement(
                    service_date=slot.service_date,
                    route_slot_id=f"{base_route_slot_id}#{index + 1:02d}",
                    route_slot_class=slot.route_slot_class,
                    required_skill=slot.required_skill,
                    vehicle_type=slot.vehicle_type,
                    shift_start=slot.shift_start,
                    shift_end=slot.shift_end,
                    estimated_hours=slot.estimated_hours,
                    source_snapshot_row_ref=slot.source_snapshot_row_ref,
                )
            )
    return tuple(expanded)


def _required_count_for_slot(slot: RouteSlotRequirement, *, default_required_count: int) -> int:
    # Allow count suffixes such as route-slot-id*3 while keeping the base id deterministic.
    if "*" not in slot.route_slot_id:
        return max(default_required_count, 1)
    _, count_text = slot.route_slot_id.rsplit("*", maxsplit=1)
    parsed = _coerce_int(count_text, default=default_required_count)
    return max(parsed, 1)


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


def _coerce_float(value: Any, *, default: float) -> float:
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _coerce_int(value: Any, *, default: int) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)
