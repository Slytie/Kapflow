# Workflow-run-backed workpages prompt pack

This tranche is for the repo **after** the first artifact-backed EOD slice is complete through `TASK-0136`.

## Package intent
The previous tranche proved one artifact-backed write loop. The next tranche should **not** reopen that proof. Its purpose is to:
- promote workpages from demo-only entrypoints to canonical workflow-run-backed surfaces,
- keep schedule query-backed/composite,
- keep EOD artifact-backed editing intact while adding run-backed landing/latest-draft resolution,
- and avoid broadening prematurely into schedule writes or legacy workspace/task modernization.

## Recommended order
1. TASK-0137
2. TASK-0138
3. TASK-0139
4. TASK-0140
5. TASK-0141

## Parallelization guidance
- Do **not** start backend or frontend implementation before `TASK-0137` freezes the route family and alias posture.
- `TASK-0138` and `TASK-0139` can be parallel after `TASK-0137` if the team is using isolated worktrees and the contract is truly frozen.
- `TASK-0140` depends on both backend run-backed routes and their generated snapshots.
- `TASK-0141` should run last because it freezes user-visible route discovery and repo-memory truth.

## Global rules
- Ask mode first.
- Keep tasks issue-like and bounded.
- Do not start schedule write-path work in this tranche.
- Do not deepen EOD into final-packet/approval semantics in this tranche.
- Keep `/demo/logistics/workpages/*` as curated aliases until the canonical run-backed routes are proven.
- Treat backend-generated snapshots, not frontend-local constants, as the active contract truth once routes exist.
