from __future__ import annotations

from dataclasses import dataclass
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
for search_path in (ROOT, SRC_ROOT):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

TASK_FRONTMATTER_PATTERN = re.compile(r"(?s)\A---\n(.*?)\n---(?:\n|$)")
TASK_ID_PATTERN = re.compile(r"TASK-\d{4}")
RELEASE_SOURCE_BUNDLE = "release_source_bundle"
RELEASE_DISTRIBUTION_CLASS = "operator_release"
SOURCE_BUNDLE_EXCLUDED_ROOT_PREFIXES = (
    "artifacts/",
    ".onetruth_artifacts/",
    "frontend/node_modules/",
    "frontend/dist/",
    "frontend/.vite/",
    "frontend/coverage/",
    ".git/",
    ".tmp/",
)
SOURCE_BUNDLE_EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        ".tmp",
        ".pytest_cache",
        ".idea",
        ".mypy_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
    }
)
SOURCE_BUNDLE_EXCLUDED_FILE_PATTERNS = (
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.db",
    "*.db-*",
    "*.sqlite",
    "*.sqlite-*",
    "*.sqlite3",
    "*.sqlite3-*",
)


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class Collector:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks: list[str] = []

    def ok(self, msg: str) -> None:
        self.checks.append(msg)

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def require(self, cond: bool, msg: str) -> None:
        if cond:
            self.ok(msg)
        else:
            self.fail(msg)

    def report(self) -> int:
        if self.errors:
            print("VALIDATION FAILED\n")
            for error in self.errors:
                print(f"- {error}")
            print(f"\n{len(self.errors)} error(s), {len(self.checks)} check(s) passed")
            return 1
        print("VALIDATION PASSED\n")
        for check in self.checks:
            print(f"- {check}")
        print(f"\n{len(self.checks)} check(s) passed")
        return 0


@dataclass
class AssuranceState:
    collector: Collector
    indexes: dict[str, Any] | None = None
    event_map: dict[str, Any] | None = None


def validate_against_schema(path: Path, schema_path: Path, collector: Collector) -> Any:
    document = load_yaml(path) if path.suffix in {".yaml", ".yml"} else load_json(path)
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        for error in errors:
            collector.fail(
                f"{path.relative_to(ROOT)} violates {schema_path.relative_to(ROOT)}: "
                f"{error.message}"
            )
    else:
        collector.ok(
            f"{path.relative_to(ROOT)} validates against {schema_path.relative_to(ROOT)}"
        )
    return document


def validate_schema_file(schema_path: Path, collector: Collector) -> None:
    try:
        Draft202012Validator.check_schema(load_json(schema_path))
    except Exception as exc:  # pragma: no cover - defensive
        collector.fail(f"Invalid JSON schema {schema_path.relative_to(ROOT)}: {exc}")
    else:
        collector.ok(f"Schema parses: {schema_path.relative_to(ROOT)}")


def workflow_pack_paths() -> list[Path]:
    return sorted((ROOT / "docs" / "workflows").glob("*/v1/WORKFLOW_CONTRACT.yaml"))


def has_egg_info_segment(parts: tuple[str, ...]) -> bool:
    return any(part.endswith(".egg-info") for part in parts)


def source_bundle_path_is_excluded(relative_path: str) -> bool:
    posix_path = PurePosixPath(relative_path)
    file_name = posix_path.name
    if has_egg_info_segment(posix_path.parts):
        return True
    if any(part in SOURCE_BUNDLE_EXCLUDED_DIR_NAMES for part in posix_path.parts):
        return True
    if any(
        relative_path == prefix[:-1] or relative_path.startswith(prefix)
        for prefix in SOURCE_BUNDLE_EXCLUDED_ROOT_PREFIXES
    ):
        return True
    if file_name == ".env" or file_name.startswith(".env."):
        return True
    return any(posix_path.match(pattern) for pattern in SOURCE_BUNDLE_EXCLUDED_FILE_PATTERNS)
