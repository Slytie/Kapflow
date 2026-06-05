# CAPEX Storage Blob Custody CED

## Status
Accepted Wave 1 design boundary. CAPEX runtime activation remains disabled.

## Scope
This CED closes `TASK-0387` as schema-design evidence for future storage/blob custody work. It does not add runtime tables, migrations, routes, storage backends, raw corpus ingest, pilot readiness, or production activation.

## Current Authority Boundary
ArtifactVersion remains the canonical artifact metadata object. It records immutable artifact identity, workflow/run scope, artifact kind, media type, byte digest, byte size, storage compatibility pointer, metadata, lineage, and creation time.

Object/blob bytes are not authoritative by themselves. Blob presence without canonical metadata, append-only events, and explicit pointers is not project truth, artifact truth, or official output truth.

ArtifactPointer targets `ArtifactVersion` only. It must never target a blob record, replica record, raw file, derived preview, search index, source occurrence, or external object directly.

The current `artifact_versions.storage_uri` field is compatibility state. It may identify where bytes can be read today, but it is not the future custody model. Later physical migrations may separate blob custody into dedicated tables while preserving existing artifact version semantics.

## Future Custody Concepts
`BlobRef` is the future durable content-addressed blob identity. It should capture digest, byte size, media type, encryption/custody metadata, and original-vs-derived posture without becoming artifact officialness.

`BlobReplica` is a future storage-location record for one `BlobRef`. It should represent backend, URI, region/location, state, verification time, and restore/copy posture. Multiple replicas may exist for one blob reference.

`BlobIngestSession` is a future audited ingest attempt. It should record actor, project/scope context, declared source, normalized input digest, idempotency key, validation state, and failure details without making bytes authoritative by itself.

`ArtifactVersionBlob` is the future binding from `ArtifactVersion` to `BlobRef`. It should allow an artifact version to identify its canonical byte payload while keeping artifact metadata and officialness in the one-truth artifact/pointer/event substrate.

`DerivedArtifact` is a future relation describing generated or transformed bytes such as preview, OCR, redaction, sanitized derivative, thumbnail, or extracted text. Derived bytes must not be treated as original evidence unless a later task explicitly models that relation and gate.

`DownloadEvent` is a future audit event/read model for download attempts. It should record authorized actor, artifact version, blob reference or compatibility URI, outcome, timestamp, and denial/error code. It is evidence, not a new source of artifact truth.

## Auth Before Download
The platform-mediated download sequence is:
1. Resolve artifact metadata by `artifact_version_id`.
2. Enforce tenant, domain, workflow-run, and project visibility before any byte read.
3. Resolve blob custody metadata or compatibility `storage_uri`.
4. Enforce storage-root/backend policy and digest expectations.
5. Read bytes.
6. Record or emit download audit evidence when the future `DownloadEvent` surface exists.

Failures before step 5 must not probe or leak blob existence. Non-members and cross-scope actors receive not-found style denial for project/workflow scope failures.

## Gate Mapping
This CED records the W1 interpretation for:
- `ARCH-W1-GATE-007`: auth-before-download is mediated by platform service.
- `ARCH-W1-GATE-008`: `BlobRef` and `BlobReplica` are separate from `ArtifactVersion`.
- `ARCH-W1-GATE-009`: `ArtifactPointer` targets `ArtifactVersion` only.

`ARCH-W1-GATE-010` remains open until the pilot storage gate checklist is satisfied or explicitly waived.

## Rollback And Recovery
Rollback posture is to leave runtime state inert or keep CAPEX storage capability disabled. Do not destructively delete governed artifacts, pointers, timeline events, project records, membership records, blob references, replicas, or download audit evidence as a rollback mechanism.

If bytes and metadata disagree, canonical metadata/events/pointers remain authoritative. Recovery is a new immutable version, explicit relation, or explicit pointer move; never mutate old artifact rows into a different truth.

## Explicit Non-Activation
This CED does not add physical tables, Alembic/bootstrap DDL, HTTP routes, frontend surfaces, raw corpus handling, storage backend rollout, Postgres rollout, index rebuild execution, pilot readiness, production readiness, or CAPEX runtime activation.
