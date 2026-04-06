from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any, Mapping, Sequence
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _command_receipt_payload,
    _execute_with_command_receipt,
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
from onetruth.infrastructure.events.event_store import utc_now_iso


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
