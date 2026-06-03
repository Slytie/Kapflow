#!/usr/bin/env python3
"""Build and validate the local CAPEX epic progress data."""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT / "frontend/src/data/capexEpicProgressData.json"
DEFAULT_OVERRIDES_PATH = ROOT / "frontend/src/data/capexEpicProgressOverrides.json"

TASK_STATUS_ORDER = ["done", "in_progress", "not_started", "blocked", "needs_review"]
TASK_STATUS_VALUES = set(TASK_STATUS_ORDER)
EPIC_STATUS_VALUES = TASK_STATUS_VALUES
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
TASK_ID_RE = re.compile(r"TASK-\d{4}")
EPIC_ID_RE = re.compile(r"EPIC-\d{3}")
ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$"
)
MIN_EPIC_COMPLETIONS_FOR_ETA = 3
MIN_GLOBAL_COMPLETIONS_FOR_ETA = 5
MIN_GLOBAL_COMPLETION_DAYS_FOR_ETA = 2


def _strip_markdown(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("`", "").strip())


def _plain_lines(section: str) -> list[str]:
    lines: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[-*]\s+", "", line)
        lines.append(_strip_markdown(line))
    return lines


def _parse_frontmatter(text: str) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    values: dict[str, Any] = {}
    for raw_line in match.group("body").splitlines():
        if not raw_line or raw_line.startswith(" ") or ":" not in raw_line:
            continue
        key, raw_value = raw_line.split(":", 1)
        value = raw_value.strip()
        if value.startswith("[") and value.endswith("]"):
            try:
                values[key.strip()] = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                values[key.strip()] = value
        else:
            values[key.strip()] = value.strip('"')
    return values


def _parse_completed_at(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    raw = str(value)
    if not ISO_DATETIME_RE.match(raw):
        return None
    normalized = raw.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _completion_timestamp(
    task_id: str,
    source_status: str,
    display_status: str,
    frontmatter: dict[str, Any],
    historical_exceptions: set[str],
) -> tuple[str | None, str, str]:
    completed_at = frontmatter.get("completed_at")
    if completed_at not in {None, ""}:
        return str(completed_at), "recorded", "task_frontmatter"
    if source_status.upper() in {"DONE", "COMPLETED"} or display_status == "done":
        if task_id not in historical_exceptions:
            return None, "missing_required", "not_recorded"
        return None, "missing_historical", "grandfathered_missing"
    return None, "not_applicable", "not_completed"


def _sections(text: str) -> dict[str, str]:
    found: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        if raw_line.startswith("## "):
            current = raw_line[3:].strip()
            found[current] = []
            continue
        if current is not None:
            found[current].append(raw_line)
    return {key: "\n".join(lines).strip() for key, lines in found.items()}


def _mapping(section: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _plain_lines(section):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
        result[normalized_key] = value.strip()
    return result


def _first_sentence(section: str) -> str:
    for line in _plain_lines(section):
        return line
    return ""


def _task_file(task_id: str) -> Path:
    matches = sorted((ROOT / "codex/tasks").glob(f"{task_id}-*.md"))
    if not matches:
        raise FileNotFoundError(f"Missing task file for {task_id}")
    return matches[0]


def _base_task_status(source_status: str, sections: dict[str, str]) -> tuple[str, str]:
    normalized = source_status.upper()
    if "Blocked closeout evidence" in sections or normalized == "BLOCKED":
        return "blocked", "Task is blocked until external evidence or prerequisite work is supplied."
    if normalized in {"DONE", "COMPLETED"} and (
        "Closeout evidence" in sections or "Completion evidence" in sections
    ):
        return "done", "Task file records DONE status and completion or closeout evidence."
    if normalized in {"DONE", "COMPLETED"}:
        return "done", "Task frontmatter records DONE status."
    if "Closeout evidence" in sections or "Completion evidence" in sections:
        return "done", "Task file records completion or closeout evidence."
    if normalized in {"IN_PROGRESS", "STARTED", "WIP"}:
        return "in_progress", "Task file records in-progress work."
    return "not_started", "Task is still planned backlog work."


def _apply_task_overrides(
    task: dict[str, Any],
    overrides: dict[str, Any],
    epic_task_rules: list[dict[str, Any]],
) -> None:
    for rule in epic_task_rules:
        if task["epicId"] != rule.get("epicId"):
            continue
        source_statuses = {str(value).upper() for value in rule.get("sourceStatuses", [])}
        if source_statuses and task["sourceStatus"].upper() not in source_statuses:
            continue
        task["displayStatus"] = rule["displayStatus"]
        task["statusReason"] = rule.get("statusReason", task["statusReason"])
    task_override = overrides.get(task["id"], {})
    if task_override:
        task["displayStatus"] = task_override.get("displayStatus", task["displayStatus"])
        task["statusReason"] = task_override.get("statusReason", task["statusReason"])


def _task_record(
    task_id: str,
    overrides: dict[str, Any],
    epic_task_rules: list[dict[str, Any]],
    historical_completion_exceptions: set[str],
) -> dict[str, Any]:
    path = _task_file(task_id)
    text = path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)
    sections = _sections(text)
    source_status = str(frontmatter.get("status", "TODO"))
    display_status, status_reason = _base_task_status(source_status, sections)
    record = {
        "id": task_id,
        "epicId": str(frontmatter.get("epic", "")),
        "title": str(frontmatter.get("title", task_id)),
        "plainPurpose": _first_sentence(sections.get("Scope", "")) or _first_sentence(sections.get("Why", "")),
        "sourceStatus": source_status,
        "displayStatus": display_status,
        "statusReason": status_reason,
        "why": _plain_lines(sections.get("Why", "")),
        "scope": _plain_lines(sections.get("Scope", "")),
        "outOfScope": _plain_lines(sections.get("Out of scope", "")),
        "dependsOn": list(frontmatter.get("depends_on", [])),
        "owners": list(frontmatter.get("owners", [])),
        "reviewers": list(frontmatter.get("reviewers", [])),
        "risk": str(frontmatter.get("risk", "unknown")),
        "verification": _plain_lines(sections.get("Verification", "")),
        "acceptanceCriteria": _plain_lines(sections.get("Acceptance criteria", "")),
        "sourceRow": _mapping(sections.get("Source row mapping", "")),
        "evidence": _plain_lines(
            sections.get("Blocked closeout evidence", "")
            or sections.get("Closeout evidence", "")
            or sections.get("Completion evidence", "")
        ),
        "taskPath": str(path.relative_to(ROOT)),
    }
    _apply_task_overrides(record, overrides, epic_task_rules)
    completed_at, timestamp_status, timestamp_source = _completion_timestamp(
        task_id,
        source_status,
        record["displayStatus"],
        frontmatter,
        historical_completion_exceptions,
    )
    record["completedAt"] = completed_at
    record["completionTimestampStatus"] = timestamp_status
    record["completionTimestampSource"] = timestamp_source
    return record


def _estimate(
    tasks: list[dict[str, Any]],
    global_completed_at: list[datetime] | None = None,
    estimate_base: datetime | None = None,
) -> dict[str, Any]:
    total = len(tasks)
    completed = sum(1 for task in tasks if task["displayStatus"] == "done")
    remaining = total - completed
    remaining_blocked_or_review = sum(
        1 for task in tasks if task["displayStatus"] in {"blocked", "needs_review"}
    )
    timestamped_completed_at = [
        parsed
        for task in tasks
        if task["displayStatus"] == "done"
        for parsed in [_parse_completed_at(task.get("completedAt"))]
        if parsed is not None
    ]
    completed_with_timestamps = len(timestamped_completed_at)
    percent_complete = round((completed / total) * 100, 1) if total else 0.0
    timestamp_coverage = round((completed_with_timestamps / completed) * 100, 1) if completed else 0.0
    eta_date: str | None = None
    eta_confidence = "insufficient_history"
    eta_source = "none"

    if remaining == 0:
        eta_confidence = "complete"
        eta_source = "none"
    elif len(timestamped_completed_at) >= MIN_EPIC_COMPLETIONS_FOR_ETA:
        velocity = _velocity_per_day(timestamped_completed_at)
        if velocity > 0:
            eta_date = _eta_date(timestamped_completed_at[-1], remaining, velocity, estimate_base)
            eta_confidence = "medium"
            eta_source = "epic_completed_at"
    elif global_completed_at and _global_history_is_sufficient(global_completed_at):
        velocity = _velocity_per_day(global_completed_at)
        if velocity > 0:
            eta_date = _eta_date(global_completed_at[-1], remaining, velocity, estimate_base)
            eta_confidence = "low"
            eta_source = "global_completed_at"

    if eta_confidence == "complete":
        label = "Complete"
    elif eta_date:
        label = f"ETA {eta_date}"
    else:
        label = "ETA needs completion timestamp history"

    if remaining_blocked_or_review:
        caveat = f"{remaining_blocked_or_review} blocked or needs-review task(s) remain."
    elif remaining:
        caveat = "Estimate is based on remaining current-scope task count."
    else:
        caveat = "No remaining current-scope tasks."

    return {
        "percentComplete": percent_complete,
        "completedTasks": completed,
        "remainingTasks": remaining,
        "remainingBlockedOrReviewTasks": remaining_blocked_or_review,
        "completedWithTimestamps": completed_with_timestamps,
        "completionTimestampCoverage": timestamp_coverage,
        "etaDate": eta_date,
        "etaConfidence": eta_confidence,
        "etaSource": eta_source,
        "label": label,
        "caveat": caveat,
    }


def _velocity_per_day(completed_at: list[datetime]) -> float:
    ordered = sorted(completed_at)
    if not ordered:
        return 0.0
    days = max((ordered[-1] - ordered[0]).days + 1, 1)
    return len(ordered) / days


def _eta_date(
    latest_completion: datetime,
    remaining: int,
    velocity_per_day: float,
    estimate_base: datetime | None,
) -> str | None:
    if velocity_per_day <= 0:
        return None
    days_remaining = max(round(remaining / velocity_per_day), 1)
    base = max(latest_completion, estimate_base) if estimate_base else latest_completion
    timestamp = base.timestamp() + (days_remaining * 86400)
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()


def _global_history_is_sufficient(completed_at: list[datetime]) -> bool:
    days = {value.date().isoformat() for value in completed_at}
    return len(completed_at) >= MIN_GLOBAL_COMPLETIONS_FOR_ETA and len(days) >= MIN_GLOBAL_COMPLETION_DAYS_FOR_ETA


def _estimate_base(meta: dict[str, Any]) -> datetime | None:
    last_updated = meta.get("lastUpdated")
    if not last_updated:
        return None
    try:
        parsed = datetime.fromisoformat(str(last_updated))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def _epic_status(tasks: list[dict[str, Any]]) -> str:
    statuses = [task["displayStatus"] for task in tasks]
    if not statuses:
        return "not_started"
    if "blocked" in statuses:
        return "blocked"
    if "needs_review" in statuses:
        return "needs_review"
    if all(status == "done" for status in statuses):
        return "done"
    if any(status in {"done", "in_progress"} for status in statuses):
        return "in_progress"
    return "not_started"


def _counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in TASK_STATUS_ORDER}
    for item in items:
        counts[item["displayStatus"]] += 1
    counts["total"] = len(items)
    return counts


def _capex_epic_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted((ROOT / "docs/planning/epics").glob("EPIC-*.md")):
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        if " - CAPEX " in first_line or first_line.endswith(" - CAPEX"):
            files.append(path)
    return files


def build_data(overrides_path: Path = DEFAULT_OVERRIDES_PATH) -> dict[str, Any]:
    overrides_data = json.loads(overrides_path.read_text(encoding="utf-8"))
    task_overrides = overrides_data.get("taskOverrides", {})
    epic_task_rules = overrides_data.get("epicTaskRules", [])
    epic_overrides = overrides_data.get("epicOverrides", {})
    historical_completion_exceptions = set(overrides_data.get("historicalCompletionTimestampExceptions", []))
    estimate_base = _estimate_base(overrides_data.get("meta", {}))
    epics: list[dict[str, Any]] = []
    all_tasks: list[dict[str, Any]] = []

    for epic_path in _capex_epic_files():
        text = epic_path.read_text(encoding="utf-8")
        first_line = text.splitlines()[0]
        title_match = re.match(r"# (EPIC-\d{3}) - (.+)", first_line)
        if not title_match:
            raise ValueError(f"Unexpected epic heading in {epic_path}")
        epic_id = title_match.group(1)
        title = title_match.group(2)
        sections = _sections(text)
        task_ids = sorted(set(TASK_ID_RE.findall(sections.get("Task stack", text))))
        tasks = [
            _task_record(
                task_id,
                task_overrides,
                epic_task_rules,
                historical_completion_exceptions,
            )
            for task_id in task_ids
        ]
        for task in tasks:
            if task["epicId"] != epic_id:
                raise ValueError(f"{task['id']} belongs to {task['epicId']}, not {epic_id}")
        display_status = _epic_status(tasks)
        epic_override = epic_overrides.get(epic_id, {})
        display_status = epic_override.get("displayStatus", display_status)
        epic = {
            "id": epic_id,
            "title": title,
            "plainPurpose": _first_sentence(sections.get("Summary", "")),
            "displayStatus": display_status,
            "reviewPosture": epic_override.get(
                "reviewPosture",
                "Review posture follows task evidence and curated blocker overrides."
            ),
            "dependencies": EPIC_ID_RE.findall(sections.get("Dependencies", "")),
            "inScope": _plain_lines(sections.get("In scope", "")),
            "outOfScope": _plain_lines(sections.get("Out of scope", "")),
            "sourceReferences": _plain_lines(sections.get("Source references", "")),
            "counts": _counts(tasks),
            "taskCount": len(tasks),
            "epicPath": str(epic_path.relative_to(ROOT)),
            "tasks": tasks,
        }
        epics.append(epic)
        all_tasks.extend(tasks)

    summary_counts = _counts(all_tasks)
    global_completed_at = [
        parsed
        for task in all_tasks
        if task["displayStatus"] == "done"
        for parsed in [_parse_completed_at(task.get("completedAt"))]
        if parsed is not None
    ]
    for epic in epics:
        epic["estimate"] = _estimate(epic["tasks"], global_completed_at, estimate_base)
    data = {
        "schemaVersion": "capex.epic_progress.v2",
        "meta": overrides_data["meta"],
        "summary": {
            "epicCount": len(epics),
            "taskCount": len(all_tasks),
            **summary_counts,
            "estimate": _estimate(all_tasks, global_completed_at, estimate_base),
        },
        "activationBlockers": overrides_data.get("activationBlockers", []),
        "epics": epics,
    }
    return data


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schemaVersion") != "capex.epic_progress.v2":
        errors.append("schemaVersion must be capex.epic_progress.v2")
    expected_epics = [path.stem for path in _capex_epic_files()]
    actual_epics = [epic.get("id") for epic in data.get("epics", [])]
    if actual_epics != expected_epics:
        errors.append(f"epic coverage mismatch: expected {expected_epics}, got {actual_epics}")
    seen_tasks: set[str] = set()
    all_tasks: list[dict[str, Any]] = []
    for epic in data.get("epics", []):
        status = epic.get("displayStatus")
        if status not in EPIC_STATUS_VALUES:
            errors.append(f"{epic.get('id')} has invalid status {status}")
        tasks = epic.get("tasks", [])
        if epic.get("taskCount") != len(tasks):
            errors.append(f"{epic.get('id')} taskCount mismatch")
        counts = _counts(tasks)
        if epic.get("counts") != counts:
            errors.append(f"{epic.get('id')} counts mismatch")
        estimate = epic.get("estimate")
        if not isinstance(estimate, dict):
            errors.append(f"{epic.get('id')} missing estimate")
        elif estimate != _estimate(tasks, _all_timestamped_done(data), _estimate_base(data.get("meta", {}))):
            errors.append(f"{epic.get('id')} estimate mismatch")
        for task in tasks:
            task_id = task.get("id")
            if task_id in seen_tasks:
                errors.append(f"duplicate task {task_id}")
            seen_tasks.add(task_id)
            if task.get("displayStatus") not in TASK_STATUS_VALUES:
                errors.append(f"{task_id} has invalid status {task.get('displayStatus')}")
            if not task.get("plainPurpose"):
                errors.append(f"{task_id} missing plainPurpose")
            if not (ROOT / str(task.get("taskPath", ""))).exists():
                errors.append(f"{task_id} taskPath missing")
            completed_at = task.get("completedAt")
            timestamp_status = task.get("completionTimestampStatus")
            timestamp_source = task.get("completionTimestampSource")
            if timestamp_status not in {"recorded", "missing_historical", "not_applicable", "missing_required"}:
                errors.append(f"{task_id} has invalid completionTimestampStatus {timestamp_status}")
            if timestamp_source not in {"task_frontmatter", "grandfathered_missing", "not_completed", "not_recorded"}:
                errors.append(f"{task_id} has invalid completionTimestampSource {timestamp_source}")
            if completed_at and _parse_completed_at(completed_at) is None:
                errors.append(f"{task_id} completedAt must be ISO 8601 with timezone")
            if task.get("sourceStatus", "").upper() in {"DONE", "COMPLETED"} and timestamp_status == "missing_required":
                errors.append(f"{task_id} source DONE must include completed_at or historical exception")
            if task.get("displayStatus") == "done":
                if timestamp_status == "missing_required":
                    errors.append(f"{task_id} is DONE and must include completed_at")
                if completed_at is None and timestamp_status != "missing_historical":
                    errors.append(f"{task_id} missing historical completedAt must be explicit")
                if completed_at and timestamp_status != "recorded":
                    errors.append(f"{task_id} completedAt requires recorded timestamp status")
            elif timestamp_status == "recorded":
                errors.append(f"{task_id} records completedAt but is not display done")
        all_tasks.extend(tasks)
    if data.get("summary", {}).get("epicCount") != len(expected_epics):
        errors.append("summary epicCount mismatch")
    if data.get("summary", {}).get("taskCount") != len(all_tasks):
        errors.append("summary taskCount mismatch")
    for key, value in _counts(all_tasks).items():
        if data.get("summary", {}).get(key) != value:
            errors.append(f"summary {key} mismatch")
    summary_estimate = data.get("summary", {}).get("estimate")
    if summary_estimate != _estimate(
        all_tasks,
        _all_timestamped_done(data),
        _estimate_base(data.get("meta", {})),
    ):
        errors.append("summary estimate mismatch")
    return errors


def _all_timestamped_done(data: dict[str, Any]) -> list[datetime]:
    return [
        parsed
        for epic in data.get("epics", [])
        for task in epic.get("tasks", [])
        if task.get("displayStatus") == "done"
        for parsed in [_parse_completed_at(task.get("completedAt"))]
        if parsed is not None
    ]


def _canonical(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_path", nargs="?", default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--overrides", default=str(DEFAULT_OVERRIDES_PATH))
    parser.add_argument("--write", action="store_true", help="Regenerate the data file")
    args = parser.parse_args()

    data_path = Path(args.data_path)
    if not data_path.is_absolute():
        data_path = ROOT / data_path
    overrides_path = Path(args.overrides)
    if not overrides_path.is_absolute():
        overrides_path = ROOT / overrides_path

    generated = build_data(overrides_path)
    errors = validate(generated)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    if args.write:
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(_canonical(generated), encoding="utf-8")
        print(f"WROTE {data_path.relative_to(ROOT)}")
        return 0

    if not data_path.exists():
        print(f"FAIL\n- missing data file {data_path.relative_to(ROOT)}")
        return 1
    existing = data_path.read_text(encoding="utf-8")
    expected = _canonical(generated)
    if existing != expected:
        print("FAIL")
        print(f"- {data_path.relative_to(ROOT)} is stale; rerun with --write")
        return 1
    print(
        "PASS capex epic progress data: "
        f"{generated['summary']['epicCount']} epics, {generated['summary']['taskCount']} tasks"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
