from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from tests.helpers.repo_paths import REPO_ROOT


TASK_FRONTMATTER_RE = re.compile(r"(?s)\A---\n(.*?)\n---(?:\n|$)")
TASK_ID_RE = re.compile(r"TASK-\d{4}")
DONE_STATUSES = {"COMPLETED", "DONE"}
OPEN_STATUSES = {"BLOCKED", "IN_PROGRESS", "NEEDS_REVIEW", "STARTED", "TODO", "WIP"}
DEPENDENCY_EXCEPTION_REASON_RE = re.compile(r"[a-z][a-z0-9_]*")
FORBIDDEN_ROOT_DEBRIS_FILENAMES = (
    ', d["proposed_copy"])',
    ', d["proposed_copy"])\n',
    ", p)",
    ", p)\n",
)


def test_task_index_statuses_match_task_frontmatter() -> None:
    frontmatter = _task_frontmatter_by_id()
    index_statuses = _task_index_statuses()

    mismatches = {
        task_id: {
            "index": index_status,
            "frontmatter": _status(frontmatter[task_id].get("status")),
        }
        for task_id, index_status in index_statuses.items()
        if task_id in frontmatter
        and index_status != _status(frontmatter[task_id].get("status"))
    }

    assert mismatches == {}


def test_done_tasks_do_not_depend_on_open_tasks_without_valid_exception() -> None:
    frontmatter = _task_frontmatter_by_id()
    violations: list[str] = []
    exception_errors: list[str] = []

    for task_id, values in sorted(frontmatter.items()):
        dependencies = _dependencies(values)
        exception_ids = _valid_dependency_exception_ids(
            task_id,
            values,
            dependencies,
            exception_errors,
        )
        if _status(values.get("status")) not in DONE_STATUSES:
            continue
        for dependency_id in dependencies:
            dependency = frontmatter.get(dependency_id)
            if dependency is None:
                continue
            dependency_status = _status(dependency.get("status"))
            if dependency_status in OPEN_STATUSES and dependency_id not in exception_ids:
                violations.append(f"{task_id} -> {dependency_id}({dependency_status})")

    assert exception_errors == []
    assert violations == []


def test_task_0299_closes_after_risk_ceo_workflow_dependency() -> None:
    frontmatter = _task_frontmatter_by_id()
    task_0299 = frontmatter["TASK-0299"]
    task_0290 = frontmatter["TASK-0290"]

    assert _status(task_0290["status"]) == "DONE"
    assert _completed_at(task_0290) == "2026-06-23T00:00:00Z"
    assert _status(task_0299["status"]) == "DONE"
    assert _completed_at(task_0299) == "2026-06-23T00:00:00Z"
    assert "TASK-0290" in _dependencies(task_0299)


def test_review_identified_root_debris_files_are_absent() -> None:
    offenders = [
        filename
        for filename in FORBIDDEN_ROOT_DEBRIS_FILENAMES
        if (REPO_ROOT / filename).exists()
    ]

    assert offenders == []


def _task_frontmatter_by_id() -> dict[str, dict[str, Any]]:
    tasks: dict[str, dict[str, Any]] = {}
    for path in sorted((REPO_ROOT / "codex/tasks").glob("TASK-*.md")):
        match = TASK_FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
        assert match is not None, f"{path} must have YAML frontmatter"
        frontmatter = yaml.safe_load(match.group(1))
        assert isinstance(frontmatter, dict), f"{path} frontmatter must be a mapping"
        task_id = frontmatter.get("id")
        assert isinstance(task_id, str) and TASK_ID_RE.fullmatch(task_id)
        tasks[task_id] = frontmatter
    return tasks


def _task_index_statuses() -> dict[str, str]:
    statuses: dict[str, str] = {}
    for line in (REPO_ROOT / "docs/planning/TASK_INDEX.md").read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.startswith("| TASK-"):
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        statuses[columns[0]] = _status(columns[2])
    return statuses


def _status(value: Any) -> str:
    return str(value or "").strip().upper().replace("-", "_")


def _completed_at(frontmatter: dict[str, Any]) -> str:
    raw = frontmatter.get("completed_at")
    if hasattr(raw, "isoformat"):
        return raw.isoformat().replace("+00:00", "Z")
    return str(raw)


def _dependencies(frontmatter: dict[str, Any]) -> list[str]:
    raw_dependencies = frontmatter.get("depends_on", [])
    if raw_dependencies is None or raw_dependencies == "":
        return []
    assert isinstance(raw_dependencies, list)
    return [
        dependency_id
        for dependency_id in raw_dependencies
        if isinstance(dependency_id, str) and TASK_ID_RE.fullmatch(dependency_id)
    ]


def _valid_dependency_exception_ids(
    task_id: str,
    frontmatter: dict[str, Any],
    dependencies: list[str],
    errors: list[str],
) -> set[str]:
    raw_exceptions = frontmatter.get("dependency_exceptions", [])
    if raw_exceptions is None or raw_exceptions == "":
        return set()
    if not isinstance(raw_exceptions, list):
        errors.append(f"{task_id} dependency_exceptions is not a list")
        return set()
    dependency_ids = set(dependencies)
    valid_ids: set[str] = set()
    for index, exception in enumerate(raw_exceptions):
        if not isinstance(exception, dict):
            errors.append(f"{task_id} dependency_exceptions[{index}] is not a mapping")
            continue
        dependency_id = exception.get("task_id")
        reason_code = exception.get("reason_code")
        rationale = exception.get("rationale")
        if not isinstance(dependency_id, str) or not TASK_ID_RE.fullmatch(dependency_id):
            errors.append(f"{task_id} dependency_exceptions[{index}] lacks task_id")
            continue
        if dependency_id not in dependency_ids:
            errors.append(
                f"{task_id} dependency_exceptions[{index}] references non-dependency"
            )
            continue
        if not isinstance(reason_code, str) or not DEPENDENCY_EXCEPTION_REASON_RE.fullmatch(
            reason_code
        ):
            errors.append(f"{task_id} dependency_exceptions[{index}] lacks reason_code")
            continue
        if not isinstance(rationale, str) or not rationale.strip():
            errors.append(f"{task_id} dependency_exceptions[{index}] lacks rationale")
            continue
        valid_ids.add(dependency_id)
    return valid_ids
