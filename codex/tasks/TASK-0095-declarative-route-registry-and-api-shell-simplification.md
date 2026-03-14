---
id: TASK-0095
epic: EPIC-080
title: "Replace the handwritten route switch with a declarative route registry"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0094"]
risk: high
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-008"]
---

## Context
`src/onetruth/api/main.py` still duplicates route truth across a long handwritten matcher and a matching dispatcher. `TASK-0094` froze the shell behavior and added a header-only request-correlation seam, so the remaining bounded hotspot is the duplicated route table itself.

This task exists to centralize route metadata without changing route behavior, trust semantics, request/response payloads, or adopting a heavier framework.

## Objective
Introduce a single declarative route registry that becomes the source of truth for route metadata, matching order, and dispatch inside the existing lightweight ASGI shell.

## Non-goals
- No framework migration.
- No route payload redesign.
- No trust/profile changes.
- No request-id propagation into bodies or timeline-event correlation.

## Source Files Changed
- `src/onetruth/api/main.py`
- `src/onetruth/api/route_registry.py`
- `tests/unit/test_api_route_registry.py`
- `codex/tasks/TASK-0095-declarative-route-registry-and-api-shell-simplification.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`

## Generated / downstream artifacts impacted
- None beyond task-memory/status docs.

## Plan
1. Add a focused route-registry characterization test that freezes route metadata, precedence, and current permissive-vs-strict parameter matching behavior.
2. Introduce a small declarative route registry with ordered route specs, lightweight pattern matching, and route-owned dispatch callables.
3. Simplify `api/main.py` so the shell delegates route matching and dispatch to the registry while keeping request correlation, CORS, principal resolution, and error mapping unchanged.
4. Update repo memory after the registry refactor is verified.

## Verification Run
- `PYTHONPATH=src pytest -q tests/unit/test_api_route_registry.py`
- `PYTHONPATH=src pytest -q tests/unit/test_api_route_registry.py tests/runtime/api/test_api_shell_contract.py tests/runtime/api/test_human_task_claim_via_api.py tests/runtime/api/test_api_retry_stability.py tests/runtime/api/test_workflow_run_detail_contract.py tests/runtime/api/test_template_registry_api.py tests/runtime/api/test_logistics_three_workflow_story_endpoint.py`
- `python3 scripts/validate_repo.py --schemas-only`
- `PYTHONPYCACHEPREFIX=/tmp/pythoncache python3 -m compileall -q src tests scripts`

## Acceptance Criteria
- Route metadata is defined once in a declarative ordered registry.
- `api/main.py` no longer carries parallel handwritten match and dispatch switches.
- Representative read/write/download/story routes remain behavior-identical.
- Current route precedence and current permissive slash behavior for selected suffix routes are preserved.

## Notes / decisions
- Preserve the current route semantics exactly, including the existing ordering that lets suffix routes like `/download`, `/timeline`, and `/claim` win before detail routes.
- Keep the registry lightweight and framework-free: dataclasses plus explicit pattern/dispatch helpers only.

## Completion Notes (2026-03-14)
- Added `src/onetruth/api/route_registry.py` as the single ordered source of truth for route names, match patterns, body expectations, page requirements, and dispatch callables.
- Simplified `src/onetruth/api/main.py` so the shell now delegates route matching and dispatch to the registry while leaving request-id handling, principal resolution, CORS, and error mapping unchanged.
- Added `tests/unit/test_api_route_registry.py` to freeze route-name uniqueness, representative metadata, route precedence, and the current permissive-vs-strict slash behavior that the handwritten matcher already exposed.
- Kept scope intentionally narrow: no endpoint-module rewrites, no framework migration, no JSON payload changes, and no trust-boundary changes.
