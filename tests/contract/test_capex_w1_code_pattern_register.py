from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTER_PATH = REPO_ROOT / "docs" / "architecture" / "CAPEX_W1_CODE_PATTERN_REGISTER.md"
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
    "activation_allowed=true",
    "activation_allowed = true",
    "capex runtime activation is enabled",
    "capex runtime is active",
    "pilot readiness granted",
    "production readiness granted",
)


def _register_text() -> str:
    return REGISTER_PATH.read_text(encoding="utf-8")


def test_capex_w1_code_pattern_register_is_registered() -> None:
    relative_path = "docs/architecture/CAPEX_W1_CODE_PATTERN_REGISTER.md"

    assert relative_path in DOC_INDEX.read_text(encoding="utf-8")
    assert f"`{relative_path}` | AUTHORITATIVE SOURCE" in STATUS_MATRIX.read_text(
        encoding="utf-8"
    )


def test_capex_w1_code_pattern_register_has_exact_pattern_families() -> None:
    text = _register_text()

    expected_headings = (
        "### Domain-Runtime Manifest Registry",
        "### AuthorizedProjectsQuery And Direct Membership Visibility",
        "### Storage Blob Custody Auth-Before-Download",
    )

    assert [line for line in text.splitlines() if line.startswith("### ")] == list(
        expected_headings
    )
    for marker in (
        "All snippets in this register are illustrative and non-production.",
        "DomainRuntimeRegistry",
        "AuthorizedProjectsQuery",
        "auth-before-download",
        "ArtifactVersion",
    ):
        assert marker in text


def test_capex_w1_code_pattern_register_records_forbidden_overbuilds() -> None:
    text = _register_text()

    required_markers = (
        "dynamic domain package loading",
        "frontend-only auth filtering",
        "global project list exposure",
        "blob truth bypassing `ArtifactVersion`",
        "pointer targets to blobs",
        "storage reads before scope authorization",
    )

    missing = [marker for marker in required_markers if marker not in text]

    assert missing == []


def test_capex_w1_code_pattern_register_has_no_raw_corpus_or_activation_claims() -> None:
    lowered = _register_text().lower()

    raw_leaks = sorted(marker for marker in RAW_CORPUS_MARKERS if marker in lowered)
    activation_claims = sorted(
        marker for marker in ACTIVATION_CLAIM_MARKERS if marker in lowered
    )

    assert raw_leaks == []
    assert activation_claims == []
    assert "CAPEX runtime activation" in _register_text()
    assert "does not add migrations" in _register_text()
