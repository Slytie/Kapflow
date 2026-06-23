from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3
from typing import Any

from onetruth.capex_platform.staged_corpus_ingest import (
    STAGED_CORPUS_INGEST_SCHEMA_VERSION,
)
from onetruth.infrastructure.repositories.capex_source_occurrences import (
    upsert_content_identity,
)


SOURCE_INVENTORY_SCHEMA_VERSION = "capex.source_inventory.v1"
SOURCE_INVENTORY_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
SOURCE_INVENTORY_ARTIFACT_KIND = "capex.source_inventory"
SOURCE_INVENTORY_ARTIFACT_ROLE = "evidence"
SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT = (
    "inventory_pre_source_occurrence"
)

_SHA256_RE = re.compile(r"^sha256:([0-9a-f]{64})$")


@dataclass(frozen=True)
class SourceInventoryError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_source_inventory(
    connection: sqlite3.Connection,
    *,
    ingest_plan: Mapping[str, Any],
    inventory_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Create content identities and return a deterministic source inventory.

    The inventory pipeline is intentionally pre-occurrence: it records content
    identity and dedupe facts only, and it does not create SourceOccurrence rows.
    """

    _require_schema(ingest_plan)
    tenant_id = _require_nonempty(ingest_plan.get("tenant_id"), "tenant_id")
    domain_id = _require_nonempty(ingest_plan.get("domain_id"), "domain_id")
    project_id = _require_nonempty(ingest_plan.get("project_id"), "project_id")
    ingest_batch_id = _require_nonempty(
        ingest_plan.get("ingest_batch_id"),
        "ingest_batch_id",
    )
    descriptors = ingest_plan.get("descriptors")
    if not isinstance(descriptors, list) or not descriptors:
        raise SourceInventoryError(
            "source_inventory_descriptors_required",
            {"field": "descriptors"},
        )

    items: list[dict[str, Any]] = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for index, raw_descriptor in enumerate(descriptors):
        if not isinstance(raw_descriptor, Mapping):
            raise SourceInventoryError(
                "source_inventory_descriptor_must_be_object",
                {"index": index},
            )
        item = _inventory_item(
            connection,
            tenant_id=tenant_id,
            domain_id=domain_id,
            ingest_batch_id=ingest_batch_id,
            inventory_id=inventory_id,
            descriptor=raw_descriptor,
            index=index,
            created_at=created_at,
        )
        items.append(item)
        groups[(item["digest_algorithm"], item["content_digest"])].append(item)

    dedupe_groups = [
        {
            "dedupe_group_id": f"dedupe:{algorithm}:{digest.removeprefix('sha256:')}",
            "digest_algorithm": algorithm,
            "content_digest": digest,
            "content_identity_id": grouped_items[0]["content_identity_id"],
            "descriptor_ids": [
                str(grouped_item["descriptor_id"]) for grouped_item in grouped_items
            ],
            "occurrence_count": len(grouped_items),
        }
        for (algorithm, digest), grouped_items in sorted(groups.items())
    ]

    return {
        "schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
        "activation_posture": SOURCE_INVENTORY_ACTIVATION_POSTURE,
        "inventory_id": _require_nonempty(inventory_id, "inventory_id"),
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "project_id": project_id,
        "ingest_batch_id": ingest_batch_id,
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "descriptor_count": len(items),
        "unique_content_count": len(dedupe_groups),
        "digest_store": {
            "repository": "capex_content_identities",
            "digest_algorithm": "sha256",
        },
        "dedupe_groups": dedupe_groups,
        "items": items,
        "truth_effects": {
            "creates_source_occurrences": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def canonical_source_inventory_bytes(inventory: Mapping[str, Any]) -> bytes:
    return json.dumps(
        inventory,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def source_inventory_digest(inventory: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_source_inventory_bytes(inventory)
    ).hexdigest()


def source_inventory_validation_summary() -> dict[str, str]:
    return {
        "result": SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT,
        "policy": "content_identity_only_no_source_occurrence_binding",
    }


def _require_schema(ingest_plan: Mapping[str, Any]) -> None:
    if ingest_plan.get("schema_version") != STAGED_CORPUS_INGEST_SCHEMA_VERSION:
        raise SourceInventoryError(
            "source_inventory_requires_staged_ingest_plan",
            {
                "expected_schema_version": STAGED_CORPUS_INGEST_SCHEMA_VERSION,
                "actual_schema_version": ingest_plan.get("schema_version"),
            },
        )


def _inventory_item(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    ingest_batch_id: str,
    inventory_id: str,
    descriptor: Mapping[str, Any],
    index: int,
    created_at: str,
) -> dict[str, Any]:
    descriptor_id = _require_nonempty(
        descriptor.get("descriptor_id"),
        f"descriptors[{index}].descriptor_id",
    )
    content_digest = _require_content_digest(descriptor, index)
    canonicalization_profile = _require_nonempty(
        descriptor.get("canonicalization_profile"),
        f"descriptors[{index}].canonicalization_profile",
    )
    content_identity_id = upsert_content_identity(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        digest_algorithm="sha256",
        content_digest=content_digest.removeprefix("sha256:"),
        byte_size=_optional_nonnegative_int(
            descriptor.get("content_byte_size"),
            f"descriptors[{index}].content_byte_size",
        ),
        media_type=(
            str(descriptor["content_media_type"])
            if descriptor.get("content_media_type") is not None
            else None
        ),
        canonicalization_profile=canonicalization_profile,
        metadata_json={
            "source_inventory_id": inventory_id,
            "ingest_batch_id": ingest_batch_id,
            "descriptor_id": descriptor_id,
            "source_occurrence_created": False,
        },
        created_at=created_at,
    )
    return {
        "descriptor_id": descriptor_id,
        "mode": _require_nonempty(descriptor.get("mode"), f"descriptors[{index}].mode"),
        "manifest_ref": _require_nonempty(
            descriptor.get("manifest_ref"),
            f"descriptors[{index}].manifest_ref",
        ),
        "manifest_digest": _require_nonempty(
            descriptor.get("manifest_digest"),
            f"descriptors[{index}].manifest_digest",
        ),
        "digest_algorithm": "sha256",
        "content_digest": content_digest,
        "content_identity_id": content_identity_id,
        "content_byte_size": _optional_nonnegative_int(
            descriptor.get("content_byte_size"),
            f"descriptors[{index}].content_byte_size",
        ),
        "content_media_type": descriptor.get("content_media_type"),
        "canonicalization_profile": canonicalization_profile,
        "source_occurrence_created": False,
    }


def _require_content_digest(descriptor: Mapping[str, Any], index: int) -> str:
    value = _require_nonempty(
        descriptor.get("content_digest"),
        f"descriptors[{index}].content_digest",
    ).lower()
    if not _SHA256_RE.match(value):
        raise SourceInventoryError(
            "source_inventory_content_digest_invalid",
            {"index": index, "content_digest": value},
        )
    return value


def _optional_nonnegative_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or value < 0:
        raise SourceInventoryError(
            "source_inventory_nonnegative_integer_required",
            {"field": field_name, "value": value},
        )
    return value


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceInventoryError(
            "source_inventory_required_field_missing",
            {"field": field_name},
        )
    return value.strip()


__all__ = [
    "SOURCE_INVENTORY_ACTIVATION_POSTURE",
    "SOURCE_INVENTORY_ARTIFACT_KIND",
    "SOURCE_INVENTORY_ARTIFACT_ROLE",
    "SOURCE_INVENTORY_PRE_OCCURRENCE_VALIDATION_RESULT",
    "SOURCE_INVENTORY_SCHEMA_VERSION",
    "SourceInventoryError",
    "build_source_inventory",
    "canonical_source_inventory_bytes",
    "source_inventory_digest",
    "source_inventory_validation_summary",
]
