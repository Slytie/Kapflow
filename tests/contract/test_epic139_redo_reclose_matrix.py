from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "docs/planning/EPIC139_REDO_RECLOSE_MATRIX.md"

EXPECTED_TASK_IDS = {
    "TASK-0245",
    "TASK-0246",
    "TASK-0247",
    "TASK-0248",
    "TASK-0249",
    "TASK-0250",
    "TASK-0251",
    "TASK-0252",
    "TASK-0253",
    "TASK-0257",
    "TASK-0258",
    "TASK-0259",
    "TASK-0260",
    "TASK-0369",
    "TASK-0370",
    "TASK-0561",
    "TASK-0576",
    "TASK-0643",
    "TASK-0644",
    "TASK-0645",
    "TASK-0646",
}
EXPECTED_COLUMNS = [
    "task_id",
    "source_row",
    "theme",
    "redo_action",
    "reclose_status",
    "evidence_command",
    "evidence_refs",
    "notes",
]
ALLOWED_STATUSES = {"reclosed", "historical_alias", "redo_task"}
REFERENCE_RE = re.compile(r"^(?:codex|docs|frontend|src|tests)/|^Makefile$")


def _task_file(task_id: str) -> Path:
    matches = sorted((ROOT / "codex/tasks").glob(f"{task_id}-*.md"))
    assert len(matches) == 1, task_id
    return matches[0]


def _rows() -> list[dict[str, str]]:
    lines = MATRIX_PATH.read_text(encoding="utf-8").splitlines()
    header_index = next(
        index for index, line in enumerate(lines) if line.startswith("| task_id |")
    )
    header = [cell.strip() for cell in lines[header_index].strip("|").split("|")]
    separator = [cell.strip() for cell in lines[header_index + 1].strip("|").split("|")]
    assert header == EXPECTED_COLUMNS
    assert all(set(cell) <= {"-", ":"} for cell in separator)

    rows: list[dict[str, str]] = []
    for line in lines[header_index + 2 :]:
        if not line.startswith("| "):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == len(header), line
        rows.append(dict(zip(header, cells, strict=True)))
    return rows


def test_epic139_redo_reclose_matrix_covers_all_required_rows() -> None:
    rows = _rows()

    assert {row["task_id"] for row in rows} == EXPECTED_TASK_IDS
    assert len(rows) == len(EXPECTED_TASK_IDS)


def test_epic139_redo_reclose_rows_are_done_and_have_allowed_statuses() -> None:
    for row in _rows():
        task_id = row["task_id"]
        task_text = _task_file(task_id).read_text(encoding="utf-8")

        assert "status: DONE" in task_text
        assert row["source_row"]
        assert row["theme"]
        assert row["redo_action"]
        assert row["reclose_status"] in ALLOWED_STATUSES
        assert row["evidence_command"]
        assert row["evidence_refs"]
        assert row["notes"]


def test_epic139_redo_reclose_matrix_references_existing_evidence() -> None:
    missing: list[str] = []
    for row in _rows():
        for raw_ref in row["evidence_refs"].split(";"):
            ref = raw_ref.strip()
            if not ref or not REFERENCE_RE.search(ref):
                continue
            if not (ROOT / ref).exists():
                missing.append(f"{row['task_id']} -> {ref}")

    assert missing == []


def test_epic139_redo_reclose_matrix_preserves_historical_alias() -> None:
    rows = {row["task_id"]: row for row in _rows()}

    assert rows["TASK-0576"]["reclose_status"] == "historical_alias"
    assert rows["TASK-0576"]["source_row"] == "V5-TASK-005"
    assert "tests/contract/test_capex_v5_reconciliation.py" in rows["TASK-0576"][
        "evidence_refs"
    ]
    assert "Historical alias" in rows["TASK-0576"]["notes"]


def test_epic139_epic_file_links_reclose_ledger() -> None:
    text = (ROOT / "docs/planning/epics/EPIC-139.md").read_text(encoding="utf-8")

    assert "`TASK-0646` (`EPIC-139-REDO`) - Task-by-task reclose ledger" in text
    assert "task-by-task reclose ledger" in text
