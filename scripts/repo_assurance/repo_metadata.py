from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re
from typing import Any

import yaml

from scripts.repo_assurance.core import (
    AssuranceState,
    ROOT,
    TASK_FRONTMATTER_PATTERN,
    TASK_ID_PATTERN,
    has_egg_info_segment,
)
from scripts.repo_assurance.secrets import iter_tracked_files


DONE_TASK_STATUSES = frozenset({"DONE", "COMPLETED"})
OPEN_TASK_STATUSES = frozenset(
    {"BLOCKED", "IN_PROGRESS", "NEEDS_REVIEW", "STARTED", "TODO", "WIP"}
)
DEPENDENCY_EXCEPTION_REASON_CODE_PATTERN = r"[a-z][a-z0-9_]*"
FORBIDDEN_ROOT_DEBRIS_FILENAMES = (
    ', d["proposed_copy"])',
    ', d["proposed_copy"])\n',
    ", p)",
    ", p)\n",
)


def run_metadata_domain(state: AssuranceState) -> None:
    validate_task_index(state)
    validate_current_focus(state)
    validate_tracked_build_artifacts(state)
    validate_forbidden_root_debris(state)


def validate_task_index(state: AssuranceState) -> None:
    collector = state.collector
    task_index_path = ROOT / "docs/planning/TASK_INDEX.md"
    content = task_index_path.read_text(encoding="utf-8").splitlines()
    task_dir = ROOT / "codex/tasks"
    task_files_by_name: defaultdict[str, list[Path]] = defaultdict(list)
    task_files_by_frontmatter: defaultdict[str, list[Path]] = defaultdict(list)
    task_files: dict[str, Path] = {}
    task_frontmatter_by_id: dict[str, dict[str, Any]] = {}
    task_paths_by_id: dict[str, Path] = {}
    for path in sorted(task_dir.glob("TASK-*.md")):
        task_id_from_name = path.name[:9]
        task_files_by_name[task_id_from_name].append(path)
        match = TASK_FRONTMATTER_PATTERN.match(path.read_text(encoding="utf-8"))
        if not match:
            collector.fail(f"task file missing YAML frontmatter: {path.relative_to(ROOT)}")
            continue
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            collector.fail(f"task frontmatter must be a mapping: {path.relative_to(ROOT)}")
            continue
        frontmatter_id = frontmatter.get("id")
        if not isinstance(frontmatter_id, str) or not TASK_ID_PATTERN.fullmatch(frontmatter_id):
            collector.fail(f"task frontmatter id missing or invalid: {path.relative_to(ROOT)}")
            continue
        collector.require(
            frontmatter_id == task_id_from_name,
            f"task frontmatter id matches filename: {path.relative_to(ROOT)}",
        )
        task_files_by_frontmatter[frontmatter_id].append(path)
        task_frontmatter_by_id[frontmatter_id] = frontmatter
        task_paths_by_id[frontmatter_id] = path
        if frontmatter_id == task_id_from_name:
            task_files[task_id_from_name] = path

    for task_id, paths in sorted(task_files_by_name.items()):
        collector.require(len(paths) == 1, f"task filename id unique: {task_id}")
        if len(paths) > 1:
            collector.fail(
                "duplicate task filename id in codex/tasks: "
                f"{task_id} -> {[path.name for path in paths]}"
            )
    for task_id, paths in sorted(task_files_by_frontmatter.items()):
        collector.require(len(paths) == 1, f"task frontmatter id unique: {task_id}")
        if len(paths) > 1:
            collector.fail(
                "duplicate task frontmatter id in codex/tasks: "
                f"{task_id} -> {[str(path.relative_to(ROOT)) for path in paths]}"
            )

    indexed: list[str] = []
    for line in content:
        if line.startswith("| TASK-"):
            columns = [column.strip() for column in line.strip("|").split("|")]
            task_id = columns[0]
            indexed.append(task_id)
            collector.require(task_id in task_files, f"task index entry has file: {task_id}")
            if len(columns) < 3:
                collector.fail(f"task index row missing status column: {task_id}")
                continue
            frontmatter = task_frontmatter_by_id.get(task_id)
            if frontmatter is not None:
                index_status = _normalize_task_status(columns[2])
                frontmatter_status = _normalize_task_status(frontmatter.get("status"))
                if index_status == frontmatter_status:
                    collector.ok(f"task index status matches frontmatter: {task_id}")
                else:
                    collector.fail(
                        "task index status mismatch: "
                        f"{task_id} index={index_status} frontmatter={frontmatter_status}"
                    )
    duplicates = [task_id for task_id, count in Counter(indexed).items() if count > 1]
    collector.require(not duplicates, "task index task ids are unique")
    for task_id in duplicates:
        collector.fail(f"duplicate task index row: {task_id}")
    indexed_set = set(indexed)
    for task_id in sorted(task_files):
        collector.require(task_id in indexed_set, f"task file indexed: {task_id}")
    validate_task_dependency_statuses(collector, task_frontmatter_by_id, task_paths_by_id)


def validate_task_dependency_statuses(
    collector: Any,
    task_frontmatter_by_id: dict[str, dict[str, Any]],
    task_paths_by_id: dict[str, Path],
) -> None:
    for task_id, frontmatter in sorted(task_frontmatter_by_id.items()):
        dependencies = _task_dependencies(frontmatter, task_paths_by_id[task_id], collector)
        exception_ids = _valid_dependency_exception_ids(
            frontmatter,
            dependencies,
            task_paths_by_id[task_id],
            collector,
        )
        task_status = _normalize_task_status(frontmatter.get("status"))
        if task_status not in DONE_TASK_STATUSES:
            continue
        for dependency_id in dependencies:
            dependency = task_frontmatter_by_id.get(dependency_id)
            if dependency is None:
                continue
            dependency_status = _normalize_task_status(dependency.get("status"))
            if dependency_status in OPEN_TASK_STATUSES and dependency_id not in exception_ids:
                collector.fail(
                    "DONE task depends on open task without dependency_exceptions entry: "
                    f"{task_id}({task_status}) -> {dependency_id}({dependency_status})"
                )
            elif dependency_status in OPEN_TASK_STATUSES:
                collector.ok(
                    "DONE task open dependency has valid dependency_exceptions entry: "
                    f"{task_id} -> {dependency_id}"
                )


def _normalize_task_status(value: Any) -> str:
    return str(value or "").strip().upper().replace("-", "_")


def _task_dependencies(frontmatter: dict[str, Any], path: Path, collector: Any) -> list[str]:
    raw_dependencies = frontmatter.get("depends_on", [])
    if raw_dependencies is None or raw_dependencies == "":
        return []
    if not isinstance(raw_dependencies, list):
        collector.fail(f"task depends_on must be a list: {path.relative_to(ROOT)}")
        return []
    dependencies: list[str] = []
    for dependency_id in raw_dependencies:
        if isinstance(dependency_id, str) and TASK_ID_PATTERN.fullmatch(dependency_id):
            dependencies.append(dependency_id)
    return dependencies


def _valid_dependency_exception_ids(
    frontmatter: dict[str, Any],
    dependencies: list[str],
    path: Path,
    collector: Any,
) -> set[str]:
    raw_exceptions = frontmatter.get("dependency_exceptions", [])
    if raw_exceptions is None or raw_exceptions == "":
        return set()
    if not isinstance(raw_exceptions, list):
        collector.fail(f"task dependency_exceptions must be a list: {path.relative_to(ROOT)}")
        return set()
    dependency_ids = set(dependencies)
    valid_ids: set[str] = set()
    for index, exception in enumerate(raw_exceptions):
        if not isinstance(exception, dict):
            collector.fail(
                "task dependency_exceptions entries must be mappings: "
                f"{path.relative_to(ROOT)}[{index}]"
            )
            continue
        dependency_id = exception.get("task_id")
        reason_code = exception.get("reason_code")
        rationale = exception.get("rationale")
        if not isinstance(dependency_id, str) or not TASK_ID_PATTERN.fullmatch(dependency_id):
            collector.fail(
                "task dependency_exceptions entry must name a TASK id: "
                f"{path.relative_to(ROOT)}[{index}]"
            )
            continue
        if dependency_id not in dependency_ids:
            collector.fail(
                "task dependency_exceptions entry must reference a depends_on task: "
                f"{path.relative_to(ROOT)}[{index}] -> {dependency_id}"
            )
            continue
        if (
            not isinstance(reason_code, str)
            or not re.fullmatch(DEPENDENCY_EXCEPTION_REASON_CODE_PATTERN, reason_code)
        ):
            collector.fail(
                "task dependency_exceptions entry must include snake_case reason_code: "
                f"{path.relative_to(ROOT)}[{index}]"
            )
            continue
        if not isinstance(rationale, str) or not rationale.strip():
            collector.fail(
                "task dependency_exceptions entry must include rationale: "
                f"{path.relative_to(ROOT)}[{index}]"
            )
            continue
        valid_ids.add(dependency_id)
    return valid_ids


def validate_current_focus(state: AssuranceState) -> None:
    collector = state.collector
    text = (ROOT / "docs/status/CURRENT_FOCUS.md").read_text(encoding="utf-8")
    task_dir = ROOT / "codex/tasks"
    task_files = {path.name[:9] for path in task_dir.glob("TASK-*.md")}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(tuple(f"{index}. TASK-" for index in range(1, 20))):
            task_id = stripped.split()[1]
            collector.require(
                task_id in task_files,
                f"current focus references task file: {task_id}",
            )


def validate_tracked_build_artifacts(state: AssuranceState) -> None:
    collector = state.collector
    tracked_files = iter_tracked_files(state)
    violations = 0
    for path in tracked_files:
        relative = path.relative_to(ROOT)
        if has_egg_info_segment(relative.parts):
            collector.fail(f"tracked build artifact detected: {relative}")
            violations += 1
    if violations == 0:
        collector.ok(
            f"tracked build artifact scan passed across {len(tracked_files)} tracked files"
        )


def validate_forbidden_root_debris(state: AssuranceState) -> None:
    collector = state.collector
    for filename in FORBIDDEN_ROOT_DEBRIS_FILENAMES:
        collector.require(
            not (ROOT / filename).exists(),
            f"forbidden root editor debris absent: {filename!r}",
        )
