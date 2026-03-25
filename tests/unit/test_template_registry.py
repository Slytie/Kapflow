from __future__ import annotations

from pathlib import Path

import pytest

from onetruth.application.services.template_registry import (
    discover_template_registry_paths,
    load_template_registry_catalog,
)
from tests.helpers.repo_paths import REPO_ROOT


def test_discover_template_registry_paths_includes_dispatch_reporting_registry() -> None:
    registry_paths = discover_template_registry_paths(REPO_ROOT / "fixtures" / "workflows")
    assert REPO_ROOT / "fixtures/workflows/dispatch_reporting/template_registry.v1.yaml" in registry_paths


def test_load_template_registry_catalog_rejects_duplicate_template_ids(tmp_path: Path) -> None:
    shared_source = tmp_path / "shared.xlsx"
    shared_source.write_bytes(b"placeholder")

    first = _write_manifest(
        tmp_path / "workflow_a" / "template_registry.v1.yaml",
        workflow_id="workflow_a.v1",
        template_id="duplicate.template.v1",
        source_path=shared_source,
    )
    second = _write_manifest(
        tmp_path / "workflow_b" / "template_registry.v1.yaml",
        workflow_id="workflow_b.v1",
        template_id="duplicate.template.v1",
        source_path=shared_source,
    )

    with pytest.raises(ValueError, match="duplicate template_id across registries"):
        load_template_registry_catalog(paths=(first, second))


def test_load_template_registry_catalog_rejects_malformed_manifest(tmp_path: Path) -> None:
    bad_manifest = tmp_path / "workflow_bad" / "template_registry.v1.yaml"
    bad_manifest.parent.mkdir(parents=True, exist_ok=True)
    bad_manifest.write_text("[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="template registry manifest must be a mapping"):
        load_template_registry_catalog(paths=(bad_manifest,))


def _write_manifest(
    path: Path,
    *,
    workflow_id: str,
    template_id: str,
    source_path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "registry:",
                f"  workflow_id: {workflow_id}",
                "  version: 1",
                "  templates:",
                f"    - template_id: {template_id}",
                "      stage_id: Stage03",
                "      dataset_key: reporting.upd_draft.workbook",
                "      variant: empty",
                "      media_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f"      source_path: {source_path}",
                "      description: Temp manifest.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path
