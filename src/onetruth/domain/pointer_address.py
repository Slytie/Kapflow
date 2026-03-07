from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import quote, unquote

import yaml


class PointerAddressError(ValueError):
    """Base error for canonical pointer-address helpers."""


class PartitionRefValidationError(PointerAddressError):
    """Raised when a partition key/value pair is invalid."""


class InvalidRegistryKindError(PointerAddressError):
    """Raised when a registry kind token cannot be parsed."""


class PointerIdParseError(PointerAddressError):
    """Raised when a pointer id cannot be parsed safely."""


class LegacyPointerResolutionError(PointerAddressError):
    """Raised when a legacy pointer shape cannot be resolved safely."""


class LegacyPointerAmbiguityError(LegacyPointerResolutionError):
    """Raised when legacy inputs imply multiple canonical addresses."""


class RegistryKind(str, Enum):
    SINGLETON = "singleton"
    MEMBERSHIP_SET = "membership_set"
    ORDERED_STREAM = "ordered_stream"
    INTERVAL = "interval"

    @classmethod
    def parse(
        cls,
        raw: "RegistryKind | str | None",
        *,
        default: "RegistryKind" = None,
    ) -> "RegistryKind":
        resolved_default = cls.SINGLETON if default is None else default
        if raw is None:
            return resolved_default
        if isinstance(raw, cls):
            return raw
        text = str(raw).strip()
        if not text:
            return resolved_default
        normalized = text.lower().replace("-", "_")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise InvalidRegistryKindError(f"unsupported registry_kind: {raw}") from exc


@dataclass(frozen=True)
class PartitionRef:
    key: str
    value: str

    def __post_init__(self) -> None:
        normalized_key = _normalize_partition_key(self.key)
        normalized_value = _normalize_partition_value(normalized_key, self.value)
        object.__setattr__(self, "key", normalized_key)
        object.__setattr__(self, "value", normalized_value)

    def to_schema_dict(self) -> dict[str, str]:
        return {"key": self.key, "value": self.value}


@dataclass(frozen=True)
class PointerAddress:
    tenant_id: str
    domain_id: str
    dataset_key: str
    partition_ref: PartitionRef
    stream_key: str | None = None

    def __post_init__(self) -> None:
        normalized_tenant_id = _normalize_required_token("tenant_id", self.tenant_id)
        normalized_domain_id = _normalize_required_token("domain_id", self.domain_id)
        normalized_dataset_key = _normalize_dataset_key(self.dataset_key)
        if not isinstance(self.partition_ref, PartitionRef):
            raise PartitionRefValidationError("partition_ref must be a PartitionRef")
        normalized_stream_key = _normalize_optional_token("stream_key", self.stream_key)

        object.__setattr__(self, "tenant_id", normalized_tenant_id)
        object.__setattr__(self, "domain_id", normalized_domain_id)
        object.__setattr__(self, "dataset_key", normalized_dataset_key)
        object.__setattr__(self, "stream_key", normalized_stream_key)

    def to_pointer_id(self) -> "PointerId":
        return PointerId.from_address(self)


@dataclass(frozen=True)
class PointerId:
    value: str

    def __post_init__(self) -> None:
        normalized = _serialize_pointer_id(_parse_pointer_id(self.value))
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_address(cls, address: PointerAddress) -> "PointerId":
        return cls(_serialize_pointer_id(address))

    @classmethod
    def parse(cls, raw: str) -> "PointerId":
        return cls(raw)

    def to_address(self) -> PointerAddress:
        return _parse_pointer_id(self.value)


@dataclass(frozen=True)
class LegacyPointerResolution:
    workflow_run_id: str
    pointer_key: str
    registry_kind: RegistryKind
    address: PointerAddress

    @property
    def pointer_id(self) -> PointerId:
        return PointerId.from_address(self.address)


def resolve_legacy_pointer_address(
    *,
    workflow_run_id: str,
    pointer_key: str,
    scope_kind: str,
    scope_ref: str,
    artifact_kind: str,
    tenant_id: str,
    domain_id: str,
    workflow_partition_key: str | None = None,
    stream_key: str | None = None,
    registry_kind: RegistryKind | str | None = None,
    dataset_partition_index: Mapping[str, str] | None = None,
) -> LegacyPointerResolution:
    normalized_workflow_run_id = _normalize_required_token("workflow_run_id", workflow_run_id)
    normalized_pointer_key = _normalize_required_token("pointer_key", pointer_key)
    normalized_scope_kind = _normalize_scope_kind(scope_kind)
    normalized_scope_ref = _normalize_optional_token("scope_ref", scope_ref)
    normalized_tenant_id = _normalize_required_token("tenant_id", tenant_id)
    normalized_domain_id = _normalize_required_token("domain_id", domain_id)

    hints = _parse_legacy_pointer_key(normalized_pointer_key)
    dataset_candidates = {
        _normalize_dataset_key(artifact_kind),
    }
    if hints.dataset_key is not None:
        dataset_candidates.add(_normalize_dataset_key(hints.dataset_key))
    if len(dataset_candidates) != 1:
        raise LegacyPointerAmbiguityError(
            "legacy dataset candidates do not agree "
            f"(workflow_run_id={normalized_workflow_run_id}, pointer_key={normalized_pointer_key}, "
            f"candidates={sorted(dataset_candidates)})"
        )
    canonical_dataset_key = next(iter(dataset_candidates))

    partition_index = _normalized_dataset_partition_index(dataset_partition_index)
    partition_key = partition_index.get(canonical_dataset_key)
    if partition_key is None:
        raise LegacyPointerResolutionError(
            "cannot resolve partition key for dataset "
            f"(workflow_run_id={normalized_workflow_run_id}, dataset_key={canonical_dataset_key})"
        )

    partition_candidates: list[str] = []
    normalized_workflow_partition = _normalize_optional_token("workflow_partition_key", workflow_partition_key)
    if normalized_workflow_partition is not None:
        partition_candidates.append(normalized_workflow_partition)

    if normalized_scope_kind == "workflow_partition":
        if normalized_scope_ref is None:
            raise LegacyPointerResolutionError(
                "scope_ref is required when scope_kind=workflow_partition "
                f"(workflow_run_id={normalized_workflow_run_id}, pointer_key={normalized_pointer_key})"
            )
        partition_candidates.append(normalized_scope_ref)
    elif normalized_scope_kind not in {"stage", "workflow_run"}:
        raise LegacyPointerResolutionError(
            "legacy scope_kind is not yet mappable "
            f"(workflow_run_id={normalized_workflow_run_id}, scope_kind={normalized_scope_kind})"
        )

    if hints.partition_value is not None:
        partition_candidates.append(hints.partition_value)

    if not partition_candidates:
        raise LegacyPointerResolutionError(
            "cannot derive canonical partition value from legacy pointer shape "
            f"(workflow_run_id={normalized_workflow_run_id}, pointer_key={normalized_pointer_key})"
        )

    normalized_partition_values = {
        PartitionRef(key=partition_key, value=candidate).value for candidate in partition_candidates
    }
    if len(normalized_partition_values) != 1:
        raise LegacyPointerAmbiguityError(
            "legacy partition candidates do not agree "
            f"(workflow_run_id={normalized_workflow_run_id}, pointer_key={normalized_pointer_key}, "
            f"candidates={sorted(normalized_partition_values)})"
        )
    canonical_partition_value = next(iter(normalized_partition_values))

    resolved_address = PointerAddress(
        tenant_id=normalized_tenant_id,
        domain_id=normalized_domain_id,
        dataset_key=canonical_dataset_key,
        partition_ref=PartitionRef(key=partition_key, value=canonical_partition_value),
        stream_key=stream_key,
    )
    return LegacyPointerResolution(
        workflow_run_id=normalized_workflow_run_id,
        pointer_key=normalized_pointer_key,
        registry_kind=RegistryKind.parse(registry_kind),
        address=resolved_address,
    )


def load_dataset_partition_index(path: Path | None = None) -> dict[str, str]:
    dataset_registry_path = _default_dataset_keys_path() if path is None else path
    loaded = yaml.safe_load(dataset_registry_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise LegacyPointerResolutionError("dataset registry must parse to an object")

    datasets = loaded.get("datasets")
    if not isinstance(datasets, list):
        raise LegacyPointerResolutionError("dataset registry must contain a datasets list")

    index: dict[str, str] = {}
    for item in datasets:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        partitioned_by = item.get("partitioned_by")
        if key is None or not isinstance(partitioned_by, list) or len(partitioned_by) != 1:
            continue
        normalized_dataset_key = _normalize_dataset_key(str(key))
        index[normalized_dataset_key] = _normalize_partition_key(str(partitioned_by[0]))
    return index


@lru_cache(maxsize=1)
def _cached_default_dataset_partition_index() -> dict[str, str]:
    return load_dataset_partition_index()


def _normalized_dataset_partition_index(
    provided: Mapping[str, str] | None,
) -> dict[str, str]:
    if provided is None:
        source = _cached_default_dataset_partition_index()
    else:
        source = provided

    index: dict[str, str] = {}
    for dataset_key, partition_key in source.items():
        index[_normalize_dataset_key(dataset_key)] = _normalize_partition_key(partition_key)
    return index


def _default_dataset_keys_path() -> Path:
    return Path(__file__).resolve().parents[3] / "schemas" / "artifacts" / "dataset_keys.yaml"


@dataclass(frozen=True)
class _LegacyPointerKeyHints:
    dataset_key: str | None = None
    partition_value: str | None = None


def _parse_legacy_pointer_key(pointer_key: str) -> _LegacyPointerKeyHints:
    parts = pointer_key.split(":")
    official_positions = [idx for idx, part in enumerate(parts) if part.lower() == "official"]

    if not official_positions:
        return _LegacyPointerKeyHints()
    if len(official_positions) > 1:
        raise LegacyPointerAmbiguityError(
            f"legacy pointer_key contains multiple official markers: {pointer_key}"
        )

    official_pos = official_positions[0]
    if official_pos == 0 and len(parts) == 2:
        return _LegacyPointerKeyHints(dataset_key=parts[1])
    if official_pos == 1 and len(parts) == 3:
        return _LegacyPointerKeyHints(dataset_key=parts[0], partition_value=parts[2])

    raise LegacyPointerAmbiguityError(
        "legacy pointer_key shape cannot be resolved safely "
        f"(pointer_key={pointer_key})"
    )


def _normalize_required_token(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise PointerAddressError(f"{name} must be non-empty")
    return text


def _normalize_optional_token(name: str, value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "/" in text and name == "stream_key":
        # Keep pointer-id segment parsing safe and deterministic.
        return text
    return text


def _normalize_scope_kind(scope_kind: Any) -> str:
    return _normalize_required_token("scope_kind", scope_kind).lower()


def _normalize_dataset_key(dataset_key: Any) -> str:
    return _normalize_required_token("dataset_key", dataset_key).lower()


_PARTITION_KEY_CANONICAL = {
    "scheduledateid": "ScheduleDateID",
    "payperiodid": "PayPeriodID",
}


def _normalize_partition_key(raw_key: Any) -> str:
    text = _normalize_required_token("partition.key", raw_key)
    folded = re.sub(r"[^a-z0-9]", "", text.lower())
    return _PARTITION_KEY_CANONICAL.get(folded, text)


_SCHEDULE_DATE_ID_PATTERN = re.compile(r"^SD-\d{4}-\d{2}-\d{2}$")
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _normalize_partition_value(partition_key: str, raw_value: Any) -> str:
    text = _normalize_required_token("partition.value", raw_value)

    if partition_key == "ScheduleDateID":
        if _ISO_DATE_PATTERN.fullmatch(text):
            return f"SD-{text}"
        upper = text.upper()
        if _SCHEDULE_DATE_ID_PATTERN.fullmatch(upper):
            return f"SD-{upper[3:]}"
        raise PartitionRefValidationError(
            f"invalid ScheduleDateID value: {raw_value}"
        )

    # Keep non-ScheduleDateID partition codecs intentionally thin for this slice.
    return text


def _serialize_pointer_id(address: PointerAddress) -> str:
    parts = [
        "ptr",
        "v1",
        _encode_segment(address.tenant_id),
        _encode_segment(address.domain_id),
        _encode_segment(address.dataset_key),
        _encode_segment(address.partition_ref.key),
        _encode_segment(address.partition_ref.value),
    ]
    if address.stream_key is not None:
        parts.extend(["stream", _encode_segment(address.stream_key)])
    return "/".join(parts)


def _parse_pointer_id(pointer_id: str) -> PointerAddress:
    raw = _normalize_required_token("pointer_id", pointer_id)
    parts = raw.split("/")
    if len(parts) not in {7, 9}:
        raise PointerIdParseError(f"pointer_id has unsupported segment count: {pointer_id}")
    if parts[0] != "ptr" or parts[1] != "v1":
        raise PointerIdParseError(f"pointer_id must begin with ptr/v1: {pointer_id}")

    if len(parts) == 9 and parts[7] != "stream":
        raise PointerIdParseError(f"pointer_id stream marker missing: {pointer_id}")

    stream_key = _decode_segment(parts[8]) if len(parts) == 9 else None
    return PointerAddress(
        tenant_id=_decode_segment(parts[2]),
        domain_id=_decode_segment(parts[3]),
        dataset_key=_decode_segment(parts[4]),
        partition_ref=PartitionRef(
            key=_decode_segment(parts[5]),
            value=_decode_segment(parts[6]),
        ),
        stream_key=stream_key,
    )


def _encode_segment(value: str) -> str:
    return quote(value, safe="")


def _decode_segment(value: str) -> str:
    decoded = unquote(value)
    if not decoded:
        raise PointerIdParseError("pointer_id contains an empty identity segment")
    return decoded


__all__ = [
    "InvalidRegistryKindError",
    "LegacyPointerAmbiguityError",
    "LegacyPointerResolution",
    "LegacyPointerResolutionError",
    "PartitionRef",
    "PartitionRefValidationError",
    "PointerAddress",
    "PointerAddressError",
    "PointerId",
    "PointerIdParseError",
    "RegistryKind",
    "load_dataset_partition_index",
    "resolve_legacy_pointer_address",
]
