from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from onetruth.application.services.capex_invariant_audit import (
    AuditEvaluation,
    CAPEX_INVARIANT_REGISTRY,
    CapexInvariant,
    capex_invariant_audit_exit_code,
    run_capex_invariant_audit,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def test_capex_invariant_registry_has_expected_gate_modes() -> None:
    modes = {entry.gate_mode for entry in CAPEX_INVARIANT_REGISTRY}

    assert modes == {"hard_gate", "known_gap"}
    assert sum(1 for entry in CAPEX_INVARIANT_REGISTRY if entry.gate_mode == "hard_gate") == 6
    assert sum(1 for entry in CAPEX_INVARIANT_REGISTRY if entry.gate_mode == "known_gap") == 4
    assert all(entry.task_refs for entry in CAPEX_INVARIANT_REGISTRY)


def test_capex_invariant_audit_report_records_known_gaps_without_failing(
    tmp_path: Path,
) -> None:
    manifest = run_capex_invariant_audit(
        repo_root=REPO_ROOT,
        output_root=tmp_path / "audit",
        now_iso="2026-06-02T00:00:00Z",
    )

    assert manifest["status"] == "passed"
    assert capex_invariant_audit_exit_code(manifest) == 0
    assert manifest["summary"] == {
        "total": 10,
        "hard_gate_passed": 6,
        "hard_gate_failed": 0,
        "known_gaps": 4,
        "advisory": 0,
    }
    statuses = {check["invariant_id"]: check["status"] for check in manifest["checks"]}
    assert statuses["capex.known_gap.approval_side_effect_coupling"] == "known_gap"
    assert statuses["capex.pr002.artifact_storage_root_confined"] == "passed"
    assert statuses["capex.pr006.run_input_edge_helpers"] == "passed"
    assert statuses["capex.pr007.platform_foundation_v0"] == "passed"

    report_paths = manifest["report_paths"]
    json_report = Path(str(report_paths["json"]))
    markdown_report = Path(str(report_paths["markdown"]))
    assert json_report.exists()
    assert markdown_report.exists()
    assert json.loads(json_report.read_text(encoding="utf-8"))["status"] == "passed"
    assert "| capex.pr001.no_active_tracked_node_modules |" in markdown_report.read_text(
        encoding="utf-8"
    )


def test_capex_invariant_audit_fails_only_for_hard_gate_failure(tmp_path: Path) -> None:
    registry = (
        CapexInvariant(
            invariant_id="test.hard_failure",
            title="hard failure",
            gate_mode="hard_gate",
            task_refs=("TASK-0000",),
            description="test hard failure",
            evaluator=lambda _repo_root: AuditEvaluation(False, {"reason": "expected"}),
        ),
        CapexInvariant(
            invariant_id="test.known_gap",
            title="known gap",
            gate_mode="known_gap",
            task_refs=("TASK-0001",),
            description="test known gap",
        ),
    )

    manifest = run_capex_invariant_audit(
        repo_root=REPO_ROOT,
        output_root=tmp_path / "audit",
        now_iso="2026-06-02T00:00:00Z",
        registry=registry,
    )

    assert manifest["status"] == "failed"
    assert capex_invariant_audit_exit_code(manifest) == 1
    assert manifest["summary"]["hard_gate_failed"] == 1
    assert manifest["summary"]["known_gaps"] == 1


def test_capex_invariant_audit_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(SRC_ROOT)
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_capex_invariant_audit.py",
            "--output-root",
            str(tmp_path / "audit"),
            "--json",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert Path(payload["report_paths"]["json"]).exists()
    assert Path(payload["report_paths"]["markdown"]).exists()


def test_capex_platform_foundation_v0_doc_records_branch_gate_and_blocked_scopes() -> None:
    path = REPO_ROOT / "docs/planning/CAPEX_PLATFORM_FOUNDATION_V0.md"
    text = path.read_text(encoding="utf-8")

    for gate_id in ("PR000", "PR001", "PR002", "PR003", "PR004", "PR005", "PR006", "PR007"):
        assert gate_id in text
    assert "foundation/ip5" in text
    assert "CAPEX production activation and pilot readiness claims remain blocked" in text
    assert "Raw K12, K3, and blind-validation corpus files" in text
    assert "Release/deploy work" in text
    assert "CAPEX project membership runtime remains blocked" in text
    assert "Source occurrence and SourceRef runtime remain blocked" in text
    assert "external/operator-managed" in text
