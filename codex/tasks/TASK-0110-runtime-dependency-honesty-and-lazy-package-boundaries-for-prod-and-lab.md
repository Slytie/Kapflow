---
id: TASK-0110
epic: EPIC-100
title: "Restore runtime dependency honesty and lazy package boundaries for productization and future lab surfaces"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: []
risk: medium
context_packs: ["codex/context/EPIC-100.md", "codex/context/EPIC-110.md"]
patterns: ["PATTERN-008"]
---

## Context
The repo is now honest about many boundaries, but package metadata is still less truthful than runtime imports. Multiple `src/onetruth` runtime modules import `yaml`, while `PyYAML` is still effectively hidden behind non-runtime extras. If we start adding Workflow Lab runtime code on top of this, the metadata drift becomes worse.

## Objective
Align runtime dependencies and package import surfaces so `src/onetruth` modules — including any future thin Workflow Lab package — do not rely on undeclared runtime dependencies or eager package imports.

## Non-goals
- No broad packaging-platform rewrite.
- No new Workflow Lab runtime package unless it stays dependency-light.
- No reopening of shared-env or capability semantics.

## Source files to read first
- `pyproject.toml`
- `src/onetruth/api/__init__.py`
- `src/onetruth/api/main.py`
- runtime modules under `src/onetruth/` that import `yaml`
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`

## Context packs / patterns to consult
- codex/context/EPIC-100.md
- codex/context/EPIC-110.md
- PATTERN-008

## Source files to change
- `pyproject.toml`
- relevant `__init__.py` surfaces
- any targeted import-boundary tests
- `README.md` / docs if install truth changes

## Generated / downstream artifacts impacted
- Task-memory and epic/context updates only.

## Plan
1. Inventory runtime imports under `src/onetruth/` that rely on undeclared core dependencies.
2. Decide which packages belong in core runtime vs a future explicit extra.
3. Keep package entrypoints/imports lazy so lightweight tools stay lightweight.
4. Add tests/validation so future runtime/lab work cannot regress metadata honesty.

## Verification
- targeted import/package-boundary tests
- `python3 scripts/validate_repo.py --schemas-only`
- any dependency/install truth checks added by the task

## Acceptance criteria
- Core runtime dependency metadata matches actual `src/onetruth` import behavior.
- Lightweight package imports remain honest and future lab work does not inherit a hidden dependency leak.
- Documentation tells future agents which dependency boundary is authoritative.

## Notes / decisions
Treat this as a prerequisite support task. The goal is to keep future productization and Workflow Lab work from building on misleading metadata.

## Implementation notes (2026-03-17)
- `pyproject.toml` now declares `PyYAML>=6,<7` in core runtime dependencies instead of hiding it in the `dev` extra.
- `src/onetruth/infrastructure/definitions/__init__.py`, `src/onetruth/infrastructure/generation/__init__.py`, and `src/onetruth/integrations/openai/__init__.py` now resolve public exports lazily so bare package imports stay lightweight and do not preload YAML-backed submodules.
- Added subprocess-based contract coverage in `tests/contract/test_runtime_package_dependency_honesty.py` to freeze both the metadata truth and the lazy package-boundary behavior.

## Verification run
- `python3.11 -m pytest -q tests/contract/test_runtime_package_dependency_honesty.py`
- `python3.11 -m pytest -q tests/contract/test_api_optional_extra_import_boundaries.py`
- `python3.11 -m pytest -q tests/contract/test_runtime_package_dependency_honesty.py tests/contract/test_api_optional_extra_import_boundaries.py`
- `python3 scripts/validate_repo.py --schemas-only`
