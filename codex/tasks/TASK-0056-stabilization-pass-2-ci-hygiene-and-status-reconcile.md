---
id: TASK-0056
epic: EPIC-080
title: "Stabilization pass 2: CI hygiene, reproducibility, and status reconciliation"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0055"]
risk: medium
context_packs: ["codex/context/EPIC-080.md", "codex/context/EPIC-060.md"]
patterns: []
---

## Objective
Stabilize repository hygiene and CI reproducibility by:
- enforcing backend + snapshot + frontend quality gates in Make/CI,
- removing tracked local-noise artifacts from Git index,
- reconciling stale task/status docs against actual in-repo deliverables (including TASK-0031).

## Scope
Hygiene + CI + staleness reconciliation only.

## Non-goals
- No new product/runtime/frontend features.
- No expansion of OpenAI real-network test scope in default PR CI.
- No task-status promotion without matching in-repo deliverables.

## Source Files To Change
- `.gitignore`
- `docs/planning/REPO_HYGIENE.md`
- `Makefile`
- `.github/workflows/main.yml`
- `.github/workflows/agent_api.yml`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0056-stabilization-pass-2-ci-hygiene-and-status-reconcile.md`

## Verification Commands
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `make frontend-snapshots-check`
- `cd frontend && npm run typecheck`
- `make ci`

## Acceptance Criteria
- `.gitignore` excludes local/runtime/build/editor noise and secret env files.
- any currently tracked ignored-noise paths are removed from the Git index.
- Makefile has explicit frontend/install/typecheck/test/build targets and a `ci` target for combined backend+snapshot+frontend gating.
- PR CI workflow includes backend snapshot check + frontend typecheck/tests, while OpenAI real-network tests remain gated/scheduled.
- TASK-0031 status remains aligned to concrete projection-coherence deliverables in-repo; status docs reflect actual repo artifacts.
