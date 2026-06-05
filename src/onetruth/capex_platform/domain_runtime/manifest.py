from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml


DomainReadiness = Literal["ready", "incubation", "disabled"]


@dataclass(frozen=True)
class DomainSourceRef:
    kind: str
    path: str

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> DomainSourceRef:
        return cls(kind=str(row["kind"]), path=str(row["path"]))

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "path": self.path}


@dataclass(frozen=True)
class DomainWorkflowRef:
    workflow_id: str
    module_id: str
    pack_path: str
    partition_kind: str
    family_status: str
    readiness: DomainReadiness

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> DomainWorkflowRef:
        return cls(
            workflow_id=str(row["workflow_id"]),
            module_id=str(row["module_id"]),
            pack_path=str(row["pack_path"]),
            partition_kind=str(row["partition_kind"]),
            family_status=str(row["family_status"]),
            readiness=_readiness(row["readiness"]),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "workflow_id": self.workflow_id,
            "module_id": self.module_id,
            "pack_path": self.pack_path,
            "partition_kind": self.partition_kind,
            "family_status": self.family_status,
            "readiness": self.readiness,
        }


@dataclass(frozen=True)
class DomainActionSubject:
    subject_kind: str
    workflow_id: str
    stage_id: str | None = None
    task_kind: str | None = None
    scope_kind: str | None = None
    scope_ref: str | None = None

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> DomainActionSubject:
        return cls(
            subject_kind=str(row["subject_kind"]),
            workflow_id=str(row["workflow_id"]),
            stage_id=_optional_str(row.get("stage_id")),
            task_kind=_optional_str(row.get("task_kind")),
            scope_kind=_optional_str(row.get("scope_kind")),
            scope_ref=_optional_str(row.get("scope_ref")),
        )

    def to_dict(self) -> dict[str, str]:
        row = {
            "subject_kind": self.subject_kind,
            "workflow_id": self.workflow_id,
        }
        if self.stage_id is not None:
            row["stage_id"] = self.stage_id
        if self.task_kind is not None:
            row["task_kind"] = self.task_kind
        if self.scope_kind is not None:
            row["scope_kind"] = self.scope_kind
        if self.scope_ref is not None:
            row["scope_ref"] = self.scope_ref
        return row


@dataclass(frozen=True)
class DomainWorkpageRef:
    kind: str
    workflow_id: str
    descriptor_pack_ref: str
    action_pack_ref: str | None
    run_enabled: bool
    artifact_enabled: bool
    submit_enabled: bool
    artifact_kinds: tuple[str, ...] = field(default_factory=tuple)
    action_subjects: tuple[DomainActionSubject, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> DomainWorkpageRef:
        return cls(
            kind=str(row["kind"]),
            workflow_id=str(row["workflow_id"]),
            descriptor_pack_ref=str(row["descriptor_pack_ref"]),
            action_pack_ref=_optional_str(row.get("action_pack_ref")),
            run_enabled=bool(row["run_enabled"]),
            artifact_enabled=bool(row["artifact_enabled"]),
            submit_enabled=bool(row["submit_enabled"]),
            artifact_kinds=tuple(str(value) for value in row.get("artifact_kinds", ())),
            action_subjects=tuple(
                DomainActionSubject.from_mapping(subject)
                for subject in row.get("action_subjects", ())
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "workflow_id": self.workflow_id,
            "descriptor_pack_ref": self.descriptor_pack_ref,
            "action_pack_ref": self.action_pack_ref,
            "run_enabled": self.run_enabled,
            "artifact_enabled": self.artifact_enabled,
            "submit_enabled": self.submit_enabled,
            "artifact_kinds": list(self.artifact_kinds),
            "action_subjects": [
                subject.to_dict() for subject in self.action_subjects
            ],
        }


@dataclass(frozen=True)
class DomainSideEffectRef:
    kind: str
    effect_id: str
    source_ref: str
    workflow_id: str | None = None
    status: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> DomainSideEffectRef:
        return cls(
            kind=str(row["kind"]),
            effect_id=str(row["effect_id"]),
            source_ref=str(row["source_ref"]),
            workflow_id=_optional_str(row.get("workflow_id")),
            status=_optional_str(row.get("status")),
            details=dict(row.get("details") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "kind": self.kind,
            "effect_id": self.effect_id,
            "source_ref": self.source_ref,
            "details": dict(self.details),
        }
        if self.workflow_id is not None:
            row["workflow_id"] = self.workflow_id
        if self.status is not None:
            row["status"] = self.status
        return row


@dataclass(frozen=True)
class DomainReadinessPrerequisite:
    prerequisite_id: str
    description: str
    status: str
    task_refs: tuple[str, ...] = field(default_factory=tuple)
    source_refs: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(
        cls, row: dict[str, Any]
    ) -> DomainReadinessPrerequisite:
        return cls(
            prerequisite_id=str(row["prerequisite_id"]),
            description=str(row["description"]),
            status=str(row["status"]),
            task_refs=tuple(str(value) for value in row.get("task_refs", ())),
            source_refs=tuple(str(value) for value in row.get("source_refs", ())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "prerequisite_id": self.prerequisite_id,
            "description": self.description,
            "status": self.status,
            "task_refs": list(self.task_refs),
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class DomainDisabledCapability:
    capability_id: str
    description: str
    disabled_reason: str
    owner_task_refs: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(
        cls, row: dict[str, Any]
    ) -> DomainDisabledCapability:
        return cls(
            capability_id=str(row["capability_id"]),
            description=str(row["description"]),
            disabled_reason=str(row["disabled_reason"]),
            owner_task_refs=tuple(
                str(value) for value in row.get("owner_task_refs", ())
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "description": self.description,
            "disabled_reason": self.disabled_reason,
            "owner_task_refs": list(self.owner_task_refs),
        }


@dataclass(frozen=True)
class DomainManifest:
    schema_version: str
    domain_id: str
    display_name: str
    readiness: DomainReadiness
    source_refs: tuple[DomainSourceRef, ...] = field(default_factory=tuple)
    workflows: tuple[DomainWorkflowRef, ...] = field(default_factory=tuple)
    workpages: tuple[DomainWorkpageRef, ...] = field(default_factory=tuple)
    side_effects: tuple[DomainSideEffectRef, ...] = field(default_factory=tuple)
    readiness_prerequisites: tuple[DomainReadinessPrerequisite, ...] = field(
        default_factory=tuple
    )
    disabled_capabilities: tuple[DomainDisabledCapability, ...] = field(
        default_factory=tuple
    )

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> DomainManifest:
        return cls(
            schema_version=str(mapping["schema_version"]),
            domain_id=str(mapping["domain_id"]),
            display_name=str(mapping["display_name"]),
            readiness=_readiness(mapping["readiness"]),
            source_refs=tuple(
                DomainSourceRef.from_mapping(row)
                for row in mapping.get("source_refs", ())
            ),
            workflows=tuple(
                DomainWorkflowRef.from_mapping(row)
                for row in mapping.get("workflows", ())
            ),
            workpages=tuple(
                DomainWorkpageRef.from_mapping(row)
                for row in mapping.get("workpages", ())
            ),
            side_effects=tuple(
                DomainSideEffectRef.from_mapping(row)
                for row in mapping.get("side_effects", ())
            ),
            readiness_prerequisites=tuple(
                DomainReadinessPrerequisite.from_mapping(row)
                for row in mapping.get("readiness_prerequisites", ())
            ),
            disabled_capabilities=tuple(
                DomainDisabledCapability.from_mapping(row)
                for row in mapping.get("disabled_capabilities", ())
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "domain_id": self.domain_id,
            "display_name": self.display_name,
            "readiness": self.readiness,
            "source_refs": [source_ref.to_dict() for source_ref in self.source_refs],
            "workflows": [workflow.to_dict() for workflow in self.workflows],
            "workpages": [workpage.to_dict() for workpage in self.workpages],
            "side_effects": [side_effect.to_dict() for side_effect in self.side_effects],
            "readiness_prerequisites": [
                prerequisite.to_dict()
                for prerequisite in self.readiness_prerequisites
            ],
            "disabled_capabilities": [
                capability.to_dict() for capability in self.disabled_capabilities
            ],
        }


def load_domain_manifest(path: str | Path) -> DomainManifest:
    manifest_path = Path(path)
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"domain manifest must be a mapping: {manifest_path}")
    return DomainManifest.from_mapping(payload)


def _readiness(value: Any) -> DomainReadiness:
    normalized = str(value)
    if normalized not in {"ready", "incubation", "disabled"}:
        raise ValueError(f"unsupported domain readiness: {normalized}")
    return normalized  # type: ignore[return-value]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
