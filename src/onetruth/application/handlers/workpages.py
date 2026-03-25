from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any, Mapping, Sequence
from uuid import uuid4

from onetruth.application.handlers._shared.artifact_effects import (
    _create_artifact_version_effects,
)
from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _command_receipt_payload,
    _event_envelope,
    _execute_with_command_receipt,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
)
from onetruth.application.services.dispatch_reporting_workbook import (
    DATASET_KEY,
    WORKFLOW_ID,
    materialize_upd_draft_workbook,
    project_upd_draft_workbook,
)
from onetruth.application.services.template_registry import (
    TemplateRecord,
    load_template_registry_catalog,
)
from onetruth.infrastructure.artifacts.storage import (
    ArtifactStorageError,
    read_blob,
    write_blob,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.artifact_versions import (
    get_artifact_version,
    get_latest_artifact_version_in_chain,
    get_superseding_artifact_version,
)
from onetruth.infrastructure.repositories.workflow_runs import (
    create_workflow_run,
    get_workflow_run,
    list_workflow_runs,
)


WORKFLOW_VERSION = "v1"
DEMO_WORKPAGE_ID = "eod-v0"
DEMO_SERVICE_DATE_ID = "SD-2026-03-16"
DEMO_SERVICE_DATE = "2026-03-16"
DEMO_STATION_CODE = "DVC4"
DEMO_DSP_NAME = "QDCI"
DEMO_ACTIVATION_KEY = "dispatch_reporting.v1:SD-2026-03-16:eod-v0:artifact-draft"
EOD_TEMPLATE_ID = "dispatch_reporting.stage03.upd_draft.workbook.empty.v1"
EOD_UI_ROUTE_PREFIX = "/demo/logistics/workpages/eod-v0/artifacts/"


def create_demo_eod_draft_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    storage_root: Path,
    include_receipt: bool = False,
) -> dict[str, Any]:
    tenant_id = _require_non_empty_string(payload.get("tenant_id"), field_name="tenant_id")
    domain_id = _require_non_empty_string(payload.get("domain_id"), field_name="domain_id")
    actor_id = _require_non_empty_string(payload.get("actor_id"), field_name="actor_id")
    actor_type = _require_non_empty_string(payload.get("actor_type"), field_name="actor_type")

    existing_run = _find_demo_reporting_run(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )
    receipt = _prepare_command_receipt(
        command_name="workpages.eod-drafts.create",
        payload={
            **payload,
            "workflow_id": WORKFLOW_ID,
            "partition_key": DEMO_SERVICE_DATE_ID,
            "workpage_id": DEMO_WORKPAGE_ID,
        },
        fingerprint_payload={
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "workflow_id": WORKFLOW_ID,
            "partition_key": DEMO_SERVICE_DATE_ID,
            "workpage_id": DEMO_WORKPAGE_ID,
            "template_id": EOD_TEMPLATE_ID,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        tenant_id=tenant_id,
        domain_id=domain_id,
        workflow_run_id=(
            str(existing_run["workflow_run_id"])
            if existing_run is not None
            else None
        ),
        idempotency_required=True,
    )
    run_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.eod-drafts.create.workflow.run.created",
    )
    artifact_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.eod-drafts.create.artifact.version.created",
    )

    def _operation() -> dict[str, Any]:
        now = utc_now_iso()
        workflow_run = _resolve_or_create_demo_reporting_run(
            connection,
            tenant_id=tenant_id,
            domain_id=domain_id,
            actor_id=actor_id,
            actor_type=actor_type,
            created_at=now,
            event_idempotency=run_event_idempotency,
        )
        template = _load_eod_template_record()
        artifact = _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=str(workflow_run["workflow_run_id"]),
            artifact_bytes=template.source_path.read_bytes(),
            artifact_role=None,
            file_name=_draft_file_name(),
            media_type=template.media_type,
            metadata_json=_draft_metadata(template),
            parent_artifact_version_id=None,
            supersedes_artifact_version_id=None,
            lineage_note="Initial artifact-backed EOD draft seeded from Stage03 template.",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=artifact_event_idempotency,
        )
        artifact_version_id = str(artifact["artifact_version_id"])
        return {
            "draft": {
                "workflow_run_id": str(workflow_run["workflow_run_id"]),
                "artifact_version_id": artifact_version_id,
                "route": f"{EOD_UI_ROUTE_PREFIX}{artifact_version_id}",
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

    receipt = _prepare_command_receipt(
        command_name="workpages.artifact.submit",
        payload=payload,
        fingerprint_payload={
            "artifact_version_id": artifact_version_id,
            "form_values": payload.get("form_values"),
            "checklist_values": payload.get("checklist_values"),
            "actor_id": actor_id,
            "actor_type": actor_type,
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
        _assert_artifact_not_already_superseded(connection, artifact_version_id)
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
        )
        submitted_artifact_version_id = str(new_artifact["artifact_version_id"])
        return {
            "submitted": {
                "workflow_run_id": str(base_artifact["workflow_run_id"]),
                "artifact_version_id": submitted_artifact_version_id,
                "supersedes_artifact_version_id": artifact_version_id,
                "route": f"{EOD_UI_ROUTE_PREFIX}{submitted_artifact_version_id}",
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


def _resolve_or_create_demo_reporting_run(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    actor_id: str,
    actor_type: str,
    created_at: str,
    event_idempotency: str | None,
) -> dict[str, Any]:
    existing = _find_demo_reporting_run(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )
    if existing is not None:
        return existing

    workflow_run_id = f"wr-{uuid4()}"
    try:
        create_workflow_run(
            connection,
            workflow_run_id=workflow_run_id,
            workflow_id=WORKFLOW_ID,
            workflow_version=WORKFLOW_VERSION,
            tenant_id=tenant_id,
            domain_id=domain_id,
            partition_key=DEMO_SERVICE_DATE_ID,
            logical_date=DEMO_SERVICE_DATE,
            activation_key=DEMO_ACTIVATION_KEY,
            state="OPEN",
            created_at=created_at,
        )
    except sqlite3.IntegrityError:
        refreshed = _find_demo_reporting_run(
            connection,
            tenant_id=tenant_id,
            domain_id=domain_id,
        )
        if refreshed is not None:
            return refreshed
        raise

    append_event(
        connection,
        _event_envelope(
            event_type="workflow.run.created",
            tenant_id=tenant_id,
            domain_id=domain_id,
            actor_type=actor_type,
            actor_id=actor_id,
            links=[
                {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                {
                    "rel": "uses_definition",
                    "type": "workflow_contract_version",
                    "id": f"{WORKFLOW_ID}@{WORKFLOW_VERSION}",
                },
                {
                    "rel": "uses_decisions",
                    "type": "decision_catalog_version",
                    "id": f"{WORKFLOW_ID}@{WORKFLOW_VERSION}",
                },
                {
                    "rel": "uses_profile",
                    "type": "execution_profile_version",
                    "id": f"{WORKFLOW_ID}@{WORKFLOW_VERSION}",
                },
            ],
            payload={
                "workflow_id": WORKFLOW_ID,
                "partition_key": DEMO_SERVICE_DATE_ID,
                "activation_key": DEMO_ACTIVATION_KEY,
                "logical_date": DEMO_SERVICE_DATE,
            },
            idempotency_key=event_idempotency,
        ),
    )
    created = get_workflow_run(connection, workflow_run_id)
    if created is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found after creation",
            details={"workflow_run_id": workflow_run_id},
        )
    return created


def _find_demo_reporting_run(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
) -> dict[str, Any] | None:
    for run in list_workflow_runs(
        connection,
        workflow_id=WORKFLOW_ID,
        tenant_id=tenant_id,
        domain_id=domain_id,
        state=None,
    ):
        if str(run["partition_key"]) == DEMO_SERVICE_DATE_ID:
            return run
    return None


def _create_workbook_artifact_version(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    workflow_run_id: str,
    artifact_bytes: bytes,
    artifact_role: str | None,
    file_name: str,
    media_type: str,
    metadata_json: dict[str, Any],
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    lineage_note: str,
    actor_id: str,
    actor_type: str,
    event_idempotency: str | None,
) -> dict[str, Any]:
    storage_uri, content_digest, byte_size = write_blob(
        storage_root=storage_root,
        workflow_run_id=workflow_run_id,
        file_name=file_name,
        content=artifact_bytes,
    )
    return _create_artifact_version_effects(
        connection,
        {
            "artifact_version_id": f"av-{uuid4()}",
            "workflow_run_id": workflow_run_id,
            "artifact_kind": DATASET_KEY,
            "artifact_role": artifact_role,
            "media_type": media_type,
            "storage_uri": storage_uri,
            "content_digest": content_digest,
            "byte_size": byte_size,
            "metadata_json": {
                **metadata_json,
                "file_name": file_name,
                "ingress_file_name": file_name,
                "ingress_media_type": media_type,
            },
            "parent_artifact_version_id": parent_artifact_version_id,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "lineage_note": lineage_note,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=event_idempotency,
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


def _draft_metadata(template: TemplateRecord) -> dict[str, Any]:
    template_path = template.as_public_dict()["file_path"]
    return {
        "template_id": template.template_id,
        "template_source_path": template_path,
        "seed_source_path": template_path,
        "ingress_source_path": template_path,
        "ingress_kind": "local_source_path",
        "demo_workpage_id": DEMO_WORKPAGE_ID,
        "service_date": DEMO_SERVICE_DATE,
        "station_code": DEMO_STATION_CODE,
        "dsp_name": DEMO_DSP_NAME,
    }


def _submitted_metadata(base_artifact: Mapping[str, Any]) -> dict[str, Any]:
    metadata_json = base_artifact.get("metadata_json")
    if not isinstance(metadata_json, Mapping):
        metadata_json = {}

    result = dict(metadata_json)
    result["ingress_kind"] = "workpage_submit"
    result.setdefault("template_id", EOD_TEMPLATE_ID)
    result.setdefault("demo_workpage_id", DEMO_WORKPAGE_ID)
    result.setdefault("service_date", DEMO_SERVICE_DATE)
    result.setdefault("station_code", DEMO_STATION_CODE)
    result.setdefault("dsp_name", DEMO_DSP_NAME)
    return result


def _load_eod_template_record() -> TemplateRecord:
    try:
        return load_template_registry_catalog().template_by_id(EOD_TEMPLATE_ID)
    except ValueError as exc:
        raise CommandError(
            code="template_not_found",
            message="required EOD draft template is unavailable",
            details={"template_id": EOD_TEMPLATE_ID},
        ) from exc


def _read_workbook_bytes(artifact: Mapping[str, Any]) -> bytes:
    storage_uri = _require_non_empty_string(
        artifact.get("storage_uri"),
        field_name="storage_uri",
    )
    try:
        return read_blob(storage_uri)
    except ArtifactStorageError as exc:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact blob not found",
            details={"artifact_version_id": str(artifact.get("artifact_version_id") or "")},
        ) from exc


def _assert_artifact_not_already_superseded(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> None:
    superseding = get_superseding_artifact_version(connection, artifact_version_id)
    if superseding is None:
        return
    latest = get_latest_artifact_version_in_chain(connection, artifact_version_id)
    latest_id = (
        str(latest["artifact_version_id"])
        if latest is not None
        else str(superseding["artifact_version_id"])
    )
    raise CommandError(
        code="workpage_artifact_conflict",
        message="artifact-backed workpage submit references a stale base artifact version",
        details={
            "artifact_version_id": artifact_version_id,
            "latest_artifact_version_id": latest_id,
            "workflow_run_id": str(superseding["workflow_run_id"]),
            "route": f"{EOD_UI_ROUTE_PREFIX}{latest_id}",
        },
    )


def _require_eod_artifact_version(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any]:
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    if str(artifact.get("artifact_kind") or "") != DATASET_KEY:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = get_workflow_run(connection, str(artifact["workflow_run_id"]))
    if workflow_run is None or str(workflow_run.get("workflow_id") or "") != WORKFLOW_ID:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact


def _require_projection_rows(raw_value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_value, list):
        raise CommandError(
            code="invalid_payload",
            message=f"{label} projection must be a list",
            details={},
        )
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(raw_value):
        if not isinstance(row, Mapping):
            raise CommandError(
                code="invalid_payload",
                message=f"{label}[{index}] projection row must be an object",
                details={},
            )
        rows.append(dict(row))
    return rows


def _metadata_string(
    metadata_json: Any,
    key: str,
    *,
    default: str,
) -> str:
    if isinstance(metadata_json, Mapping):
        value = metadata_json.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return default


def _draft_file_name() -> str:
    return "dispatch_reporting_eod_v0_2026-03-16_qdci_dvc4_upd_draft.xlsx"


def _xlsx_media_type() -> str:
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _require_non_empty_string(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise CommandError(
        code="invalid_payload",
        message=f"{field_name} is required",
        details={"field_name": field_name},
    )
