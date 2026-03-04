from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from onetruth.application.handlers.workflow_task_lifecycle import show_workflow_run_command
from onetruth.infrastructure.db.session import open_sqlite_connection
from tests.runtime.helpers.runtime_cli import REPO_ROOT, SRC_ROOT

REQUIRED_BUNDLE_FILES = {
    "README.md",
    "workspace_projection.json",
    "workflow_summary.json",
    "tasks.json",
    "approvals.json",
    "flags.json",
    "execution_sessions.json",
    "tool_executions.json",
    "policy_decisions.json",
    "timeline_excerpt.json",
    "artifact_manifest.json",
    "official_outputs.json",
    "graph_nodes.json",
    "graph_edges.json",
}


def _run_demo(tmp_path: Path, *, scenario: str) -> tuple[str, dict[str, object]]:
    db_url = f"sqlite:///{tmp_path / 'workspace-demo.db'}"
    output_json_path = tmp_path / "demo_output.json"
    result = _run_script(
        [
            "scripts/run_schedule_workspace_demo.py",
            "--db-url",
            db_url,
            "--scenario",
            scenario,
            "--pilot-key",
            "tests-workspace-demo",
            "--output-root",
            str(tmp_path / "demo_artifacts"),
            "--output-json",
            str(output_json_path),
        ]
    )
    payload = json.loads(result.stdout)
    assert output_json_path.exists()
    from_file = json.loads(output_json_path.read_text(encoding="utf-8"))
    assert from_file["workflow_run_id"] == payload["workflow_run_id"]
    return db_url, payload


def _run_export(tmp_path: Path, *, db_url: str, workflow_run_id: str) -> tuple[Path, dict[str, object]]:
    bundle_path = tmp_path / "workspace_bundle.zip"
    result = _run_script(
        [
            "scripts/export_run_workspace_bundle.py",
            "--db-url",
            db_url,
            "--workflow-run-id",
            workflow_run_id,
            "--output",
            str(bundle_path),
        ]
    )
    payload = json.loads(result.stdout)
    return bundle_path, payload


def _run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = str(SRC_ROOT)
    result = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"script failed ({result.returncode})\nCMD: {' '.join(args)}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    return result


def test_demo_runner_creates_real_workflow_run_and_emits_run_id(tmp_path: Path) -> None:
    db_url, payload = _run_demo(tmp_path, scenario="stage06_publish_ready")
    workflow_run_id = str(payload["workflow_run_id"])
    assert workflow_run_id
    assert payload["scenario"] == "stage06_publish_ready"
    assert payload["recommended_ui_url"] == f"/runs/{workflow_run_id}/workspace"

    connection = open_sqlite_connection(db_url)
    try:
        workflow_run = show_workflow_run_command(connection, workflow_run_id)
    finally:
        connection.close()
    assert workflow_run["workflow_run_id"] == workflow_run_id


def test_export_bundle_zip_is_created(tmp_path: Path) -> None:
    db_url, demo_payload = _run_demo(tmp_path, scenario="stage06_publish_ready")
    workflow_run_id = str(demo_payload["workflow_run_id"])
    bundle_path, export_payload = _run_export(
        tmp_path,
        db_url=db_url,
        workflow_run_id=workflow_run_id,
    )
    assert bundle_path.exists()
    assert export_payload["status"] == "ok"
    assert export_payload["workflow_run_id"] == workflow_run_id


def test_export_bundle_contains_required_files(tmp_path: Path) -> None:
    db_url, demo_payload = _run_demo(tmp_path, scenario="stage06_needs_information")
    workflow_run_id = str(demo_payload["workflow_run_id"])
    bundle_path, _ = _run_export(
        tmp_path,
        db_url=db_url,
        workflow_run_id=workflow_run_id,
    )

    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = set(archive.namelist())
    assert REQUIRED_BUNDLE_FILES.issubset(names)


def test_export_bundle_readme_references_workflow_run_id(tmp_path: Path) -> None:
    db_url, demo_payload = _run_demo(tmp_path, scenario="stage07_major_replan")
    workflow_run_id = str(demo_payload["workflow_run_id"])
    bundle_path, _ = _run_export(
        tmp_path,
        db_url=db_url,
        workflow_run_id=workflow_run_id,
    )

    with zipfile.ZipFile(bundle_path, "r") as archive:
        readme = archive.read("README.md").decode("utf-8")
    assert workflow_run_id in readme
