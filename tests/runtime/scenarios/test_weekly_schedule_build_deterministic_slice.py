from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT
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
    assert build_result["candidate_count"] == 4
    assert build_result["selected_candidate_count"] == 2

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

    validation_summary = build_result["artifact_payloads"]["planning.validation_summary.doc"][
        "summary"
    ]
    assert validation_summary["hard_rule_result"] == "pass"
    assert validation_summary["violations"] == []

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
