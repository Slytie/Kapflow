from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from onetruth.application.services.current_capability_certification import (
    SCENARIO_LOGISTICS_WEEKLY_TO_LIVE,
    SCENARIO_STAGE06_PUBLISH_READY,
    run_current_capability_certification,
)
from onetruth.application.services.logistics_weekly_agent_pilot import (
    PILOT_WEEKLY_STAGE04_AGENT,
    run_logistics_weekly_agent_pilot_suite,
)
from onetruth.application.services.realistic_schedule_planning_pilot import (
    PILOT_STAGE06_PUBLISH_READY,
    run_realistic_schedule_planning_pilot_suite,
)
from onetruth.application.services.workflow_lab_normalization import (
    WORKFLOW_LAB_REVIEW_PACKET_FILENAME,
    WORKFLOW_LAB_RUN_REPORT_FILENAME,
    render_workflow_lab_review_packet,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO_ROOT / "schemas" / "workflow_lab"


def _run_report_validator() -> Draft202012Validator:
    registry = Registry()
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        registry = registry.with_resource(
            schema_path.name,
            Resource.from_contents(schema),
        )
    root_schema = json.loads(
        (SCHEMA_DIR / "run_report_core.schema.json").read_text(encoding="utf-8")
    )
    return Draft202012Validator(root_schema, registry=registry)


def _validate_run_report(report: dict[str, object]) -> None:
    validator = _run_report_validator()
    errors = sorted(validator.iter_errors(report), key=lambda error: list(error.path))
    assert not errors, "\n".join(str(error) for error in errors)


def test_weekly_stage04_pilot_emits_workflow_lab_run_report_and_review_packet(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    output_root = tmp_path / "weekly-output"
    artifact_root = tmp_path / "weekly-artifacts"

    connection = open_sqlite_connection(db_url)
    try:
        create_sqlite_substrate(connection)
        summary = run_logistics_weekly_agent_pilot_suite(
            connection,
            db_url=db_url,
            pilot_key="weekly-stage04-normalization",
            output_root=output_root,
            artifact_root=artifact_root,
            pilot_ids=[PILOT_WEEKLY_STAGE04_AGENT],
            openai_mode="mock",
        )
    finally:
        connection.close()

    run = summary["pilot_runs"][0]
    report_path = Path(str(run["workflow_lab_run_report_path"]))
    review_path = Path(str(run["workflow_lab_review_packet_path"]))

    assert report_path.name == WORKFLOW_LAB_RUN_REPORT_FILENAME
    assert review_path.name == WORKFLOW_LAB_REVIEW_PACKET_FILENAME
    assert report_path.exists()
    assert review_path.exists()
    assert not (report_path.parent / "workflow_lab_compare_report.json").exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    _validate_run_report(report)

    assert report["source_kind"] == "weekly_stage04_pilot"
    assert report["workflow_family"] == "weekly_schedule_planning.v1"
    assert report["summary"]["status"] == "passed"
    assert report["variant"]["execution_axes"]["pilot_id"] == PILOT_WEEKLY_STAGE04_AGENT
    assert report["variant"]["execution_axes"]["openai_mode"] == "mock"
    evidence_kinds = {item["kind"] for item in report["evidence_refs"]}
    assert "inspection_packet" in evidence_kinds
    assert "pilot_summary" in evidence_kinds
    assert "workflow_run_id" in evidence_kinds

    review_packet = review_path.read_text(encoding="utf-8")
    assert report["report_id"] in review_packet
    assert report["workflow_family"] in review_packet
    assert report["summary"]["headline"] in review_packet


def test_schedule_planning_pilot_emits_workflow_lab_run_report_and_review_packet(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    output_root = tmp_path / "schedule-output"
    artifact_root = tmp_path / "schedule-artifacts"

    connection = open_sqlite_connection(db_url)
    try:
        create_sqlite_substrate(connection)
        summary = run_realistic_schedule_planning_pilot_suite(
            connection,
            db_url=db_url,
            pilot_key="schedule-normalization",
            output_root=output_root,
            artifact_root=artifact_root,
            pilot_ids=[PILOT_STAGE06_PUBLISH_READY],
            openai_mode="mock",
        )
    finally:
        connection.close()

    run = summary["pilot_runs"][0]
    report_path = Path(str(run["workflow_lab_run_report_path"]))
    review_path = Path(str(run["workflow_lab_review_packet_path"]))
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_path.exists()
    assert review_path.exists()
    _validate_run_report(report)

    assert report["source_kind"] == "schedule_planning_pilot"
    assert report["workflow_family"] == "schedule_planning.v1"
    assert report["summary"]["status"] == "passed"
    assert report["variant"]["execution_axes"]["pilot_id"] == PILOT_STAGE06_PUBLISH_READY
    assert report["variant"]["execution_axes"]["seed_set_id"] == "stage06_review_ready_example_set"
    assert "schedule_planning.v1" in review_path.read_text(encoding="utf-8")


def test_capability_certification_emits_one_normalized_report_per_scenario(
    tmp_path: Path,
) -> None:
    def _runner_factory(suffix: str):
        def _runner(_ctx: object) -> dict[str, object]:
            bundle_path = tmp_path / f"{suffix}-bundle.zip"
            artifact_path = tmp_path / f"{suffix}-artifact.json"
            bundle_path.write_text("bundle", encoding="utf-8")
            artifact_path.write_text("{}", encoding="utf-8")
            return {
                "entrypoint_commands": [
                    {
                        "entrypoint": "fake.entrypoint",
                        "command": f"fake --scenario {suffix}",
                        "argv": ["fake", "--scenario", suffix],
                        "exit_code": 0,
                    }
                ],
                "run_ids": {"workflow_run_id": f"wr-{suffix}"},
                "edge_execution_ids": [f"edge-{suffix}"],
                "output_bundle_path": str(bundle_path),
                "artifact_paths": [str(artifact_path)],
                "invariants": [
                    {
                        "invariant_id": "fake_invariant",
                        "description": "fake invariant",
                        "status": "passed",
                        "details": {"suffix": suffix},
                    }
                ],
            }

        return _runner

    manifest = run_current_capability_certification(
        db_url=f"sqlite:///{tmp_path / 'runtime.db'}",
        certification_key="normalization-cert",
        output_root=tmp_path / "cert-output",
        openai_mode="mock",
        selected_scenarios=[
            SCENARIO_STAGE06_PUBLISH_READY,
            SCENARIO_LOGISTICS_WEEKLY_TO_LIVE,
        ],
        scenario_runners={
            SCENARIO_STAGE06_PUBLISH_READY: _runner_factory("stage06"),
            SCENARIO_LOGISTICS_WEEKLY_TO_LIVE: _runner_factory("logistics"),
        },
        now_iso="2026-03-18T00:00:00Z",
    )

    cert_root = Path(str(manifest["output_root"]))
    assert not (cert_root / WORKFLOW_LAB_RUN_REPORT_FILENAME).exists()
    assert not (cert_root / WORKFLOW_LAB_REVIEW_PACKET_FILENAME).exists()

    scenario_rows = {
        str(scenario["scenario_id"]): scenario for scenario in manifest["scenarios"]
    }
    assert set(scenario_rows) == {
        SCENARIO_STAGE06_PUBLISH_READY,
        SCENARIO_LOGISTICS_WEEKLY_TO_LIVE,
    }

    stage06_report = json.loads(
        Path(str(scenario_rows[SCENARIO_STAGE06_PUBLISH_READY]["workflow_lab_run_report_path"])).read_text(
            encoding="utf-8"
        )
    )
    logistics_report = json.loads(
        Path(str(scenario_rows[SCENARIO_LOGISTICS_WEEKLY_TO_LIVE]["workflow_lab_run_report_path"])).read_text(
            encoding="utf-8"
        )
    )

    _validate_run_report(stage06_report)
    _validate_run_report(logistics_report)

    assert stage06_report["source_kind"] == "current_capability_certification"
    assert stage06_report["workflow_family"] == "schedule_planning.v1"
    assert stage06_report["summary"]["status"] == "passed"
    assert logistics_report["workflow_family"] == "logistics_ops_family.v1"
    assert logistics_report["variant"]["execution_axes"]["scenario_id"] == (
        SCENARIO_LOGISTICS_WEEKLY_TO_LIVE
    )


def test_review_packet_renderer_consumes_normalized_report_only() -> None:
    report = {
        "report_id": "synthetic-report",
        "source_kind": "weekly_stage04_pilot",
        "workflow_family": "weekly_schedule_planning.v1",
        "workflow_version": 1,
        "variant": {
            "variant_id": "synthetic-variant",
            "workflow_family": "weekly_schedule_planning.v1",
            "workflow_version": 1,
            "execution_axes": {
                "pilot_id": "pilot-a",
                "openai_mode": "mock",
                "stage_focus": "Stage04",
            },
        },
        "run_profile": {
            "profile_id": "weekly_stage04_pilot_suite",
            "profile_kind": "pilot_suite",
        },
        "world_instance": {
            "world_id": "pilot_run__synthetic",
            "world_kind": "pilot_run",
            "environment_class": "local_eval",
            "isolation_class": "standalone_artifact_set",
        },
        "freshness": {
            "generated_at": "2026-03-18T00:00:00Z",
            "basis_kind": "inspection_packet",
            "source_as_of": "2026-03-18T00:00:00Z",
        },
        "summary": {
            "status": "passed",
            "headline": "Synthetic normalization headline",
            "metrics": {"artifact_count": 3, "reused_existing": False},
        },
        "evidence_refs": [
            {
                "kind": "inspection_packet",
                "ref": "/tmp/synthetic/inspection_packet.json",
                "label": "inspection_packet.json",
            }
        ],
    }

    rendered = render_workflow_lab_review_packet(report)

    assert "Synthetic normalization headline" in rendered
    assert "synthetic-report" in rendered
    assert "weekly_schedule_planning.v1" in rendered
    assert "artifact_count" in rendered
    assert "/tmp/synthetic/inspection_packet.json" in rendered
