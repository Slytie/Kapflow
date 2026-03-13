---
id: TASK-0087
epic: EPIC-070
title: "Repo hygiene cleanup for local state, tracked runtime outputs, and workstation clutter"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0056", "TASK-0065", "TASK-0070"]
risk: medium
context_packs: ["codex/context/EPIC-070.md"]
patterns: ["PATTERN-003", "PATTERN-005", "PATTERN-009"]
---

## Objective
Remove tracked local/runtime byproducts from the repo boundary, tighten ignore coverage for the default runtime evidence root and local databases, and refresh repo memory so future Codex runs do not treat workstation clutter as source.

## Non-goals
- no weekly/live workflow semantic changes,
- no movement of authoritative generated contracts,
- no refactor of OpenAI runtime behavior beyond a tiny diff-hygiene formatting cleanup.

## Source Files Changed
- `.gitignore`
- `README.md`
- `docs/planning/REPO_HYGIENE.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `src/onetruth/integrations/openai/responses_agent_runner.py`
- `codex/tasks/TASK-0087-repo-hygiene-local-state-and-tracked-output-cleanup.md`
- tracked `.onetruth_artifacts/**` runtime evidence files removed from version control
- tracked `.DS_Store` files under `docs/`, `fixtures/`, and `src/` removed from version control
- tracked `onetruth.db` removed from version control
- tracked `codex_handoff_packet_schedule_planning.zip` removed from version control

## Verification Run
- `git ls-files .onetruth_artifacts onetruth.db '*.DS_Store' 'codex_handoff_packet_schedule_planning.zip'` - passed (no tracked matches)
- `git diff --check` - passed
- `python scripts/validate_repo.py` - could not run on this machine because `python` is not installed
- `python3 scripts/validate_repo.py` - passed (`1357 check(s) passed`)

## Acceptance Criteria Coverage
- The default runtime evidence root (`.onetruth_artifacts/`) and local SQLite outputs are now explicitly ignored.
- Previously tracked workstation/runtime clutter is removed from version control.
- Repo docs/status memory now record that live runtime evidence belongs outside the source tree boundary unless intentionally promoted into `fixtures/`.
- Cleanup leaves weekly/live business semantics untouched and keeps repo validation green.

## Completion Notes (2026-03-13)
- Audit confirmed the tracked `.onetruth_artifacts/` content was live execution evidence only; no fixture migration was required for this cleanup.
- The tracked handoff zip and `.DS_Store` files were treated as workstation/handoff clutter and removed from version control.
- `src/onetruth/integrations/openai/responses_agent_runner.py` received a formatting-only cleanup so the bounded hygiene diff stays `git diff --check` clean.
- Backlog sync note: this task was formerly duplicated as `TASK-0071` before the truth-alignment planning sync. The Stage04 weekly artifact task keeps canonical ownership of `TASK-0071`.
