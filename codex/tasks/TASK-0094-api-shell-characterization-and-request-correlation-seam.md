---
id: TASK-0094
epic: EPIC-080
title: "Characterize the API shell and add a request-correlation seam"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0078", "TASK-0083"]
risk: medium
context_packs: ["codex/context/EPIC-080.md", "codex/context/EPIC-010.md"]
patterns: ["PATTERN-008"]
---

## Context
`api/main.py` still hand-rolls matching, dispatch, body parsing, and response emission. Before changing that structure, the repo needed two things: characterization of the current shell behavior, and a tiny request-correlation seam that can survive a later route-registry refactor.

This task intentionally stayed at the HTTP boundary. It does not propagate request IDs into timeline-event `correlation_id`, and it does not change JSON response bodies.

## Objective
Freeze the current API shell behavior with focused tests and add a header-only request-correlation seam (`x-request-id`) without redesigning the routing layer.

## Non-goals
- No declarative route registry yet.
- No body-size ceilings or binary transport yet.
- No event-correlation plumbing across API mutation routes.
- No full observability platform or external logging stack.

## Source Files Changed
- `src/onetruth/api/main.py`
- `src/onetruth/api/request_correlation.py`
- `src/onetruth/api/dependencies.py`
- `tests/runtime/api/test_api_shell_contract.py`
- `tests/runtime/api/test_request_context_profiles.py`
- `tests/runtime/api/test_api_cors_preflight.py`
- `codex/tasks/TASK-0094-api-shell-characterization-and-request-correlation-seam.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`

## Generated / downstream artifacts impacted
- None beyond API response headers and task-memory/status docs.

## Plan
1. Add focused shell-characterization tests for route misses, JSON parsing failures, unsupported scopes, and unhandled-exception fallback.
2. Introduce a tiny `x-request-id` helper seam for normalization/generation and response-header emission.
3. Thread the request id through the hand-rolled API shell and keep trust-profile behavior unchanged.
4. Update repo memory after the shell contract and header-only seam are verified.

## Verification Run
- `PYTHONPATH=src pytest -q tests/runtime/api/test_api_shell_contract.py tests/runtime/api/test_request_context_profiles.py tests/runtime/api/test_api_cors_preflight.py`
- `PYTHONPATH=src pytest -q tests/runtime/api/test_scoped_idempotency.py`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance Criteria Coverage
- The current API shell behavior is frozen by focused tests before any route-registry refactor.
- Every API response now emits `x-request-id`.
- Local-dev CORS exposes `x-request-id` without changing the frozen `shared_env` trust posture.
- No request ids were added to public JSON payloads or mutation timeline events.

## Completion Notes (2026-03-14)
- Added `tests/runtime/api/test_api_shell_contract.py` to freeze core shell behavior for route misses, malformed JSON, non-object payloads, unsupported scopes, and internal-error fallback.
- Added `src/onetruth/api/request_correlation.py` as a minimal request-id seam that accepts a safe incoming `x-request-id` or generates `httpreq_<32 hex>` when absent or unusable.
- Threaded that seam through `src/onetruth/api/main.py` so JSON and no-content responses always emit `x-request-id`, while local-dev CORS now exposes the header for loopback browser use.
- Extended `RequestContext` with optional request-id metadata only; trust/profile semantics and public API bodies remain unchanged.
- Kept scope intentionally bounded: no route-registry redesign and no propagation of HTTP request ids into timeline-event `correlation_id`.
