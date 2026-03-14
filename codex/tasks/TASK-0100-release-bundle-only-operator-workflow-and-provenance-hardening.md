---
id: TASK-0100
epic: EPIC-080
title: "Make the release bundle the only operator-facing distribution path and harden provenance"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0084", "TASK-0099"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: []
---

## Context
The repo already had explicit bundle kinds and clean-clone release-bundle validation, but operator-facing guidance still treated the handoff bundle as a normal share path and the release bundle shipped only a minimal manifest.

This task closes that truth gap by making the release bundle the only endorsed operator/share distribution artifact while keeping internal handoff bundles available for Codex/review work.

## Objective
Promote `release_source_bundle` to the only documented/operator-default shareable source artifact and add a deterministic repo-owned provenance sidecar to that path.

## Non-goals
- No signing PKI or full supply-chain platform.
- No attempt to technically block every bad manual zip.
- No change to `runtime_workspace_bundle` semantics or runtime behavior.

## Source Files Changed
- `scripts/export_clean_source_bundle.py`
- `scripts/release_bundle_provenance.py`
- `scripts/validate_repo.py`
- `Makefile`
- `tests/contract/test_release_source_bundle_export.py`
- `tests/contract/test_clean_source_bundle_export.py`
- `tests/contract/test_source_bundle_distribution_truth.py`
- `README.md`
- `docs/planning/REPO_HYGIENE.md`
- `codex/tasks/TASK-0100-release-bundle-only-operator-workflow-and-provenance-hardening.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`

## Generated / downstream artifacts impacted
- `release_source_bundle` archives now include `release_provenance.json`.

## Plan
1. Freeze the new release vs handoff contract in targeted contract tests.
2. Add a deterministic repo-owned provenance sidecar for release bundles only.
3. Flip the human/operator Make alias so `clean-source-bundle` now means release export, while preserving an explicit internal handoff target.
4. Update validator and docs so the operator/review/runtime bundle distinction is explicit and enforced.

## Verification Run
- `pytest -q tests/contract/test_release_source_bundle_export.py tests/contract/test_clean_source_bundle_export.py tests/contract/test_source_bundle_distribution_truth.py`
- `python3 scripts/validate_repo.py --schemas-only`
- clean-clone `release_source_bundle` export + manifest/provenance inspection
- `git diff --check`

## Acceptance Criteria Coverage
- `release_source_bundle` is the only documented/operator-default shareable source artifact.
- Release bundles now include explicit deterministic provenance beyond the original manifest.
- Handoff and runtime bundles remain valid, but are explicitly internal/non-release.

## Completion Notes (2026-03-14)
- Added `release_provenance.json` for `release_source_bundle`, with deterministic file digests, curated manifest/lockfile inventory, and archive/commit metadata.
- Classified release bundles as `operator_release` and handoff bundles as `internal_handoff` in `bundle_manifest.json`.
- Flipped `make clean-source-bundle` to the release path, added explicit `release-source-bundle` and `handoff-source-bundle` targets, and demoted handoff/manual zip flows to internal-only documentation.
- Hardened `scripts/validate_repo.py` so the clean-clone release export path verifies the provenance sidecar against actual archive contents.
