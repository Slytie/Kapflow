from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

MODULE_LINE_BUDGETS = {
    REPO_ROOT / "src" / "onetruth" / "application" / "handlers" / "workpages.py": 700,
    REPO_ROOT / "src" / "onetruth" / "application" / "services" / "logistics_workpages.py": 700,
    REPO_ROOT / "frontend" / "src" / "components" / "WorkspaceTaskBoard.tsx": 700,
    REPO_ROOT / "frontend" / "src" / "pages" / "LogisticsScheduleWorkpagePage.tsx": 800,
    REPO_ROOT / "frontend" / "src" / "pages" / "LogisticsDemoPage.tsx": 600,
}


def test_workpage_concentration_files_stay_within_budget() -> None:
    violations: list[str] = []
    for path, budget in MODULE_LINE_BUDGETS.items():
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > budget:
            violations.append(
                f"{path.relative_to(REPO_ROOT)} is {line_count} lines (budget {budget})"
            )

    assert violations == []
