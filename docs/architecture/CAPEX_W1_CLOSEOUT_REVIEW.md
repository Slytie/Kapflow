# CAPEX Wave 1 Closeout Review

## Status
Accepted Wave 1 closeout review. CAPEX runtime activation remains disabled.

## Scope
This review closes `TASK-0390` as decision-docket and traceability evidence. It records Wave 1 repository evidence, overkill assessment, old-decision posture, and master patch instructions without changing runtime behavior.

## Decision Docket

| Gate | Decision | Evidence | Status |
|---|---|---|---|
| `ARCH-W1-GATE-001` | `capex_platform` cannot import domain packages. | `tests/unit/test_domain_runtime_registry.py`; `docs/architecture/CAPEX_DOMAIN_RUNTIME_MANIFESTS.md` | repo evidence recorded |
| `ARCH-W1-GATE-002` | Domain manifests validate under the domain manifest schema. | `tests/contract/test_domain_manifest_schema.py`; `docs/domains/logistics/domain.yaml`; `docs/domains/capex/domain.yaml` | repo evidence recorded |
| `ARCH-W1-GATE-003` | Generic approval response emits canonical approval transition/event only; domain effects live behind hooks. | `docs/adr/ADR-005-approval-response-domain-hooks.md`; `tests/contract/test_handler_import_boundaries.py`; `tests/unit/test_approval_effect_registry.py` | repo evidence recorded |
| `ARCH-W1-GATE-004` | `capex_projects.project_id` is the durable root; workflow runs are execution identity only. | `docs/architecture/CAPEX_PROJECT_AUTHORIZATION_CED.md`; project access API and schema parity tests | repo evidence recorded |
| `ARCH-W1-GATE-005` | Direct `project_memberships` and future authorization projections are separate. | `docs/architecture/CAPEX_PROJECT_AUTHORIZATION_CED.md`; `tests/unit/test_capex_authorized_projects_query.py` | repo evidence recorded |
| `ARCH-W1-GATE-006` | Project-scoped runtime rows use direct project IDs where the foundation has accepted them. | CAPEX project schema parity and child API tests | repo evidence recorded |
| `ARCH-W1-GATE-007` | Auth-before-download is mediated by platform service. | `docs/architecture/CAPEX_STORAGE_BLOB_CUSTODY_CED.md`; focused artifact download API regressions | repo evidence recorded |
| `ARCH-W1-GATE-008` | Future `BlobRef` and `BlobReplica` are separate from `ArtifactVersion`. | `docs/architecture/CAPEX_STORAGE_BLOB_CUSTODY_CED.md`; CED contract tests | repo evidence recorded |
| `ARCH-W1-GATE-009` | `ArtifactPointer` targets `ArtifactVersion` only. | `docs/architecture/CAPEX_STORAGE_BLOB_CUSTODY_CED.md`; pointer-family and CED contract tests | repo evidence recorded |
| `ARCH-W1-GATE-010` | Real pilot storage gate must be resolved before pilot readiness. | `docs/planning/checklists/CAPEX_PILOT_STORAGE_GATE.md` | `blocked_pending_evidence` |

Gates `ARCH-W1-GATE-001` through `ARCH-W1-GATE-009` have repo evidence. `ARCH-W1-GATE-010` remains `blocked_pending_evidence` unless a future task supplies real pilot evidence or an explicit waiver.

## Overkill Assessment
Wave 1 remains intentionally narrow: typed registries, architecture docs, contract tests, and direct-membership prototypes only.

Defer physical authorization projections, custody migrations, storage backend rollout, Postgres rollout, richer CAPEX workpages, raw corpus ingestion, production-like dashboards, and CAPEX activation. Adopt heavier tooling only after a later task proves a concrete need and records the activation or waiver decision.

## Old-Decision Updates
- Prior wording that treated Wave 1 storage custody as pure unknown is now refined: the CED and checklist exist, while real pilot storage evidence or waiver remains open.
- Prior wording that implied project authorization projection state exists is corrected: direct membership and `AuthorizedProjectsQuery` exist; physical authorization projection runtime state remains future work.
- No old decision is updated to permit CAPEX activation, raw corpus handling, production-like execution, or direct blob authority.

## Master Patch Instructions
Master patch instructions are repo-native traceability text only. If a future source package or master plan is reconciled, update planning rows to reference this closeout review, the code pattern register, the project authorization CED, and the storage custody CED/checklist.

Do not mutate the source ZIP, import raw project material, copy extracted filenames or document text, or treat this closeout as a pilot or production approval decision.

## Explicit Non-Activation
This closeout does not add migrations, schema DDL, HTTP routes, frontend behavior, storage backend rollout, Postgres rollout, raw corpus approval, pilot readiness, production readiness, or CAPEX runtime activation.
