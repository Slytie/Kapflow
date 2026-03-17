---
id: TASK-0107
epic: EPIC-080
title: "Modularize the route registry and add control-plane framework fitness checks"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0095"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
`route_registry.py` was a good first move: it centralized route truth and removed duplicated match/dispatch logic. But it is now a 700+ line control-plane table in its own right. Complexity did not disappear; it moved into a more legitimate home.

This task keeps that home from becoming an unmanaged internal framework.

## Objective
Split the route registry into resource-scoped route-spec modules with one small assembly point, and add architecture tests that keep the control-plane framework narrow.

## Non-goals
- No framework migration.
- No route naming or payload-shape changes.
- No new transport semantics.

## Source files to read first
- `src/onetruth/api/route_registry.py`
- `src/onetruth/api/main.py`
- `tests/unit/test_api_route_registry.py`
- representative route modules under `src/onetruth/api/routes/`

## Context packs / patterns to consult
- `codex/context/EPIC-080.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-009.md`

## Source files to change
- `src/onetruth/api/route_registry.py`
- new resource-scoped route-spec modules under `src/onetruth/api/`
- `tests/unit/test_api_route_registry.py`
- new architecture/fitness tests for control-plane boundaries if needed
- task/epic/context docs

## Generated / downstream artifacts impacted
- Task-memory and epic/context updates only.

## Plan
1. Identify the minimal resource group split that reduces registry sprawl without hiding route order truth.
2. Keep one assembled `ROUTES`/`match_route` truth surface.
3. Add tests that forbid route-spec modules from importing each other or `api.main`.
4. Preserve route names, precedence, and permissive-vs-strict path behavior.

## Verification
- `PYTHONPATH=src pytest -q tests/unit/test_api_route_registry.py`
- targeted runtime API smoke tests for representative routes
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Route metadata is no longer concentrated in one oversized file.
- The control-plane registry remains declarative and framework-light.
- Architecture tests make framework sprawl harder to reintroduce.

## Notes / decisions
This task should make the internal boundary framework smaller in cognition cost, not more abstract.

## Implementation notes (2026-03-17)
- `src/onetruth/api/route_registry.py` is now a slim assembly surface that re-exports the route metadata/types from `src/onetruth/api/route_specs/_core.py`, assembles `ROUTES` in the preserved global order, and keeps `match_route()` as the one public matcher.
- Route metadata now lives in resource-scoped modules under `src/onetruth/api/route_specs/`, so the control-plane table no longer concentrates in one oversized file while route handlers, payloads, and trust behavior stay unchanged.
- `tests/unit/test_api_route_registry.py` now freezes the exact assembled route-name order, and `tests/contract/test_route_registry_framework_fitness.py` forbids `route_registry.py`, `main.py`, route modules, and route-spec modules from drifting into a wider internal framework.
