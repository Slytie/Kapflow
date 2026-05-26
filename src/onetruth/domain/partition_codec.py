from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re


class PartitionCodecError(ValueError):
    """Raised when a typed partition key or transform is invalid."""


PARTITION_PATTERNS: dict[str, re.Pattern[str]] = {
    "AvailabilityRequestID": re.compile(r"^AR-\d{8}-\d{4}$"),
    "PlanningWeekID": re.compile(r"^PW-(\d{4})-W(\d{2})$"),
    "ServiceDateID": re.compile(r"^SD-(\d{4})-(\d{2})-(\d{2})$"),
    "PayPeriodID": re.compile(r"^PP-(\d{4})-W(\d{2})$"),
    "ScheduleDateID": re.compile(r"^SD-(\d{4})-(\d{2})-(\d{2})$"),
}


@dataclass(frozen=True)
class PartitionTransformContract:
    implementation_ref: str
    source_kind: str
    target_kind: str
    shape: str


KNOWN_TRANSFORM_CONTRACTS: dict[str, PartitionTransformContract] = {
    "partition_codec.planning_week_to_service_days.v1": PartitionTransformContract(
        implementation_ref="partition_codec.planning_week_to_service_days.v1",
        source_kind="PlanningWeekID",
        target_kind="ServiceDateID",
        shape="one_to_many",
    ),
    "partition_codec.availability_dates_to_planning_weeks.v1": PartitionTransformContract(
        implementation_ref="partition_codec.availability_dates_to_planning_weeks.v1",
        source_kind="AvailabilityRequestID",
        target_kind="PlanningWeekID",
        shape="one_to_many",
    ),
    "partition_codec.service_day_to_future_planning_week.v1": PartitionTransformContract(
        implementation_ref="partition_codec.service_day_to_future_planning_week.v1",
        source_kind="ServiceDateID",
        target_kind="PlanningWeekID",
        shape="one_to_one",
    ),
    "partition_codec.service_day_to_pay_period.v1": PartitionTransformContract(
        implementation_ref="partition_codec.service_day_to_pay_period.v1",
        source_kind="ServiceDateID",
        target_kind="PayPeriodID",
        shape="many_to_one",
    ),
}


def validate_partition_key(kind: str, key: str) -> None:
    pattern = PARTITION_PATTERNS.get(kind)
    if pattern is None:
        raise PartitionCodecError(f"unsupported partition kind: {kind}")
    if pattern.match(key) is None:
        raise PartitionCodecError(f"partition key does not match {kind}: {key}")


def validate_transform_contract(
    *,
    implementation_ref: str,
    source_kind: str,
    target_kind: str,
    shape: str,
) -> None:
    known = KNOWN_TRANSFORM_CONTRACTS.get(implementation_ref)
    if known is None:
        raise PartitionCodecError(f"unknown transform implementation_ref: {implementation_ref}")
    if (
        known.source_kind != source_kind
        or known.target_kind != target_kind
        or known.shape != shape
    ):
        raise PartitionCodecError(
            "partition transform contract mismatch for "
            f"{implementation_ref}: expected "
            f"({known.source_kind}, {known.target_kind}, {known.shape}) got "
            f"({source_kind}, {target_kind}, {shape})"
        )


def planning_week_to_service_days(planning_week_id: str) -> list[str]:
    validate_partition_key("PlanningWeekID", planning_week_id)
    match = PARTITION_PATTERNS["PlanningWeekID"].match(planning_week_id)
    assert match is not None
    year = int(match.group(1))
    week = int(match.group(2))
    return [
        _to_service_date_id(date.fromisocalendar(year, week, day))
        for day in range(1, 8)
    ]


def service_day_to_pay_period(service_date_id: str) -> str:
    service_date = _parse_service_date(service_date_id)
    iso_year, iso_week, _ = service_date.isocalendar()
    return f"PP-{iso_year:04d}-W{iso_week:02d}"


def service_day_to_future_planning_week(service_date_id: str) -> str:
    service_date = _parse_service_date(service_date_id)
    sunday_offset = (service_date.weekday() + 1) % 7
    current_operational_week_start = service_date - timedelta(days=sunday_offset)
    future_operational_week_start = current_operational_week_start + timedelta(days=7)
    label_monday = future_operational_week_start + timedelta(days=1)
    iso_year, iso_week, _ = label_monday.isocalendar()
    return f"PW-{iso_year:04d}-W{iso_week:02d}"


def availability_dates_to_planning_weeks(*, dates: list[str]) -> list[str]:
    if not dates:
        return []
    weeks = set()
    for raw_date in dates:
        parsed = date.fromisoformat(raw_date)
        iso_year, iso_week, _ = parsed.isocalendar()
        weeks.add(f"PW-{iso_year:04d}-W{iso_week:02d}")
    return sorted(weeks)


def _parse_service_date(service_date_id: str) -> date:
    validate_partition_key("ServiceDateID", service_date_id)
    match = PARTITION_PATTERNS["ServiceDateID"].match(service_date_id)
    assert match is not None
    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _to_service_date_id(value: date) -> str:
    return f"SD-{value.year:04d}-{value.month:02d}-{value.day:02d}"
