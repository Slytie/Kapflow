---
id: TASK-0078
epic: EPIC-010
title: "Add explicit API boundary profiles and a principal-resolver seam"
status: DONE
owners: ["platform"]
reviewers: ["security", "qa"]
depends_on: ["TASK-0077"]
risk: high
context_packs: ["codex/context/EPIC-010.md"]
patterns: ["PATTERN-008"]
---

## Context
Trusted request headers are useful for local development and CI, but the repo does not yet make that trust boundary explicit. Shared environments need a fail-closed posture before capability enforcement moves deeper into the stack.

## Objective
Introduce explicit API boundary profiles (`local_dev`, `ci_test`, `shared_env`) plus a principal-resolver seam so trusted headers remain a deliberate local-only mode instead of an ambient default.

## Non-goals
- No capability-enforcement changes in this task.
- No JWT/OIDC implementation.
- No broad API-shell rewrite.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-010.md`
- `codex/context/EPIC-010.md`
- `docs/architecture/scope_model.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/main.py`

## Context packs / patterns to consult
- `codex/context/EPIC-010.md`
- `docs/patterns/cards/PATTERN-008.md`

## Source files to change
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/main.py`
- `tests/runtime/api/test_request_context_profiles.py`
- `README.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-010.md`
- `codex/context/EPIC-010.md`
- `codex/tasks/TASK-0078-api-boundary-profiles-and-principal-resolver-seam.md`

## Generated / downstream artifacts impacted
- API request-context contract coverage.
- No generated runtime artifacts expected.

## Plan
1. Define the minimal profile model and trust assumptions for each environment.
2. Add a small `PrincipalResolver` seam so shared environments can fail closed without new auth provider work.
3. Add focused runtime tests for profile-specific request-context behavior.
4. Update docs so local-dev affordances stay explicit and bounded.

## Verification
- `PYTHONPATH=src pytest tests/runtime/api/test_request_context_profiles.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_cross_scope_api_denial.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Trusted headers are allowed only in `local_dev` and `ci_test`.
- `shared_env` fails closed when no non-header principal adapter is configured.
- Profile behavior is explicit in docs and tests.
- Capability enforcement remains unchanged in this task.

## Notes / decisions
- This task establishes the trust boundary that later write-path hardening will rely on.
- `shared_env` is now the default API boundary profile and fails closed with `principal_resolver_unavailable` unless a non-header principal resolver is injected.
- Trusted `x-onetruth-*` headers are now explicit `local_dev` / `ci_test` affordances instead of the ambient HTTP default.
- Trusted-header CORS is now loopback-only and local-dev-only; the runtime API test harness opts into `ci_test` explicitly so existing API semantics remain stable under the secure default.
