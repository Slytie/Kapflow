# EPIC-080 Context Pack — Ops/UI readiness for canonical demo and HITL surfaces

**Purpose (why you might open this):**

- You are changing frontend operator/demo routing, HITL board/workspace/read-model UX, or CI/quality gates tied to those surfaces.
- You need to keep navigation/copy/docs truthful when the primary demo posture changes.
- You are tightening repo bootstrap/install truth or lightweight operational guardrails without reopening runtime semantics.
- You are adding repo automation metadata or clarifying which follow-up actions stay outside Codex code scope.

## Non-negotiable invariants to keep in mind
- UI is a derived surface over canonical backend/runtime state; no second client truth model.
- Primary demo changes must not delete legacy regression surfaces unless replacement coverage is stronger and explicit.
- Cross-workflow truth for logistics demo shells must come from backend-authored story/query seams.

## Contracts / docs to treat as authoritative
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/TEST_STRATEGY.md`
- `docs/planning/TEST_MATRIX.md`
- `pyproject.toml`
- `scripts/doctor.py`
- `scripts/validate_repo.py`
- `.github/dependabot.yml`
- `.github/workflows/secret_hygiene.yml`
- `docs/planning/THREE_WORKFLOW_DEMO_STORY.yaml`
- `src/onetruth/api/routes/logistics_story.py`
- `frontend/src/app/App.tsx`
- `frontend/src/lib/api/onetruthApi.ts`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-008.md`
- `docs/patterns/cards/PATTERN-009.md`

## Required test coverage (tests-as-spec)
- Route/integration tests proving the primary app entrypoint and nav labels.
- Component/integration tests proving story graph + unified board + linked runs render from canonical story payload.
- Regression tests proving schedule-only routes remain reachable as legacy/internal surfaces.
- Contract/validation tests proving the repo has one install path and excludes tracked build artifacts from source truth.
- Contract/validation tests proving repo automation metadata exists for dependency updates and secret-hygiene automation.

## Current Repo Status (2026-03-14)
- `TASK-0064` is complete:
  - primary frontend route: `/demo/logistics`,
  - canonical story source: `GET /api/v1/stories/logistics-three-workflow`,
  - schedule-only board/workspace/runs/timeline views remain legacy/internal regression surfaces.
- `TASK-0090` is complete:
  - validated Python baseline is explicit in package metadata (`>=3.11,<3.12`),
  - local and CI installs use the same editable extras path,
  - tracked `*.egg-info` build artifacts are excluded from source truth by validation.
- `TASK-0091` is complete:
  - Dependabot covers Python, frontend, and GitHub Actions metadata,
  - a dedicated `secret_hygiene` workflow runs `python scripts/validate_repo.py --secrets-only`,
  - revocation/history rewrite follow-ups are recorded as operator-only rather than code-task work.
- `TASK-0094` is complete:
  - the hand-rolled API shell is characterized by focused runtime tests before any refactor,
  - every API response now emits a header-only `x-request-id`,
  - request ids are not yet added to JSON bodies or timeline-event correlation.
- `TASK-0095` is complete:
  - the duplicated handwritten matcher/dispatcher in `src/onetruth/api/main.py` has been replaced by a single declarative route registry,
  - route precedence, current permissive slash behavior, and endpoint payload semantics were preserved,
  - the shell remains lightweight and framework-free while route metadata now lives in one place.
- `TASK-0096` is complete:
  - JSON POST routes now use explicit route-aware request body policies instead of a loose `body_mode`,
  - the API shell deterministically returns `415 unsupported_media_type` for non-empty wrong/missing JSON media type and `413 payload_too_large` for oversize envelopes,
  - artifact-ingress routes intentionally keep a larger bounded JSON envelope than ordinary command routes without changing artifact ingress semantics.
- `TASK-0098` is complete:
  - frontend/client download flows now call `/download.bin` directly and no longer depend on JSON/base64 download envelopes,
  - the frontend download seam now derives file names/media types from attachment headers through a narrow binary client helper,
  - clean `npm ci` from `frontend/package-lock.json` is the explicit frontend install truth.
- `TASK-0099` is complete:
  - the main CI workflow now exposes parallel fast required lanes for `lint`, `contract`, `unit`, and `security` plus a separate `runtime-required` lane and standalone `frontend` lane,
  - `release-confidence` is now post-merge/manual only instead of adding pull-request lane count,
  - `secret_hygiene` remains a separate PR-capable guardrail workflow and `agent_api` now reuses `ci-fast-backend` before gated OpenAI integration tests.
- `TASK-0100` is complete:
  - `release_source_bundle` is now the only documented/operator-default shareable source artifact,
  - release exports now include a deterministic repo-owned `release_provenance.json` sidecar in addition to `bundle_manifest.json`,
  - internal handoff bundles and runtime workspace bundles remain valid but are explicitly non-release distribution paths.
- Scope remains intentionally bounded to the authored three-workflow logistics story shell.
