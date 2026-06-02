from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any
from urllib.parse import urlparse

from onetruth.domain.logistics_calendar import (
    LATE_REPORTING_CONFLICT_CODE,
    late_reporting_policy_for_boundary,
)
from onetruth.domain.partition_codec import (
    PartitionCodecError,
    planning_week_to_service_days,
    service_day_to_next_planning_week,
    validate_partition_key,
)


LOGISTICS_RECONCILER_REPORT_SCHEMA_VERSION = "logistics_reconciler_dry_run.v1"
LOGISTICS_RECONCILER_MODE = "dry_run"

API_BOUNDARY_PROFILE_ENV_VAR = "ONETRUTH_API_BOUNDARY_PROFILE"
EDGE_ID_WEEKLY_TO_LIVE = "weekly_seed_to_live_dispatch"
REPORTING_TO_PLANNING_EDGE_ID = "reporting_actuals_to_future_planning"
WEEKLY_WORKFLOW_ID = "weekly_schedule_planning.v1"
LIVE_WORKFLOW_ID = "live_dispatch.v1"
REPORTING_WORKFLOW_ID = "dispatch_reporting.v1"
WEEKLY_PUBLISHED_KIND = "planning.published_weekly_schedule.workbook"
WEEKLY_DAILY_SEED_KIND = "planning.daily_dispatch_seed.workbook"
LIVE_SEED_KIND = "dispatch.base_schedule_seed.workbook"
LIVE_ROUTE_DELTA_KIND = "dispatch.route_delta_intake.workbook"
LIVE_ACTUAL_HOURS_KIND = "dispatch.actual_hours_snapshot.workbook"
REPORTING_FINAL_PACKET_KIND = "reporting.final_packet.workbook"
PLANNING_ACTUAL_HOURS_KIND = "planning.actual_hours_snapshot.workbook"

_LIVE_INPUT_BINDINGS = {
    LIVE_SEED_KIND: "stage01.base_seed",
    LIVE_ROUTE_DELTA_KIND: "stage01.route_delta_intake",
    LIVE_ACTUAL_HOURS_KIND: "stage01.actual_hours_snapshot",
}

_OBSERVED_TABLES = (
    "workflow_runs",
    "artifact_versions",
    "edge_executions",
    "workflow_run_inputs",
    "artifact_provenance_edges",
    "artifact_pointers",
    "task_runs",
    "human_tasks",
    "timeline_events",
)


def run_logistics_reconciler_dry_run(
    connection: sqlite3.Connection,
    *,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    boundary_profile: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic logistics handoff reconciliation report without writes."""

    normalized_tenant_id = _optional_text(tenant_id)
    normalized_domain_id = _optional_text(domain_id)
    normalized_boundary_profile = _boundary_profile(boundary_profile)
    policy = late_reporting_policy_for_boundary(normalized_boundary_profile)
    findings: list[dict[str, Any]] = []

    checks = [
        {
            "check_id": "weekly_seed_materialization",
            "description": "published weekly schedules have one daily seed artifact and edge per service date",
        },
        {
            "check_id": "handoff_edge_integrity",
            "description": "handoff edges reference existing source, seed, and target runtime rows",
        },
        {
            "check_id": "notify_only_target_inputs",
            "description": "notify-only edges retain target run, target input artifact, and input binding",
        },
        {
            "check_id": "reporting_late_feedback",
            "description": "reporting final packets are notified once and do not silently replace safe-profile inputs",
        },
        {
            "check_id": "file_backed_artifact_blobs",
            "description": "file-backed logistics artifact rows still resolve to local blobs",
        },
    ]

    _check_weekly_seed_materialization(
        connection,
        findings=findings,
        tenant_id=normalized_tenant_id,
        domain_id=normalized_domain_id,
    )
    _check_handoff_edge_integrity(
        connection,
        findings=findings,
        tenant_id=normalized_tenant_id,
        domain_id=normalized_domain_id,
    )
    _check_notify_only_target_inputs(
        connection,
        findings=findings,
        tenant_id=normalized_tenant_id,
        domain_id=normalized_domain_id,
    )
    _check_reporting_late_feedback(
        connection,
        findings=findings,
        tenant_id=normalized_tenant_id,
        domain_id=normalized_domain_id,
        boundary_profile=normalized_boundary_profile,
        replace_on_conflict_allowed=policy.replace_on_conflict_allowed,
    )
    _check_file_backed_artifact_blobs(
        connection,
        findings=findings,
        tenant_id=normalized_tenant_id,
        domain_id=normalized_domain_id,
    )

    findings.sort(
        key=lambda item: (
            str(item["severity"]),
            str(item["code"]),
            str(item["finding_id"]),
        )
    )
    severity_counts = Counter(str(item["severity"]) for item in findings)
    code_counts = Counter(str(item["code"]) for item in findings)
    return {
        "schema_version": LOGISTICS_RECONCILER_REPORT_SCHEMA_VERSION,
        "mode": LOGISTICS_RECONCILER_MODE,
        "scope": {
            "tenant_id": normalized_tenant_id,
            "domain_id": normalized_domain_id,
            "boundary_profile": normalized_boundary_profile,
        },
        "checks": checks,
        "summary": {
            "finding_count": len(findings),
            "error_count": severity_counts.get("error", 0),
            "warning_count": severity_counts.get("warning", 0),
            "info_count": severity_counts.get("info", 0),
            "mutations_performed": 0,
            "code_counts": dict(sorted(code_counts.items())),
        },
        "observed_table_counts": _table_counts(connection),
        "findings": findings,
    }


def _check_weekly_seed_materialization(
    connection: sqlite3.Connection,
    *,
    findings: list[dict[str, Any]],
    tenant_id: str | None,
    domain_id: str | None,
) -> None:
    for row in _published_weekly_artifacts(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
    ):
        planning_week_id = str(row["partition_key"])
        try:
            service_dates = planning_week_to_service_days(planning_week_id)
        except (PartitionCodecError, ValueError) as exc:
            _add_finding(
                findings,
                code="weekly_partition_invalid",
                severity="error",
                subject=_subject_from_row(row),
                expected={"partition_kind": "PlanningWeekID"},
                observed={"partition_key": planning_week_id, "error": str(exc)},
                message="weekly schedule run has an invalid planning-week partition key",
                repair_hint="Fix the source workflow run partition before handoff repair.",
            )
            continue

        for service_date_id in service_dates:
            seed_rows = _seed_artifacts_for_service_date(
                connection,
                workflow_run_id=str(row["workflow_run_id"]),
                service_date_id=service_date_id,
            )
            if not seed_rows:
                _add_finding(
                    findings,
                    code="weekly_daily_seed_missing",
                    severity="error",
                    subject={
                        **_subject_from_row(row),
                        "service_date_id": service_date_id,
                    },
                    expected={
                        "artifact_kind": WEEKLY_DAILY_SEED_KIND,
                        "partition_kind": "ServiceDateID",
                        "partition_key": service_date_id,
                    },
                    observed={"artifact_count": 0},
                    message="published weekly schedule is missing a daily dispatch seed artifact",
                    repair_hint="Future apply mode must materialize the missing seed once without changing officialness.",
                )
                continue
            if len(seed_rows) > 1:
                _add_finding(
                    findings,
                    code="weekly_daily_seed_duplicate",
                    severity="warning",
                    subject={
                        **_subject_from_row(row),
                        "service_date_id": service_date_id,
                    },
                    expected={"artifact_count": 1},
                    observed={
                        "artifact_count": len(seed_rows),
                        "artifact_version_ids": [
                            str(item["artifact_version_id"]) for item in seed_rows
                        ],
                    },
                    message="published weekly schedule has multiple daily seed artifacts for one service date",
                    repair_hint="Review duplicate seed lineage before any apply-mode repair.",
                )
            for seed in seed_rows:
                if str(seed.get("parent_artifact_version_id") or "") != str(
                    row["artifact_version_id"]
                ):
                    _add_finding(
                        findings,
                        code="weekly_daily_seed_parent_mismatch",
                        severity="warning",
                        subject={
                            **_subject_from_row(seed),
                            "service_date_id": service_date_id,
                        },
                        expected={
                            "parent_artifact_version_id": str(row["artifact_version_id"]),
                        },
                        observed={
                            "parent_artifact_version_id": str(
                                seed.get("parent_artifact_version_id") or ""
                            ),
                        },
                        message="daily seed artifact does not point back to the published schedule artifact",
                        repair_hint="Review seed lineage before trusting downstream handoff evidence.",
                    )
                edge_rows = _weekly_edges_for_seed(
                    connection,
                    workflow_run_id=str(row["workflow_run_id"]),
                    seed_artifact_version_id=str(seed["artifact_version_id"]),
                    service_date_id=service_date_id,
                )
                if not edge_rows:
                    _add_finding(
                        findings,
                        code="weekly_seed_edge_missing",
                        severity="error",
                        subject={
                            **_subject_from_row(seed),
                            "service_date_id": service_date_id,
                        },
                        expected={
                            "edge_id": EDGE_ID_WEEKLY_TO_LIVE,
                            "target_partition_key": service_date_id,
                        },
                        observed={"edge_execution_count": 0},
                        message="daily seed artifact is missing its weekly-to-live edge execution row",
                        repair_hint="Future apply mode must recreate the missing edge idempotently from seed truth.",
                    )


def _check_handoff_edge_integrity(
    connection: sqlite3.Connection,
    *,
    findings: list[dict[str, Any]],
    tenant_id: str | None,
    domain_id: str | None,
) -> None:
    for edge in _logistics_edges(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
    ):
        subject = _edge_subject(edge)
        status = str(edge.get("status") or "")
        if status == "stale":
            _add_finding(
                findings,
                code="stale_edge_execution",
                severity="warning",
                subject=subject,
                expected={"status": "prepared_or_activated"},
                observed={
                    "status": status,
                    "cursor_state": edge.get("cursor_state"),
                    "compensation_state": edge.get("compensation_state"),
                },
                message="handoff edge execution is marked stale",
                repair_hint="Dry-run reports stale edges only; apply policy belongs to a later gated task.",
            )
        source_run = _workflow_run_by_id(
            connection,
            str(edge.get("source_workflow_run_id") or ""),
        )
        if source_run is None:
            _add_finding(
                findings,
                code="edge_source_run_missing",
                severity="error",
                subject=subject,
                expected={"source_workflow_run_id": str(edge.get("source_workflow_run_id") or "")},
                observed={"workflow_run_found": False},
                message="handoff edge references a missing source workflow run",
                repair_hint="Repair requires restoring the source run or quarantining the orphan edge.",
            )
        source_artifact_id = str(edge.get("source_artifact_version_id") or "")
        if source_artifact_id and _artifact_by_id(connection, source_artifact_id) is None:
            _add_finding(
                findings,
                code="edge_source_artifact_missing",
                severity="error",
                subject=subject,
                expected={"source_artifact_version_id": source_artifact_id},
                observed={"artifact_found": False},
                message="handoff edge references a missing source artifact",
                repair_hint="Repair requires restoring source artifact truth before downstream mutation.",
            )
        if source_artifact_id and _superseding_artifact_id(connection, source_artifact_id):
            _add_finding(
                findings,
                code="stale_edge_source_superseded",
                severity="warning",
                subject=subject,
                expected={"source_artifact_latest": True},
                observed={
                    "source_artifact_version_id": source_artifact_id,
                    "superseding_artifact_version_id": _superseding_artifact_id(
                        connection,
                        source_artifact_id,
                    ),
                },
                message="handoff edge source artifact has been superseded",
                repair_hint="Review downstream basis before activation or apply-mode repair.",
            )
        seed_artifact_id = str(edge.get("seed_artifact_version_id") or "")
        if seed_artifact_id and _artifact_by_id(connection, seed_artifact_id) is None:
            _add_finding(
                findings,
                code="edge_seed_artifact_missing",
                severity="error",
                subject=subject,
                expected={"seed_artifact_version_id": seed_artifact_id},
                observed={"artifact_found": False},
                message="handoff edge references a missing seed artifact",
                repair_hint="Repair requires recreating seed truth before target input mutation.",
            )
        target_run_id = str(edge.get("target_workflow_run_id") or "")
        if target_run_id:
            target_run = _workflow_run_by_id(connection, target_run_id)
            if target_run is None:
                _add_finding(
                    findings,
                    code="edge_target_run_missing",
                    severity="error",
                    subject=subject,
                    expected={"target_workflow_run_id": target_run_id},
                    observed={"workflow_run_found": False},
                    message="handoff edge references a missing target workflow run",
                    repair_hint="Repair must recreate or rebind the target run under tenant/domain isolation.",
                )
            else:
                _check_edge_target_run_matches(
                    findings=findings,
                    edge=edge,
                    target_run=target_run,
                )


def _check_notify_only_target_inputs(
    connection: sqlite3.Connection,
    *,
    findings: list[dict[str, Any]],
    tenant_id: str | None,
    domain_id: str | None,
) -> None:
    for edge in _logistics_edges(
        connection,
        edge_id=REPORTING_TO_PLANNING_EDGE_ID,
        tenant_id=tenant_id,
        domain_id=domain_id,
    ):
        input_bindings = edge.get("input_bindings")
        if not isinstance(input_bindings, dict):
            _add_finding(
                findings,
                code="notify_only_edge_input_bindings_missing",
                severity="error",
                subject=_edge_subject(edge),
                expected={"input_bindings": "object"},
                observed={"input_bindings": input_bindings},
                message="notify-only edge is missing recorded input binding metadata",
                repair_hint="Review edge provenance before any target-side repair.",
            )
            continue
        target_run_id = str(edge.get("target_workflow_run_id") or "")
        target_binding_key = str(input_bindings.get("target_binding_key") or "")
        target_artifact_id = str(input_bindings.get("target_input_artifact_version_id") or "")
        source_artifact_id = str(edge.get("source_artifact_version_id") or "")
        if not target_run_id:
            _add_finding(
                findings,
                code="notify_only_target_run_missing",
                severity="error",
                subject=_edge_subject(edge),
                expected={"target_workflow_run_id": "present"},
                observed={"target_workflow_run_id": ""},
                message="notify-only edge is missing its target workflow run reference",
                repair_hint="Future apply mode must recreate target run resolution deterministically.",
            )
            continue
        if target_artifact_id and _artifact_by_id(connection, target_artifact_id) is None:
            _add_finding(
                findings,
                code="notify_only_target_input_artifact_missing",
                severity="error",
                subject=_edge_subject(edge),
                expected={"artifact_version_id": target_artifact_id},
                observed={"artifact_found": False},
                message="notify-only edge target input artifact is missing",
                repair_hint="Repair must materialize the target input artifact before binding.",
            )
        binding = _workflow_input_binding(
            connection,
            workflow_run_id=target_run_id,
            binding_key=target_binding_key,
        )
        if binding is None:
            _add_finding(
                findings,
                code="notify_only_target_input_binding_missing",
                severity="error",
                subject={
                    **_edge_subject(edge),
                    "binding_key": target_binding_key,
                },
                expected={
                    "workflow_run_id": target_run_id,
                    "binding_key": target_binding_key,
                    "source_ref": source_artifact_id,
                    "artifact_version_id": target_artifact_id,
                },
                observed={"binding_found": False},
                message="notify-only edge target run is missing its workflow input binding",
                repair_hint="Future apply mode must recreate the binding without replacing unrelated inputs.",
            )
            continue
        if str(binding.get("source_ref") or "") != source_artifact_id or str(
            binding.get("artifact_version_id") or ""
        ) != target_artifact_id:
            _add_finding(
                findings,
                code="notify_only_target_input_binding_drift",
                severity="error",
                subject={
                    **_edge_subject(edge),
                    "binding_key": target_binding_key,
                },
                expected={
                    "source_ref": source_artifact_id,
                    "artifact_version_id": target_artifact_id,
                },
                observed={
                    "source_ref": str(binding.get("source_ref") or ""),
                    "artifact_version_id": str(binding.get("artifact_version_id") or ""),
                },
                message="notify-only edge target input binding no longer matches edge truth",
                repair_hint="Review binding drift before any replacement policy is considered.",
            )

    for edge in _logistics_edges(
        connection,
        edge_id=EDGE_ID_WEEKLY_TO_LIVE,
        tenant_id=tenant_id,
        domain_id=domain_id,
    ):
        if str(edge.get("status") or "") != "activated":
            continue
        target_run_id = str(edge.get("target_workflow_run_id") or "")
        if not target_run_id:
            continue
        input_bindings = edge.get("input_bindings")
        live_input_artifact_ids = (
            input_bindings.get("live_input_artifact_version_ids")
            if isinstance(input_bindings, dict)
            else None
        )
        if not isinstance(live_input_artifact_ids, dict):
            _add_finding(
                findings,
                code="live_edge_input_artifacts_missing",
                severity="error",
                subject=_edge_subject(edge),
                expected={"live_input_artifact_version_ids": "object"},
                observed={"live_input_artifact_version_ids": live_input_artifact_ids},
                message="activated live handoff edge is missing target input artifact metadata",
                repair_hint="Review activated edge before trusting live input bindings.",
            )
            continue
        source_refs = {
            LIVE_SEED_KIND: str(edge.get("seed_artifact_version_id") or ""),
            LIVE_ROUTE_DELTA_KIND: str(input_bindings.get("route_delta_source_artifact_version_id") or ""),
            LIVE_ACTUAL_HOURS_KIND: str(input_bindings.get("actual_hours_source_artifact_version_id") or ""),
        }
        for artifact_kind, binding_key in _LIVE_INPUT_BINDINGS.items():
            artifact_id = str(live_input_artifact_ids.get(artifact_kind) or "")
            if not artifact_id:
                continue
            binding = _workflow_input_binding(
                connection,
                workflow_run_id=target_run_id,
                binding_key=binding_key,
            )
            if binding is None:
                _add_finding(
                    findings,
                    code="live_target_input_binding_missing",
                    severity="error",
                    subject={
                        **_edge_subject(edge),
                        "binding_key": binding_key,
                    },
                    expected={
                        "workflow_run_id": target_run_id,
                        "binding_key": binding_key,
                        "artifact_version_id": artifact_id,
                    },
                    observed={"binding_found": False},
                    message="activated live handoff target run is missing an input binding",
                    repair_hint="Future apply mode must recreate missing live input binding under policy gate.",
                )
                continue
            if str(binding.get("artifact_version_id") or "") != artifact_id or str(
                binding.get("source_ref") or ""
            ) != source_refs.get(artifact_kind, ""):
                _add_finding(
                    findings,
                    code="live_target_input_binding_drift",
                    severity="error",
                    subject={
                        **_edge_subject(edge),
                        "binding_key": binding_key,
                    },
                    expected={
                        "source_ref": source_refs.get(artifact_kind, ""),
                        "artifact_version_id": artifact_id,
                    },
                    observed={
                        "source_ref": str(binding.get("source_ref") or ""),
                        "artifact_version_id": str(binding.get("artifact_version_id") or ""),
                    },
                    message="activated live handoff target input binding no longer matches edge truth",
                    repair_hint="Review drift before any target input repair.",
                )


def _check_reporting_late_feedback(
    connection: sqlite3.Connection,
    *,
    findings: list[dict[str, Any]],
    tenant_id: str | None,
    domain_id: str | None,
    boundary_profile: str,
    replace_on_conflict_allowed: bool,
) -> None:
    for packet in _reporting_final_packets(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
    ):
        subject = _subject_from_row(packet)
        source_partition_key = str(packet.get("partition_key") or "")
        try:
            validate_partition_key("ServiceDateID", source_partition_key)
            target_planning_week_id = service_day_to_next_planning_week(source_partition_key)
        except PartitionCodecError as exc:
            _add_finding(
                findings,
                code="reporting_partition_invalid",
                severity="error",
                subject=subject,
                expected={"partition_kind": "ServiceDateID"},
                observed={"partition_key": source_partition_key, "error": str(exc)},
                message="reporting final packet is not scoped to a valid service-date partition",
                repair_hint="Fix reporting partition truth before reconciliation.",
            )
            continue
        metadata_json = packet.get("metadata_json")
        if not isinstance(metadata_json, dict) or not str(
            metadata_json.get("normalized_artifact_version_id") or ""
        ):
            _add_finding(
                findings,
                code="reporting_final_packet_normalized_artifact_missing",
                severity="error",
                subject=subject,
                expected={"metadata_json.normalized_artifact_version_id": "present"},
                observed={"metadata_json": metadata_json},
                message="reporting final packet is missing its normalized artifact reference",
                repair_hint="Cannot reconcile reporting feedback without normalized row evidence.",
            )

        notify_edges = _notify_edges_for_reporting_packet(
            connection,
            source_workflow_run_id=str(packet["workflow_run_id"]),
            source_artifact_version_id=str(packet["artifact_version_id"]),
            target_partition_key=target_planning_week_id,
        )
        if not notify_edges:
            _add_finding(
                findings,
                code="reporting_notify_edge_missing",
                severity="error",
                subject={
                    **subject,
                    "target_planning_week_id": target_planning_week_id,
                },
                expected={
                    "edge_id": REPORTING_TO_PLANNING_EDGE_ID,
                    "target_partition_key": target_planning_week_id,
                },
                observed={"edge_execution_count": 0},
                message="reporting final packet has not produced its notify-only planning handoff edge",
                repair_hint="Future apply mode may notify once after policy and role gates close.",
            )
        target_runs = _target_weekly_runs(
            connection,
            tenant_id=str(packet["tenant_id"]),
            domain_id=str(packet["domain_id"]),
            planning_week_id=target_planning_week_id,
        )
        if not target_runs:
            if notify_edges:
                _add_finding(
                    findings,
                    code="reporting_notify_target_run_missing",
                    severity="error",
                    subject={
                        **subject,
                        "target_planning_week_id": target_planning_week_id,
                    },
                    expected={
                        "workflow_id": WEEKLY_WORKFLOW_ID,
                        "partition_key": target_planning_week_id,
                    },
                    observed={"target_run_count": 0},
                    message="reporting notify-only edge exists but target weekly run is missing",
                    repair_hint="Repair must recreate target run resolution deterministically.",
                )
            continue
        for target_run in target_runs:
            binding = _workflow_input_binding(
                connection,
                workflow_run_id=str(target_run["workflow_run_id"]),
                binding_key="stage03.actual_hours_snapshot",
            )
            if binding is None:
                continue
            existing_source_ref = str(binding.get("source_ref") or "")
            packet_id = str(packet["artifact_version_id"])
            if existing_source_ref and existing_source_ref != packet_id:
                _add_finding(
                    findings,
                    code="late_reporting_input_conflict",
                    severity="error" if not replace_on_conflict_allowed else "warning",
                    subject={
                        **subject,
                        "target_workflow_run_id": str(target_run["workflow_run_id"]),
                        "target_planning_week_id": target_planning_week_id,
                    },
                    expected={
                        "binding_key": "stage03.actual_hours_snapshot",
                        "source_ref": packet_id,
                        "replace_on_conflict_allowed": replace_on_conflict_allowed,
                    },
                    observed={
                        "binding_key": "stage03.actual_hours_snapshot",
                        "existing_source_ref": existing_source_ref,
                        "artifact_version_id": str(binding.get("artifact_version_id") or ""),
                    },
                    message="reporting final packet would collide with an existing planning actual-hours input",
                    repair_hint=(
                        "Safe/default profile leaves late reporting blocked; local compatibility may merge explicitly."
                    ),
                    extra={
                        "conflict_code": LATE_REPORTING_CONFLICT_CODE,
                        "boundary_profile": boundary_profile,
                    },
                )


def _check_file_backed_artifact_blobs(
    connection: sqlite3.Connection,
    *,
    findings: list[dict[str, Any]],
    tenant_id: str | None,
    domain_id: str | None,
) -> None:
    for artifact in _file_backed_artifacts(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
    ):
        storage_uri = str(artifact.get("storage_uri") or "")
        parsed = urlparse(storage_uri)
        if parsed.scheme != "file":
            continue
        blob_path = Path(parsed.path)
        if blob_path.exists() and blob_path.is_file():
            continue
        _add_finding(
            findings,
            code="artifact_blob_missing",
            severity="error",
            subject=_subject_from_row(artifact),
            expected={"storage_scheme": "file", "blob_exists": True},
            observed={
                "storage_scheme": parsed.scheme,
                "blob_exists": blob_path.exists(),
                "is_file": blob_path.is_file() if blob_path.exists() else False,
            },
            message="file-backed artifact row points at a missing blob",
            repair_hint="Restore the blob from backup or quarantine the artifact before downstream use.",
        )


def _check_edge_target_run_matches(
    *,
    findings: list[dict[str, Any]],
    edge: dict[str, Any],
    target_run: dict[str, Any],
) -> None:
    observed = {
        "workflow_id": str(target_run.get("workflow_id") or ""),
        "partition_key": str(target_run.get("partition_key") or ""),
        "activation_key": str(target_run.get("activation_key") or ""),
    }
    expected = {
        "workflow_id": str(edge.get("target_workflow_id") or ""),
        "partition_key": str(edge.get("target_partition_key") or ""),
        "activation_key": str(edge.get("target_activation_key") or ""),
    }
    if observed != expected:
        _add_finding(
            findings,
            code="edge_target_run_drift",
            severity="error",
            subject=_edge_subject(edge),
            expected=expected,
            observed=observed,
            message="handoff target run no longer matches edge target workflow, partition, or activation key",
            repair_hint="Stop before mutation; target-run drift must be resolved under tenant/domain isolation.",
        )


def _add_finding(
    findings: list[dict[str, Any]],
    *,
    code: str,
    severity: str,
    subject: dict[str, Any],
    expected: dict[str, Any],
    observed: dict[str, Any],
    message: str,
    repair_hint: str,
    extra: dict[str, Any] | None = None,
) -> None:
    body: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "subject": _json_object(subject),
        "expected": _json_object(expected),
        "observed": _json_object(observed),
        "message": message,
        "mode": LOGISTICS_RECONCILER_MODE,
        "mutates": False,
        "repair_hint": repair_hint,
    }
    if extra:
        body.update(_json_object(extra))
    body["finding_id"] = _stable_id(body)
    findings.append(body)


def _published_weekly_artifacts(
    connection: sqlite3.Connection,
    *,
    tenant_id: str | None,
    domain_id: str | None,
) -> list[dict[str, Any]]:
    where = [
        "wr.workflow_id = ?",
        "av.artifact_kind = ?",
    ]
    params: list[Any] = [WEEKLY_WORKFLOW_ID, WEEKLY_PUBLISHED_KIND]
    _append_scope_filters(where, params, tenant_id=tenant_id, domain_id=domain_id)
    return _fetch_all(
        connection,
        f"""
        SELECT
            wr.workflow_run_id,
            wr.workflow_id,
            wr.tenant_id,
            wr.domain_id,
            wr.partition_key,
            av.artifact_version_id,
            av.artifact_kind,
            av.parent_artifact_version_id,
            av.created_at
        FROM artifact_versions av
        JOIN workflow_runs wr ON wr.workflow_run_id = av.workflow_run_id
        WHERE {' AND '.join(where)}
        ORDER BY wr.partition_key ASC, av.created_at ASC, av.artifact_version_id ASC
        """,
        params,
    )


def _reporting_final_packets(
    connection: sqlite3.Connection,
    *,
    tenant_id: str | None,
    domain_id: str | None,
) -> list[dict[str, Any]]:
    where = [
        "wr.workflow_id = ?",
        "av.artifact_kind = ?",
    ]
    params: list[Any] = [REPORTING_WORKFLOW_ID, REPORTING_FINAL_PACKET_KIND]
    _append_scope_filters(where, params, tenant_id=tenant_id, domain_id=domain_id)
    rows = _fetch_all(
        connection,
        f"""
        SELECT
            wr.workflow_run_id,
            wr.workflow_id,
            wr.tenant_id,
            wr.domain_id,
            wr.partition_key,
            av.artifact_version_id,
            av.artifact_kind,
            av.metadata_json,
            av.created_at
        FROM artifact_versions av
        JOIN workflow_runs wr ON wr.workflow_run_id = av.workflow_run_id
        WHERE {' AND '.join(where)}
        ORDER BY wr.partition_key ASC, av.created_at ASC, av.artifact_version_id ASC
        """,
        params,
    )
    for row in rows:
        row["metadata_json"] = _loads_json(row.get("metadata_json"))
    return rows


def _file_backed_artifacts(
    connection: sqlite3.Connection,
    *,
    tenant_id: str | None,
    domain_id: str | None,
) -> list[dict[str, Any]]:
    where = [
        "av.storage_uri LIKE 'file://%'",
    ]
    params: list[Any] = []
    _append_scope_filters(where, params, tenant_id=tenant_id, domain_id=domain_id)
    return _fetch_all(
        connection,
        f"""
        SELECT
            wr.workflow_run_id,
            wr.workflow_id,
            wr.tenant_id,
            wr.domain_id,
            wr.partition_key,
            av.artifact_version_id,
            av.artifact_kind,
            av.storage_uri,
            av.created_at
        FROM artifact_versions av
        JOIN workflow_runs wr ON wr.workflow_run_id = av.workflow_run_id
        WHERE {' AND '.join(where)}
        ORDER BY av.created_at ASC, av.artifact_version_id ASC
        """,
        params,
    )


def _logistics_edges(
    connection: sqlite3.Connection,
    *,
    edge_id: str | None = None,
    tenant_id: str | None,
    domain_id: str | None,
) -> list[dict[str, Any]]:
    where = [
        "ee.edge_id IN (?, ?, ?)",
    ]
    params: list[Any] = [
        EDGE_ID_WEEKLY_TO_LIVE,
        REPORTING_TO_PLANNING_EDGE_ID,
        "weekly_to_weekly_carry_forward",
    ]
    if edge_id is not None:
        where.append("ee.edge_id = ?")
        params.append(edge_id)
    _append_scope_filters(where, params, tenant_id=tenant_id, domain_id=domain_id, alias="wr")
    rows = _fetch_all(
        connection,
        f"""
        SELECT
            ee.edge_execution_id,
            ee.edge_id,
            ee.source_workflow_run_id,
            ee.source_stage_id,
            ee.source_artifact_version_id,
            ee.source_activation_key,
            ee.target_workflow_id,
            ee.target_workflow_run_id,
            ee.target_stage_id,
            ee.target_partition_kind,
            ee.target_partition_key,
            ee.target_activation_key,
            ee.correlation_key,
            ee.materialize_idempotency_key,
            ee.activation_idempotency_key,
            ee.status,
            ee.cursor_state_json,
            ee.compensation_state_json,
            ee.input_bindings_json,
            ee.trigger_ref,
            ee.seed_artifact_version_id,
            ee.created_at,
            ee.updated_at,
            ee.activated_at
        FROM edge_executions ee
        LEFT JOIN workflow_runs wr ON wr.workflow_run_id = ee.source_workflow_run_id
        WHERE {' AND '.join(where)}
        ORDER BY ee.created_at ASC, ee.edge_execution_id ASC
        """,
        params,
    )
    for row in rows:
        row["cursor_state"] = _loads_json(row.pop("cursor_state_json", None))
        row["compensation_state"] = _loads_json(row.pop("compensation_state_json", None))
        row["input_bindings"] = _loads_json(row.pop("input_bindings_json", None))
    return rows


def _seed_artifacts_for_service_date(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    service_date_id: str,
) -> list[dict[str, Any]]:
    return _fetch_all(
        connection,
        """
        SELECT
            artifact_version_id,
            workflow_run_id,
            artifact_kind,
            partition_kind,
            partition_key,
            parent_artifact_version_id,
            created_at
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind = ?
          AND partition_kind = 'ServiceDateID'
          AND partition_key = ?
        ORDER BY created_at ASC, artifact_version_id ASC
        """,
        [workflow_run_id, WEEKLY_DAILY_SEED_KIND, service_date_id],
    )


def _weekly_edges_for_seed(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    seed_artifact_version_id: str,
    service_date_id: str,
) -> list[dict[str, Any]]:
    return _fetch_all(
        connection,
        """
        SELECT edge_execution_id
        FROM edge_executions
        WHERE edge_id = ?
          AND source_workflow_run_id = ?
          AND seed_artifact_version_id = ?
          AND target_partition_key = ?
        ORDER BY created_at ASC, edge_execution_id ASC
        """,
        [EDGE_ID_WEEKLY_TO_LIVE, workflow_run_id, seed_artifact_version_id, service_date_id],
    )


def _notify_edges_for_reporting_packet(
    connection: sqlite3.Connection,
    *,
    source_workflow_run_id: str,
    source_artifact_version_id: str,
    target_partition_key: str,
) -> list[dict[str, Any]]:
    return _fetch_all(
        connection,
        """
        SELECT edge_execution_id
        FROM edge_executions
        WHERE edge_id = ?
          AND source_workflow_run_id = ?
          AND source_artifact_version_id = ?
          AND target_partition_key = ?
        ORDER BY created_at ASC, edge_execution_id ASC
        """,
        [
            REPORTING_TO_PLANNING_EDGE_ID,
            source_workflow_run_id,
            source_artifact_version_id,
            target_partition_key,
        ],
    )


def _target_weekly_runs(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    planning_week_id: str,
) -> list[dict[str, Any]]:
    return _fetch_all(
        connection,
        """
        SELECT workflow_run_id, workflow_id, tenant_id, domain_id, partition_key, activation_key
        FROM workflow_runs
        WHERE workflow_id = ?
          AND tenant_id = ?
          AND domain_id = ?
          AND partition_key = ?
        ORDER BY created_at ASC, workflow_run_id ASC
        """,
        [WEEKLY_WORKFLOW_ID, tenant_id, domain_id, planning_week_id],
    )


def _workflow_run_by_id(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    if not workflow_run_id:
        return None
    row = connection.execute(
        """
        SELECT workflow_run_id, workflow_id, tenant_id, domain_id, partition_key, activation_key
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _artifact_by_id(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any] | None:
    if not artifact_version_id:
        return None
    row = connection.execute(
        """
        SELECT artifact_version_id, workflow_run_id, artifact_kind, metadata_json
        FROM artifact_versions
        WHERE artifact_version_id = ?
        """,
        (artifact_version_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = _loads_json(item.get("metadata_json"))
    return item


def _superseding_artifact_id(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> str | None:
    row = connection.execute(
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE supersedes_artifact_version_id = ?
        ORDER BY created_at ASC, artifact_version_id ASC
        LIMIT 1
        """,
        (artifact_version_id,),
    ).fetchone()
    return str(row["artifact_version_id"]) if row is not None else None


def _workflow_input_binding(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    binding_key: str,
) -> dict[str, Any] | None:
    if not workflow_run_id or not binding_key:
        return None
    row = connection.execute(
        """
        SELECT workflow_run_input_id, workflow_run_id, binding_key, source_ref, artifact_version_id
        FROM workflow_run_inputs
        WHERE workflow_run_id = ?
          AND binding_key = ?
        LIMIT 1
        """,
        (workflow_run_id, binding_key),
    ).fetchone()
    return dict(row) if row is not None else None


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in _OBSERVED_TABLES:
        try:
            row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        except sqlite3.Error:
            continue
        counts[table] = int(row["count"])
    return counts


def _append_scope_filters(
    where: list[str],
    params: list[Any],
    *,
    tenant_id: str | None,
    domain_id: str | None,
    alias: str = "wr",
) -> None:
    if tenant_id is not None:
        where.append(f"{alias}.tenant_id = ?")
        params.append(tenant_id)
    if domain_id is not None:
        where.append(f"{alias}.domain_id = ?")
        params.append(domain_id)


def _fetch_all(
    connection: sqlite3.Connection,
    sql: str,
    params: list[Any],
) -> list[dict[str, Any]]:
    rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def _edge_subject(edge: dict[str, Any]) -> dict[str, str]:
    return {
        "edge_execution_id": str(edge.get("edge_execution_id") or ""),
        "edge_id": str(edge.get("edge_id") or ""),
        "source_workflow_run_id": str(edge.get("source_workflow_run_id") or ""),
        "target_partition_key": str(edge.get("target_partition_key") or ""),
    }


def _subject_from_row(row: dict[str, Any]) -> dict[str, str]:
    subject = {
        "workflow_run_id": str(row.get("workflow_run_id") or ""),
        "workflow_id": str(row.get("workflow_id") or ""),
        "tenant_id": str(row.get("tenant_id") or ""),
        "domain_id": str(row.get("domain_id") or ""),
        "partition_key": str(row.get("partition_key") or ""),
    }
    artifact_version_id = str(row.get("artifact_version_id") or "")
    if artifact_version_id:
        subject["artifact_version_id"] = artifact_version_id
    artifact_kind = str(row.get("artifact_kind") or "")
    if artifact_kind:
        subject["artifact_kind"] = artifact_kind
    return subject


def _stable_id(body: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"lrd-{digest[:16]}"


def _json_object(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    )


def _loads_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return None


def _boundary_profile(boundary_profile: str | None) -> str:
    raw = (
        boundary_profile
        if boundary_profile is not None
        else os.environ.get(API_BOUNDARY_PROFILE_ENV_VAR, "shared_env")
    )
    profile = str(raw or "").strip()
    return profile or "shared_env"


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None
