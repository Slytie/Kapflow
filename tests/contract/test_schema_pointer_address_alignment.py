from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from onetruth.domain.pointer_address import (
    PartitionRef,
    PointerAddress,
    PointerId,
    load_dataset_partition_index,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pointer_address_maps_to_pointer_runtime_schema_shape() -> None:
    schema = json.loads((REPO_ROOT / "schemas" / "runtime" / "pointer.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    address = PointerAddress(
        tenant_id="tenant-a",
        domain_id="domain-ops",
        dataset_key="schedule.published_schedule.workbook",
        partition_ref=PartitionRef(key="ScheduleDateID", value="SD-2026-03-04"),
    )

    payload = {
        "pointer_id": str(PointerId.from_address(address)),
        "tenant_id": address.tenant_id,
        "domain_id": address.domain_id,
        "dataset_key": address.dataset_key,
        "partition": address.partition_ref.to_schema_dict(),
        "current_artifact_version_id": "av-001",
        "promoted_at": "2026-03-07T09:15:00Z",
        "promoted_by": {"type": "human", "id": "human:supervisor"},
    }

    validator.validate(payload)


def test_dataset_registry_partition_keys_drive_typed_partition_refs() -> None:
    index = load_dataset_partition_index()

    assert index["schedule.published_schedule.workbook"] == "ScheduleDateID"
    assert index["payroll.run_register.workbook"] == "PayPeriodID"

    assert PartitionRef(key=index["schedule.published_schedule.workbook"], value="SD-2026-03-04").key == "ScheduleDateID"
    assert PartitionRef(key=index["payroll.run_register.workbook"], value="PP-2026-03").key == "PayPeriodID"
