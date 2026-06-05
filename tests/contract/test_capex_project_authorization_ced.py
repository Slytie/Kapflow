from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CED_PATH = REPO_ROOT / "docs" / "architecture" / "CAPEX_PROJECT_AUTHORIZATION_CED.md"
DOC_INDEX = REPO_ROOT / "docs" / "index.md"
STATUS_MATRIX = REPO_ROOT / "docs" / "architecture" / "DOCUMENT_STATUS_MATRIX.md"

RAW_CORPUS_MARKERS = (
    "projektordner",
    "reference project",
    "blind-validation",
    "alma ruma",
    "11639 otc",
    "k12 primary",
    "k3 primary",
)


def test_capex_project_authorization_ced_records_w1_project_identity_gates() -> None:
    text = CED_PATH.read_text(encoding="utf-8")

    required_markers = (
        "Accepted Wave 1 design and prototype boundary",
        "capex_projects.project_id",
        "workflow_run_id is an execution identity",
        "project_memberships",
        "project_viewer",
        "project_contributor",
        "project_admin",
        "capex_project_authorization",
        "capex_project_feature",
        "capex_user_project_view",
        "AuthorizedProjectsQuery",
        "not a frontend-only filter",
        "does not expose a global project list",
        "ARCH-W1-GATE-004",
        "ARCH-W1-GATE-005",
        "ARCH-W1-GATE-006",
        "leave runtime state inert",
        "does not add routes",
        "migrations",
        "CAPEX runtime activation",
    )

    missing = [marker for marker in required_markers if marker not in text]
    assert missing == []


def test_capex_project_authorization_ced_is_registered_as_authoritative_source() -> None:
    relative_path = "docs/architecture/CAPEX_PROJECT_AUTHORIZATION_CED.md"

    assert relative_path in DOC_INDEX.read_text(encoding="utf-8")
    matrix_text = STATUS_MATRIX.read_text(encoding="utf-8")
    assert f"`{relative_path}` | AUTHORITATIVE SOURCE" in matrix_text


def test_capex_project_authorization_ced_has_no_raw_corpus_markers() -> None:
    text = CED_PATH.read_text(encoding="utf-8").lower()

    leaks = sorted(marker for marker in RAW_CORPUS_MARKERS if marker in text)

    assert leaks == []
