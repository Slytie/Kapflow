from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]

EXPECTED_RECONCILIATION = {
    "V5-TASK-001": ("TASK-0572", ("TASK-0447", "TASK-0565", "TASK-0305")),
    "V5-TASK-002": ("TASK-0573", ("TASK-0392", "TASK-0373")),
    "V5-TASK-003": ("TASK-0574", ("TASK-0565",)),
    "V5-TASK-004": ("TASK-0575", ("TASK-0305", "TASK-0565")),
    "V5-TASK-005": ("TASK-0576", ("TASK-0257", "TASK-0561")),
    "V5-TASK-006": ("TASK-0577", ("TASK-0235", "TASK-0562")),
    "V5-TASK-007": ("TASK-0578", ("TASK-0564", "TASK-0428")),
    "V5-TASK-008": ("TASK-0579", ("TASK-0582",)),
    "V5-TASK-009": ("TASK-0580", ("TASK-0583", "TASK-0584")),
    "V5-TASK-010": ("TASK-0581", ("TASK-0566",)),
}

EPIC_ALIAS_TASKS = {
    "EPIC-136": ("TASK-0579", "TASK-0580"),
    "EPIC-137": ("TASK-0577",),
    "EPIC-139": ("TASK-0576",),
    "EPIC-141": ("TASK-0578",),
    "EPIC-142": ("TASK-0572", "TASK-0573", "TASK-0575"),
    "EPIC-143": ("TASK-0574", "TASK-0581"),
}


def _csv_rows(path: str) -> list[dict[str, str]]:
    return list(csv.DictReader((ROOT / path).read_text(encoding="utf-8").splitlines()))


def _task_file(task_id: str) -> Path:
    matches = sorted((ROOT / "codex/tasks").glob(f"{task_id}-*.md"))
    assert len(matches) == 1
    return matches[0]


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---", text, flags=re.S)
    assert match is not None
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def _section(text: str, start: str, end: str) -> str:
    start_index = text.index(start) + len(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


def test_v5_conversion_rows_are_historical_aliases() -> None:
    rows = _csv_rows("docs/planning/CAPEX_V6_CONVERSION_MAP.csv")
    v5_rows = {
        row["source_task_id"]: row for row in rows if row["source_task_id"].startswith("V5-TASK-")
    }

    assert set(v5_rows) == set(EXPECTED_RECONCILIATION)
    for source_id, (task_id, canonical_refs) in EXPECTED_RECONCILIATION.items():
        row = v5_rows[source_id]
        assert row["repo_task_id"] == task_id
        assert row["status"] == "DONE"
        assert row["source_lineage"] == "v5_carried_forward"
        assert row["active_disposition"] == "historical_alias"
        assert tuple(row["canonical_task_refs"].split(";")) == canonical_refs


def test_v5_task_files_record_reconciliation_closeout() -> None:
    for source_id, (task_id, canonical_refs) in EXPECTED_RECONCILIATION.items():
        path = _task_file(task_id)
        frontmatter = _frontmatter(path)
        text = path.read_text(encoding="utf-8")

        assert frontmatter["status"] == "DONE"
        assert frontmatter["source_lineage"] == "v5_carried_forward"
        assert frontmatter["active_disposition"] == "historical_alias"
        assert tuple(frontmatter["canonical_task_refs"]) == canonical_refs
        assert f"Source task ID: `{source_id}`" in text
        assert "## Reconciliation closeout evidence" in text
        assert "does not mark those target tasks complete" in text


def test_epic_active_task_stacks_do_not_present_v5_rows_as_active() -> None:
    for epic_id, task_ids in EPIC_ALIAS_TASKS.items():
        text = (ROOT / f"docs/planning/epics/{epic_id}.md").read_text(encoding="utf-8")
        task_stack = _section(text, "## Task stack\n", "## Historical/reconciled aliases")
        historical_aliases = _section(
            text,
            "## Historical/reconciled aliases\n",
            "## Acceptance criteria",
        )

        assert "V5-TASK-" not in task_stack
        for task_id in task_ids:
            assert f"`{task_id}` (`V5-TASK-" in historical_aliases


def test_v5_gate_risk_decision_rows_are_historical_references() -> None:
    rows = _csv_rows("docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv")
    v5_rows = [row for row in rows if row["source_id"].startswith("V5-")]

    assert v5_rows
    for row in v5_rows:
        assert row["source_lineage"] == "v5_carried_forward"
        assert row["active_disposition"] == "historical_reference"


def test_current_focus_does_not_point_at_v5_alias_tasks() -> None:
    text = (ROOT / "docs/status/CURRENT_FOCUS.md").read_text(encoding="utf-8")

    assert "V5-TASK-" not in text
    for _, (task_id, _) in EXPECTED_RECONCILIATION.items():
        assert task_id not in text
