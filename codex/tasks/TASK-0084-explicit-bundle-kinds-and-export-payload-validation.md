---
id: TASK-0084
epic: EPIC-080
title: "Make bundle kinds explicit and validate the exported payload"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0075"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-009", "PATTERN-003"]
---

## Context
The repo now has a clean source bundle exporter, but the semantics of handoff, release, and runtime workspace bundles are still implicit. Validation should prove the actual exported payload, not just assumptions about tracked files.

## Objective
Define explicit bundle kinds and validate the actual archive payload for each, while keeping handoff bundles available without mislabeling them as release artifacts.

## Non-goals
- No full SBOM/provenance implementation.
- No runtime workspace bundle redesign.
- No new release engineering platform.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`
- `scripts/export_clean_source_bundle.py`
- `tests/contract/test_clean_source_bundle_export.py`
- `tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `docs/planning/REPO_HYGIENE.md`
- `README.md`

## Context packs / patterns to consult
- `codex/context/EPIC-080.md`
- `docs/patterns/cards/PATTERN-009.md`
- `docs/patterns/cards/PATTERN-003.md`

## Source files to change
- `scripts/export_clean_source_bundle.py`
- `scripts/validate_repo.py`
- `tests/contract/test_clean_source_bundle_export.py`
- `tests/contract/test_release_source_bundle_export.py`
- `README.md`
- `docs/planning/REPO_HYGIENE.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/tasks/TASK-0084-explicit-bundle-kinds-and-export-payload-validation.md`

## Generated / downstream artifacts impacted
- Source bundle archives and validation checks.

## Plan
1. Define explicit semantics for handoff source, release source, and runtime workspace bundles.
2. Extend validation to inspect the actual exported archive payload.
3. Add contract coverage for the new release-bundle posture.
4. Keep the existing handoff workflow working with clearer naming and trust assumptions.

## Verification
- `pytest tests/contract/test_clean_source_bundle_export.py -q`
- `pytest tests/contract/test_release_source_bundle_export.py -q`
- `python3 scripts/validate_repo.py`

## Acceptance criteria
- Bundle kinds and trust assumptions are explicit in code and docs.
- Validation can inspect the actual exported payload.
- Handoff bundles remain available but are not mislabeled as release artifacts.
- The task stays bounded and does not expand into full provenance infrastructure.

## Notes / decisions
- The exported payload must be the thing that gets validated.
