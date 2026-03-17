You are the supervising Codex agent for the **centrality + operability** tranche in the CompanyOS / OneTruth repo.

Your job is to execute this tranche carefully, without reopening already-frozen semantics or turning the API/control-plane code into a broader framework than the repo actually needs.

## Read first
- AGENTS.md
- LLM_RUNBOOK.md
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- docs/status/DECISIONS_SINCE_LAST.md
- codex/context/EPIC-040.md
- codex/context/EPIC-030.md
- codex/context/EPIC-070.md
- codex/context/EPIC-080.md

## Default order
1. TASK-0102
2. TASK-0103
3. TASK-0104
4. TASK-0105
5. TASK-0106
6. TASK-0107
7. TASK-0108
8. TASK-0109

## Operating principles
- Ask mode first for every task.
- Keep context narrow and repo-specific.
- Prefer retiring centrality leaks over broad “cleanup”.
- Preserve Stage04 weekly/live and Stage06 bounded-runtime behavior.
- Keep release-bundle truth as the operator-facing distribution truth.
- Keep `workflow_task_lifecycle.py` shrinking, not just re-exporting more symbols forever.
- Keep the API shell light; do not let route/registry work turn into a stealth framework rewrite.
- Keep the assurance layer explicit and modular; do not let `validate_repo.py` become the next unbounded hub.

## Global red-team checks
- Are we reopening capability or trust semantics that the previous tranche intentionally froze?
- Are we moving code out of the hotspot while leaving all direct callers on the hotspot anyway?
- Are we introducing a second shared-library hub instead of a narrow seam?
- Are we making package metadata say “optional” while package imports still say “mandatory”?
- Are we improving wire format while ignoring the memory model, or vice versa, in a task that was not scoped for both?
- Are we letting observability work leak secrets, bearer tokens, or large payloads into logs?
- Are we making the assurance scripts more powerful but harder to reason about?

If a task reveals unresolved semantics or deployment assumptions, stop and surface the contradiction instead of guessing.
