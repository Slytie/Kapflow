from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = REPO_ROOT / "docs" / "domains" / "logistics" / "DOC_INVENTORY.yaml"
CLASSIFICATIONS = {"normative", "descriptive", "historical"}


def _inventory_entries() -> list[dict[str, object]]:
    inventory = yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert inventory["domain"] == "logistics"
    entries = inventory["entries"]
    assert isinstance(entries, list)
    return entries


def test_logistics_doc_inventory_paths_exist_and_have_valid_classifications() -> None:
    entries = _inventory_entries()
    seen_paths: set[str] = set()

    for entry in entries:
        path = str(entry["path"])
        classification = str(entry["classification"])
        assert classification in CLASSIFICATIONS
        assert path not in seen_paths
        seen_paths.add(path)
        assert (REPO_ROOT / path).exists(), path


def test_moved_logistics_docs_have_document_classification_headers() -> None:
    missing_headers: list[str] = []
    for path in sorted((REPO_ROOT / "docs" / "domains" / "logistics").rglob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        if "Document classification:" not in text.splitlines()[0]:
            missing_headers.append(str(path.relative_to(REPO_ROOT)))

    assert missing_headers == []


def test_logistics_planning_docs_are_not_left_orphaned_in_planning_dir() -> None:
    leftovers = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "docs" / "planning").glob("*.md*")
        if path.name.startswith(("LOGISTICS_", "WORKPAGES_POST_EPIC131"))
        or path.name in {
            "CONTINUOUS_SCHEDULE_CONTROL_ARTIFACTS.md",
            "REALISTIC_SCHEDULE_PLANNING_PILOT.md",
        }
    )

    assert leftovers == []
