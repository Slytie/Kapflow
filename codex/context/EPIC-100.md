# EPIC-100 Context Pack — Production perimeter + substrate + release-mediated promotion

**Purpose (why you might open this):**
- You are changing shared-env identity/bootstrap, startup posture, deploy/runbook docs, or operator-facing release discipline.
- You are defining what production and lab actually are for the first stable user.
- You are adding observability or GitHub/CI perimeter controls that directly affect production confidence.

## Non-negotiable invariants to keep in mind
- Production truth remains the canonical runtime/event/artifact/pointer substrate plus reviewed release bundles.
- Shared-env identity should be server-derived; browser identity is local-dev/demo only.
- Prod and lab must not share live DBs, artifact roots, or secrets.
- Promotion should default to reviewed release promotion, not direct lab-to-prod runtime mutation.
- Keep the current logistics weekly/live primary surface stable while hardening the perimeter.

## Contracts / docs to treat as authoritative
- `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
- `docs/workflow_lab/PROMOTION_GATE.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-100.md`
- `docs/ops/README.md`
- `docs/ops/runbooks/rollback_and_deploy.md`
- `src/onetruth/api/dependencies.py`
- `src/onetruth/api/main.py`
- `src/onetruth/api/shared_env_principal_resolver.py`
- `frontend/src/app/AppShell.tsx`
- `frontend/src/lib/api/httpClient.ts`
- `scripts/export_clean_source_bundle.py`
- `scripts/repo_assurance/release.py`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-008.md`
- `docs/patterns/cards/PATTERN-009.md`

## Required test coverage (tests-as-spec)
- shared-env attested identity and trusted-header isolation tests
- startup/CLI tests for local-dev loopback guard behavior
- release/export/runbook validation checks
- frontend tests proving viewer/bootstrap-derived identity in shared environments
- observability and perimeter regression tests where applicable

## Current Repo Status (2026-03-18 implementation pass)
- Backend `shared_env` is credible, the frontend now bootstraps viewer identity from server-derived `GET /api/v1/viewer`, and the supported `onetruth-api` `local_dev` startup path now enforces loopback-only binds by default with one explicit unsafe override for controlled test scenarios.
- Production and lab topology are now explicit: separate single-node environments over the current `SQLite + local filesystem artifacts` substrate, deployed from `release_source_bundle`.
- Backup/restore/rollback docs and rehearsal basis now exist for the first-user substrate, but G1 still requires actual recorded rehearsal evidence.
- Structured boundary logs plus internal JSON health/readiness/metrics now exist for the first-user lane, and the GitHub perimeter now also has full-SHA action pinning, dependency review, CodeQL, and a mock-vs-live OpenAI workflow split.
- The explicit Workflow Lab promotion gate and current G1/G2 status ledger now live in `docs/workflow_lab/PROMOTION_GATE.md`.
- Hosted GitHub settings verification remains operator-owned, and Workflow Lab execution/comparison work remains blocked until gate evidence is explicitly recorded.

## Planned task order inside this epic
1. `TASK-0110`
2. `TASK-0111`
3. `TASK-0112`
4. `TASK-0113`
5. `TASK-0114`
6. `TASK-0115`
7. `TASK-0116`

## Red-team questions for future runs
- Are we letting the browser keep production identity authority by convenience?
- Are we treating “same deployment, different tenant/domain” as if it were enough separation for prod vs lab?
- Are we trying to build cloud-native infrastructure before a single-node production story is explicit and restorable?
- Are we improving operator rigor while still normalizing raw workspace sharing?
