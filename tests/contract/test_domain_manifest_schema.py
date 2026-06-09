from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from onetruth.capex_platform.domain_runtime import load_domain_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "domain_runtime" / "domain_manifest.schema.json"
LOGISTICS_MANIFEST_PATH = REPO_ROOT / "docs" / "domains" / "logistics" / "domain.yaml"
CAPEX_MANIFEST_PATH = REPO_ROOT / "docs" / "domains" / "capex" / "domain.yaml"

RAW_CORPUS_MARKERS = (
    "raw corpus",
    "raw_corpus",
    "projektordner",
    "reference project",
    "blind-validation",
    "alma ruma",
    "11639 otc",
    "k12 primary",
    "k3 primary",
)


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _logistics_manifest_mapping() -> dict[str, Any]:
    payload = yaml.safe_load(LOGISTICS_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _capex_manifest_mapping() -> dict[str, Any]:
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


def test_domain_manifest_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(_schema())


def test_logistics_domain_manifest_validates_under_domain_manifest_schema() -> None:
    Draft202012Validator(_schema()).validate(_logistics_manifest_mapping())

    manifest = load_domain_manifest(LOGISTICS_MANIFEST_PATH)
    assert manifest.domain_id == "logistics"
    assert manifest.readiness == "ready"
    assert len(manifest.workflows) == 5
    assert len(manifest.workpages) == 4
    assert len(manifest.side_effects) == 6


def test_capex_domain_manifest_validates_under_domain_manifest_schema() -> None:
    Draft202012Validator(_schema()).validate(_capex_manifest_mapping())

    manifest = load_domain_manifest(CAPEX_MANIFEST_PATH)
    assert manifest.domain_id == "capex"
    assert manifest.readiness == "incubation"
    assert len(manifest.workflows) == 0
    assert len(manifest.workpages) == 0
    assert len(manifest.side_effects) == 0
    assert len(manifest.readiness_prerequisites) == 8
    assert len(manifest.disabled_capabilities) == 5


def test_logistics_domain_manifest_has_no_raw_corpus_paths_or_content() -> None:
    lowered_strings = [
        value.lower() for value in _iter_strings(_logistics_manifest_mapping())
    ]

    leaks = sorted(
        {
            marker
            for marker in RAW_CORPUS_MARKERS
            if any(marker in value for value in lowered_strings)
        }
    )

    assert leaks == []
