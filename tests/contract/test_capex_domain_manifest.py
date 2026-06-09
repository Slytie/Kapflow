from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from onetruth.capex_platform.domain_runtime import load_domain_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
CAPEX_MANIFEST_PATH = REPO_ROOT / "docs" / "domains" / "capex" / "domain.yaml"

EXPECTED_DISABLED_CAPABILITIES = {
    "capex.production_pilot_activation",
    "capex.runtime_activation",
    "capex.source_data_governance",
    "capex.workflow_catalog",
    "capex.workpages",
}
EXPECTED_PREREQUISITES = {
    "capex.interface_burden_policy",
    "capex.production_preflight",
    "capex.project_authorization_model",
    "capex.semantic_quality_gate",
    "capex.source_occurrence_governance",
    "capex.storage_custody_gate",
    "capex.workflow_catalog",
    "capex.workpage_projection_family",
}

RAW_CORPUS_MARKERS = (
    "projektordner",
    "reference project",
    "blind-validation",
    "alma ruma",
    "11639 otc",
    "k12 primary",
    "k3 primary",
)


def _manifest_mapping() -> dict[str, Any]:
    payload = yaml.safe_load(CAPEX_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for key, child in value.items():
            strings.extend(_iter_strings(key))
            strings.extend(_iter_strings(child))
        return strings
    if isinstance(value, list):
        strings = []
        for child in value:
            strings.extend(_iter_strings(child))
        return strings
    return []


def test_capex_domain_manifest_is_incubation_with_no_runtime_inventory() -> None:
    manifest = load_domain_manifest(CAPEX_MANIFEST_PATH)

    assert manifest.domain_id == "capex"
    assert manifest.readiness == "incubation"
    assert manifest.workflows == ()
    assert manifest.workpages == ()
    assert manifest.side_effects == ()
    assert {
        capability.capability_id for capability in manifest.disabled_capabilities
    } == EXPECTED_DISABLED_CAPABILITIES
    assert {
        prerequisite.prerequisite_id
        for prerequisite in manifest.readiness_prerequisites
    } == EXPECTED_PREREQUISITES


def test_capex_domain_manifest_source_refs_stay_in_planning_or_architecture() -> None:
    manifest = load_domain_manifest(CAPEX_MANIFEST_PATH)

    assert manifest.source_refs
    for source_ref in manifest.source_refs:
        assert source_ref.path.startswith(
            ("docs/planning/", "docs/architecture/")
        ), source_ref.path
        assert (REPO_ROOT / source_ref.path).exists(), source_ref.path


def test_capex_domain_manifest_prerequisites_link_future_tasks() -> None:
    manifest = load_domain_manifest(CAPEX_MANIFEST_PATH)
    prerequisite_task_refs = {
        task_ref
        for prerequisite in manifest.readiness_prerequisites
        for task_ref in prerequisite.task_refs
    }

    assert {
        "TASK-0385",
        "TASK-0386",
        "TASK-0387",
        "TASK-0388",
        "TASK-0391",
        "TASK-0563",
        "TASK-0568",
        "TASK-0569",
        "TASK-0283",
        "TASK-0289",
    } <= prerequisite_task_refs
    assert all(task_ref.startswith("TASK-") for task_ref in prerequisite_task_refs)


def test_capex_domain_manifest_has_no_raw_corpus_paths_or_content() -> None:
    lowered_strings = [value.lower() for value in _iter_strings(_manifest_mapping())]

    leaks = sorted(
        {
            marker
            for marker in RAW_CORPUS_MARKERS
            if any(marker in value for value in lowered_strings)
        }
    )

    assert leaks == []
