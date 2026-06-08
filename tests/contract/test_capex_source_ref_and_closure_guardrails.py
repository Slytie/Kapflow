from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs/architecture/CAPEX_SOURCE_REF_AND_CLOSURE_GUARDRAILS.md"
INDEX_PATH = REPO_ROOT / "docs/index.md"
STATUS_MATRIX_PATH = REPO_ROOT / "docs/architecture/DOCUMENT_STATUS_MATRIX.md"


def test_source_ref_and_closure_guardrails_are_registered() -> None:
    relative = "docs/architecture/CAPEX_SOURCE_REF_AND_CLOSURE_GUARDRAILS.md"

    assert relative in INDEX_PATH.read_text(encoding="utf-8")
    assert relative in STATUS_MATRIX_PATH.read_text(encoding="utf-8")
    assert "AUTHORITATIVE SOURCE" in STATUS_MATRIX_PATH.read_text(encoding="utf-8")


def test_source_ref_and_closure_guardrails_record_no_false_closure_rules() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    for marker in [
        "source_occurrence:{source_occurrence_id}",
        "presence-only evidence are not meaningful evidence",
        "a waiver is never a pass",
        "Stale snapshots must not be treated as fresh closure truth",
        "does not activate CAPEX runtime/product behavior",
    ]:
        assert marker in text


def test_source_ref_and_closure_guardrails_do_not_contain_raw_corpus_markers() -> None:
    lowered = DOC_PATH.read_text(encoding="utf-8").lower()

    for marker in [
        "projektordner",
        "reference project",
        "blind-validation holdout",
        "alma ruma",
        "11639 otc",
    ]:
        assert marker not in lowered
