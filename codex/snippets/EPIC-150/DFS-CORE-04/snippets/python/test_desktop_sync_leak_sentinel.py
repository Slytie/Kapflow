"""Illustrative leak sentinel test.

Adapt `run_desktop_sync_fixture_with_sentinel` and surfaces to the real CAPEX test harness.
"""

from __future__ import annotations

from pathlib import Path


SENTINELS = [
    "CAPEX_SECRET_PROJECT",
    "Privileged Settlement Draft FINAL.pdf",
    "CAPEX_SENTINEL_RAW_DOCUMENT_CONTENT_9b7f7a",
    "/Users/Alice/Desktop",
    "C:\\Users\\Alice\\Desktop",
]

LEAK_SURFACES = [
    "var/log",
    "artifacts",
    "test-results",
    "generated-packs",
    "tmp/ai-prompts",
    "tmp/vector-index-debug",
]


def assert_no_sentinel_text(root: Path):
    leaks = []
    for surface in LEAK_SURFACES:
        surface_path = root / surface
        if not surface_path.exists():
            continue
        for file in surface_path.rglob("*"):
            if not file.is_file():
                continue
            try:
                text = file.read_text(errors="ignore")
            except Exception:
                continue
            for sentinel in SENTINELS:
                if sentinel in text:
                    leaks.append((str(file), sentinel))
    assert not leaks, "raw desktop/project data leaked: " + repr(leaks)


def test_desktop_sync_does_not_leak_raw_paths_or_content(tmp_path):
    run_desktop_sync_fixture_with_sentinel(tmp_path)
    assert_no_sentinel_text(tmp_path)
