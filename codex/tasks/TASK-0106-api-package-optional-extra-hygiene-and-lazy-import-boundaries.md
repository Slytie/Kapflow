---
id: TASK-0106
epic: EPIC-080
title: "Restore optional-extra honesty for onetruth.api with lazy import boundaries"
status: TODO
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0095", "TASK-0101"]
risk: medium
context_packs: ["codex/context/EPIC-080.md", "codex/context/EPIC-010.md"]
patterns: ["PATTERN-007", "PATTERN-008"]
---

## Context
The repo metadata says the API stack depends on the optional `api` extra, but the package layout is still too eager:
- `onetruth.api.__init__` imports `main`
- `main` imports the shared-env JWT resolver
- the JWT resolver imports `jwt`

So modules that should be importable without the `api` extra are effectively coupled to it. That is a packaging-boundary leak, not a runtime bug, but it matters for test isolation, tooling, and long-term modularity.

## Objective
Make `onetruth.api` import surfaces honest:
- modules that do not need optional API dependencies should import cleanly without them
- entrypoints that do need optional deps should fail clearly and locally
- package `__init__` files should not force eager import of heavy optional modules

## Non-goals
- No auth/profile semantic changes.
- No new principal resolver types.
- No FastAPI/Starlette/framework migration.

## Source files to read first
- `src/onetruth/api/__init__.py`
- `src/onetruth/api/main.py`
- `src/onetruth/api/shared_env_principal_resolver.py`
- `pyproject.toml`
- `tests/security/isolation/test_shared_env_attested_identity.py`
- `tests/unit/test_api_route_registry.py`

## Context packs / patterns to consult
- `codex/context/EPIC-080.md`
- `codex/context/EPIC-010.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-008.md`

## Source files to change
- `src/onetruth/api/__init__.py`
- `src/onetruth/api/main.py`
- any new lightweight import-guard helper modules if justified
- targeted packaging/import tests
- task/epic/context docs

## Generated / downstream artifacts impacted
- Task-memory and epic/context updates only.

## Plan
1. Remove eager `api.__init__` imports that drag in optional runtime dependencies.
2. Localize optional dependency imports to the smallest entrypoint/helper surface that actually requires them.
3. Add tests proving package submodules that should be lightweight can import without `jwt`/`uvicorn`.
4. Keep entrypoint error messages explicit and developer-friendly.

## Verification
- targeted pytest for import/package-boundary behavior
- `python3 scripts/doctor.py --check` (where environment permits)
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Optional API dependencies are no longer effectively mandatory for importing lightweight API modules.
- Entry points still fail clearly when an actually required optional dependency is missing.
- Packaging truth and runtime truth align more closely.

## Notes / decisions
Treat this as packaging discipline, not as a semantic runtime change.
