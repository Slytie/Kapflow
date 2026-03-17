# Centrality + Operability Next Tranche Prompt Pack

This tranche is for the repo **after** TASK-0101.

## Package intent
The previous tranche resolved most trust-boundary contradictions. The next tranche should **not** reopen those semantics. Its purpose is to:
- reduce centrality around `workflow_task_lifecycle.py`
- keep the new control-plane code from becoming the next hidden framework
- improve package-boundary honesty and API observability
- keep the assurance layer from becoming the next monolith

## Recommended order
1. TASK-0102
2. TASK-0103
3. TASK-0104
4. TASK-0105
5. TASK-0106
6. TASK-0107
7. TASK-0108
8. TASK-0109

## Parallelization guidance
- Do **not** parallelize `TASK-0102` with the handler extraction tasks.
- `TASK-0103`, `TASK-0104`, and `TASK-0105` all touch the legacy hotspot; keep them serial.
- `TASK-0106` can usually run in parallel with extraction work after `TASK-0102`, but prefer serial execution unless the team is explicitly using isolated worktrees.
- `TASK-0109` can run independently late in the tranche because it mostly touches scripts/CI/docs.

## Global rules
- Ask mode first.
- Keep tasks issue-like and bounded.
- Do not reopen the capability lattice or trust-profile semantics unless a task explicitly says so.
- Preserve the logistics weekly/live primary surface.
- Treat release-bundle truth, not raw workspace truth, as the operator-facing target.
