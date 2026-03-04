from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "fixtures/example_document_corpus/manifest.yaml"


@dataclass(frozen=True)
class CorpusDocument:
    fixture_id: str
    workflow_id: str
    category: str
    artifact_kind: str
    artifact_role: str | None
    media_type: str
    source_path: Path
    description: str


@dataclass(frozen=True)
class CorpusSeedSet:
    seed_set_id: str
    workflow_id: str
    description: str
    document_fixture_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExampleDocumentCorpus:
    corpus_id: str
    version: int
    manifest_path: Path
    documents: tuple[CorpusDocument, ...]
    seed_sets: tuple[CorpusSeedSet, ...]

    def document_by_id(self, fixture_id: str) -> CorpusDocument:
        for item in self.documents:
            if item.fixture_id == fixture_id:
                return item
        raise ValueError(f"document fixture_id not found: {fixture_id}")

    def seed_set_by_id(self, seed_set_id: str) -> CorpusSeedSet:
        for item in self.seed_sets:
            if item.seed_set_id == seed_set_id:
                return item
        raise ValueError(f"seed_set_id not found: {seed_set_id}")


def load_example_document_corpus(
    manifest_path: Path | None = None,
) -> ExampleDocumentCorpus:
    path = (manifest_path or DEFAULT_MANIFEST_PATH).resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("example document corpus manifest must be a mapping")

    corpus_id = str(raw.get("corpus_id") or "").strip()
    version = int(raw.get("version") or 0)
    if not corpus_id:
        raise ValueError("manifest missing corpus_id")
    if version <= 0:
        raise ValueError("manifest version must be positive")

    raw_documents = raw.get("documents")
    if not isinstance(raw_documents, list):
        raise ValueError("manifest documents must be a list")
    docs: list[CorpusDocument] = []
    seen_fixture_ids: set[str] = set()
    for item in raw_documents:
        if not isinstance(item, dict):
            raise ValueError("document entries must be objects")
        fixture_id = str(item.get("fixture_id") or "").strip()
        if not fixture_id:
            raise ValueError("document fixture_id is required")
        if fixture_id in seen_fixture_ids:
            raise ValueError(f"duplicate fixture_id in manifest: {fixture_id}")
        seen_fixture_ids.add(fixture_id)
        source_path = _resolve_source_path(path.parent, item.get("source_path"))
        docs.append(
            CorpusDocument(
                fixture_id=fixture_id,
                workflow_id=str(item.get("workflow_id") or "").strip(),
                category=str(item.get("category") or "").strip(),
                artifact_kind=str(item.get("artifact_kind") or "").strip(),
                artifact_role=(
                    str(item["artifact_role"]).strip()
                    if item.get("artifact_role") is not None
                    else None
                ),
                media_type=str(item.get("media_type") or "").strip(),
                source_path=source_path,
                description=str(item.get("description") or "").strip(),
            )
        )

    raw_seed_sets = raw.get("seed_sets")
    if not isinstance(raw_seed_sets, list):
        raise ValueError("manifest seed_sets must be a list")
    sets: list[CorpusSeedSet] = []
    seen_seed_set_ids: set[str] = set()
    for item in raw_seed_sets:
        if not isinstance(item, dict):
            raise ValueError("seed set entries must be objects")
        seed_set_id = str(item.get("seed_set_id") or "").strip()
        if not seed_set_id:
            raise ValueError("seed_set_id is required")
        if seed_set_id in seen_seed_set_ids:
            raise ValueError(f"duplicate seed_set_id in manifest: {seed_set_id}")
        seen_seed_set_ids.add(seed_set_id)
        doc_ids = item.get("document_fixture_ids")
        if not isinstance(doc_ids, list) or not doc_ids:
            raise ValueError(f"seed_set {seed_set_id} must include document_fixture_ids")
        normalized_doc_ids = tuple(str(doc_id).strip() for doc_id in doc_ids)
        for doc_id in normalized_doc_ids:
            if doc_id not in seen_fixture_ids:
                raise ValueError(
                    f"seed_set {seed_set_id} references unknown fixture_id: {doc_id}"
                )
        sets.append(
            CorpusSeedSet(
                seed_set_id=seed_set_id,
                workflow_id=str(item.get("workflow_id") or "").strip(),
                description=str(item.get("description") or "").strip(),
                document_fixture_ids=normalized_doc_ids,
            )
        )

    return ExampleDocumentCorpus(
        corpus_id=corpus_id,
        version=version,
        manifest_path=path,
        documents=tuple(docs),
        seed_sets=tuple(sets),
    )


def seed_payloads_for_set(
    *,
    corpus: ExampleDocumentCorpus,
    seed_set_id: str,
    workflow_run_id: str,
    idempotency_prefix: str,
) -> list[dict[str, Any]]:
    seed_set = corpus.seed_set_by_id(seed_set_id)
    payloads: list[dict[str, Any]] = []
    for index, fixture_id in enumerate(seed_set.document_fixture_ids):
        document = corpus.document_by_id(fixture_id)
        payloads.append(
            {
                "workflow_run_id": workflow_run_id,
                "artifact_kind": document.artifact_kind,
                "artifact_role": document.artifact_role,
                "media_type": document.media_type,
                "source_path": str(document.source_path),
                "file_name": document.source_path.name,
                "metadata_json": {
                    "fixture_id": document.fixture_id,
                    "corpus_id": corpus.corpus_id,
                    "corpus_version": corpus.version,
                    "category": document.category,
                    "description": document.description,
                },
                "idempotency_key": f"{idempotency_prefix}:{seed_set_id}:{index}:{document.fixture_id}",
            }
        )
    return payloads


def _resolve_source_path(base_dir: Path, raw: Any) -> Path:
    if raw is None:
        raise ValueError("document source_path is required")
    source = Path(str(raw))
    if not source.is_absolute():
        source = (base_dir / source).resolve()
    if not source.exists() or not source.is_file():
        raise ValueError(f"document source_path does not exist: {source}")
    return source

