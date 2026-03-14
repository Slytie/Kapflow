---
id: TASK-0090
epic: EPIC-080
title: "Close the remaining bootstrap/install truth gap and ban tracked build artifacts"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0085", "TASK-0087"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: []
---

## Context
`TASK-0085` made the repo far more honest, but a few bootstrap and packaging mismatches remained: Python support metadata was broader than the validated baseline, CI still installed from `requirements.txt` even though the actual lint/test toolchain lived in `pyproject` extras, `.editorconfig` was absent, `frontend/package.json` lacked explicit `engines`, and tracked `src/onetruth_runtime.egg-info/*` kept generated build output inside the source boundary.

## Objective
Make the repo tell one coherent toolchain/bootstrap story: one validated Python baseline, one authoritative dev/CI install path, explicit editor/runtime metadata, and an executable rule that tracked build artifacts such as `*.egg-info` are not part of source truth.

## Non-goals
- No broad dependency-version upgrade sweep.
- No redesign of release bundle kinds from `TASK-0084`.
- No removal of intentionally tracked generated artifacts under `build/generated/` without an explicit source-of-truth decision.

## Source Files Changed
- `pyproject.toml`
- `requirements.txt`
- `.github/workflows/main.yml`
- `.github/workflows/agent_api.yml`
- `scripts/doctor.py`
- `scripts/validate_repo.py`
- `README.md`
- `docs/ops/CI_TROUBLESHOOTING.md`
- `.editorconfig`
- `frontend/package.json`
- `.gitignore`
- `tests/contract/test_toolchain_truth.py`
- `codex/tasks/TASK-0090-bootstrap-install-truth-and-tracked-build-artifact-ban.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`
- tracked `src/onetruth_runtime.egg-info/*` build artifacts removed from version control

## Generated / downstream artifacts impacted
- Bootstrap/toolchain contract only; no business-runtime outputs changed.

## Plan
1. Freeze the repo’s validated Python baseline in package metadata and contract tests.
2. Collapse local/CI installation onto one editable `pyproject` extras path.
3. Add missing workspace-truth metadata (`.editorconfig`, frontend Node engines).
4. Remove tracked `egg-info` output and fail validation if it reappears.

## Verification Run
- PASS - `python3 scripts/doctor.py --check`
- PASS - `python3.11 -m pip install -e ".[api,dev]"` (required to verify the repo under the validated Python `3.11` baseline)
- PASS - `python3 -m pytest tests/contract/test_toolchain_truth.py -q`
- PASS - `git ls-files -- '*.egg-info/*'` (no tracked matches after removing `src/onetruth_runtime.egg-info/` from the Git index)
- BLOCKED BY EXISTING HEAD-CLONE VALIDATION SEMANTICS - `python3 scripts/validate_repo.py --schemas-only`
- BLOCKED BY EXISTING HEAD-CLONE VALIDATION SEMANTICS - `make lint`
- BLOCKED BY EXISTING HEAD-CLONE VALIDATION SEMANTICS - `python3 -m pytest tests/contract/test_toolchain_truth.py tests/contract/test_validation_harness.py -q`

## Acceptance Criteria Coverage
- The repo now has one explicit validated Python baseline and one obvious CI/dev install story.
- `.editorconfig` and frontend engine metadata exist and match the documented baseline.
- Tracked `*.egg-info` content is removed and validation fails if it returns.
- No business-runtime semantics changed as part of this task.

## Completion Notes (2026-03-14)
- `requirements.txt` is now only a compatibility shim; authoritative local/CI dependencies come from `pyproject.toml` editable extras.
- CI, doctor guidance, and README quickstart now all point at the same backend install command: `python3.11 -m pip install -e ".[api,dev]"`.
- `scripts/validate_repo.py` now treats tracked `.egg-info` content as an explicit source-boundary violation, aligned with release-bundle clutter exclusion.
- Remaining verification nuance: the repo’s existing release-bundle validation clones committed `HEAD`, so local pre-commit runs still see the old tracked `egg-info` content until these changes are committed.
