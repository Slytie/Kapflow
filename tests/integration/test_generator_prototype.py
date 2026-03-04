from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from onetruth.infrastructure.generation.prototype import (
    GenerationError,
    check_workflow_prototype,
    generate_workflow_prototype,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ID = "schedule_planning.v1"


def _workflow_pack_dir(repo_root: Path) -> Path:
    return repo_root / "docs" / "workflows" / "schedule_planning" / "v1"


def _output_root(repo_root: Path) -> Path:
    return repo_root / "build" / "generated"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    assert isinstance(value, dict)
    return value


def _copy_schedule_sources(tmp_path: Path) -> Path:
    target_repo = tmp_path / "repo"
    source_pack_dir = _workflow_pack_dir(REPO_ROOT)
    target_pack_dir = _workflow_pack_dir(target_repo)
    target_pack_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_pack_dir, target_pack_dir)
    return target_repo


def test_generator_outputs_include_lineage_from_repo_sources(tmp_path: Path) -> None:
    target_repo = _copy_schedule_sources(tmp_path)
    result = generate_workflow_prototype(
        repo_root=target_repo,
        workflow_id=WORKFLOW_ID,
        output_root=_output_root(target_repo),
    )

    lineage = _read_json(Path(result["lineage_path"]))
    source_paths = {entry["path"] for entry in lineage["sources"]}
    assert source_paths == {
        "docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml",
        "docs/workflows/schedule_planning/v1/ARTIFACT_MAP.yaml",
        "docs/workflows/schedule_planning/v1/DECISION_CATALOG.yaml",
        "docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml",
        "docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md",
    }
    assert all(str(entry["sha256"]).startswith("sha256:") for entry in lineage["sources"])
    assert lineage["workflow_id"] == WORKFLOW_ID
    assert lineage["workflow_version"] == "v1"
    assert lineage["generator_version"] == "prototype-v1"


def test_generator_ir_does_not_invent_ids_or_keys(tmp_path: Path) -> None:
    target_repo = _copy_schedule_sources(tmp_path)
    result = generate_workflow_prototype(
        repo_root=target_repo,
        workflow_id=WORKFLOW_ID,
        output_root=_output_root(target_repo),
    )
    generated_ir = _read_json(Path(result["ir_path"]))

    workflow_contract = yaml.safe_load(
        (_workflow_pack_dir(target_repo) / "WORKFLOW_CONTRACT.yaml").read_text(encoding="utf-8")
    )
    decision_catalog = yaml.safe_load(
        (_workflow_pack_dir(target_repo) / "DECISION_CATALOG.yaml").read_text(encoding="utf-8")
    )
    artifact_map = yaml.safe_load(
        (_workflow_pack_dir(target_repo) / "ARTIFACT_MAP.yaml").read_text(encoding="utf-8")
    )

    source_stage_ids = {stage["id"] for stage in workflow_contract["stages"]}
    generated_stage_ids = {stage["stage_id"] for stage in generated_ir["stages"]}
    assert generated_stage_ids == source_stage_ids

    source_decision_ids = {decision["id"] for decision in decision_catalog["catalog"]["decisions"]}
    generated_decision_ids = {decision["id"] for decision in generated_ir["decisions"]}
    assert generated_decision_ids == source_decision_ids

    source_artifact_keys = {
        item["key"]
        for stage_items in artifact_map["artifact_sets"].values()
        for item in stage_items
    }
    generated_artifact_keys = {
        item["key"]
        for stage_items in generated_ir["artifacts"]["artifact_sets"].values()
        for item in stage_items
    }
    assert generated_artifact_keys == source_artifact_keys


def test_generator_check_fails_when_source_changes_without_regeneration(tmp_path: Path) -> None:
    target_repo = _copy_schedule_sources(tmp_path)
    generate_workflow_prototype(
        repo_root=target_repo,
        workflow_id=WORKFLOW_ID,
        output_root=_output_root(target_repo),
    )

    check_workflow_prototype(
        repo_root=target_repo,
        workflow_id=WORKFLOW_ID,
        output_root=_output_root(target_repo),
    )

    acceptance_criteria_path = _workflow_pack_dir(target_repo) / "ACCEPTANCE_CRITERIA.md"
    acceptance_criteria_path.write_text(
        acceptance_criteria_path.read_text(encoding="utf-8")
        + "\n- [ ] temporary stale edit for test\n",
        encoding="utf-8",
    )

    with pytest.raises(GenerationError):
        check_workflow_prototype(
            repo_root=target_repo,
            workflow_id=WORKFLOW_ID,
            output_root=_output_root(target_repo),
        )


def test_runbook_renders_spawn_rules_and_follow_on_semantics(tmp_path: Path) -> None:
    target_repo = _copy_schedule_sources(tmp_path)
    result = generate_workflow_prototype(
        repo_root=target_repo,
        workflow_id=WORKFLOW_ID,
        output_root=_output_root(target_repo),
    )
    runbook_text = Path(result["runbook_path"]).read_text(encoding="utf-8")

    assert "Generated artifact (non-authoritative)" in runbook_text
    assert "stage06_final_publish_review" in runbook_text
    assert "stage06_request_missing_information" in runbook_text
    assert "stage07_final_replan_review" in runbook_text
    assert "bounded_exception_loop" in runbook_text
    assert "Stage06 publishes a stable base schedule as an official promoted artifact." in runbook_text
