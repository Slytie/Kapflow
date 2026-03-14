from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE_PATH = REPO_ROOT / "Makefile"


def test_clean_source_bundle_make_alias_points_at_release_bundle() -> None:
    makefile_text = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "release-source-bundle:" in makefile_text
    assert "handoff-source-bundle:" in makefile_text
    assert "clean-source-bundle: release-source-bundle" in makefile_text
    assert (
        'scripts/export_clean_source_bundle.py --bundle-kind release_source_bundle --output "$(RELEASE_SOURCE_BUNDLE_OUTPUT)"'
        in makefile_text
    )
    assert (
        'scripts/export_clean_source_bundle.py --output "$(HANDOFF_SOURCE_BUNDLE_OUTPUT)"'
        in makefile_text
    )
