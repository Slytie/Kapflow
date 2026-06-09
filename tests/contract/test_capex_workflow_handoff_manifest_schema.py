from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "runtime" / "capex_workflow_handoff_manifest.schema.json"


def _example_manifest() -> dict[str, object]:
    return {
        "manifest_id": "hm-example",
        "schema_version": "capex.workflow_handoff_manifest.v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-example",
        "source_workflow_run_id": "wr-source",
        "target_workflow_id": "capex.assumption_closure.v1",
        "target_workflow_version": "v1",
        "target_partition_key": "project:cp-example",
        "artifact_versions": [
            {
                "artifact_version_id": "av-source",
                "artifact_kind": "capex.source.validation.packet",
                "content_digest": "sha256-example",
            }
        ],
        "pointers": [
            {
                "pointer_id": "ptr-source",
                "pointer_key": "official:source-validation",
                "artifact_version_id": "av-source",
                "generation": 0,
            }
        ],
        "source_refs": ["source_occurrence:so-example"],
        "validation_summaries": [
            {
                "validation_id": "validation-source",
                "result": "pass",
                "summary": "Sanitized source basis is present.",
            }
        ],
        "closure_gate_evaluation_ids": ["cge-example"],
        "closure_snapshot_ids": ["cs-example"],
        "task_handoff_bindings": [
            {
                "binding_id": "task-binding",
                "task_kind": "capex.review_source_basis",
                "basis_ref": "av-source",
            }
        ],
        "workpage_handoff_bindings": [
            {
                "binding_id": "workpage-binding",
                "workpage_kind": "capex-source-review-v0",
                "basis_ref": "ptr-source",
            }
        ],
        "basis_version_vector_json": {
            "basis_refs": [
                "source_occurrence:so-example",
                "artifact_version:av-source",
                "pointer:ptr-source:0",
            ]
        },
        "metadata_json": {"activation_allowed": False},
    }


def test_capex_workflow_handoff_manifest_schema_accepts_internal_contract_example() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator(schema).validate(_example_manifest())


def test_capex_workflow_handoff_manifest_schema_requires_exact_basis_surfaces() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    manifest = _example_manifest()
    manifest["pointers"] = []

    errors = list(Draft202012Validator(schema).iter_errors(manifest))

    assert any("should be non-empty" in error.message for error in errors)


def test_capex_workflow_handoff_manifest_schema_has_no_raw_corpus_markers() -> None:
    content = SCHEMA_PATH.read_text()

    forbidden = ("K12", "K3", "blind", "raw corpus", "ocr", "screenshot")
    assert not any(marker.lower() in content.lower() for marker in forbidden)
