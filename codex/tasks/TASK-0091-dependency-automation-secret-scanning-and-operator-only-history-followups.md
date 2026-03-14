---
id: TASK-0091
epic: EPIC-080
title: "Add dependency automation, secret scanning, and explicit operator-only history follow-ups"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0090"]
risk: medium
context_packs: ["codex/context/EPIC-080.md"]
patterns: []
---

## Context
The repo now has validator-based secret hygiene and a cleaner release path, but dependency updates and secret scanning were still partly manual. The earlier leaked key is now a process issue rather than a code issue: revocation and any history rewrite decision are operator/admin actions, not Codex implementation tasks.

## Objective
Add repo-native dependency/update automation and secret scanning workflows, and document the operator-only follow-up actions that do not belong in routine Codex coding tasks.

## Non-goals
- No speculative history rewrite inside this task.
- No SBOM/release-provenance work yet; that belongs to the later release tranche.
- No major CI topology refactor beyond wiring the new automation into current workflows.

## Source Files Changed
- `.github/dependabot.yml`
- `.github/workflows/secret_hygiene.yml`
- `scripts/validate_repo.py`
- `tests/contract/test_repo_automation_truth.py`
- `tests/contract/test_validation_harness.py`
- `README.md`
- `docs/planning/REPO_HYGIENE.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-080.md`
- `codex/context/EPIC-080.md`
- `codex/tasks/TASK-0091-dependency-automation-secret-scanning-and-operator-only-history-followups.md`

## Generated / downstream artifacts impacted
- CI/security automation metadata only.

## Plan
1. Add contract coverage for repo automation metadata and the narrow secret-only validator mode.
2. Add repo-native dependency automation and a dedicated secret-hygiene workflow.
3. Document operator-only follow-ups so revocation/history actions stay outside routine Codex code scope.
4. Update repo memory with the new automation posture.

## Verification Run
- `python3 scripts/validate_repo.py --secrets-only`
- `pytest tests/contract/test_repo_automation_truth.py tests/contract/test_validation_harness.py -q`
- `git diff --check`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance Criteria Coverage
- Dependency update automation exists for Python, frontend, and GitHub Actions package managers.
- Secret scanning is explicit and automated beyond the validator-only manual path.
- The old key/history issue is clearly documented as an operator/admin follow-up rather than a hidden repo TODO.

## Completion Notes (2026-03-14)
- Added repo-native automation metadata for dependency updates and a dedicated `secret_hygiene` workflow over `python scripts/validate_repo.py --secrets-only`.
- Explicitly documented that secret revocation confirmation, Git history rewrite decisions, and hosted GitHub security settings remain operator/admin follow-ups rather than Codex code tasks.
- Kept the change bounded to automation metadata, validator surface, and docs/memory updates without changing runtime or transport semantics.

