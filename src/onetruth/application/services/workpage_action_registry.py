from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from onetruth.application.services.workpage_descriptors import (
    WorkpageDescriptor,
    require_workpage_descriptor,
)
from onetruth.application.services.workpage_descriptor_registry import (
    WorkpageDescriptorRegistry,
)


ActionMode = Literal["open_latest_artifact", "open_or_create_artifact"]
ProjectionBuilder = Callable[
    [dict[str, Any], list[dict[str, Any]]],
    dict[str, Any],
]


@dataclass(frozen=True)
class HumanTaskWorkpageActionRule:
    workflow_id: str
    surfaces: frozenset[tuple[str, str]]
    workpage_kind: str
    latest_artifact_projection_key: str
    unavailable_reason: str
    action_mode: ActionMode


@dataclass(frozen=True)
class ApprovalWorkpageActionRule:
    workflow_id: str
    scope_refs: frozenset[str]
    workpage_kind: str
    latest_artifact_projection_key: str
    unavailable_reason: str
    action_mode: ActionMode


@dataclass(frozen=True)
class WorkpageActionPack:
    pack_name: str
    projection_builder: ProjectionBuilder | None = None
    human_task_rules: tuple[HumanTaskWorkpageActionRule, ...] = field(default_factory=tuple)
    approval_rules: tuple[ApprovalWorkpageActionRule, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkpageActionRegistry:
    packs: tuple[WorkpageActionPack, ...] = field(default_factory=tuple)
    descriptor_registry: WorkpageDescriptorRegistry | None = None

    @property
    def pack_names(self) -> tuple[str, ...]:
        return tuple(pack.pack_name for pack in self.packs)

    def with_pack(self, pack: WorkpageActionPack) -> WorkpageActionRegistry:
        return WorkpageActionRegistry(
            (*self.packs, pack),
            descriptor_registry=self.descriptor_registry,
        )

    def build_projection(
        self,
        *,
        workflow_run: dict[str, Any],
        artifact_versions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        projection = {
            "workflow_id": str(workflow_run.get("workflow_id") or ""),
            "workflow_run_id": str(workflow_run.get("workflow_run_id") or ""),
        }
        for pack in self.packs:
            if pack.projection_builder is None:
                continue
            projection.update(
                pack.projection_builder(
                    workflow_run=workflow_run,
                    artifact_versions=artifact_versions,
                )
            )
        return projection

    def project_human_task_actions(
        self,
        *,
        task: dict[str, Any],
        workflow_run: dict[str, Any],
        workpage_projection: dict[str, Any],
    ) -> list[dict[str, Any]]:
        workflow_id = str(workflow_run.get("workflow_id") or "")
        surface = (str(task.get("stage_id") or ""), str(task.get("task_kind") or ""))
        workflow_run_id = str(task["workflow_run_id"])
        subject_id = str(task["human_task_id"])
        actions: list[dict[str, Any]] = []
        for rule in self._human_task_rules():
            if rule.workflow_id != workflow_id or surface not in rule.surfaces:
                continue
            actions.append(
                _project_rule_action(
                    workpage_kind=rule.workpage_kind,
                    action_mode=rule.action_mode,
                    workflow_run_id=workflow_run_id,
                    subject_kind="human_task",
                    subject_id=subject_id,
                    latest_artifact=workpage_projection.get(rule.latest_artifact_projection_key),
                    unavailable_reason=rule.unavailable_reason,
                    descriptor_registry=self.descriptor_registry,
                )
            )
        return actions

    def project_approval_actions(
        self,
        *,
        approval: dict[str, Any],
        workflow_run: dict[str, Any],
        workpage_projection: dict[str, Any],
    ) -> list[dict[str, Any]]:
        workflow_id = str(workflow_run.get("workflow_id") or "")
        scope_ref = str(approval.get("scope_ref") or "")
        workflow_run_id = str(approval["workflow_run_id"])
        subject_id = str(approval["approval_id"])
        actions: list[dict[str, Any]] = []
        for rule in self._approval_rules():
            if rule.workflow_id != workflow_id or scope_ref not in rule.scope_refs:
                continue
            actions.append(
                _project_rule_action(
                    workpage_kind=rule.workpage_kind,
                    action_mode=rule.action_mode,
                    workflow_run_id=workflow_run_id,
                    subject_kind="approval",
                    subject_id=subject_id,
                    latest_artifact=workpage_projection.get(rule.latest_artifact_projection_key),
                    unavailable_reason=rule.unavailable_reason,
                    descriptor_registry=self.descriptor_registry,
                )
            )
        return actions

    def supports_human_task_subject(
        self,
        *,
        workflow_id: str,
        workpage_kind: str,
        stage_id: str,
        task_kind: str,
    ) -> bool:
        surface = (stage_id, task_kind)
        return any(
            rule.workflow_id == workflow_id
            and rule.workpage_kind == workpage_kind
            and surface in rule.surfaces
            for rule in self._human_task_rules()
        )

    def supports_approval_subject(
        self,
        *,
        workflow_id: str,
        workpage_kind: str,
        scope_kind: str,
        scope_ref: str,
    ) -> bool:
        if scope_kind != "stage":
            return False
        return any(
            rule.workflow_id == workflow_id
            and rule.workpage_kind == workpage_kind
            and scope_ref in rule.scope_refs
            for rule in self._approval_rules()
        )

    def _human_task_rules(self) -> tuple[HumanTaskWorkpageActionRule, ...]:
        rules: list[HumanTaskWorkpageActionRule] = []
        for pack in self.packs:
            rules.extend(pack.human_task_rules)
        return tuple(rules)

    def _approval_rules(self) -> tuple[ApprovalWorkpageActionRule, ...]:
        rules: list[ApprovalWorkpageActionRule] = []
        for pack in self.packs:
            rules.extend(pack.approval_rules)
        return tuple(rules)


def _project_rule_action(
    *,
    workpage_kind: str,
    action_mode: ActionMode,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
    latest_artifact: Any,
    unavailable_reason: str,
    descriptor_registry: WorkpageDescriptorRegistry | None,
) -> dict[str, Any]:
    descriptor = (
        descriptor_registry.require_descriptor(workpage_kind)
        if descriptor_registry is not None
        else require_workpage_descriptor(workpage_kind)
    )
    if action_mode == "open_or_create_artifact":
        return _open_or_create_action(
            descriptor=descriptor,
            workflow_run_id=workflow_run_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            latest_artifact=latest_artifact,
            unavailable_reason=unavailable_reason,
        )
    return _open_latest_artifact_action(
        descriptor=descriptor,
        workflow_run_id=workflow_run_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
        latest_artifact=latest_artifact,
        unavailable_reason=unavailable_reason,
    )


def _open_latest_artifact_action(
    *,
    descriptor: WorkpageDescriptor,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
    latest_artifact: Any,
    unavailable_reason: str,
) -> dict[str, Any]:
    route: str | None = None
    state = "unavailable"
    disabled_reason = unavailable_reason
    artifact_version_id = None
    if isinstance(latest_artifact, dict):
        artifact_version_id = str(latest_artifact.get("artifact_version_id") or "")
        if artifact_version_id:
            route = descriptor.frontend_artifact_route_builder(
                workflow_run_id,
                artifact_version_id,
            )
            state = "available"
            disabled_reason = None
    return _workpage_action_payload(
        descriptor=descriptor,
        action_id=str(descriptor.open_action_id or ""),
        label=str(descriptor.open_action_label or ""),
        presentation="open_route",
        state=state,
        route=route,
        create_path=None,
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id or None,
        subject_kind=subject_kind,
        subject_id=subject_id,
        disabled_reason=disabled_reason,
    )


def _open_or_create_action(
    *,
    descriptor: WorkpageDescriptor,
    workflow_run_id: str,
    subject_kind: str,
    subject_id: str,
    latest_artifact: Any,
    unavailable_reason: str,
) -> dict[str, Any]:
    if isinstance(latest_artifact, dict):
        artifact_version_id = str(latest_artifact.get("artifact_version_id") or "")
        if artifact_version_id:
            return _workpage_action_payload(
                descriptor=descriptor,
                action_id=str(descriptor.open_action_id or ""),
                label=str(descriptor.open_action_label or ""),
                presentation="open_route",
                state="available",
                route=descriptor.frontend_artifact_route_builder(
                    workflow_run_id,
                    artifact_version_id,
                ),
                create_path=None,
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
                subject_kind=subject_kind,
                subject_id=subject_id,
                disabled_reason=None,
            )

    create_path = (
        descriptor.create_path_builder(workflow_run_id)
        if descriptor.create_path_builder is not None
        else None
    )
    return _workpage_action_payload(
        descriptor=descriptor,
        action_id=str(descriptor.create_action_id or ""),
        label=str(descriptor.create_action_label or ""),
        presentation="create_then_open",
        state="available" if create_path else "unavailable",
        route=None,
        create_path=create_path,
        workflow_run_id=workflow_run_id,
        artifact_version_id=None,
        subject_kind=subject_kind,
        subject_id=subject_id,
        disabled_reason=None if create_path else unavailable_reason,
    )


def _workpage_action_payload(
    *,
    descriptor: WorkpageDescriptor,
    action_id: str,
    label: str,
    presentation: str,
    state: str,
    route: str | None,
    create_path: str | None,
    workflow_run_id: str,
    artifact_version_id: str | None,
    subject_kind: str,
    subject_id: str,
    disabled_reason: str | None,
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "workpage_kind": descriptor.kind,
        "label": label,
        "presentation": presentation,
        "state": state,
        "route": route,
        "create_path": create_path,
        "subject_context": {
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "workflow_run_id": workflow_run_id,
        },
        "link_policy": {
            "create_relation_kind": descriptor.create_relation_kind,
            "submit_relation_kind": descriptor.submit_relation_kind,
        },
        "action_ref": _build_workpage_action_ref(
            action_id=action_id,
            workpage_kind=descriptor.kind,
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
        ),
        "disabled_reason": disabled_reason,
    }


def _build_workpage_action_ref(
    *,
    action_id: str,
    workpage_kind: str,
    workflow_run_id: str,
    artifact_version_id: str | None,
    subject_kind: str,
    subject_id: str,
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "workpage_kind": workpage_kind,
        "workflow_run_id": workflow_run_id,
        "artifact_version_id": artifact_version_id,
        "subject": {
            "subject_kind": subject_kind,
            "subject_id": subject_id,
        },
    }
