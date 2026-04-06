from __future__ import annotations

from typing import Any

from onetruth.application.services.logistics_workpages import (
    build_workpage_action_ref,
    latest_compatible_eod_draft_artifact,
    latest_schedule_draft_artifact,
)
from onetruth.application.services.workpage_descriptors import (
    EOD_WORKPAGE_KIND,
    SCHEDULE_WORKPAGE_KIND,
    WorkpageDescriptor,
    get_workpage_descriptor,
)


SCHEDULE_WORKPAGE_SUPPORTED_TASK_SURFACES = frozenset(
    {
        ("Stage04", "work_item"),
        ("Stage05", "information_request"),
        ("Stage05", "final_review"),
    }
)
SCHEDULE_WORKPAGE_SUPPORTED_APPROVAL_SCOPE_REFS = frozenset({"Stage06"})
EOD_WORKPAGE_SUPPORTED_TASK_SURFACES = frozenset({("Stage04", "final_packet_review")})
EOD_WORKPAGE_SUPPORTED_APPROVAL_SCOPE_REFS = frozenset({"Stage04"})


def build_workspace_workpage_projection(
    *,
    workflow_run: dict[str, Any],
    artifact_versions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "workflow_id": str(workflow_run.get("workflow_id") or ""),
        "workflow_run_id": str(workflow_run.get("workflow_run_id") or ""),
        "latest_schedule_draft": latest_schedule_draft_artifact(artifact_versions),
        "latest_eod_draft": latest_compatible_eod_draft_artifact(artifact_versions),
    }


def project_human_task_workpage_actions(
    *,
    task: dict[str, Any],
    workflow_run: dict[str, Any],
    workpage_projection: dict[str, Any],
) -> list[dict[str, Any]]:
    workflow_id = str(workflow_run.get("workflow_id") or "")
    surface = (str(task.get("stage_id") or ""), str(task.get("task_kind") or ""))
    if workflow_id == "weekly_schedule_planning.v1":
        if surface not in SCHEDULE_WORKPAGE_SUPPORTED_TASK_SURFACES:
            return []
        return [
            _open_latest_draft_action(
                descriptor=_require_descriptor(SCHEDULE_WORKPAGE_KIND),
                workflow_run_id=str(task["workflow_run_id"]),
                subject_kind="human_task",
                subject_id=str(task["human_task_id"]),
                latest_artifact=workpage_projection.get("latest_schedule_draft"),
                unavailable_reason="schedule_draft_unavailable",
            )
        ]
    if workflow_id == "dispatch_reporting.v1" and surface in EOD_WORKPAGE_SUPPORTED_TASK_SURFACES:
        return [
            _open_or_create_action(
                descriptor=_require_descriptor(EOD_WORKPAGE_KIND),
                workflow_run_id=str(task["workflow_run_id"]),
                subject_kind="human_task",
                subject_id=str(task["human_task_id"]),
                latest_artifact=workpage_projection.get("latest_eod_draft"),
                unavailable_reason="eod_draft_unavailable",
            )
        ]
    return []


def project_approval_workpage_actions(
    *,
    approval: dict[str, Any],
    workflow_run: dict[str, Any],
    workpage_projection: dict[str, Any],
) -> list[dict[str, Any]]:
    workflow_id = str(workflow_run.get("workflow_id") or "")
    scope_ref = str(approval.get("scope_ref") or "")
    workflow_run_id = str(approval["workflow_run_id"])
    approval_id = str(approval["approval_id"])
    if workflow_id == "weekly_schedule_planning.v1" and scope_ref in SCHEDULE_WORKPAGE_SUPPORTED_APPROVAL_SCOPE_REFS:
        return [
            _open_latest_draft_action(
                descriptor=_require_descriptor(SCHEDULE_WORKPAGE_KIND),
                workflow_run_id=workflow_run_id,
                subject_kind="approval",
                subject_id=approval_id,
                latest_artifact=workpage_projection.get("latest_schedule_draft"),
                unavailable_reason="schedule_draft_unavailable",
            )
        ]
    if workflow_id == "dispatch_reporting.v1" and scope_ref in EOD_WORKPAGE_SUPPORTED_APPROVAL_SCOPE_REFS:
        return [
            _open_or_create_action(
                descriptor=_require_descriptor(EOD_WORKPAGE_KIND),
                workflow_run_id=workflow_run_id,
                subject_kind="approval",
                subject_id=approval_id,
                latest_artifact=workpage_projection.get("latest_eod_draft"),
                unavailable_reason="eod_draft_unavailable",
            )
        ]
    return []


def project_flag_workpage_actions(
    *,
    flag: dict[str, Any],
    workpage_projection: dict[str, Any],
) -> list[dict[str, Any]]:
    del flag, workpage_projection
    return []


def _open_latest_draft_action(
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
    return {
        "action_id": str(descriptor.open_action_id or ""),
        "workpage_kind": descriptor.kind,
        "label": str(descriptor.open_action_label or ""),
        "presentation": "open_route",
        "state": state,
        "route": route,
        "create_path": None,
        "subject_context": {
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "workflow_run_id": workflow_run_id,
        },
        "link_policy": {
            "create_relation_kind": descriptor.create_relation_kind,
            "submit_relation_kind": descriptor.submit_relation_kind,
        },
        "action_ref": build_workpage_action_ref(
            action_id=str(descriptor.open_action_id or ""),
            workpage_kind=descriptor.kind,
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id or None,
            subject_kind=subject_kind,
            subject_id=subject_id,
        ),
        "disabled_reason": disabled_reason,
    }


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
            return {
                "action_id": str(descriptor.open_action_id or ""),
                "workpage_kind": descriptor.kind,
                "label": str(descriptor.open_action_label or ""),
                "presentation": "open_route",
                "state": "available",
                "route": descriptor.frontend_artifact_route_builder(
                    workflow_run_id,
                    artifact_version_id,
                ),
                "create_path": None,
                "subject_context": {
                    "subject_kind": subject_kind,
                    "subject_id": subject_id,
                    "workflow_run_id": workflow_run_id,
                },
                "link_policy": {
                    "create_relation_kind": descriptor.create_relation_kind,
                    "submit_relation_kind": descriptor.submit_relation_kind,
                },
                "action_ref": build_workpage_action_ref(
                    action_id=str(descriptor.open_action_id or ""),
                    workpage_kind=descriptor.kind,
                    workflow_run_id=workflow_run_id,
                    artifact_version_id=artifact_version_id,
                    subject_kind=subject_kind,
                    subject_id=subject_id,
                ),
                "disabled_reason": None,
            }
    create_path = (
        descriptor.create_path_builder(workflow_run_id)
        if descriptor.create_path_builder is not None
        else None
    )
    return {
        "action_id": str(descriptor.create_action_id or ""),
        "workpage_kind": descriptor.kind,
        "label": str(descriptor.create_action_label or ""),
        "presentation": "create_then_open",
        "state": "available" if create_path else "unavailable",
        "route": None,
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
        "action_ref": build_workpage_action_ref(
            action_id=str(descriptor.create_action_id or ""),
            workpage_kind=descriptor.kind,
            workflow_run_id=workflow_run_id,
            artifact_version_id=None,
            subject_kind=subject_kind,
            subject_id=subject_id,
        ),
        "disabled_reason": None if create_path else unavailable_reason,
    }


def _require_descriptor(workpage_kind: str) -> WorkpageDescriptor:
    descriptor = get_workpage_descriptor(workpage_kind)
    if descriptor is None:
        raise KeyError(f"unknown workpage kind: {workpage_kind}")
    return descriptor
