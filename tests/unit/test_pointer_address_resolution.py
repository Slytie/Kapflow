from __future__ import annotations

import pytest

from onetruth.domain.pointer_address import (
    LegacyPointerAmbiguityError,
    LegacyPointerResolutionError,
    PartitionRef,
    PointerAddress,
    PointerId,
    RegistryKind,
    resolve_legacy_pointer_address,
)


def test_pointer_address_normalization_and_equality() -> None:
    left = PointerAddress(
        tenant_id=" tenant-a ",
        domain_id=" domain-ops ",
        dataset_key=" SCHEDULE.PUBLISHED_SCHEDULE.WORKBOOK ",
        partition_ref=PartitionRef(key="schedule_date_id", value="2026-03-04"),
        stream_key=" lane-1 ",
    )
    right = PointerAddress(
        tenant_id="tenant-a",
        domain_id="domain-ops",
        dataset_key="schedule.published_schedule.workbook",
        partition_ref=PartitionRef(key="ScheduleDateID", value="SD-2026-03-04"),
        stream_key="lane-1",
    )
    assert left == right


def test_pointer_id_round_trips_stably() -> None:
    address = PointerAddress(
        tenant_id="tenant-a",
        domain_id="domain-ops",
        dataset_key="schedule.published_schedule.workbook",
        partition_ref=PartitionRef(key="ScheduleDateID", value="SD-2026-03-04"),
    )
    pointer_id = PointerId.from_address(address)
    assert str(pointer_id) == str(PointerId.from_address(address))
    assert pointer_id.to_address() == address
    assert PointerId.parse(str(pointer_id)).to_address() == address


def test_legacy_resolution_is_deterministic_for_stage_scoped_shape() -> None:
    resolved = resolve_legacy_pointer_address(
        workflow_run_id="wr-001",
        pointer_key="official:schedule.published_schedule.workbook",
        scope_kind="stage",
        scope_ref="Stage06",
        artifact_kind="schedule.published_schedule.workbook",
        tenant_id="tenant-a",
        domain_id="domain-ops",
        workflow_partition_key="SD-2026-03-04",
    )

    assert resolved.registry_kind is RegistryKind.SINGLETON
    assert resolved.address == PointerAddress(
        tenant_id="tenant-a",
        domain_id="domain-ops",
        dataset_key="schedule.published_schedule.workbook",
        partition_ref=PartitionRef(key="ScheduleDateID", value="SD-2026-03-04"),
    )


def test_legacy_resolution_supports_workflow_partition_legacy_shape() -> None:
    resolved = resolve_legacy_pointer_address(
        workflow_run_id="wr-002",
        pointer_key="schedule.replan_delta.workbook:official:SD-2026-03-04",
        scope_kind="workflow_partition",
        scope_ref="SD-2026-03-04",
        artifact_kind="schedule.replan_delta.workbook",
        tenant_id="tenant-a",
        domain_id="domain-ops",
    )

    assert resolved.address.partition_ref == PartitionRef(
        key="ScheduleDateID",
        value="SD-2026-03-04",
    )


def test_legacy_resolution_fails_closed_on_dataset_ambiguity() -> None:
    with pytest.raises(LegacyPointerAmbiguityError):
        resolve_legacy_pointer_address(
            workflow_run_id="wr-003",
            pointer_key="official:schedule.replan_delta.workbook",
            scope_kind="stage",
            scope_ref="Stage06",
            artifact_kind="schedule.published_schedule.workbook",
            tenant_id="tenant-a",
            domain_id="domain-ops",
            workflow_partition_key="SD-2026-03-04",
        )


def test_legacy_resolution_fails_closed_on_partition_ambiguity() -> None:
    with pytest.raises(LegacyPointerAmbiguityError):
        resolve_legacy_pointer_address(
            workflow_run_id="wr-004",
            pointer_key="schedule.replan_delta.workbook:official:SD-2026-03-05",
            scope_kind="workflow_partition",
            scope_ref="SD-2026-03-04",
            artifact_kind="schedule.replan_delta.workbook",
            tenant_id="tenant-a",
            domain_id="domain-ops",
            workflow_partition_key="SD-2026-03-04",
        )


def test_legacy_resolution_fails_when_partition_cannot_be_derived() -> None:
    with pytest.raises(LegacyPointerResolutionError):
        resolve_legacy_pointer_address(
            workflow_run_id="wr-005",
            pointer_key="official:schedule.published_schedule.workbook",
            scope_kind="stage",
            scope_ref="Stage06",
            artifact_kind="schedule.published_schedule.workbook",
            tenant_id="tenant-a",
            domain_id="domain-ops",
        )
