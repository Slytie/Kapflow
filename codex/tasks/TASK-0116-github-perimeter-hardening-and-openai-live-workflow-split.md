---
id: TASK-0116
epic: EPIC-100
title: "Harden the GitHub perimeter and split scheduled mock vs manual live OpenAI workflows"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0099"]
risk: medium
context_packs: ["codex/context/EPIC-100.md"]
patterns: []
---

## Context
The repo’s CI topology is now much better, but the GitHub perimeter still lags the rest of the system: actions are not pinned to full SHAs, dependency-review/CodeQL are absent, and live OpenAI workflow posture is not yet separated as sharply as it could be.

## Objective
Tighten the GitHub/CI perimeter so the production lane has stronger provenance and safer automation defaults without making every confidence slice merge-blocking.

## Non-goals
- No merge-queue rollout by default.
- No new test matrix explosion.
- No change to current runtime semantics.

## Source files to read first
- `.github/workflows/*.yml`
- `README.md` / ops docs for CI posture
- current release-confidence and agent_api workflows

## Context packs / patterns to consult
- codex/context/EPIC-100.md

## Source files to change
- GitHub workflow files
- docs describing CI / live OpenAI posture
- task-memory / epic/context updates

## Generated / downstream artifacts impacted
- CI/workflow metadata only
- no product/runtime artifacts

## Plan
1. Pin actions to full SHAs or the repo’s chosen stronger standard.
2. Add dependency-review / CodeQL or equivalent perimeter checks.
3. Split scheduled mock coverage from manual/gated live OpenAI coverage.
4. Document the resulting operator/security posture.

## Verification
- workflow validation / dry review
- `python3 scripts/validate_repo.py --schemas-only`
- any repo-native CI metadata checks

## Acceptance criteria
- GitHub automation defaults are materially safer and more auditable.
- Live OpenAI coverage is clearly gated/manual while scheduled coverage remains mock-only.
- The repo’s strongest assurance story is no longer undermined by a weaker GitHub perimeter.

## Notes / decisions
Treat this as perimeter hardening, not as an excuse to redesign the whole CI system again.

## Implementation notes
- Repo-managed GitHub Actions workflows are now pinned to verified full commit SHAs.
- `agent_api.yml` is now the scheduled/manual mock lane over `ci-fast-backend`, while `agent_api_live.yml` is the manual gated real OpenAI lane.
- Added `dependency_review.yml` for pull requests and `codeql.yml` for push/pull_request/schedule perimeter scanning.
- Hosted GitHub settings verification remains a documented operator responsibility rather than a source-controlled automation layer.
