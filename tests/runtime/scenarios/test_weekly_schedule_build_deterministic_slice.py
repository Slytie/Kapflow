from __future__ import annotations

import json
from pathlib import Path

from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_realistic_weekly_stage04_fixture_payloads,
)
from tests.runtime.helpers.runtime_cli import REPO_ROOT, run_cli, stdout_json
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness


SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/weekly_schedule_build_deterministic_slice.yaml"
)


def test_weekly_schedule_build_deterministic_slice_materializes_stage04_artifacts_idempotently(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    build_result = harness.output("build_result")["result"]
    build_retry = harness.output("build_retry")["result"]

    assert build_result["bundle_id"].startswith("bundle-pw-2026-w10-stage04-")
    assert build_result["candidate_count"] >= 4
    assert build_result["selected_candidate_count"] == 2
    assert build_result["coverage_summary"]["assigned_route_slots"] == 2
    assert build_result["coverage_summary"]["uncovered_route_slots"] == 0
    assert len(build_result["iteration_summaries"]) == 1
    assert build_result["iteration_summaries"][0]["batch_size"] == 2

    selected = build_result["selected_candidates"]
    assert [
        (row["route_slot_id"], row["candidate_driver_id"], row["hard_filter_status"])
        for row in selected
    ] == [
        ("slot-20260302-cx100", "DRV-01", "pass"),
        ("slot-20260303-cx086", "DRV-01", "pass"),
    ]

    candidate_payload = build_result["artifact_payloads"][
        "planning.candidate_schedule_delta.workbook"
    ]
    assert len(candidate_payload["rows"]) == 2
    assert candidate_payload["rows"][0][4] == "DRV-01"
    assert len(candidate_payload["iteration_deltas"]) == 1

    validation_summary = build_result["artifact_payloads"]["planning.validation_summary.doc"][
        "summary"
    ]
    assert validation_summary["hard_rule_result"] == "pass"
    assert validation_summary["violations"] == []
    assert validation_summary["iteration_summary"]["iteration_count"] == 1

    assert (
        build_retry["artifacts"]["input_bundle"]["artifact_version_id"]
        == build_result["artifacts"]["input_bundle"]["artifact_version_id"]
    )
    assert (
        build_retry["artifacts"]["candidate_delta"]["artifact_version_id"]
        == build_result["artifacts"]["candidate_delta"]["artifact_version_id"]
    )

    stage04_artifact_rows = harness.query_rows(
        """
        SELECT artifact_kind, artifact_version_id
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind IN (
            'planning.input_bundle.doc',
            'planning.candidate_schedule_delta.workbook',
            'planning.validation_summary.doc',
            'planning.draft_weekly_schedule.workbook',
            'planning.draft_weekly_schedule.doc'
          )
        ORDER BY artifact_kind ASC
        """,
        (harness.workflow_run_id,),
    )
    assert len(stage04_artifact_rows) == 5

    provenance_rows = harness.query_rows(
        """
        SELECT edge_type, output_artifact_version_id
        FROM artifact_provenance_edges
        WHERE workflow_run_id = ?
          AND edge_type = 'derives_from'
        """,
        (harness.workflow_run_id,),
    )
    assert len(provenance_rows) >= 9


def test_weekly_schedule_build_realistic_source_material_emits_richer_stage04_inputs(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    fixture = build_realistic_weekly_stage04_fixture_payloads()
    workflow_run_id = _create_realistic_weekly_workflow_run(harness)

    route_slots = _create_stage04_input_artifact(
        harness=harness,
        workflow_run_id=workflow_run_id,
        step_key="realistic-route-slots",
        artifact_kind="planning.route_slot_requirements.workbook",
        metadata_json=fixture["route_slot_requirements"],
    )
    driver_caps = _create_stage04_input_artifact(
        harness=harness,
        workflow_run_id=workflow_run_id,
        step_key="realistic-driver-caps",
        artifact_kind="planning.driver_capabilities.workbook",
        metadata_json=fixture["driver_capabilities"],
    )
    availability = _create_stage04_input_artifact(
        harness=harness,
        workflow_run_id=workflow_run_id,
        step_key="realistic-availability",
        artifact_kind="planning.approved_availability.workbook",
        metadata_json=fixture["approved_availability"],
    )
    actual_hours = _create_stage04_input_artifact(
        harness=harness,
        workflow_run_id=workflow_run_id,
        step_key="realistic-actual-hours",
        artifact_kind="planning.actual_hours_snapshot.workbook",
        metadata_json=fixture["actual_hours"],
    )

    build_result = harness.run_action(
        action="schedule-control.build-weekly",
        payload={
            "workflow_run_id": workflow_run_id,
            "route_slot_requirements_artifact_version_id": route_slots["artifact_version"]["artifact_version_id"],
            "driver_capabilities_artifact_version_id": driver_caps["artifact_version"]["artifact_version_id"],
            "approved_availability_artifact_version_id": availability["artifact_version"]["artifact_version_id"],
            "actual_hours_artifact_version_id": actual_hours["artifact_version"]["artifact_version_id"],
            "idempotency_key": "scenario:weekly_schedule_build_realistic_source_material:build",
        },
    )["result"]

    assert build_result["selected_candidate_count"] == 139
    assert build_result["candidate_count"] > 139 * 40
    assert build_result["coverage_summary"]["assigned_route_slots"] == 135
    assert build_result["coverage_summary"]["uncovered_route_slots"] == 4
    assert all(
        route_slot_id.startswith("slot-20260316-std-")
        for route_slot_id in build_result["coverage_summary"]["uncovered_route_slot_ids"]
    )
    assert len(build_result["iteration_summaries"]) >= 10

    input_bundle = build_result["artifact_payloads"]["planning.input_bundle.doc"]["bundle"]
    assert len(input_bundle["driver_profiles"]) == 40
    assert len(input_bundle["route_slots"]) == 28
    assert sum(item["planned_route_count"] for item in input_bundle["demand_by_service_date"]) == 139
    assert sum(item["planned_route_count"] for item in input_bundle["demand_by_service_date"]) < (40 * 4)
    assert input_bundle["demand_by_service_date"][0]["service_date"] == "2026-03-16"
    assert input_bundle["demand_by_service_date"][-1]["service_date"] == "2026-03-22"
    assert input_bundle["deterministic_iteration_model"]["batch_size_range"] == {"min": 5, "max": 10}
    assert {"route_family", "preferred_shift_band", "projected_minutes"} <= set(
        input_bundle["route_slots"][0].keys()
    )

    profile = next(item for item in input_bundle["driver_profiles"] if item["driver_id"] == "ODRV-01")
    assert len(profile["daily_states"]) == 7
    assert len(profile["previous_week_states"]) == 7
    assert profile["daily_states"][0]["state"] == "PREFERRED"
    assert profile["daily_states"][0]["normalized_state"] == "available"
    assert profile["previous_week_states"][-1]["state"] == "NA"
    assert profile["rolling_7_compliance"]["limit_minutes"] == 2400
    assert profile["policy_signal"]["target_shifts_per_week"] == 4
    assert profile["seniority_rank"] > 0
    assert profile["attendance_reliability_index"] > 0.0

    candidate_delta = build_result["artifact_payloads"]["planning.candidate_schedule_delta.workbook"]
    assert len(candidate_delta["iteration_deltas"]) == len(build_result["iteration_summaries"])
    assert candidate_delta["coverage_summary"]["phase_counts"]["baseline"] >= 1
    assert candidate_delta["coverage_summary"]["phase_counts"]["improvement"] >= 1
    assert candidate_delta["coverage_summary"]["reallocation_move_count"] >= 1

    validation_summary = build_result["artifact_payloads"]["planning.validation_summary.doc"]["summary"]
    assert validation_summary["hard_rule_result"] == "fail"
    assert validation_summary["recommended_action"] == "request_stage04_route_gap_review"
    assert validation_summary["coverage_summary"]["uncovered_route_slots"] == 4
    assert validation_summary["coverage_summary"]["reallocation_move_count"] >= 1
    assert validation_summary["soft_score_totals"]["previous_week_stability"] > 0.0


def _create_stage04_input_artifact(
    *,
    harness: RuntimeScenarioHarness,
    workflow_run_id: str,
    step_key: str,
    artifact_kind: str,
    metadata_json: dict[str, object],
) -> dict[str, object]:
    return harness.run_action(
        action="artifacts.create-version",
        payload={
            "workflow_run_id": workflow_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": "official_input",
            "media_type": "application/json",
            "storage_uri": f"inmem://scenario/logistics/stage04/{step_key}",
            "content_digest": f"sha256:{step_key}",
            "metadata_json": metadata_json,
            "idempotency_key": f"scenario:weekly_schedule_build_realistic_source_material:{step_key}",
        },
    )


def _create_realistic_weekly_workflow_run(harness: RuntimeScenarioHarness) -> str:
    result = run_cli(
        "--db-url",
        harness.db_url,
        "runs",
        "create",
        "--json",
        json.dumps(
            {
                "workflow_id": "weekly_schedule_planning.v1",
                "workflow_version": "v1",
                "tenant_id": "tenant-logistics",
                "domain_id": "domain-hub",
                "partition_key": "PW-2026-W12",
                "logical_date": "2026-03-16",
                "activation_key": "weekly_schedule_build_realistic_source_material:workflow-run",
                "idempotency_key": "scenario:weekly_schedule_build_realistic_source_material:runs.create",
            },
            separators=(",", ":"),
        ),
    )
    return str(stdout_json(result)["workflow_run"]["workflow_run_id"])
