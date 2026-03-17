---
id: TASK-0112
epic: EPIC-100
title: "Enforce local_dev loopback-only startup with an explicit unsafe override contract"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0111"]
risk: high
context_packs: ["codex/context/EPIC-100.md"]
patterns: []
---

## Context
The repo documents `local_dev` as a loopback-only trusted-header environment, but startup still accepts arbitrary hosts. That leaves too much room for accidental exposure and weakens the current profile model by turning a documented assumption into a non-enforced convention.

## Objective
Make `local_dev` loopback-only by executable invariant, with any non-loopback startup requiring a deliberately named unsafe override intended only for controlled test scenarios.

## Non-goals
- No new deployment system.
- No auth redesign.
- No attempt to turn `local_dev` into a shared environment.

## Source files to read first
- `src/onetruth/api/main.py`
- `src/onetruth/api/dependencies.py`
- CLI/startup docs
- runtime/security tests around profile startup behavior

## Context packs / patterns to consult
- codex/context/EPIC-100.md

## Source files to change
- API startup/profile handling
- docs/ops / README startup guidance
- targeted tests for host/profile combinations

## Generated / downstream artifacts impacted
- task-memory / epic/context updates only

## Plan
1. Identify the narrowest startup seam that controls `local_dev` host binding.
2. Enforce loopback-only behavior by default.
3. Add an explicit unsafe override with docs that make the risk visible.
4. Freeze expected behavior in runtime/security tests.

## Verification
- targeted startup/runtime/security tests
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- `local_dev` refuses non-loopback bind unless the explicit unsafe override is present.
- Docs and CLI behavior tell the same story.
- The production/shared-env posture is not affected.

## Notes / decisions
This task should stay small and profile-specific. It is about executable startup truth, not broader deployment architecture.

## Implementation notes
- `src/onetruth/api/main.py` now enforces loopback-only `local_dev` startup in the supported `onetruth-api` entrypoint and advertises the explicit unsafe override in CLI help text.
- Added `tests/runtime/api/test_api_startup_host_guard.py` to freeze loopback allows, fail-closed non-loopback binds, the explicit override, and unaffected `shared_env` / `ci_test` behavior.
- README, ops guidance, and runtime-bootstrap docs now treat `onetruth-api` as the guarded local-dev startup contract and document non-loopback bind only as a controlled test escape hatch.

## Completion notes
- The request-context trust model and `shared_env` posture were left unchanged.
- This task intentionally did not attempt to guard every ad hoc raw `uvicorn onetruth.api.main:app` invocation style; that broader entrypoint unification remains a separate concern.
