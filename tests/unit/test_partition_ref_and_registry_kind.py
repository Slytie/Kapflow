from __future__ import annotations

import pytest

from onetruth.domain.pointer_address import (
    InvalidRegistryKindError,
    PartitionRef,
    PartitionRefValidationError,
    RegistryKind,
)


def test_partition_ref_normalizes_schedule_date_and_key_aliases() -> None:
    partition = PartitionRef(key="schedule_date_id", value="2026-03-04")
    assert partition.key == "ScheduleDateID"
    assert partition.value == "SD-2026-03-04"


def test_partition_ref_equality_uses_normalized_representation() -> None:
    left = PartitionRef(key="ScheduleDateID", value="SD-2026-03-04")
    right = PartitionRef(key="schedule_date_id", value=" 2026-03-04 ")
    assert left == right


def test_partition_ref_rejects_invalid_schedule_date_values() -> None:
    with pytest.raises(PartitionRefValidationError):
        PartitionRef(key="ScheduleDateID", value="not-a-date")


def test_registry_kind_parse_defaults_to_singleton() -> None:
    assert RegistryKind.parse(None) is RegistryKind.SINGLETON
    assert RegistryKind.parse(" ") is RegistryKind.SINGLETON


def test_registry_kind_parse_accepts_case_and_dash_variants() -> None:
    assert RegistryKind.parse("ORDERED-STREAM") is RegistryKind.ORDERED_STREAM
    assert RegistryKind.parse("membership_set") is RegistryKind.MEMBERSHIP_SET


def test_registry_kind_parse_rejects_unknown_values() -> None:
    with pytest.raises(InvalidRegistryKindError):
        RegistryKind.parse("bag")
