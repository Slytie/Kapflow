from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs/architecture/CAPEX_INTERFACE_BURDEN_POLICY.md"
INDEX_PATH = REPO_ROOT / "docs/index.md"
STATUS_MATRIX_PATH = REPO_ROOT / "docs/architecture/DOCUMENT_STATUS_MATRIX.md"


def test_capex_interface_burden_policy_doc_is_registered() -> None:
    relative = "docs/architecture/CAPEX_INTERFACE_BURDEN_POLICY.md"

    assert relative in INDEX_PATH.read_text(encoding="utf-8")
    assert relative in STATUS_MATRIX_PATH.read_text(encoding="utf-8")
    assert "AUTHORITATIVE SOURCE" in STATUS_MATRIX_PATH.read_text(encoding="utf-8")


def test_capex_interface_burden_policy_records_conservation_states() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    for marker in [
        "owned",
        "transferred",
        "waived",
        "accepted_residual",
        "open",
        "Interface responsibility must not disappear",
        "does not create tasks",
        "does not create a second task system",
        "CAPEX runtime activation disabled",
    ]:
        assert marker in text


def test_capex_interface_burden_policy_doc_contains_no_raw_corpus_markers() -> None:
    lowered = DOC_PATH.read_text(encoding="utf-8").lower()

    for marker in [
        "projektordner",
        "reference project",
        "blind-validation holdout",
        "alma ruma",
        "11639 otc",
    ]:
        assert marker not in lowered
