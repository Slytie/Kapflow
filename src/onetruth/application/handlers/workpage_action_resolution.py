from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from onetruth.application.handlers._shared.artifact_effects import (
    _validate_artifact_link_subject,
)
from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.services.workpage_action_registry_defaults import (
    DEFAULT_WORKPAGE_ACTION_REGISTRY,
)
from onetruth.application.services.workpage_action_registry import WorkpageActionRegistry
from onetruth.application.services.workpage_descriptor_registry import (
    WorkpageDescriptorRegistry,
)
from onetruth.application.services.workpage_descriptor_registry_defaults import (
    DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY,
)
from onetruth.application.services.workpage_descriptors import (
    WorkpageDescriptor,
)
from onetruth.infrastructure.repositories.approvals import get_approval
from onetruth.infrastructure.repositories.human_tasks import get_human_task
from onetruth.infrastructure.repositories.task_runs import get_task_run

WORKPAGE_SUBJECT_LINK_FIELDS = frozenset({"subject_kind", "subject_id"})
WORKPAGE_ACTION_REF_FIELDS = frozenset(
    {"action_id", "workpage_kind", "workflow_run_id", "artifact_version_id", "subject"}
)
WORKPAGE_ACTION_REF_SUBJECT_FIELDS = frozenset({"subject_kind", "subject_id"})


def _resolve_workpage_action_subject(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str,
    workpage_kind: str,
    flow_kind: str,
    artifact_version_id: str | None,
    raw_action_ref: Any,
    raw_subject_link: Any,
    expected_action_id: str | None = None,
    action_registry: WorkpageActionRegistry | None = None,
    descriptor_registry: WorkpageDescriptorRegistry | None = None,
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    if raw_action_ref is not None and raw_subject_link is not None:
        raise CommandError(
            code="invalid_payload",
            message="action_ref and subject_link may not both be supplied",
            details={"field_names": ["action_ref", "subject_link"]},
        )
    if raw_action_ref is not None:
        action_ref = _resolve_workpage_action_ref(
            connection,
            workflow_run_id=workflow_run_id,
            workflow_id=workflow_id,
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            artifact_version_id=artifact_version_id,
            raw_action_ref=raw_action_ref,
            expected_action_id=expected_action_id,
            action_registry=action_registry,
            descriptor_registry=descriptor_registry,
        )
        subject = action_ref.get("subject")
        if isinstance(subject, Mapping):
            return {
                "subject_kind": str(subject["subject_kind"]),
                "subject_id": str(subject["subject_id"]),
            }, action_ref
        return None, action_ref
    subject_link = _resolve_workpage_subject_link(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=workflow_id,
        workpage_kind=workpage_kind,
        flow_kind=flow_kind,
        raw_subject_link=raw_subject_link,
        action_registry=action_registry,
        descriptor_registry=descriptor_registry,
    )
    return subject_link, None

def _resolve_workpage_action_ref(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str,
    workpage_kind: str,
    flow_kind: str,
    artifact_version_id: str | None,
    raw_action_ref: Any,
    expected_action_id: str | None = None,
    action_registry: WorkpageActionRegistry | None = None,
    descriptor_registry: WorkpageDescriptorRegistry | None = None,
) -> dict[str, Any]:
    if not isinstance(raw_action_ref, Mapping):
        raise _invalid_workpage_action_ref(
            message="action_ref must be an object",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
        )
    extra_fields = sorted(set(raw_action_ref.keys()).difference(WORKPAGE_ACTION_REF_FIELDS))
    if extra_fields:
        raise _invalid_workpage_action_ref(
            message="action_ref contains unsupported fields",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            extra_fields=extra_fields,
        )
    action_id = _require_non_empty_string(raw_action_ref.get("action_id"), field_name="action_ref.action_id")
    action_workpage_kind = _require_non_empty_string(
        raw_action_ref.get("workpage_kind"),
        field_name="action_ref.workpage_kind",
    )
    action_workflow_run_id = _require_non_empty_string(
        raw_action_ref.get("workflow_run_id"),
        field_name="action_ref.workflow_run_id",
    )
    if action_workpage_kind != workpage_kind:
        raise _invalid_workpage_action_ref(
            message="action_ref workpage_kind does not match the requested workpage flow",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            action_workpage_kind=action_workpage_kind,
        )
    if action_workflow_run_id != workflow_run_id:
        raise _invalid_workpage_action_ref(
            message="action_ref workflow_run_id does not match the requested workpage flow",
            workflow_run_id=workflow_run_id,
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            action_workflow_run_id=action_workflow_run_id,
        )
    descriptor = _active_descriptor_registry(descriptor_registry).require_descriptor(
        workpage_kind
    )
    if descriptor.workflow_id != workflow_id:
        raise _invalid_workpage_action_ref(
            message="action_ref is unsupported for this workflow/workpage pair",
            workflow_id=workflow_id,
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
        )
    resolved_expected_action_id = (
        str(expected_action_id)
        if expected_action_id is not None
        else _expected_action_id_for_workpage_flow(descriptor, flow_kind=flow_kind)
    )
    if action_id != resolved_expected_action_id:
        raise _invalid_workpage_action_ref(
            message="action_ref action_id does not match the requested workpage flow",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            action_id=action_id,
            expected_action_id=resolved_expected_action_id,
        )
    normalized_artifact_version_id = _normalize_action_ref_artifact_version_id(
        raw_action_ref.get("artifact_version_id")
    )
    if flow_kind == "create":
        if normalized_artifact_version_id is not None:
            raise _invalid_workpage_action_ref(
                message="create action_ref must not include artifact_version_id",
                workpage_kind=workpage_kind,
                flow_kind=flow_kind,
                artifact_version_id=normalized_artifact_version_id,
            )
    elif normalized_artifact_version_id != artifact_version_id:
        raise _invalid_workpage_action_ref(
            message="submit action_ref artifact_version_id does not match the requested artifact",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            artifact_version_id=artifact_version_id,
            action_artifact_version_id=normalized_artifact_version_id,
        )
    subject = _normalize_action_ref_subject(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=workflow_id,
        workpage_kind=workpage_kind,
        flow_kind=flow_kind,
        raw_subject=raw_action_ref.get("subject"),
        action_registry=action_registry,
        descriptor_registry=descriptor_registry,
    )
    return {
        "action_id": action_id,
        "workpage_kind": workpage_kind,
        "workflow_run_id": workflow_run_id,
        "artifact_version_id": normalized_artifact_version_id,
        "subject": subject,
    }

def _expected_action_id_for_workpage_flow(
    descriptor: WorkpageDescriptor,
    *,
    flow_kind: str,
) -> str:
    if flow_kind == "create":
        action_id = descriptor.create_action_id
    elif flow_kind == "submit":
        action_id = descriptor.submit_action_id
    else:
        action_id = None
    if action_id:
        return str(action_id)
    raise _invalid_workpage_action_ref(
        message="action_ref is unsupported for this workpage flow",
        workpage_kind=descriptor.kind,
        workflow_id=descriptor.workflow_id,
        flow_kind=flow_kind,
    )

def _normalize_action_ref_artifact_version_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

def _normalize_action_ref_subject(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str,
    workpage_kind: str,
    flow_kind: str,
    raw_subject: Any,
    action_registry: WorkpageActionRegistry | None = None,
    descriptor_registry: WorkpageDescriptorRegistry | None = None,
) -> dict[str, str] | None:
    if raw_subject is None:
        return None
    if not isinstance(raw_subject, Mapping):
        raise _invalid_workpage_action_ref(
            message="action_ref subject must be an object or null",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
        )
    extra_fields = sorted(set(raw_subject.keys()).difference(WORKPAGE_ACTION_REF_SUBJECT_FIELDS))
    if extra_fields:
        raise _invalid_workpage_action_ref(
            message="action_ref subject contains unsupported fields",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            extra_fields=extra_fields,
        )
    subject_kind = _require_non_empty_string(
        raw_subject.get("subject_kind"),
        field_name="action_ref.subject.subject_kind",
    )
    subject_id = _require_non_empty_string(
        raw_subject.get("subject_id"),
        field_name="action_ref.subject.subject_id",
    )
    subject = {"subject_kind": subject_kind, "subject_id": subject_id}
    _validate_workpage_subject(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=workflow_id,
        workpage_kind=workpage_kind,
        flow_kind=flow_kind,
        subject_link=subject,
        action_registry=action_registry,
        descriptor_registry=descriptor_registry,
    )
    return subject

def _resolve_workpage_subject_link(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str,
    workpage_kind: str,
    flow_kind: str,
    raw_subject_link: Any,
    action_registry: WorkpageActionRegistry | None = None,
    descriptor_registry: WorkpageDescriptorRegistry | None = None,
) -> dict[str, str] | None:
    if raw_subject_link is None:
        return None
    if not isinstance(raw_subject_link, Mapping):
        raise _invalid_workpage_subject_link(
            message="subject_link must be an object",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
        )
    extra_fields = sorted(set(raw_subject_link.keys()).difference(WORKPAGE_SUBJECT_LINK_FIELDS))
    if extra_fields:
        raise _invalid_workpage_subject_link(
            message="subject_link contains unsupported fields",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            extra_fields=extra_fields,
        )
    subject_kind = str(raw_subject_link.get("subject_kind") or "").strip()
    subject_id = str(raw_subject_link.get("subject_id") or "").strip()
    if not subject_kind or not subject_id:
        raise _invalid_workpage_subject_link(
            message="subject_link requires subject_kind and subject_id",
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
        )
    subject_link = {"subject_kind": subject_kind, "subject_id": subject_id}
    _validate_workpage_subject(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=workflow_id,
        workpage_kind=workpage_kind,
        flow_kind=flow_kind,
        subject_link=subject_link,
        action_registry=action_registry,
        descriptor_registry=descriptor_registry,
    )
    return subject_link

def _validate_workpage_subject(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str,
    workpage_kind: str,
    flow_kind: str,
    subject_link: Mapping[str, str],
    action_registry: WorkpageActionRegistry | None = None,
    descriptor_registry: WorkpageDescriptorRegistry | None = None,
) -> None:
    subject_kind = str(subject_link["subject_kind"])
    subject_id = str(subject_link["subject_id"])
    _validate_artifact_link_subject(
        connection,
        workflow_run_id=workflow_run_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
    )
    descriptor = _active_descriptor_registry(descriptor_registry).require_descriptor(
        workpage_kind
    )
    if flow_kind == "create" and descriptor.create_action_id is None:
        raise _invalid_workpage_subject_link(
            message="subject_link is unsupported for this workpage flow",
            workflow_id=workflow_id,
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            subject_kind=subject_kind,
            subject_id=subject_id,
        )
    if flow_kind == "submit" and descriptor.submit_action_id is None:
        raise _invalid_workpage_subject_link(
            message="subject_link is unsupported for this workpage flow",
            workflow_id=workflow_id,
            workpage_kind=workpage_kind,
            flow_kind=flow_kind,
            subject_kind=subject_kind,
            subject_id=subject_id,
        )
    if subject_kind == "human_task":
        _validate_human_task_workpage_subject_link(
            connection,
            workflow_run_id=workflow_run_id,
            workflow_id=workflow_id,
            workpage_kind=workpage_kind,
            subject_id=subject_id,
            action_registry=action_registry,
        )
        return
    if subject_kind == "approval":
        _validate_approval_workpage_subject_link(
            connection,
            workflow_run_id=workflow_run_id,
            workflow_id=workflow_id,
            workpage_kind=workpage_kind,
            subject_id=subject_id,
            action_registry=action_registry,
        )
        return
    raise _invalid_workpage_subject_link(
        message="unsupported subject_kind for workpage subject_link",
        workflow_id=workflow_id,
        workpage_kind=workpage_kind,
        flow_kind=flow_kind,
        subject_kind=subject_kind,
        subject_id=subject_id,
    )


def _validate_human_task_workpage_subject_link(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str,
    workpage_kind: str,
    subject_id: str,
    action_registry: WorkpageActionRegistry | None = None,
) -> None:
    human_task = get_human_task(connection, subject_id)
    if human_task is None:
        raise _invalid_workpage_subject_link(
            message="human task not found for workpage subject_link",
            workflow_run_id=workflow_run_id,
            subject_kind="human_task",
            subject_id=subject_id,
        )
    task_run = get_task_run(connection, str(human_task["task_run_id"]))
    if task_run is None:
        raise _invalid_workpage_subject_link(
            message="human task stage could not be resolved for workpage subject_link",
            workflow_run_id=workflow_run_id,
            subject_kind="human_task",
            subject_id=subject_id,
        )
    stage_id = str(task_run.get("stage_id") or "")
    task_kind = str(human_task.get("task_kind") or "")
    if _active_action_registry(action_registry).supports_human_task_subject(
        workflow_id=workflow_id,
        workpage_kind=workpage_kind,
        stage_id=stage_id,
        task_kind=task_kind,
    ):
        return
    raise _invalid_workpage_subject_link(
        message="human task is not a supported workpage surface",
        workflow_run_id=workflow_run_id,
        workflow_id=workflow_id,
        workpage_kind=workpage_kind,
        subject_kind="human_task",
        subject_id=subject_id,
        stage_id=stage_id,
        task_kind=task_kind,
    )


def _validate_approval_workpage_subject_link(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str,
    workpage_kind: str,
    subject_id: str,
    action_registry: WorkpageActionRegistry | None = None,
) -> None:
    approval = get_approval(connection, subject_id)
    if approval is None:
        raise _invalid_workpage_subject_link(
            message="approval not found for workpage subject_link",
            workflow_run_id=workflow_run_id,
            subject_kind="approval",
            subject_id=subject_id,
        )
    scope_kind = str(approval.get("scope_kind") or "")
    scope_ref = str(approval.get("scope_ref") or "")
    if _active_action_registry(action_registry).supports_approval_subject(
        workflow_id=workflow_id,
        workpage_kind=workpage_kind,
        scope_kind=scope_kind,
        scope_ref=scope_ref,
    ):
        return
    raise _invalid_workpage_subject_link(
        message="approval is not a supported workpage surface",
        workflow_run_id=workflow_run_id,
        workflow_id=workflow_id,
        workpage_kind=workpage_kind,
        subject_kind="approval",
        subject_id=subject_id,
        scope_kind=scope_kind,
        scope_ref=scope_ref,
    )


def _active_action_registry(
    registry: WorkpageActionRegistry | None,
) -> WorkpageActionRegistry:
    return DEFAULT_WORKPAGE_ACTION_REGISTRY if registry is None else registry


def _active_descriptor_registry(
    registry: WorkpageDescriptorRegistry | None,
) -> WorkpageDescriptorRegistry:
    return DEFAULT_WORKPAGE_DESCRIPTOR_REGISTRY if registry is None else registry

def _invalid_workpage_subject_link(
    *,
    message: str,
    **details: Any,
) -> CommandError:
    return CommandError(
        code="invalid_workpage_subject_link",
        message=message,
        details=details,
    )

def _invalid_workpage_action_ref(
    *,
    message: str,
    **details: Any,
) -> CommandError:
    return CommandError(
        code="invalid_workpage_action_ref",
        message=message,
        details=details,
    )

def _require_non_empty_string(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise CommandError(
        code="invalid_payload",
        message=f"{field_name} is required",
        details={"field_name": field_name},
    )
