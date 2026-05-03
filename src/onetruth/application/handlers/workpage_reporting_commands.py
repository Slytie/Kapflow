from __future__ import annotations

from datetime import date
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Sequence
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _command_receipt_payload,
    _event_envelope,
    _execute_with_command_receipt,
    _normalize_actor_roles,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
)
from onetruth.application.handlers.workpage_action_resolution import (
    _require_non_empty_string,
    _resolve_workpage_action_subject,
)
from onetruth.application.handlers.workpage_command_support import (
    EOD_DEFAULT_DSP_NAME,
    EOD_DEFAULT_SERVICE_DATE,
    EOD_DEFAULT_STATION_CODE,
    EOD_TEMPLATE_ID,
    _artifact_links_for_workpage_subject,
    _assert_artifact_not_already_superseded,
    _canonical_eod_ui_route,
    _create_workbook_artifact_version,
    _draft_file_name,
    _load_eod_template_record,
    _metadata_string,
    _read_workbook_bytes,
    _require_eod_artifact_version,
    _require_projection_rows,
    _xlsx_media_type,
)
from onetruth.application.services.dispatch_reporting_workbook import (
    DATASET_KEY as EOD_DATASET_KEY,
    WORKFLOW_ID as EOD_WORKFLOW_ID,
    materialize_upd_draft_workbook,
    project_upd_draft_workbook,
)
from onetruth.application.services.workpage_descriptors import EOD_WORKPAGE_KIND
from onetruth.application.services.template_registry import TemplateRecord
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.human_tasks import (
    create_human_task,
    get_human_task,
    list_human_tasks_for_workflow_run,
)
from onetruth.infrastructure.repositories.task_runs import create_task_run, get_task_run
from onetruth.infrastructure.repositories.workflow_runs import (
    create_workflow_run,
    get_workflow_run,
    list_workflow_runs,
)


_EOD_INTAKE_STAGE_ID = "Stage01"
_EOD_INTAKE_TASK_KIND = "eos_input_intake"
_EOD_INTAKE_OWNER_ROLE = "dispatch_supervisor"


def ensure_workflow_run_eod_intake_task_command(
    connection: sqlite3.Connection,
    workflow_run: Mapping[str, Any],
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    source_workflow_run_id = _require_non_empty_string(
        workflow_run.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    requested_service_date = _resolve_eod_intake_service_date(
        workflow_run=workflow_run,
        payload=payload,
    )
    tenant_id = _require_non_empty_string(payload.get("tenant_id"), field_name="tenant_id")
    domain_id = _require_non_empty_string(payload.get("domain_id"), field_name="domain_id")
    actor_id = _require_non_empty_string(payload.get("actor_id"), field_name="actor_id")
    actor_type = _require_non_empty_string(payload.get("actor_type"), field_name="actor_type")
    actor_roles = _normalize_actor_roles(payload.get("actor_roles"), required=True)

    receipt = _prepare_command_receipt(
        command_name="workpages.eod-intake.ensure",
        payload={
            **payload,
            "workflow_run_id": source_workflow_run_id,
            "workflow_id": EOD_WORKFLOW_ID,
            "workpage_id": EOD_WORKPAGE_KIND,
            "service_date": requested_service_date,
        },
        fingerprint_payload={
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "workflow_run_id": source_workflow_run_id,
            "workflow_id": EOD_WORKFLOW_ID,
            "workpage_id": EOD_WORKPAGE_KIND,
            "service_date": requested_service_date,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "actor_roles": list(actor_roles),
        },
        tenant_id=tenant_id,
        domain_id=domain_id,
        workflow_run_id=source_workflow_run_id,
        idempotency_required=True,
    )

    def _operation() -> dict[str, Any]:
        target_workflow_run, created_workflow_run = _resolve_target_eod_workflow_run(
            connection,
            workflow_run=workflow_run,
            service_date=requested_service_date,
        )
        target_workflow_run_id = _require_non_empty_string(
            target_workflow_run.get("workflow_run_id"),
            field_name="workflow_run_id",
        )
        reusable = _reusable_eod_intake_task(
            connection,
            workflow_run_id=target_workflow_run_id,
            actor_id=actor_id,
            actor_type=actor_type,
        )
        if reusable is not None:
            return {
                "intake_task": _eod_intake_task_payload(
                    task_run=reusable["task_run"],
                    human_task=reusable["human_task"],
                    created=False,
                    service_date=requested_service_date,
                    target_workflow_run_id=target_workflow_run_id,
                    target_route=_canonical_eod_landing_route(
                        workflow_run_id=target_workflow_run_id
                    ),
                    created_workflow_run=created_workflow_run,
                )
            }

        generation = _next_eod_intake_generation(
            connection,
            workflow_run_id=target_workflow_run_id,
        )
        activation_key = _next_eod_intake_activation_key(
            workflow_run=target_workflow_run,
            generation=generation,
        )
        now = utc_now_iso()
        task_run_id = f"tr-{uuid4()}"
        human_task_id = f"ht-{uuid4()}"
        create_task_run(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=target_workflow_run_id,
            stage_id=_EOD_INTAKE_STAGE_ID,
            task_kind=_EOD_INTAKE_TASK_KIND,
            state="READY",
            generation=generation,
            activation_key=activation_key,
            blocked_on_kind=None,
            blocked_on_ref=None,
            spawned_from_flag_id=None,
            spawned_from_task_run_id=None,
            spawn_rule_id=None,
            spawn_cause_kind=None,
            spawn_cause_event_id=None,
            spawn_depth=0,
            spawn_budget_key=None,
            created_at=now,
        )
        create_human_task(
            connection,
            human_task_id=human_task_id,
            workflow_run_id=target_workflow_run_id,
            task_run_id=task_run_id,
            task_kind=_EOD_INTAKE_TASK_KIND,
            state="OPEN",
            candidate_roles=[_EOD_INTAKE_OWNER_ROLE],
            owner_role=_EOD_INTAKE_OWNER_ROLE,
            due_at=None,
            escalation_at=None,
            generation=generation,
            created_at=now,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="task.run.created",
                tenant_id=tenant_id,
                domain_id=domain_id,
                actor_type=actor_type,
                actor_id=actor_id,
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": target_workflow_run_id},
                    {"rel": "subject", "type": "task_run", "id": task_run_id},
                ],
                payload={
                    "task_run_id": task_run_id,
                    "stage_id": _EOD_INTAKE_STAGE_ID,
                    "task_kind": _EOD_INTAKE_TASK_KIND,
                    "activation_key": activation_key,
                    "generation": generation,
                    "spawned_from_flag_id": None,
                    "spawned_from_task_run_id": None,
                    "spawn_rule_id": None,
                    "spawn_cause_kind": "manual_reimport",
                    "spawn_cause_event_id": None,
                    "spawn_budget_key": None,
                    "spawn_depth": 0,
                },
                idempotency_key=None,
            ),
        )
        append_event(
            connection,
            _event_envelope(
                event_type="task.created",
                tenant_id=tenant_id,
                domain_id=domain_id,
                actor_type=actor_type,
                actor_id=actor_id,
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": target_workflow_run_id},
                    {"rel": "subject", "type": "task_run", "id": task_run_id},
                    {"rel": "subject", "type": "human_task", "id": human_task_id},
                ],
                payload={
                    "human_task_id": human_task_id,
                    "task_kind": _EOD_INTAKE_TASK_KIND,
                    "state": "OPEN",
                    "candidate_roles": [_EOD_INTAKE_OWNER_ROLE],
                },
                idempotency_key=None,
            ),
        )
        task_run = get_task_run(connection, task_run_id)
        human_task = get_human_task(connection, human_task_id)
        if task_run is None or human_task is None:
            raise CommandError(
                code="intake_task_not_created",
                message="dispatch reporting intake task was not created",
                details={"workflow_run_id": target_workflow_run_id},
            )
        return {
            "intake_task": _eod_intake_task_payload(
                task_run=task_run,
                human_task=human_task,
                created=True,
                service_date=requested_service_date,
                target_workflow_run_id=target_workflow_run_id,
                target_route=_canonical_eod_landing_route(
                    workflow_run_id=target_workflow_run_id
                ),
                created_workflow_run=created_workflow_run,
            )
        }

    result, replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=_operation,
    )
    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def create_workflow_run_eod_draft_command(
    connection: sqlite3.Connection,
    workflow_run: Mapping[str, Any],
    payload: dict[str, Any],
    *,
    storage_root: Path,
    include_receipt: bool = False,
) -> dict[str, Any]:
    workflow_run_id = _require_non_empty_string(
        workflow_run.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    tenant_id = _require_non_empty_string(payload.get("tenant_id"), field_name="tenant_id")
    domain_id = _require_non_empty_string(payload.get("domain_id"), field_name="domain_id")
    actor_id = _require_non_empty_string(payload.get("actor_id"), field_name="actor_id")
    actor_type = _require_non_empty_string(payload.get("actor_type"), field_name="actor_type")
    subject_link, action_ref = _resolve_workpage_action_subject(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=EOD_WORKFLOW_ID,
        workpage_kind=EOD_WORKPAGE_KIND,
        flow_kind="create",
        artifact_version_id=None,
        raw_action_ref=payload.get("action_ref"),
        raw_subject_link=payload.get("subject_link"),
    )

    receipt = _prepare_command_receipt(
        command_name="workpages.eod-drafts.create",
        payload={
            **payload,
            "workflow_run_id": workflow_run_id,
            "workflow_id": EOD_WORKFLOW_ID,
            "workpage_id": EOD_WORKPAGE_KIND,
        },
        fingerprint_payload={
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "workflow_run_id": workflow_run_id,
            "workflow_id": EOD_WORKFLOW_ID,
            "workpage_id": EOD_WORKPAGE_KIND,
            "template_id": EOD_TEMPLATE_ID,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action_ref": action_ref,
            "subject_link": subject_link,
        },
        tenant_id=tenant_id,
        domain_id=domain_id,
        workflow_run_id=workflow_run_id,
        idempotency_required=True,
    )
    artifact_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.eod-drafts.create.artifact.version.created",
    )

    def _operation() -> dict[str, Any]:
        artifact = _create_eod_draft_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            parent_artifact_version_id=None,
            supersedes_artifact_version_id=None,
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=artifact_event_idempotency,
            links=_artifact_links_for_workpage_subject(
                subject_link,
                relation_kind="draft",
            ),
        )
        artifact_version_id = str(artifact["artifact_version_id"])
        return {
            "draft": {
                "workflow_run_id": workflow_run_id,
                "artifact_version_id": artifact_version_id,
                "route": _canonical_eod_ui_route(
                    workflow_run_id=workflow_run_id,
                    artifact_version_id=artifact_version_id,
                ),
            }
        }

    result, replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=_operation,
    )
    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )

def submit_eod_artifact_workpage_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    storage_root: Path,
    include_receipt: bool = False,
) -> dict[str, Any]:
    artifact_version_id = _require_non_empty_string(
        payload.get("artifact_version_id"),
        field_name="artifact_version_id",
    )
    actor_id = _require_non_empty_string(payload.get("actor_id"), field_name="actor_id")
    actor_type = _require_non_empty_string(payload.get("actor_type"), field_name="actor_type")
    base_artifact = _require_eod_artifact_version(connection, artifact_version_id)
    subject_link, action_ref = _resolve_workpage_action_subject(
        connection,
        workflow_run_id=str(base_artifact["workflow_run_id"]),
        workflow_id=EOD_WORKFLOW_ID,
        workpage_kind=EOD_WORKPAGE_KIND,
        flow_kind="submit",
        artifact_version_id=artifact_version_id,
        raw_action_ref=payload.get("action_ref"),
        raw_subject_link=payload.get("subject_link"),
    )

    receipt = _prepare_command_receipt(
        command_name="workpages.artifact.submit",
        payload=payload,
        fingerprint_payload={
            "artifact_version_id": artifact_version_id,
            "form_values": payload.get("form_values"),
            "checklist_values": payload.get("checklist_values"),
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action_ref": action_ref,
            "subject_link": subject_link,
        },
        tenant_id=str(base_artifact.get("tenant_id") or ""),
        domain_id=str(base_artifact.get("domain_id") or ""),
        workflow_run_id=str(base_artifact["workflow_run_id"]),
        idempotency_required=True,
    )
    artifact_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.artifact.submit.artifact.version.created",
    )

    def _operation() -> dict[str, Any]:
        _assert_artifact_not_already_superseded(
            connection,
            artifact_version_id,
            route_builder=_canonical_eod_ui_route,
        )
        workbook_bytes = _read_workbook_bytes(base_artifact)
        projection = project_upd_draft_workbook(workbook_bytes)
        edits = _build_submit_edits(
            projection,
            form_values=payload.get("form_values"),
            checklist_values=payload.get("checklist_values"),
        )
        updated_bytes = materialize_upd_draft_workbook(
            workbook_bytes,
            edits,
            change_log_entry=_change_log_entry(actor_id=actor_id),
        )
        new_artifact = _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=str(base_artifact["workflow_run_id"]),
            artifact_kind=EOD_DATASET_KEY,
            artifact_bytes=updated_bytes,
            artifact_role=(
                str(base_artifact["artifact_role"])
                if base_artifact.get("artifact_role") is not None
                else None
            ),
            file_name=_metadata_string(
                base_artifact.get("metadata_json"),
                "file_name",
                default=_draft_file_name(),
            ),
            media_type=str(base_artifact.get("media_type") or _xlsx_media_type()),
            metadata_json=_submitted_metadata(base_artifact),
            parent_artifact_version_id=artifact_version_id,
            supersedes_artifact_version_id=artifact_version_id,
            lineage_note="Submitted artifact-backed EOD draft version.",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=artifact_event_idempotency,
            links=_artifact_links_for_workpage_subject(
                subject_link,
                relation_kind="response",
            ),
        )
        submitted_artifact_version_id = str(new_artifact["artifact_version_id"])
        workflow_run_id = str(base_artifact["workflow_run_id"])
        return {
            "submitted": {
                "workflow_run_id": workflow_run_id,
                "artifact_version_id": submitted_artifact_version_id,
                "supersedes_artifact_version_id": artifact_version_id,
                "route": _canonical_eod_ui_route(
                    workflow_run_id=workflow_run_id,
                    artifact_version_id=submitted_artifact_version_id,
                ),
            }
        }

    result, replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=_operation,
    )
    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def _reusable_eod_intake_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    actor_id: str,
    actor_type: str,
) -> dict[str, Any] | None:
    conflicting_claim: dict[str, Any] | None = None
    for human_task in reversed(list_human_tasks_for_workflow_run(connection, workflow_run_id)):
        task_run = get_task_run(connection, str(human_task.get("task_run_id") or ""))
        if task_run is None:
            continue
        if str(task_run.get("stage_id") or "") != _EOD_INTAKE_STAGE_ID:
            continue
        if str(task_run.get("task_kind") or "") != _EOD_INTAKE_TASK_KIND:
            continue
        state = str(human_task.get("state") or "")
        if state == "OPEN":
            return {"task_run": task_run, "human_task": human_task}
        if state == "CLAIMED":
            if (
                str(human_task.get("assignee_actor_id") or "") == actor_id
                and str(human_task.get("assignee_actor_type") or "") == actor_type
            ):
                return {"task_run": task_run, "human_task": human_task}
            conflicting_claim = {"task_run": task_run, "human_task": human_task}
            continue
    if conflicting_claim is not None:
        human_task = conflicting_claim["human_task"]
        raise CommandError(
            code="task_not_claimable",
            message="dispatch reporting intake is currently claimed by another actor",
            details={
                "workflow_run_id": workflow_run_id,
                "human_task_id": str(human_task.get("human_task_id") or ""),
                "state": str(human_task.get("state") or ""),
            },
        )
    return None


def _resolve_eod_intake_service_date(
    *,
    workflow_run: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> str:
    raw_value = payload.get("service_date")
    if raw_value is None or str(raw_value).strip() == "":
        return _require_non_empty_string(
            workflow_run.get("logical_date"),
            field_name="logical_date",
        )
    text = str(raw_value).strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise CommandError(
            code="invalid_service_date",
            message="service_date must be an ISO date",
            details={"service_date": text},
        ) from exc


def _resolve_target_eod_workflow_run(
    connection: sqlite3.Connection,
    *,
    workflow_run: Mapping[str, Any],
    service_date: str,
) -> tuple[Mapping[str, Any], bool]:
    current_logical_date = _require_non_empty_string(
        workflow_run.get("logical_date"),
        field_name="logical_date",
    )
    if service_date == current_logical_date:
        return workflow_run, False
    return _resolve_or_create_reporting_run(
        connection,
        tenant_id=_require_non_empty_string(workflow_run.get("tenant_id"), field_name="tenant_id"),
        domain_id=_require_non_empty_string(workflow_run.get("domain_id"), field_name="domain_id"),
        workflow_version=_require_non_empty_string(
            workflow_run.get("workflow_version"),
            field_name="workflow_version",
        ),
        service_date=service_date,
    )


def _resolve_or_create_reporting_run(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    workflow_version: str,
    service_date: str,
) -> tuple[Mapping[str, Any], bool]:
    partition_key = f"SD-{service_date}"
    existing_runs = list_workflow_runs(
        connection,
        workflow_id=EOD_WORKFLOW_ID,
        tenant_id=tenant_id,
        domain_id=domain_id,
        state=None,
    )
    for existing_run in existing_runs:
        if str(existing_run.get("partition_key") or "") == partition_key:
            return existing_run, False

    workflow_run_id = f"wr-{uuid4()}"
    created_at = utc_now_iso()
    try:
        create_workflow_run(
            connection,
            workflow_run_id=workflow_run_id,
            workflow_id=EOD_WORKFLOW_ID,
            workflow_version=workflow_version,
            tenant_id=tenant_id,
            domain_id=domain_id,
            partition_key=partition_key,
            logical_date=service_date,
            activation_key=_reporting_run_activation_key(partition_key=partition_key),
            state="OPEN",
            created_at=created_at,
        )
    except sqlite3.IntegrityError:
        refreshed_runs = list_workflow_runs(
            connection,
            workflow_id=EOD_WORKFLOW_ID,
            tenant_id=tenant_id,
            domain_id=domain_id,
            state=None,
        )
        for existing_run in refreshed_runs:
            if str(existing_run.get("partition_key") or "") == partition_key:
                return existing_run, False
        raise

    created_run = get_workflow_run(connection, workflow_run_id)
    if created_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="dispatch reporting workflow run was not created",
            details={"workflow_run_id": workflow_run_id},
        )
    return created_run, True


def _next_eod_intake_generation(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
) -> int:
    generations = [0]
    for human_task in list_human_tasks_for_workflow_run(connection, workflow_run_id):
        task_run = get_task_run(connection, str(human_task.get("task_run_id") or ""))
        if task_run is None:
            continue
        if str(task_run.get("stage_id") or "") != _EOD_INTAKE_STAGE_ID:
            continue
        if str(task_run.get("task_kind") or "") != _EOD_INTAKE_TASK_KIND:
            continue
        generations.append(int(task_run.get("generation") or 0))
    return max(generations) + 1


def _next_eod_intake_activation_key(
    *,
    workflow_run: Mapping[str, Any],
    generation: int,
) -> str:
    partition_key = _require_non_empty_string(
        workflow_run.get("partition_key"),
        field_name="partition_key",
    )
    base = f"workpage:dispatch-reporting:{partition_key}:stage01:eos_input_intake"
    return f"{base}:generation:{generation}"


def _reporting_run_activation_key(*, partition_key: str) -> str:
    return f"workpage:dispatch-reporting:{partition_key}:workflow-run"


def _canonical_eod_landing_route(*, workflow_run_id: str) -> str:
    return f"/runs/{workflow_run_id}/workpages/eod-v0"


def _eod_intake_task_payload(
    *,
    task_run: Mapping[str, Any],
    human_task: Mapping[str, Any],
    created: bool,
    service_date: str,
    target_workflow_run_id: str,
    target_route: str,
    created_workflow_run: bool,
) -> dict[str, Any]:
    return {
        "workflow_run_id": str(human_task.get("workflow_run_id") or ""),
        "task_run_id": str(task_run.get("task_run_id") or ""),
        "human_task_id": str(human_task.get("human_task_id") or ""),
        "stage_id": str(task_run.get("stage_id") or ""),
        "task_kind": str(task_run.get("task_kind") or ""),
        "task_run_state": str(task_run.get("state") or ""),
        "human_task_state": str(human_task.get("state") or ""),
        "activation_key": str(task_run.get("activation_key") or ""),
        "generation": int(task_run.get("generation") or 0),
        "created": created,
        "service_date": service_date,
        "target_workflow_run_id": target_workflow_run_id,
        "target_route": target_route,
        "created_workflow_run": created_workflow_run,
    }


def _build_submit_edits(
    projection: Mapping[str, Any],
    *,
    form_values: Any,
    checklist_values: Any,
) -> dict[str, Any]:
    manual_closeout_rows = projection.get("manual_closeout")
    if not isinstance(manual_closeout_rows, list) or not manual_closeout_rows:
        raise CommandError(
            code="invalid_payload",
            message="base workbook projection must contain one manual_closeout row",
            details={},
        )
    manual_closeout_row = dict(manual_closeout_rows[0])
    updates = _normalize_form_values(form_values)
    for field_key, value in updates.items():
        if field_key not in manual_closeout_row:
            raise CommandError(
                code="invalid_payload",
                message=f"unsupported form field: {field_key}",
                details={"field_key": field_key},
            )
        manual_closeout_row[field_key] = value

    updated_checklist_rows = [
        dict(item) for item in _require_projection_rows(projection.get("upd_candidates"), "upd_candidates")
    ]
    checklist_updates = _normalize_checklist_values(checklist_values)
    by_row_id = {
        str(item.get("row_id") or ""): item
        for item in updated_checklist_rows
    }
    for item in checklist_updates:
        row_id = item["item_id"]
        target = by_row_id.get(row_id)
        if target is None:
            raise CommandError(
                code="invalid_payload",
                message=f"unknown checklist item_id: {row_id}",
                details={"item_id": row_id},
            )
        target["selected"] = item["selected"]
        target["manager_note"] = item["note"]

    return {
        "manual_closeout": [manual_closeout_row],
        "upd_candidates": updated_checklist_rows,
    }

def _normalize_form_values(raw_form_values: Any) -> dict[str, str]:
    if raw_form_values is None:
        return {}
    if not isinstance(raw_form_values, Mapping):
        raise CommandError(
            code="invalid_payload",
            message="form_values must be an object",
            details={},
        )

    normalized: dict[str, str] = {}
    for field_key, value in raw_form_values.items():
        key = str(field_key).strip()
        if not key:
            raise CommandError(
                code="invalid_payload",
                message="form_values field keys must be non-empty strings",
                details={},
            )
        normalized[key] = _stringify_form_value(value)
    return normalized

def _normalize_checklist_values(raw_checklist_values: Any) -> list[dict[str, Any]]:
    if raw_checklist_values is None:
        return []
    if not isinstance(raw_checklist_values, Sequence) or isinstance(
        raw_checklist_values,
        (str, bytes, bytearray),
    ):
        raise CommandError(
            code="invalid_payload",
            message="checklist_values must be a list",
            details={},
        )

    normalized: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()
    for index, item in enumerate(raw_checklist_values):
        if not isinstance(item, Mapping):
            raise CommandError(
                code="invalid_payload",
                message=f"checklist_values[{index}] must be an object",
                details={},
            )
        item_id = _require_non_empty_string(
            item.get("item_id"),
            field_name=f"checklist_values[{index}].item_id",
        )
        if item_id in seen_item_ids:
            raise CommandError(
                code="invalid_payload",
                message=f"duplicate checklist_values item_id: {item_id}",
                details={"item_id": item_id},
            )
        seen_item_ids.add(item_id)
        selected = bool(item.get("selected", False))
        note = str(item.get("note") or "")
        normalized.append(
            {
                "item_id": item_id,
                "selected": selected,
                "note": note,
            }
        )
    return normalized

def _stringify_form_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        normalized_values: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text:
                normalized_values.append(text)
        return "\n".join(normalized_values)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)

def _change_log_entry(*, actor_id: str) -> dict[str, str]:
    return {
        "row_id": f"changelog-{uuid4().hex[:12]}",
        "change_type": "submit",
        "actor_id": actor_id,
        "changed_at": utc_now_iso(),
        "summary": "Artifact-backed EOD workpage submit created a superseding workbook version.",
    }

def _create_eod_draft_artifact_version(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    workflow_run_id: str,
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    actor_id: str,
    actor_type: str,
    event_idempotency: str | None,
    links: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    template = _load_eod_template_record()
    return _create_workbook_artifact_version(
        connection,
        storage_root=storage_root,
        workflow_run_id=workflow_run_id,
        artifact_kind=EOD_DATASET_KEY,
        artifact_bytes=template.source_path.read_bytes(),
        artifact_role=None,
        file_name=_draft_file_name(),
        media_type=template.media_type,
        metadata_json=_draft_metadata(template),
        parent_artifact_version_id=parent_artifact_version_id,
        supersedes_artifact_version_id=supersedes_artifact_version_id,
        lineage_note="Initial artifact-backed EOD draft seeded from Stage03 template.",
        actor_id=actor_id,
        actor_type=actor_type,
        event_idempotency=event_idempotency,
        links=links,
    )

def _draft_metadata(template: TemplateRecord) -> dict[str, Any]:
    template_path = template.as_public_dict()["file_path"]
    return {
        "template_id": template.template_id,
        "template_source_path": template_path,
        "seed_source_path": template_path,
        "ingress_source_path": template_path,
        "ingress_kind": "local_source_path",
        "service_date": EOD_DEFAULT_SERVICE_DATE,
        "station_code": EOD_DEFAULT_STATION_CODE,
        "dsp_name": EOD_DEFAULT_DSP_NAME,
    }

def _submitted_metadata(base_artifact: Mapping[str, Any]) -> dict[str, Any]:
    metadata_json = base_artifact.get("metadata_json")
    if not isinstance(metadata_json, Mapping):
        metadata_json = {}

    result = dict(metadata_json)
    result["ingress_kind"] = "workpage_submit"
    result.setdefault("template_id", EOD_TEMPLATE_ID)
    result.setdefault("service_date", EOD_DEFAULT_SERVICE_DATE)
    result.setdefault("station_code", EOD_DEFAULT_STATION_CODE)
    result.setdefault("dsp_name", EOD_DEFAULT_DSP_NAME)
    return result
