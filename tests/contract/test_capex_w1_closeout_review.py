from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT_PATH = REPO_ROOT / "docs" / "architecture" / "CAPEX_W1_CLOSEOUT_REVIEW.md"
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

ACTIVATION_CLAIM_MARKERS = (
    "capex runtime activation is enabled",
    "capex runtime is active",
    "pilot readiness granted",
    "production readiness granted",
    "pilot go decision",
    "production go decision",
)


def _closeout_text() -> str:
    return CLOSEOUT_PATH.read_text(encoding="utf-8")


def test_capex_w1_closeout_review_is_registered() -> None:
    relative_path = "docs/architecture/CAPEX_W1_CLOSEOUT_REVIEW.md"

    assert relative_path in DOC_INDEX.read_text(encoding="utf-8")
    assert f"`{relative_path}` | AUTHORITATIVE SOURCE" in STATUS_MATRIX.read_text(
        encoding="utf-8"
    )


def test_capex_w1_closeout_review_maps_all_w1_gates() -> None:
    text = _closeout_text()

    for gate_number in range(1, 11):
        assert f"ARCH-W1-GATE-{gate_number:03d}" in text

    assert (
        "Gates `ARCH-W1-GATE-001` through `ARCH-W1-GATE-009` have repo evidence."
        in text
    )
    assert "`ARCH-W1-GATE-010` remains `blocked_pending_evidence`" in text
    assert "future task supplies real pilot evidence or an explicit waiver" in text


def test_capex_w1_closeout_review_records_overkill_and_master_patch_posture() -> None:
    text = _closeout_text()

    required_markers = (
        "typed registries, architecture docs, contract tests, and direct-membership prototypes only",
        "Defer physical authorization projections",
        "custody migrations",
        "storage backend rollout",
        "richer CAPEX workpages",
        "raw corpus ingestion",
        "CAPEX activation",
        "Master patch instructions are repo-native traceability text only",
        "Do not mutate the source ZIP",
        "import raw project material",
    )

    missing = [marker for marker in required_markers if marker not in text]

    assert missing == []


def test_capex_w1_closeout_review_has_no_raw_corpus_or_activation_claims() -> None:
    lowered = _closeout_text().lower()

    raw_leaks = sorted(marker for marker in RAW_CORPUS_MARKERS if marker in lowered)
    activation_claims = sorted(
        marker for marker in ACTIVATION_CLAIM_MARKERS if marker in lowered
    )

    assert raw_leaks == []
    assert activation_claims == []
    assert "CAPEX runtime activation" in _closeout_text()
    assert "does not add migrations" in _closeout_text()
