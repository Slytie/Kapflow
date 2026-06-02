---
id: TASK-0235
epic: EPIC-137
title: "Artifact storage safety"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0234"]
risk: high
context_packs:
  - "codex/context/EPIC-137.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Root confinement on write/read; safe path segments; auth-before-blob-read; shared_env rejects authoritative inmem://.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-137.md`
- `codex/context/EPIC-137.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-002 plus regression tests
- Acceptance gate: `Storage safety tests pass; artifact download authorizes before read.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Storage safety tests pass; artifact download authorizes before read.
- Review focus covered: CR-002
- Refactor focus covered: RF-002;RF-003
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR002`
- Source phase: `P1 Platform Foundation`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR001`
- Recommended source branch: `foundation/ip5`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- `write_blob` sanitizes all path segments, including `workflow_run_id`, and rejects writes that do not resolve under the configured artifact root.
- Authoritative artifact downloads load metadata and enforce workflow-run scope before reading the blob; CLI/API download paths pass the DB-derived artifact root into blob reads.
- `shared_env` rejects authoritative `inmem://` downloads with a fail-closed forbidden error.
- Focused storage/API/shared-env regressions passed on 2026-06-02 with `python3.11 -m pytest -q tests/unit/test_artifact_storage_safety.py tests/runtime/api/test_artifact_upload_profiles.py::test_cross_scope_artifact_download_authorizes_before_blob_read tests/security/isolation/test_shared_env_attested_identity.py::test_shared_env_rejects_authoritative_inmem_artifact_download tests/runtime/test_transaction_composition_safety.py`.
- This closes `MP-PR002` as a repo runtime safety gate only; it does not activate CAPEX production or import raw corpora.
