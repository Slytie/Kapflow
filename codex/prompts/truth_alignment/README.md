# Truth-alignment Codex prompt pack

This prompt pack translates `TASK-0076` through `TASK-0086` into execution-ready Codex prompts.

## How to use this pack
1. Start with `PROMPT-0000-truth-alignment-supervisor.md` if you want Codex to triage the tranche and choose the next task.
2. For each task, use the **Ask mode** section first. Do not let Codex edit code until the plan is coherent and the task still fits one bounded tranche.
3. Once the Ask-mode plan is approved, use the **Code mode** section for the same task.
4. Update the matching `codex/tasks/TASK-....md` file with plan, commands run, outcomes, and follow-ups.
5. Keep the default context small: baseline repo files + the exact task file + the exact epic/context pack + the smallest relevant source files.

## Execution order
Recommended sequence:
- `TASK-0076`
- `TASK-0077`
- `TASK-0078`
- `TASK-0079`
- `TASK-0081`
- `TASK-0080`
- `TASK-0082` and `TASK-0083` can run in parallel once their prerequisites are done
- `TASK-0084` and `TASK-0085` can run in parallel once `TASK-0075` is in place
- `TASK-0086` only after the invariant tasks are complete and green

## Prompt design rules used here
- Every prompt is issue-shaped and repo-specific.
- Every prompt starts with the repo’s own context surfaces (`AGENTS.md`, `LLM_RUNBOOK.md`, `codex/CODEX_CONTEXT.yaml`, task brief, epic/context pack).
- Ask mode is used first for all non-trivial tasks.
- Each prompt carries task-specific red-team checks so Codex does not “solve” the wrong problem.
- Each prompt ends with explicit deliverables and verification commands.

## Files in this pack
- `PROMPT-0000-truth-alignment-supervisor.md`
- `PROMPT-TASK-0076-...md` through `PROMPT-TASK-0086-...md`

## Notes
- These prompts assume the task briefs from the truth-alignment planning bundle are present in `codex/tasks/`. If they are not yet in the checkout, apply the task-plan patch first.
- The prompts are intentionally stricter than the task briefs about Ask-vs-Code separation, because this tranche has several semantic pitfalls where premature code changes would harden the wrong behavior.
