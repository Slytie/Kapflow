# Supervisor prompt for the truth-alignment tranche

Use this in **Ask mode only**.

You are a Codex coding agent working in this repo.

Your job is to triage the truth-alignment tranche and recommend the next safe task to run.
Do not edit files in this prompt. Do not implement code here.

## Step 0 — Load context
Read, in order:
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/EPICS.md`
- `codex/prompts/truth_alignment/README.md`
- `codex/tasks/TASK-0076-board-stability-and-query-surface-classification.md`
- `codex/tasks/TASK-0077-freeze-capability-lattice-and-policy-semantics.md`
- `codex/tasks/TASK-0078-api-boundary-profiles-and-principal-resolver-seam.md`
- `codex/tasks/TASK-0079-capability-decision-primitives-for-read-side-actionability.md`
- `codex/tasks/TASK-0080-write-boundary-capability-enforcement.md`
- `codex/tasks/TASK-0081-public-artifact-upload-vs-local-seeding-split.md`
- `codex/tasks/TASK-0082-scoped-command-idempotency-receipts.md`
- `codex/tasks/TASK-0083-shared-read-model-seam-and-route-boundary-fitness.md`
- `codex/tasks/TASK-0084-explicit-bundle-kinds-and-export-payload-validation.md`
- `codex/tasks/TASK-0085-bootstrap-truth-and-governance-cleanup.md`
- `codex/tasks/TASK-0086-first-controlled-hotspot-extraction.md`

## What to do
1. Determine which task is the next correct move, respecting dependencies and the repo’s current state.
2. Identify any blockers or semantic ambiguities that should prevent coding.
3. Suggest safe parallel lanes, if any.
4. Point to the exact prompt file that should be used next.

## Output format
Return:
1. **Current tranche status** — completed / blocked / ready tasks.
2. **Recommended next task** — one task only, with a short why-now justification.
3. **Blockers / prerequisites** — anything that must be resolved first.
4. **Parallelizable follow-ons** — only if truly safe.
5. **Prompt to use next** — exact file path.
6. **Red-team warning** — the main way the next task could go wrong.

## Non-goals
- No code changes.
- No task re-scoping unless the current task graph is clearly inconsistent.
- No hotspot decomposition planning until invariants are green.
