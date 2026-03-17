---
id: TASK-0111
epic: EPIC-100
title: "Add a server-derived viewer/bootstrap/session contract and migrate frontend shared-env identity"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0110"]
risk: high
context_packs: ["codex/context/EPIC-100.md"]
patterns: ["PATTERN-008", "PATTERN-009"]
---

## Context
The backend now has a credible `shared_env` principal resolver, but the frontend still behaves like a production identity surface: browser configuration drives `x-onetruth-*` headers and the AppShell still exposes an active-user switcher. That is acceptable for local-dev/demo, but not as the stable first-user production posture.

## Objective
Introduce a backend-derived viewer/bootstrap/session contract and migrate the frontend so `shared_env` identity and actor context come from the server, while local actor switching remains strictly local-dev/demo only.

## Non-goals
- No redesign of capability semantics or JWT claim mapping.
- No public Workflow Lab UI or session model.
- No attempt to support every future auth provider in this task.

## Source files to read first
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/main.py`
- `frontend/src/app/AppShell.tsx`
- `frontend/src/lib/api/httpClient.ts`
- security tests for shared-env identity

## Context packs / patterns to consult
- codex/context/EPIC-100.md
- PATTERN-008
- PATTERN-009

## Source files to change
- API route(s) for viewer/bootstrap/session
- frontend bootstrap/session state handling
- docs/ops and README identity guidance
- targeted runtime/security/frontend tests

## Generated / downstream artifacts impacted
- Shared-env bootstrap/session docs and frontend wiring
- task-memory / epic/context updates

## Plan
1. Define the narrowest server-derived bootstrap/session contract needed by the current UI.
2. Gate browser-set actor switching to local-dev/demo only.
3. Remove production/shared-env dependence on browser-set `x-onetruth-*` headers.
4. Freeze the new contract with backend + frontend + security tests.

## Verification
- targeted runtime/security tests for shared-env identity
- targeted frontend tests for bootstrap/session behavior
- `python3 scripts/validate_repo.py --schemas-only`
- clean frontend verification if package changes are involved

## Acceptance criteria
- In `shared_env`, the frontend derives viewer/bootstrap state from the backend rather than browser header configuration.
- Active-user switching is explicitly non-production.
- Production/shared-env identity is no longer ambiguous to a fresh operator or Codex session.

## Notes / decisions
This is the highest-leverage productization task because it closes the last major mismatch between backend trust posture and frontend behavior.

## Implementation notes
- Added read-only `GET /api/v1/viewer` as the server-derived viewer/bootstrap contract over the already-resolved request context and boundary profile.
- Frontend bootstrap now resolves `viewer_session` first, keeps trusted-header actor switching local-dev/ci-only, and omits browser-set `x-onetruth-*` identity headers after shared-env bootstrap.
- README and ops guidance now treat browser-set actor env vars as local-dev/demo only, not as shared-env production identity.

## Completion notes
- `frontend/src/lib/api/config.ts` now separates local debug headers from the active viewer session.
- `frontend/src/app/AppShell.tsx` blocks shell rendering on viewer bootstrap and hides the actor switcher in shared environments.
- Existing shared-env backend trust semantics, Stage04/Stage06 runtime behavior, and release-mediated promotion rules were left unchanged.
