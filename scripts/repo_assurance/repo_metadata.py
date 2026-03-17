from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import yaml

from scripts.repo_assurance.core import (
    AssuranceState,
    ROOT,
    TASK_FRONTMATTER_PATTERN,
    TASK_ID_PATTERN,
    has_egg_info_segment,
)
from scripts.repo_assurance.secrets import iter_tracked_files


def run_metadata_domain(state: AssuranceState) -> None:
    validate_task_index(state)
    validate_current_focus(state)
    validate_tracked_build_artifacts(state)


def validate_task_index(state: AssuranceState) -> None:
    collector = state.collector
    task_index_path = ROOT / "docs/planning/TASK_INDEX.md"
    content = task_index_path.read_text(encoding="utf-8").splitlines()
    task_dir = ROOT / "codex/tasks"
    task_files_by_name: defaultdict[str, list[Path]] = defaultdict(list)
    task_files_by_frontmatter: defaultdict[str, list[Path]] = defaultdict(list)
    task_files: dict[str, Path] = {}
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
    duplicates = [task_id for task_id, count in Counter(indexed).items() if count > 1]
    collector.require(not duplicates, "task index task ids are unique")
    for task_id in duplicates:
        collector.fail(f"duplicate task index row: {task_id}")
    indexed_set = set(indexed)
    for task_id in sorted(task_files):
        collector.require(task_id in indexed_set, f"task file indexed: {task_id}")


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
