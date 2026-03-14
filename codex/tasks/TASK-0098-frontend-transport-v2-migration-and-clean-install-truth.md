---
id: TASK-0098
epic: EPIC-080
title: "Migrate frontend/client surfaces to transport v2 and clean-install truth"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0097", "TASK-0090"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-009"]
---

## Context
The backend now exposes sibling binary download routes for artifacts and templates, but the frontend still decodes base64 from the legacy JSON `/download` paths. At the same time, the frontend quickstart was still describing `npm install` even though clean `npm ci` from `package-lock.json` is the truthful supported baseline.

This task completes the user-facing half of transport v2 without broadening into a general frontend refactor.

## Objective
Move frontend/client download surfaces to the binary `.bin` transport and make clean `npm ci` the only documented/supported frontend install assumption.

## Non-goals
- No new UI product surface.
- No broad frontend hotspot decomposition.
- No backend transport redesign or removal of compatibility `/download` endpoints.

## Source Files Changed
- `frontend/src/lib/api/httpClient.ts`
- `frontend/src/lib/api/httpClient.test.ts`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/artifactAttachments.ts`
- `frontend/src/lib/repositories/templatesRepository.ts`
- `frontend/src/lib/repositories/humanTasksRepository.ts`
- `frontend/src/components/DetailDrawer.tsx`
- `frontend/src/components/detailDrawer.test.tsx`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- `frontend/src/pages/logisticsDemoPage.test.tsx`
- `frontend/src/pages/runWorkspacePage.test.tsx`
- `frontend/src/test/api/handlers.ts`
- `frontend/src/test/setup.ts`
- `frontend/package.json`
- `README.md`
- `codex/tasks/TASK-0098-frontend-transport-v2-migration-and-clean-install-truth.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`

## Generated / downstream artifacts impacted
- Frontend/client download behavior only.

## Plan
1. Freeze a small binary client seam with focused frontend tests before rewiring existing pages.
2. Switch frontend download APIs and repositories to `.bin` without changing upload/base64 ingress behavior.
3. Update the MSW test layer so existing drawer/workspace/logistics flows prove the new route usage.
4. Close the clean-install truth gap in `frontend/package.json`, `README.md`, and repo memory.

## Verification Run
- `cd frontend && npm ci`
- `cd frontend && npm run test:run -- src/lib/api/httpClient.test.ts src/components/detailDrawer.test.tsx src/pages/runWorkspacePage.test.tsx src/pages/logisticsDemoPage.test.tsx`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `git diff --check`

## Acceptance Criteria Coverage
- Primary frontend/client download flows now use `.bin` routes instead of JSON/base64 download envelopes.
- Frontend code no longer depends on `content_base64` for downloads; base64 remains only for upload payloads.
- Clean `npm ci` from the lockfile is the documented/supported frontend baseline.
- No new UI surface or backend transport change was introduced.

## Completion Notes (2026-03-14)
- Added a narrow binary client seam in `frontend/src/lib/api/httpClient.ts` with header parsing for filename, media type, content length, and request id plus JSON-error fallback for binary routes.
- Switched frontend artifact/template download calls to `/download.bin` and replaced base64-to-blob download logic with a binary/blob helper while leaving artifact upload/base64 ingress unchanged.
- Updated the MSW frontend test layer and focused drawer/workspace/logistics tests to assert `.bin` route usage through distinct audit markers.
- Added explicit frontend package-manager truth (`npm@10.8.2`) and updated the README so clean `npm ci` is the supported frontend install path.
- Kept scope intentionally narrow: no fallback to legacy JSON downloads in the frontend, no backend transport changes, and no broader UI decomposition.
