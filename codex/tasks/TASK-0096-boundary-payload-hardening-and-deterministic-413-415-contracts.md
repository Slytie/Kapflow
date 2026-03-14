---
id: TASK-0096
epic: EPIC-080
title: "Harden boundary payload parsing with deterministic 400/413/415 contracts"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0095"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-008"]
---

## Context
The API shell was already simplified behind a declarative route registry, but JSON body handling still relied on fully buffered reads with no explicit content-type or size policy. That left `400 invalid_json` doing too much work and gave the boundary no deterministic `413` or `415` contract.

This task hardens the API boundary only. It does not redesign artifact transport, add multipart/binary upload support, or change route business logic.

## Objective
Centralize content-type validation, JSON-body size limits, and deterministic `400`/`413`/`415` behavior in the API boundary layer.

## Non-goals
- No binary upload redesign.
- No route-registry redesign beyond consuming explicit body policies.
- No shared-env rate limiting or auth adapter work.
- No payload-schema, trust-profile, or artifact-semantic changes.

## Source Files Changed
- `src/onetruth/api/main.py`
- `src/onetruth/api/route_registry.py`
- `tests/runtime/api/test_api_shell_contract.py`
- `tests/runtime/api/test_artifact_upload_profiles.py`
- `tests/unit/test_api_route_registry.py`
- `README.md`
- `codex/tasks/TASK-0096-boundary-payload-hardening-and-deterministic-413-415-contracts.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`

## Generated / downstream artifacts impacted
- None beyond task-memory/status docs and deterministic API error responses.

## Plan
1. Freeze the boundary contract first in focused shell and artifact-ingress tests.
2. Replace loose `body_mode` metadata with explicit request body policies in the route registry.
3. Harden shell parsing so content type and byte ceilings are enforced before JSON decode while preserving the existing empty-body `400 invalid_payload` behavior.
4. Record the new bounded boundary contract in repo memory and API operator guidance.

## Verification Run
- `PYTHONPATH=src pytest -q tests/unit/test_api_route_registry.py`
- `PYTHONPATH=src pytest -q tests/runtime/api/test_api_shell_contract.py`
- `PYTHONPATH=src pytest -q tests/unit/test_api_route_registry.py tests/runtime/api/test_api_shell_contract.py tests/runtime/api/test_artifact_upload_profiles.py`
- `PYTHONPATH=src pytest -q tests/runtime/api/test_human_task_claim_via_api.py tests/runtime/api/test_stage06_openai_review_sandbox_api.py tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance Criteria Coverage
- Non-empty JSON POST requests with missing or wrong media type now fail with deterministic `415 unsupported_media_type`.
- Oversize JSON request bodies now fail with deterministic `413 payload_too_large` and route-aware `max_bytes` details.
- Empty-body and malformed/non-object JSON requests still return deterministic `400` contracts.
- Artifact-ingress routes keep a larger bounded JSON envelope than ordinary command routes without changing artifact semantics.

## Completion Notes (2026-03-14)
- Replaced the route registry's loose `body_mode` metadata with explicit `RequestBodyPolicy` values so command JSON routes use a `256 KiB` ceiling and artifact-ingress JSON routes use a bounded `2 MiB` ceiling.
- Hardened `src/onetruth/api/main.py` so body parsing now validates `Content-Type: application/json` on first non-empty bytes, accepts `application/json` parameters such as `charset=utf-8`, enforces byte ceilings while reading, and preserves the existing empty-body `invalid_payload` behavior.
- Added focused shell tests for deterministic `415`, `413`, charset-parameter acceptance, and unchanged empty-body `400` behavior, plus artifact-ingress tests that prove oversize requests fail without side effects and that artifact-ingress retains a broader bounded envelope than normal command routes.
- Kept scope intentionally bounded: no multipart/binary transport redesign, no endpoint-module rewrites, no trust-profile changes, and no change to artifact ingestion semantics beyond shell-level rejection of wrong-media-type or oversize JSON envelopes.
