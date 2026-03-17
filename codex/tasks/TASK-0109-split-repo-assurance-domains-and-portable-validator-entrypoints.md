---
id: TASK-0109
epic: EPIC-080
title: "Split repo assurance domains and make validator entrypoints portable"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0100"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
`scripts/validate_repo.py` has become a high-value assurance harness, but it is also becoming the next monolith:
- schema checks
- governance checks
- secret hygiene
- bundle/export validation
- release-provenance validation
- task-index/current-focus consistency

This is strategically valuable code, but it is now too overloaded in naming and structure. There is also a portability nuance: some release-bundle checks assume a live git clone in ways that can be awkward in handoff/unpacked contexts.

## Objective
Refactor repo assurance into clearer domains while preserving the current one-command entrypoint:
- schema validation
- governance/metadata validation
- release/bundle validation
- secret hygiene

…and make clone-dependent release validation fail more portably and transparently when a live git context is unavailable.

## Non-goals
- No change to release policy itself.
- No new security rules beyond the current source-of-truth posture.
- No attempt to support arbitrary non-git source trees as full release contexts.

## Source files to read first
- `scripts/validate_repo.py`
- `scripts/export_clean_source_bundle.py`
- `scripts/doctor.py`
- `Makefile`
- `.github/workflows/main.yml`
- `.github/workflows/secret_hygiene.yml`

## Context packs / patterns to consult
- `codex/context/EPIC-080.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-009.md`

## Source files to change
- `scripts/validate_repo.py`
- one or more new validator helper/entrypoint modules under `scripts/`
- `Makefile`
- docs/runbook/README text for validator entrypoints
- targeted contract/unit tests for validator behavior

## Generated / downstream artifacts impacted
- Task-memory and epic/context updates only.

## Plan
1. Split assurance code into clear helper/entrypoint domains while keeping `validate_repo.py` as the umbrella wrapper.
2. Make the CLI taxonomy more truthful (`schema`, `governance`, `release`, `secrets`, etc.).
3. Improve release-validation failure semantics when a clone-dependent path is unavailable.
4. Keep existing CI and docs behavior compatible or explicitly updated.

## Verification
- targeted tests around validator entrypoints
- `python3 scripts/validate_repo.py --schemas-only`
- `python3 scripts/validate_repo.py --secrets-only`
- representative release validation path
- `make lint`

## Acceptance criteria
- Assurance code is less monolithic and easier to reason about.
- Validator modes are clearer and more portable.
- CI/operator workflows remain aligned with the new assurance taxonomy.

## Notes / decisions
This task is about maintainability of the assurance layer itself. Treat it as platform work, not product work.
