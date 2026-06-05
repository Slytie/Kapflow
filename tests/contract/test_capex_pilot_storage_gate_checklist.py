from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKLIST_PATH = REPO_ROOT / "docs" / "planning" / "checklists" / "CAPEX_PILOT_STORAGE_GATE.md"
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


def test_capex_pilot_storage_gate_checklist_defaults_to_blocked() -> None:
    text = CHECKLIST_PATH.read_text(encoding="utf-8")

    assert "Gate result: `blocked_pending_evidence`." in text
    assert "does not pass, waive, or execute the pilot storage gate" in text
    assert "CAPEX remains disabled" in text


def test_capex_pilot_storage_gate_checklist_covers_required_evidence() -> None:
    text = CHECKLIST_PATH.read_text(encoding="utf-8")

    required_markers = (
        "Pilot DB topology selected",
        "Postgres decision recorded, or explicit waiver",
        "Blob custody backend selected",
        "Backup set includes DB state, artifact/blob state, release bundle, and secret/config references",
        "Restore rehearsal completed",
        "auth-before-read after restore",
        "Digest verification",
        "Index rebuild rehearsal",
        "DB capacity, blob capacity, and temporary workspace capacity",
        "Secret/config references are recorded without secret values",
        "Production and lab storage roots/backends are separate",
        "Tenant/domain/project authorization is enforced before blob read",
        "Deployment reviewer signoff",
        "SRE reviewer signoff",
        "Security reviewer signoff",
        "Architecture reviewer signoff",
    )

    missing = [marker for marker in required_markers if marker not in text]

    assert missing == []


def test_capex_pilot_storage_gate_checklist_is_registered_and_has_no_raw_corpus_markers() -> None:
    relative_path = "docs/planning/checklists/CAPEX_PILOT_STORAGE_GATE.md"
    text = CHECKLIST_PATH.read_text(encoding="utf-8")

    assert relative_path in DOC_INDEX.read_text(encoding="utf-8")
    assert f"`{relative_path}` | AUTHORITATIVE SOURCE" in STATUS_MATRIX.read_text(
        encoding="utf-8"
    )
    leaks = sorted(marker for marker in RAW_CORPUS_MARKERS if marker in text.lower())

    assert leaks == []


def test_capex_pilot_storage_gate_checklist_does_not_activate_capex() -> None:
    text = CHECKLIST_PATH.read_text(encoding="utf-8")

    required_markers = (
        "does not create pilot readiness",
        "production readiness",
        "storage backend rollout",
        "Postgres rollout",
        "raw corpus approval",
        "route/API changes",
        "schema migrations",
        "CAPEX runtime activation",
    )

    missing = [marker for marker in required_markers if marker not in text]

    assert missing == []
