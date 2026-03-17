# TASK-0108

## Ask mode

```text
You are working on `TASK-0108`.

### Step 0 — Load context in this order
- AGENTS.md
- LLM_RUNBOOK.md
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0108-structured-api-boundary-logging-and-mutation-audit-correlation.md
- src/onetruth/api/main.py
- src/onetruth/api/request_correlation.py
- src/onetruth/api/route_registry.py
- src/onetruth/application/handlers/_shared/command_boundary.py

### Ask-mode objective
Add structured boundary logs and mutation audit correlation without changing runtime semantics or leaking secrets.

### What to figure out before coding
- Confirm this still fits one bounded Codex task.
- Identify the minimum failing or missing checks that should move first.
- Surface any repo-specific centrality leaks, boundary leaks, or compatibility shims this task must respect.
- Plan the smallest file set that meaningfully retires the targeted risk.

### Red-team checks
- Do not reopen the capability lattice or trust-profile semantics unless the task explicitly requires it.
- Do not let this task quietly expand into PostgreSQL/object-store/platform work.
- Do not preserve a centrality leak just by adding another re-export layer.
- Keep Stage04 weekly/live and Stage06 behavior stable unless the task explicitly says otherwise.
- Keep raw workspace vs release-bundle distinctions unchanged unless the task explicitly touches assurance/distribution.

### Output required from Ask mode
- Short diagnosis of the current state.
- Proposed change set in dependency order.
- Exact files to change and why.
- Tests/checks to add or update.
- Risks, stop conditions, and any follow-on tasks that should stay separate.
- A smallness check explaining why this still fits one bounded Codex task.
```

## Code mode

```text
You are resuming `TASK-0108` in **Code mode**.

### Step 0 — Reload the minimum context
- AGENTS.md
- LLM_RUNBOOK.md
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0108-structured-api-boundary-logging-and-mutation-audit-correlation.md
- src/onetruth/api/main.py
- src/onetruth/api/request_correlation.py
- src/onetruth/api/route_registry.py
- src/onetruth/application/handlers/_shared/command_boundary.py

### Implementation rules
- Keep the change set tight and aligned to the task objective.
- Update the matching task file, task index, current-focus notes, and touched epic/context files if the task changes repo memory.
- Prefer contract/tests/architecture-guardrails first when the task is about structure.
- If the task is larger than expected, stop and split the follow-on explicitly instead of silently broadening scope.

### Verification to run
- targeted runtime/unit tests for logging behavior
- python3 scripts/validate_repo.py --schemas-only

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any task-memory / status / epic-context updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
```
