---
id: TASK-0101
epic: EPIC-010
title: "Conditional shared_env principal resolver and attested identity integration"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0078"]
risk: high
context_packs: ["codex/context/EPIC-010.md"]
patterns: ["PATTERN-008"]
---

## Context
The repo already had the right fail-closed `shared_env` seam from `TASK-0078`, but it still required callers to inject a resolver manually to make shared-env requests succeed.

This task closes that gap with one concrete attested-identity adapter for `shared_env`, while keeping trusted `x-onetruth-*` headers confined to `local_dev` and `ci_test`.

## Objective
Implement a conditional `shared_env` principal resolver that derives `RequestContext` from an attested `Authorization: Bearer <JWT>` identity instead of trusted headers.

## Non-goals
- No identity-platform expansion beyond one bounded JWT adapter.
- No JWKS fetcher, token introspection, cookie/session login, or broader authz redesign.
- No change to `local_dev` / `ci_test` trust semantics or trusted-header CORS posture.

## Source Files Changed
- `pyproject.toml`
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/main.py`
- `src/onetruth/api/shared_env_principal_resolver.py`
- `tests/runtime/api/test_request_context_profiles.py`
- `tests/security/isolation/test_shared_env_attested_identity.py`
- `codex/tasks/TASK-0101-conditional-shared-env-principal-resolver-and-attested-identity-integration.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-010.md`
- `codex/context/EPIC-010.md`

## Generated / downstream artifacts impacted
- None. This is an API trust-boundary integration only.

## Plan
1. Freeze the shared-env JWT boundary contract in focused runtime/security tests.
2. Add one concrete JWT-based `shared_env` resolver using offline `RS256` verification and fixed claim mapping.
3. Keep the existing precedence intact: explicit injected resolver first, trusted headers only for `local_dev` / `ci_test`, JWT resolver only for configured `shared_env`, and fail-closed otherwise.
4. Update task/status/epic memory so the shared-env attested-identity posture is explicit.

## Verification Run
- `PYTHONPATH=src pytest -q tests/runtime/api/test_request_context_profiles.py tests/runtime/api/test_api_cors_preflight.py tests/security/isolation/test_shared_env_attested_identity.py`
- `python3 scripts/validate_repo.py --schemas-only`
- `git diff --check`

## Acceptance Criteria Coverage
- `shared_env` still fails closed by default.
- Configured `shared_env` can resolve an attested principal from a bearer JWT without trusting `x-onetruth-*` headers.
- `local_dev` / `ci_test` behavior remains unchanged and separated from shared-env identity.

## Completion Notes (2026-03-14)
- Added `src/onetruth/api/shared_env_principal_resolver.py`, which resolves `RequestContext` from offline-validated `RS256` bearer JWTs when `ONETRUTH_SHARED_ENV_JWT_ISSUER`, `ONETRUTH_SHARED_ENV_JWT_AUDIENCE`, and `ONETRUTH_SHARED_ENV_JWT_PUBLIC_KEY_PEM` are all configured.
- Kept explicit `principal_resolver=` injection as the highest-precedence override and preserved the existing `503 principal_resolver_unavailable` fail-closed behavior when shared-env JWT config is absent.
- Shared request-context validation now reuses common actor-type / actor-role normalization, while conflicting trusted headers are ignored in `shared_env` and remain local/CI-only affordances.
