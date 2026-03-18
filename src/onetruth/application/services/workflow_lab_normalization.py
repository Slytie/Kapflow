from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

WORKFLOW_LAB_RUN_REPORT_FILENAME = "workflow_lab_run_report.json"
WORKFLOW_LAB_REVIEW_PACKET_FILENAME = "workflow_lab_review_packet.md"

_CERTIFICATION_WORKFLOW_FAMILIES = {
    "stage06_publish_ready": "schedule_planning.v1",
    "stage07_major_replan": "schedule_planning.v1",
    "logistics_weekly_to_live_golden_slice": "logistics_ops_family.v1",
}


def normalize_weekly_stage04_report(
    summary: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    summary_path: Path,
    packet_path: Path,
) -> dict[str, Any]:
    pilot_id = _require_text(packet.get("pilot_id"), field_name="pilot_id")
    pilot_key = _require_text(packet.get("pilot_key"), field_name="pilot_key")
    workflow_run_id = _workflow_run_id(packet)
    openai_mode = _require_text(
        summary.get("openai_mode") or packet.get("openai_mode"),
        field_name="openai_mode",
    )
    stage_focus = _require_text(packet.get("stage_focus"), field_name="stage_focus")
    description = _require_text(packet.get("description"), field_name="description")
    artifacts = _mapping_list(packet.get("artifacts"))
    execution_runtime = _mapping(packet.get("execution_runtime"))
    stage04_analysis = _mapping(packet.get("stage04_analysis"))
    timeline = _mapping(packet.get("timeline"))

    report = {
        "report_id": f"weekly_stage04_pilot__{pilot_key}__{pilot_id}",
        "source_kind": "weekly_stage04_pilot",
        "workflow_family": "weekly_schedule_planning.v1",
        "workflow_version": 1,
        "variant": {
            "variant_id": f"weekly_stage04_pilot__{pilot_id}__{openai_mode}__{stage_focus.lower()}",
            "workflow_family": "weekly_schedule_planning.v1",
            "workflow_version": 1,
            "execution_axes": {
                "pilot_id": pilot_id,
                "openai_mode": openai_mode,
                "stage_focus": stage_focus,
            },
        },
        "run_profile": {
            "profile_id": "weekly_stage04_pilot_suite",
            "profile_kind": "pilot_suite",
        },
        "world_instance": {
            "world_id": f"pilot_run__{pilot_key}__{pilot_id}",
            "world_kind": "pilot_run",
            "environment_class": "local_eval",
            "isolation_class": "standalone_artifact_set",
        },
        "freshness": {
            "generated_at": _require_text(
                packet.get("generated_at"),
                field_name="generated_at",
            ),
            "basis_kind": "inspection_packet",
            "source_as_of": _require_text(
                packet.get("generated_at"),
                field_name="generated_at",
            ),
        },
        "summary": {
            "status": _normalize_status(summary.get("status")),
            "headline": description,
            "metrics": _compact_scalars(
                {
                    "artifact_count": len(artifacts),
                    "task_count": len(_mapping_list(packet.get("tasks"))),
                    "approval_count": len(_mapping_list(packet.get("approvals"))),
                    "flag_count": len(_mapping_list(packet.get("flags"))),
                    "pointer_count": len(_mapping_list(packet.get("pointers"))),
                    "execution_session_count": len(
                        _mapping_list(execution_runtime.get("execution_sessions"))
                    ),
                    "tool_execution_count": len(
                        _mapping_list(execution_runtime.get("tool_executions"))
                    ),
                    "policy_decision_count": len(
                        _mapping_list(execution_runtime.get("policy_decisions"))
                    ),
                    "event_count": _int_or_zero(timeline.get("event_count")),
                    "iteration_count": len(_sequence(stage04_analysis.get("iterations"))),
                    "runtime_turn_count": len(
                        _sequence(stage04_analysis.get("runtime_turns"))
                    ),
                    "reused_existing": bool(packet.get("reused_existing")),
                }
            ),
        },
        "evidence_refs": _dedupe_evidence_refs(
            [
                _evidence_ref(
                    kind="inspection_packet",
                    ref=str(packet_path),
                    label=packet_path.name,
                ),
                _evidence_ref(
                    kind="pilot_summary",
                    ref=str(summary_path),
                    label=summary_path.name,
                ),
                _evidence_ref(
                    kind="workflow_run_id",
                    ref=workflow_run_id,
                    label=workflow_run_id,
                ),
                *_artifact_storage_refs(artifacts),
            ]
        ),
    }
    return report


def normalize_schedule_planning_report(
    summary: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    summary_path: Path,
    packet_path: Path,
) -> dict[str, Any]:
    pilot_id = _require_text(packet.get("pilot_id"), field_name="pilot_id")
    pilot_key = _require_text(packet.get("pilot_key"), field_name="pilot_key")
    workflow_run_id = _workflow_run_id(packet)
    openai_mode = _require_text(
        summary.get("openai_mode") or "mock",
        field_name="openai_mode",
    )
    stage_focus = _require_text(packet.get("stage_focus"), field_name="stage_focus")
    description = _require_text(packet.get("description"), field_name="description")
    seed_set_id = _optional_text(packet.get("seed_set_id")) or ""
    artifacts = _mapping_list(packet.get("artifacts"))
    execution_runtime = _mapping(packet.get("execution_runtime"))
    timeline = _mapping(packet.get("timeline"))

    report = {
        "report_id": f"schedule_planning_pilot__{pilot_key}__{pilot_id}",
        "source_kind": "schedule_planning_pilot",
        "workflow_family": "schedule_planning.v1",
        "workflow_version": 1,
        "variant": {
            "variant_id": (
                f"schedule_planning_pilot__{pilot_id}__{openai_mode}__"
                f"{stage_focus.lower()}__{seed_set_id or 'no_seed_set'}"
            ),
            "workflow_family": "schedule_planning.v1",
            "workflow_version": 1,
            "execution_axes": {
                "pilot_id": pilot_id,
                "openai_mode": openai_mode,
                "stage_focus": stage_focus,
                "seed_set_id": seed_set_id,
            },
        },
        "run_profile": {
            "profile_id": "schedule_planning_pilot_suite",
            "profile_kind": "pilot_suite",
        },
        "world_instance": {
            "world_id": f"pilot_run__{pilot_key}__{pilot_id}",
            "world_kind": "pilot_run",
            "environment_class": "local_eval",
            "isolation_class": "standalone_artifact_set",
        },
        "freshness": {
            "generated_at": _require_text(
                packet.get("generated_at"),
                field_name="generated_at",
            ),
            "basis_kind": "inspection_packet",
            "source_as_of": _require_text(
                packet.get("generated_at"),
                field_name="generated_at",
            ),
        },
        "summary": {
            "status": _normalize_status(summary.get("status")),
            "headline": description,
            "metrics": _compact_scalars(
                {
                    "artifact_count": len(artifacts),
                    "task_count": len(_mapping_list(packet.get("tasks"))),
                    "approval_count": len(_mapping_list(packet.get("approvals"))),
                    "flag_count": len(_mapping_list(packet.get("flags"))),
                    "pointer_count": len(_mapping_list(packet.get("pointers"))),
                    "execution_session_count": len(
                        _mapping_list(execution_runtime.get("execution_sessions"))
                    ),
                    "tool_execution_count": len(
                        _mapping_list(execution_runtime.get("tool_executions"))
                    ),
                    "policy_decision_count": len(
                        _mapping_list(execution_runtime.get("policy_decisions"))
                    ),
                    "event_count": _int_or_zero(timeline.get("event_count")),
                    "reused_existing": bool(packet.get("reused_existing")),
                }
            ),
        },
        "evidence_refs": _dedupe_evidence_refs(
            [
                _evidence_ref(
                    kind="inspection_packet",
                    ref=str(packet_path),
                    label=packet_path.name,
                ),
                _evidence_ref(
                    kind="pilot_summary",
                    ref=str(summary_path),
                    label=summary_path.name,
                ),
                _evidence_ref(
                    kind="workflow_run_id",
                    ref=workflow_run_id,
                    label=workflow_run_id,
                ),
                *_artifact_storage_refs(artifacts),
            ]
        ),
    }
    return report


def normalize_capability_certification_reports(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path,
) -> list[dict[str, Any]]:
    certification_key = _require_text(
        manifest.get("certification_key"),
        field_name="certification_key",
    )
    openai_mode = _require_text(manifest.get("openai_mode"), field_name="openai_mode")
    generated_at = _require_text(manifest.get("generated_at"), field_name="generated_at")
    reports: list[dict[str, Any]] = []

    for scenario in _mapping_list(manifest.get("scenarios")):
        scenario_id = _require_text(scenario.get("scenario_id"), field_name="scenario_id")
        scenario_label = _require_text(
            scenario.get("scenario_label"),
            field_name="scenario_label",
        )
        workflow_family = _CERTIFICATION_WORKFLOW_FAMILIES.get(scenario_id)
        if workflow_family is None:
            raise ValueError(f"unsupported certification scenario_id: {scenario_id}")
        completed_at = _optional_text(scenario.get("completed_at")) or generated_at
        invariant_summary = _mapping(scenario.get("invariant_summary"))
        run_ids = _mapping(scenario.get("run_ids"))
        artifact_paths = _string_list(scenario.get("artifact_paths"))
        output_bundle_path = _optional_text(scenario.get("output_bundle_path"))
        entrypoint_commands = _sequence(scenario.get("entrypoint_commands"))
        edge_execution_ids = _string_list(scenario.get("edge_execution_ids"))

        report = {
            "report_id": (
                f"current_capability_certification__{certification_key}__{scenario_id}"
            ),
            "source_kind": "current_capability_certification",
            "workflow_family": workflow_family,
            "workflow_version": 1,
            "variant": {
                "variant_id": (
                    f"current_capability_certification__{scenario_id}__{openai_mode}"
                ),
                "workflow_family": workflow_family,
                "workflow_version": 1,
                "execution_axes": {
                    "scenario_id": scenario_id,
                    "scenario_label": scenario_label,
                    "openai_mode": openai_mode,
                },
            },
            "run_profile": {
                "profile_id": "current_capability_certification",
                "profile_kind": "certification_suite",
            },
            "world_instance": {
                "world_id": (
                    f"certification_scenario__{certification_key}__{scenario_id}"
                ),
                "world_kind": "certification_scenario",
                "environment_class": "local_eval",
                "isolation_class": "standalone_artifact_set",
            },
            "freshness": {
                "generated_at": generated_at,
                "basis_kind": "certification_manifest",
                "source_as_of": completed_at,
            },
            "summary": {
                "status": _normalize_status(scenario.get("status")),
                "headline": scenario_label,
                "metrics": _compact_scalars(
                    {
                        "invariant_passed": _int_or_zero(
                            invariant_summary.get("passed")
                        ),
                        "invariant_failed": _int_or_zero(
                            invariant_summary.get("failed")
                        ),
                        "invariant_total": _int_or_zero(
                            invariant_summary.get("total")
                        ),
                        "entrypoint_command_count": len(entrypoint_commands),
                        "edge_execution_count": len(edge_execution_ids),
                        "artifact_path_count": len(artifact_paths),
                        "has_output_bundle": bool(output_bundle_path),
                        "has_error": bool(_mapping(scenario.get("error"))),
                    }
                ),
            },
            "evidence_refs": _dedupe_evidence_refs(
                [
                    _evidence_ref(
                        kind="certification_manifest",
                        ref=str(manifest_path),
                        label=manifest_path.name,
                    ),
                    _evidence_ref(
                        kind="scenario_id",
                        ref=scenario_id,
                        label=scenario_label,
                    ),
                    *_run_id_refs(run_ids),
                    *(
                        [
                            _evidence_ref(
                                kind="output_bundle_path",
                                ref=output_bundle_path,
                                label="output bundle",
                            )
                        ]
                        if output_bundle_path
                        else []
                    ),
                    *[
                        _evidence_ref(
                            kind="artifact_path",
                            ref=artifact_path,
                            label=Path(artifact_path).name,
                        )
                        for artifact_path in artifact_paths
                    ],
                ]
            ),
        }
        reports.append(report)

    return reports


def render_workflow_lab_review_packet(report: Mapping[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    variant = _mapping(report.get("variant"))
    run_profile = _mapping(report.get("run_profile"))
    world_instance = _mapping(report.get("world_instance"))
    freshness = _mapping(report.get("freshness"))
    metrics = _mapping(summary.get("metrics"))
    evidence_refs = _mapping_list(report.get("evidence_refs"))

    lines = [
        "# Workflow Lab Review Packet",
        "",
        f"- Report ID: `{report['report_id']}`",
        f"- Source kind: `{report['source_kind']}`",
        f"- Workflow family: `{report['workflow_family']}`",
        f"- Workflow version: `{report['workflow_version']}`",
        f"- Status: `{summary['status']}`",
    ]
    headline = _optional_text(summary.get("headline"))
    if headline:
        lines.append(f"- Headline: {headline}")

    lines.extend(
        [
            "",
            "## Variant",
            "",
            f"- Variant ID: `{variant['variant_id']}`",
        ]
    )
    for key, value in sorted(_mapping(variant.get("execution_axes")).items()):
        lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Run Profile",
            "",
            f"- Profile ID: `{run_profile['profile_id']}`",
            f"- Profile kind: `{run_profile['profile_kind']}`",
            "",
            "## World",
            "",
            f"- World ID: `{world_instance['world_id']}`",
            f"- World kind: `{world_instance['world_kind']}`",
            f"- Environment class: `{world_instance['environment_class']}`",
            f"- Isolation class: `{world_instance['isolation_class']}`",
            "",
            "## Freshness",
            "",
            f"- Generated at: `{freshness['generated_at']}`",
            f"- Basis kind: `{freshness['basis_kind']}`",
            f"- Source as of: `{freshness['source_as_of']}`",
        ]
    )

    if metrics:
        lines.extend(["", "## Metrics", ""])
        for key, value in sorted(metrics.items()):
            lines.append(f"- {key}: `{value}`")

    if evidence_refs:
        lines.extend(["", "## Evidence", ""])
        for ref in evidence_refs:
            label = _optional_text(ref.get("label"))
            if label:
                lines.append(
                    f"- `{ref['kind']}`: `{ref['ref']}` ({label})"
                )
            else:
                lines.append(f"- `{ref['kind']}`: `{ref['ref']}`")

    return "\n".join(lines) + "\n"


def write_workflow_lab_artifacts(
    report: Mapping[str, Any],
    *,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / WORKFLOW_LAB_RUN_REPORT_FILENAME
    review_packet_path = output_dir / WORKFLOW_LAB_REVIEW_PACKET_FILENAME

    report_path.write_text(
        json.dumps(dict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    review_packet_path.write_text(
        render_workflow_lab_review_packet(report),
        encoding="utf-8",
    )
    return {
        "workflow_lab_run_report_path": str(report_path),
        "workflow_lab_review_packet_path": str(review_packet_path),
    }


def _artifact_storage_refs(artifacts: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for artifact in artifacts:
        storage_uri = _optional_text(artifact.get("storage_uri"))
        if not storage_uri:
            continue
        refs.append(
            _evidence_ref(
                kind="artifact_storage_uri",
                ref=storage_uri,
                label=_optional_text(artifact.get("artifact_kind")) or "artifact",
            )
        )
    return refs


def _run_id_refs(run_ids: Mapping[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for key, value in sorted(run_ids.items()):
        text = _optional_text(value)
        if not text:
            continue
        kind = "workflow_run_id" if key == "workflow_run_id" else "run_id"
        refs.append(_evidence_ref(kind=kind, ref=text, label=key))
    return refs


def _evidence_ref(*, kind: str, ref: str, label: str | None = None) -> dict[str, str]:
    payload = {"kind": kind, "ref": ref}
    if label:
        payload["label"] = label
    return payload


def _workflow_run_id(packet: Mapping[str, Any]) -> str:
    workflow_run = _mapping(packet.get("workflow_run"))
    return _require_text(workflow_run.get("workflow_run_id"), field_name="workflow_run_id")


def _normalize_status(value: Any) -> str:
    text = _require_text(value, field_name="status").lower()
    if text == "ok":
        return "passed"
    if text in {"pass", "passed"}:
        return "passed"
    if text in {"fail", "failed", "error"}:
        return "failed"
    return text


def _dedupe_evidence_refs(refs: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str | None]] = set()
    for ref in refs:
        kind = _require_text(ref.get("kind"), field_name="kind")
        text = _require_text(ref.get("ref"), field_name="ref")
        label = _optional_text(ref.get("label"))
        key = (kind, text, label)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(_evidence_ref(kind=kind, ref=text, label=label))
    return deduped


def _compact_scalars(values: Mapping[str, Any]) -> dict[str, Any]:
    compacted: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, (bool, int, float, str)):
            compacted[key] = value
    return compacted


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return result
    for item in value:
        if isinstance(item, Mapping):
            result.append(dict(item))
    return result


def _sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    strings: list[str] = []
    for item in value:
        text = _optional_text(item)
        if text:
            strings.append(text)
    return strings


def _require_text(value: Any, *, field_name: str) -> str:
    text = _optional_text(value)
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _int_or_zero(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
