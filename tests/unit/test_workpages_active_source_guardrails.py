from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_DOC_FILES = (
    REPO_ROOT / "docs" / "planning" / "FRONTEND_PAGE_MAP.md",
    REPO_ROOT / "docs" / "planning" / "HITL_HTTP_API_CONTRACTS.md",
    REPO_ROOT / "docs" / "planning" / "FRONTEND_ARCHITECTURE.md",
    REPO_ROOT / "docs" / "planning" / "CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md",
    REPO_ROOT
    / "docs"
    / "domains"
    / "logistics"
    / "current-state"
    / "CONTINUOUS_SCHEDULE_CONTROL_ARTIFACTS.md",
    REPO_ROOT
    / "docs"
    / "domains"
    / "logistics"
    / "current-state"
    / "LOGISTICS_WORKPAGES_V1_OPERATOR_READINESS_NOTE.md",
    REPO_ROOT / "fixtures" / "frontend_contracts" / "README.md",
    REPO_ROOT / "tests" / "runtime" / "helpers" / "frontend_snapshots.py",
)

SOURCE_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "frontend" / "src",
)

ALLOWED_RETIREMENT_ASSERTION_FILES = {
    REPO_ROOT / "frontend" / "src" / "pages" / "logisticsWorkpageRoutes.test.tsx",
}

TEXT_SUFFIXES = {
    ".css",
    ".json",
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

BANNED_SUBSTRINGS = (
    "/api/v1/workpages/demo/",
    "/api/v1/workpages/artifacts/",
    "/demo/logistics/workpages/",
    "create_draft_then_open",
    "workpage_schedule_v0_state.json",
    "workpage_eod_v0_state.json",
    "workpage_eod_v0_artifact_create_response.json",
)


def _iter_active_source_files() -> list[Path]:
    files = list(ACTIVE_DOC_FILES)
    for root in SOURCE_ROOTS:
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in TEXT_SUFFIXES
            and "__pycache__" not in path.parts
            and path not in ALLOWED_RETIREMENT_ASSERTION_FILES
        )
    return files


def test_active_workpage_sources_do_not_reintroduce_retired_aliases_or_vocabulary() -> None:
    violations: list[str] = []

    for path in _iter_active_source_files():
        text = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(REPO_ROOT)
        for banned in BANNED_SUBSTRINGS:
            if banned in text:
                violations.append(f"{relative_path}: contains {banned!r}")

    assert violations == []
