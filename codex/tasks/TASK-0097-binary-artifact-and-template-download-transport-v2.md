---
id: TASK-0097
epic: EPIC-030
title: "Add binary artifact and template download transport v2"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0096", "TASK-0081", "TASK-0088"]
risk: medium
context_packs: ["codex/context/EPIC-030.md", "codex/context/EPIC-080.md"]
patterns: ["PATTERN-003"]
---

## Context
Shared/public artifact ingress is semantically correct, but the primary API download path still returns base64 inside JSON. That is acceptable for small compatibility payloads, but it is the wrong long-term transport for primary clients and makes download operability harder than necessary.

This task adds a better transport without changing canonical artifact or template truth semantics.

## Objective
Introduce sibling binary download routes for artifact and template content while keeping the current JSON+base64 download routes available as compatibility surfaces.

## Non-goals
- No artifact metadata, pointer, or provenance semantics changes.
- No upload transport redesign.
- No frontend migration in the same tranche.
- No streaming/range/object-store redesign.

## Source Files Changed
- `src/onetruth/api/main.py`
- `src/onetruth/api/route_registry.py`
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/templates.py`
- `src/onetruth/api/responses.py`
- `tests/runtime/helpers/runtime_api.py`
- `tests/runtime/api/test_binary_download_transport.py`
- `tests/runtime/api/test_cross_scope_api_denial.py`
- `tests/unit/test_api_route_registry.py`
- `README.md`
- `codex/tasks/TASK-0097-binary-artifact-and-template-download-transport-v2.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-030.md`
- `codex/context/EPIC-030.md`

## Generated / downstream artifacts impacted
- Artifact/template HTTP transport contracts only.

## Plan
1. Freeze the sibling binary route shape in route-registry and runtime tests first.
2. Add a tiny binary-response seam so the shell can emit bytes on success while keeping error envelopes JSON.
3. Add sibling `.bin` routes for artifacts and templates, leaving existing `/download` JSON routes untouched.
4. Update repo memory and API guidance after the transport contract is verified.

## Verification Run
- `PYTHONPATH=src pytest -q tests/unit/test_api_route_registry.py tests/runtime/api/test_binary_download_transport.py tests/runtime/api/test_artifact_attachment_api.py tests/runtime/api/test_template_registry_api.py tests/runtime/api/test_cross_scope_api_denial.py`
- `python3 scripts/validate_repo.py --schemas-only`
- `PYTHONPYCACHEPREFIX=/tmp/pythoncache python3 -m compileall -q src tests scripts`
- `git diff --check`

## Acceptance Criteria Coverage
- Binary download transport now exists at sibling routes:
  - `/api/v1/artifacts/{artifact_version_id}/download.bin`
  - `/api/v1/templates/{template_id}/download.bin`
- Existing `/download` JSON+base64 routes remain available and unchanged for compatibility.
- Binary success responses return bytes plus attachment headers, while failures remain the existing JSON error envelopes.
- Cross-scope denial behavior is unchanged.

## Completion Notes (2026-03-14)
- Added `src/onetruth/api/responses.py` with a minimal `BinaryResponse` seam plus small filename sanitization for attachment headers.
- Extended the API shell so routes may return bytes on success with `content-type`, `content-length`, `content-disposition`, and `x-request-id`, while `ApiError` and unexpected failures still return the existing JSON error envelopes.
- Added sibling `.bin` routes for artifact and template download without changing the existing JSON `/download` endpoints.
- Extended the runtime test harness with a raw-response helper and added focused runtime coverage for exact bytes, headers, unknown-template JSON errors, and cross-scope denial parity.
- Kept scope intentionally tight: no frontend migration, no binary upload work, and no artifact/pointer/provenance semantic changes.
