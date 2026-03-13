# EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md

This note defines how example workflow documents are promoted into executable fixture inputs while preserving one-truth runtime semantics.

## 1) Corpus scope
The executable corpus lives at:
- `fixtures/example_document_corpus/manifest.yaml`
- `fixtures/example_document_corpus/seed_sets.json` (stable seed-set mirror for lightweight consumers)

Source documents are the existing template-pack completed examples:
- `fixtures/workflows/schedule_planning/template_pack/*_Example_COMPLETED.*`

Current fixture sets include:
- Stage06 review-ready inputs
- Stage06 needs-information inputs
- Stage07 issue/replan inputs
- approval evidence examples
- run-detail/timeline mixed examples

## 2) Categorization model
Each fixture document is categorized in the manifest as one of:
- `stage_input`
- `review_artifact`
- `stage_output`
- `issue_replan_example`

Seed sets compose these documents for scenario/test use:
- `stage06_review_ready_example_set`
- `stage06_needs_information_example_set`
- `stage07_issue_replan_example_set`
- `approval_evidence_example_set`
- `run_detail_timeline_example_set`

## 3) Ingress path (canonical)
Example documents enter runtime through the same canonical artifact path as production uploads:
- CLI:
  - `artifacts ingest --json`
  - `artifacts seed-corpus --json`
- API:
  - `POST /api/v1/artifacts/ingest`
  - subject-scoped upload endpoints (human task, approval, flag, workflow run)

Ingress behavior:
- stores bytes via canonical storage adapter (`infrastructure/artifacts/storage.py`)
- computes digest (`sha256:*`) and byte size
- creates immutable `artifact_versions` row
- records linkage through `artifact_links`
- emits authoritative `artifact.version.created` in the same transaction

Shared/public HTTP posture:
- `POST /api/v1/artifacts/ingest` and subject upload endpoints accept request bytes (`content_base64`) only.
- Shared HTTP does not accept caller-controlled `source_path` or `storage_root`.

Internal/local posture:
- CLI `artifacts ingest` / `artifacts seed-corpus`, runtime scenarios, and other internal adapters may continue to use local file-backed seeding through canonical ingress.
- Local/source-backed ingress records normalized `ingress_source_path`; request-byte ingress does not.

No fixture bypass path is allowed.

## 4) Manifest/version strategy
Manifest format:
- top-level: `corpus_id`, `version`, `documents`, `seed_sets`
- document fields: `fixture_id`, `workflow_id`, `category`, `artifact_kind`, `artifact_role`, `media_type`, `source_path`, `description`
- seed set fields: `seed_set_id`, `workflow_id`, `description`, `document_fixture_ids`

Versioning rules:
- `version` increments when fixture semantics or composition changes.
- `fixture_id` and `seed_set_id` are stable identifiers consumed by tests/export tooling.
- replacements update source files + manifest entries together; old fixture IDs should be preserved unless semantics truly change.

## 5) Naming and media-type policy
Naming strategy:
- fixture IDs are namespaced by workflow + stage intent:
  - `schedule.stage06.supervisor_review_doc.completed`
  - `schedule.stage07.replan_delta_workbook.completed`
- seed set IDs describe scenario intent, not file names.

Media types are explicit in manifest; current corpus uses:
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

## 6) Consumers
Runtime scenarios:
- Scenario harness resolves fixture IDs/source paths through the manifest and ingests through canonical commands.

Frontend snapshots:
- `scripts/export_frontend_snapshots.py` builds snapshots from real scenario-backed states seeded with canonical artifacts.

Future sandbox/agent tests:
- seed manifests provide deterministic input corpora without creating an alternate attachment truth store.

## 7) Authority rule
These files are fixtures, not authoritative workflow truth.
Authoritative claims remain:
- immutable artifact versions,
- append-only timeline events,
- audited pointers/current-state rows.

Fixtures are only repeatable inputs that must flow through the same canonical ingress path as any other artifact.
