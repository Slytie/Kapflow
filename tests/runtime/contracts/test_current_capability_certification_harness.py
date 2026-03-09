from __future__ import annotations

import json
from pathlib import Path

from onetruth.application.services.current_capability_certification import (
    SCENARIO_LOGISTICS_WEEKLY_TO_LIVE,
    SCENARIO_STAGE06_PUBLISH_READY,
    SCENARIO_STAGE07_MAJOR_REPLAN,
    deterministic_scenario_labels,
    run_current_capability_certification,
)


def _base_runner_result(tmp_path: Path, *, suffix: str) -> dict[str, object]:
    bundle_path = tmp_path / f"bundle-{suffix}.json"
    bundle_path.write_text("{}", encoding="utf-8")
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
        "edge_execution_ids": [],
        "output_bundle_path": str(bundle_path),
        "artifact_paths": [str(tmp_path / f"artifact-{suffix}.json")],
        "invariants": [
            {
                "invariant_id": "fake_invariant",
                "description": "fake invariant for harness tests",
                "status": "passed",
                "details": {"suffix": suffix},
            }
        ],
    }


def test_manifest_shape_is_stable_and_written(tmp_path: Path) -> None:
    scenario_runners = {
        SCENARIO_STAGE06_PUBLISH_READY: lambda _ctx: _base_runner_result(tmp_path, suffix="stage06"),
        SCENARIO_STAGE07_MAJOR_REPLAN: lambda _ctx: _base_runner_result(tmp_path, suffix="stage07"),
    }

    manifest = run_current_capability_certification(
        db_url=f"sqlite:///{tmp_path / 'runtime.db'}",
        certification_key="shape",
        output_root=tmp_path / "cert-output",
        selected_scenarios=[SCENARIO_STAGE07_MAJOR_REPLAN, SCENARIO_STAGE06_PUBLISH_READY],
        scenario_runners=scenario_runners,
        now_iso="2026-03-09T00:00:00Z",
    )

    assert manifest["status"] == "passed"
    assert manifest["manifest_version"] == 1
    assert manifest["command"] == "current-capability-certification.run"
    assert manifest["scenario_count"] == 2
    assert manifest["passed_scenarios"] == 2
    assert manifest["failed_scenarios"] == 0
    assert manifest["selected_scenarios"] == [
        SCENARIO_STAGE06_PUBLISH_READY,
        SCENARIO_STAGE07_MAJOR_REPLAN,
    ]

    scenarios = manifest["scenarios"]
    assert [scenario["scenario_id"] for scenario in scenarios] == [
        SCENARIO_STAGE06_PUBLISH_READY,
        SCENARIO_STAGE07_MAJOR_REPLAN,
    ]
    for scenario in scenarios:
        assert scenario["status"] == "passed"
        assert scenario["entrypoint_commands"]
        assert scenario["run_ids"]["workflow_run_id"].startswith("wr-")
        assert scenario["output_bundle_path"]
        assert scenario["invariant_summary"] == {"passed": 1, "failed": 0, "total": 1}

    manifest_path = Path(str(manifest["manifest_path"]))
    assert manifest_path.exists()
    from_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert from_disk["status"] == "passed"
    assert from_disk["scenario_count"] == 2


def test_deterministic_scenario_labeling_uses_canonical_order() -> None:
    labels = deterministic_scenario_labels(
        [
            SCENARIO_LOGISTICS_WEEKLY_TO_LIVE,
            SCENARIO_STAGE07_MAJOR_REPLAN,
            SCENARIO_STAGE06_PUBLISH_READY,
        ]
    )
    assert labels == (
        "schedule.stage06_publish_ready_workspace_demo",
        "schedule.stage07_major_replan_workspace_demo",
        "logistics.weekly_to_live_golden_slice",
    )


def test_manifest_fails_when_one_scenario_fails(tmp_path: Path) -> None:
    def _failing_runner(_ctx: object) -> dict[str, object]:
        raise RuntimeError("simulated failure")

    scenario_runners = {
        SCENARIO_STAGE06_PUBLISH_READY: lambda _ctx: _base_runner_result(tmp_path, suffix="ok"),
        SCENARIO_STAGE07_MAJOR_REPLAN: _failing_runner,
    }

    manifest = run_current_capability_certification(
        db_url=f"sqlite:///{tmp_path / 'runtime.db'}",
        certification_key="failure",
        output_root=tmp_path / "cert-output",
        selected_scenarios=[SCENARIO_STAGE06_PUBLISH_READY, SCENARIO_STAGE07_MAJOR_REPLAN],
        scenario_runners=scenario_runners,
        now_iso="2026-03-09T00:00:00Z",
    )

    assert manifest["status"] == "failed"
    assert manifest["passed_scenarios"] == 1
    assert manifest["failed_scenarios"] == 1
    failed = [scenario for scenario in manifest["scenarios"] if scenario["status"] == "failed"]
    assert len(failed) == 1
    assert failed[0]["scenario_id"] == SCENARIO_STAGE07_MAJOR_REPLAN
    assert failed[0]["error"]["message"] == "simulated failure"


def test_manifest_includes_bundle_paths_and_invariant_summaries_stably(tmp_path: Path) -> None:
    bundle_path = tmp_path / "stable-bundle.zip"
    bundle_path.write_text("bundle", encoding="utf-8")

    def _runner(_ctx: object) -> dict[str, object]:
        return {
            "entrypoint_commands": [],
            "run_ids": {"workflow_run_id": "wr-stable"},
            "edge_execution_ids": ["edge-stable"],
            "output_bundle_path": str(bundle_path),
            "artifact_paths": [],
            "invariants": [
                {
                    "invariant_id": "one",
                    "description": "pass",
                    "status": "passed",
                    "details": {},
                },
                {
                    "invariant_id": "two",
                    "description": "fail",
                    "status": "failed",
                    "details": {"reason": "expected"},
                },
            ],
        }

    manifest = run_current_capability_certification(
        db_url=f"sqlite:///{tmp_path / 'runtime.db'}",
        certification_key="stable-fields",
        output_root=tmp_path / "cert-output",
        selected_scenarios=[SCENARIO_LOGISTICS_WEEKLY_TO_LIVE],
        scenario_runners={SCENARIO_LOGISTICS_WEEKLY_TO_LIVE: _runner},
        now_iso="2026-03-09T00:00:00Z",
    )

    scenario = manifest["scenarios"][0]
    assert scenario["output_bundle_path"] == str(bundle_path)
    assert scenario["edge_execution_ids"] == ["edge-stable"]
    assert scenario["invariant_summary"] == {"passed": 1, "failed": 1, "total": 2}
    assert scenario["invariants"][1]["details"] == {"reason": "expected"}
