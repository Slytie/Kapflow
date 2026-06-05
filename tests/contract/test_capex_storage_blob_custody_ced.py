from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CED_PATH = REPO_ROOT / "docs" / "architecture" / "CAPEX_STORAGE_BLOB_CUSTODY_CED.md"
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


def test_capex_storage_blob_custody_ced_records_future_schema_boundary() -> None:
    text = CED_PATH.read_text(encoding="utf-8")

    required_markers = (
        "Accepted Wave 1 design boundary",
        "BlobRef",
        "BlobReplica",
        "BlobIngestSession",
        "ArtifactVersionBlob",
        "DerivedArtifact",
        "DownloadEvent",
        "ArtifactVersion remains the canonical artifact metadata object",
        "Object/blob bytes are not authoritative by themselves",
        "ArtifactPointer targets `ArtifactVersion` only",
        "artifact_versions.storage_uri",
        "compatibility state",
        "ARCH-W1-GATE-007",
        "ARCH-W1-GATE-008",
        "ARCH-W1-GATE-009",
        "ARCH-W1-GATE-010",
    )

    missing = [marker for marker in required_markers if marker not in text]

    assert missing == []


def test_capex_storage_blob_custody_ced_records_auth_before_download_order() -> None:
    text = CED_PATH.read_text(encoding="utf-8")

    required_order = [
        "Resolve artifact metadata by `artifact_version_id`.",
        "Enforce tenant, domain, workflow-run, and project visibility before any byte read.",
        "Resolve blob custody metadata or compatibility `storage_uri`.",
        "Enforce storage-root/backend policy and digest expectations.",
        "Read bytes.",
        "Record or emit download audit evidence",
    ]
    offsets = [text.index(marker) for marker in required_order]

    assert offsets == sorted(offsets)
    assert "Failures before step 5 must not probe or leak blob existence." in text


def test_capex_storage_blob_custody_ced_is_registered_and_has_no_raw_corpus_markers() -> None:
    relative_path = "docs/architecture/CAPEX_STORAGE_BLOB_CUSTODY_CED.md"
    text = CED_PATH.read_text(encoding="utf-8")

    assert relative_path in DOC_INDEX.read_text(encoding="utf-8")
    assert f"`{relative_path}` | AUTHORITATIVE SOURCE" in STATUS_MATRIX.read_text(
        encoding="utf-8"
    )
    leaks = sorted(marker for marker in RAW_CORPUS_MARKERS if marker in text.lower())

    assert leaks == []


def test_capex_storage_blob_custody_ced_does_not_activate_runtime_surfaces() -> None:
    text = CED_PATH.read_text(encoding="utf-8")

    required_markers = (
        "does not add physical tables",
        "Alembic/bootstrap DDL",
        "HTTP routes",
        "frontend surfaces",
        "raw corpus handling",
        "storage backend rollout",
        "Postgres rollout",
        "pilot readiness",
        "production readiness",
        "CAPEX runtime activation",
    )

    missing = [marker for marker in required_markers if marker not in text]

    assert missing == []
