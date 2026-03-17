from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas" / "workflow_lab"
SCHEMA_PACK_DOC_PATH = REPO_ROOT / "docs" / "workflow_lab" / "SCHEMA_PACK.md"
WORKFLOW_LAB_README_PATH = REPO_ROOT / "docs" / "workflow_lab" / "README.md"
WORKFLOW_LAB_PHASED_PLAN_PATH = REPO_ROOT / "docs" / "workflow_lab" / "PHASED_PLAN.md"
PLAN_PATH = REPO_ROOT / "docs" / "planning" / "PRODUCTION_AND_WORKFLOW_LAB_PLAN.md"
SCHEMA_GOVERNANCE_PATH = REPO_ROOT / "scripts" / "repo_assurance" / "schema_governance.py"

EXPECTED_SCHEMA_FILES = {
    "compare_report.schema.json",
    "freshness.schema.json",
    "run_profile.schema.json",
    "run_report_core.schema.json",
    "variant_spec.schema.json",
    "world_instance.schema.json",
}


def _load_json(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{path} must parse as a JSON object"
    return loaded


def test_workflow_lab_schema_pack_exists_and_stays_thin() -> None:
    assert SCHEMA_DIR.exists()
    assert SCHEMA_DIR.is_dir()
    assert {path.name for path in SCHEMA_DIR.glob("*.schema.json")} == EXPECTED_SCHEMA_FILES

    schema_pack_doc = SCHEMA_PACK_DOC_PATH.read_text(encoding="utf-8")
    readme = WORKFLOW_LAB_README_PATH.read_text(encoding="utf-8")
    phased_plan = WORKFLOW_LAB_PHASED_PLAN_PATH.read_text(encoding="utf-8")
    production_lab_plan = PLAN_PATH.read_text(encoding="utf-8")

    assert "non-authoritative evidence contracts" in schema_pack_doc
    assert "`pilot_summary`" in schema_pack_doc
    assert "`inspection_packet`" in schema_pack_doc
    assert "`certification_manifest`" in schema_pack_doc
    assert "does **not** add adapters, runtime APIs, execution machinery" in schema_pack_doc
    assert "semantic-version comparison" in schema_pack_doc
    assert "not production truth" in schema_pack_doc

    assert "SCHEMA_PACK.md" in readme

    assert "TASK-0118" in phased_plan
    assert "TASK-0119" in phased_plan
    assert "TASK-0121" in phased_plan
    assert "TASK-0122" in phased_plan
    assert "gated on `G1`" in phased_plan
    assert "gated on `G2`" in phased_plan

    assert "schemas/workflow_lab/" in production_lab_plan
    assert "Workflow Lab core schema pack now exists" in production_lab_plan


def test_workflow_lab_schema_shapes_and_validator_wiring() -> None:
    freshness = _load_json(SCHEMA_DIR / "freshness.schema.json")
    variant_spec = _load_json(SCHEMA_DIR / "variant_spec.schema.json")
    run_profile = _load_json(SCHEMA_DIR / "run_profile.schema.json")
    world_instance = _load_json(SCHEMA_DIR / "world_instance.schema.json")
    run_report_core = _load_json(SCHEMA_DIR / "run_report_core.schema.json")
    compare_report = _load_json(SCHEMA_DIR / "compare_report.schema.json")

    assert freshness["required"] == ["generated_at", "basis_kind", "source_as_of"]

    assert variant_spec["required"] == [
        "variant_id",
        "workflow_family",
        "workflow_version",
        "execution_axes",
    ]
    assert set(variant_spec["properties"]["execution_axes"]["additionalProperties"]["type"]) == {
        "boolean",
        "number",
        "string",
    }

    assert run_profile["required"] == ["profile_id", "profile_kind"]
    assert world_instance["required"] == [
        "world_id",
        "world_kind",
        "environment_class",
        "isolation_class",
    ]

    assert run_report_core["required"] == [
        "report_id",
        "source_kind",
        "workflow_family",
        "workflow_version",
        "variant",
        "run_profile",
        "world_instance",
        "freshness",
        "summary",
        "evidence_refs",
    ]
    assert run_report_core["properties"]["variant"]["$ref"] == "variant_spec.schema.json"
    assert run_report_core["properties"]["run_profile"]["$ref"] == "run_profile.schema.json"
    assert run_report_core["properties"]["world_instance"]["$ref"] == "world_instance.schema.json"
    assert run_report_core["properties"]["freshness"]["$ref"] == "freshness.schema.json"

    assert compare_report["required"] == [
        "compare_report_id",
        "comparison_target_kind",
        "left_report_id",
        "right_report_id",
        "freshness",
        "summary",
        "evidence_refs",
    ]
    assert compare_report["properties"]["freshness"]["$ref"] == "freshness.schema.json"

    schema_governance = SCHEMA_GOVERNANCE_PATH.read_text(encoding="utf-8")
    assert "validate_workflow_lab_schema_surfaces" in schema_governance
    assert 'ROOT / "schemas" / "workflow_lab"' in schema_governance
    for file_name in EXPECTED_SCHEMA_FILES:
        assert file_name in schema_governance
