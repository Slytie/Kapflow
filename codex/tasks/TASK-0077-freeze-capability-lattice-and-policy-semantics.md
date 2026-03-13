---
id: TASK-0077
epic: EPIC-050
title: "Freeze the capability lattice and policy semantics"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security"]
depends_on: ["TASK-0076"]
risk: high
context_packs: ["codex/context/EPIC-050.md", "codex/context/EPIC-060.md", "codex/context/EPIC-090.md"]
patterns: ["PATTERN-002", "PATTERN-007", "PATTERN-008"]
---

## Context
Task routing hints, claimability, executability, collaboration/upload rights, and override behavior are currently implied across docs, projections, and handlers. Those semantics need to be frozen before any write-path hardening lands.

## Objective
Define one explicit capability lattice for routing, claim, execute, collaborate/upload, and override semantics, then freeze it in docs and contract tests without changing runtime behavior.

## Non-goals
- No handler or mutation enforcement changes in this task.
- No giant new policy framework.
- No second authority chain for permissions.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-050.md`
- `codex/context/EPIC-050.md`
- `codex/context/EPIC-060.md`
- `codex/context/EPIC-090.md`
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/flag_model.md`
- `docs/architecture/scope_model.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `schemas/policy/permissions.yaml`
- `src/onetruth/application/services/task_actionability.py`
- `tests/runtime/api/test_workspace_actionability.py`
- `tests/runtime/api/test_human_task_claim_via_api.py`
- `tests/runtime/api/test_approval_respond_via_api.py`

## Context packs / patterns to consult
- `codex/context/EPIC-050.md`
- `codex/context/EPIC-060.md`
- `codex/context/EPIC-090.md`
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-008.md`

## Source files to change
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/flag_model.md`
- `docs/architecture/scope_model.md`
- `docs/architecture/AUTHORITY_MODEL.md` if authority assumptions materially change
- `schemas/policy/permissions.yaml` if vocabulary gaps need closure there
- `docs/planning/TEST_MATRIX.md`
- `tests/contract/test_capability_matrix.py`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-050.md`
- `codex/tasks/TASK-0077-freeze-capability-lattice-and-policy-semantics.md`

## Generated / downstream artifacts impacted
- Capability matrix contract coverage.
- Task-memory and epic routing docs only.

## Plan
1. Map current semantics implied by `candidate_roles`, `required_role`, assignee/claimant state, upload behavior, and any override/escalation paths.
2. Identify contradictions between docs, read-side actionability, write-side behavior, and tests.
3. Freeze one capability matrix and one executable contract test.
4. Record any remaining ambiguity as explicit follow-on work for later tasks.

## Verification
- `pytest tests/contract/test_capability_matrix.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- One explicit capability matrix covers routing, claim, execute, collaborate/upload, approval response, flag transition, and override semantics.
- Docs and tests agree on whether `candidate_roles` is routing-only or permission-bearing.
- Write-path enforcement remains deferred to later tasks.
- Future tasks can import the semantics without reinterpretation.

## Notes / decisions
- The external zip prompt mapping is canonical here: earlier inline prompt text that labeled the capability-freeze work as `TASK-0076` is treated as stale and folded into `TASK-0077`.
- Keep the artifact set small: one matrix, one contract test, and small task/context updates.

## Source Files Changed
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/flag_model.md`
- `docs/architecture/scope_model.md`
- `docs/planning/TEST_MATRIX.md`
- `tests/contract/test_capability_matrix.py`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-050.md`
- `codex/tasks/TASK-0077-freeze-capability-lattice-and-policy-semantics.md`

## Verification Run
- `PYTHONPATH=src pytest tests/contract/test_capability_matrix.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_workspace_actionability.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_human_task_claim_via_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_human_task_complete_via_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_approval_respond_via_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_flag_transition_via_api.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_artifact_attachment_api.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance Criteria Coverage
- One explicit capability matrix now freezes routing, claim, completion, specialized execute, collaborate/upload, approval response, and flag transition semantics.
- Docs and contract coverage now agree that `candidate_roles` are not blanket permissions and that `required_role` has approval-response precedence when present.
- No handler or mutation enforcement changes were made in this task.
- Later trust-boundary tasks can now import the frozen semantics without reinterpreting the lattice.

## Completion Notes
- The authoritative capability matrix lives in `docs/architecture/human_task_semantics.md`, with short cross-references in the approval, flag, and scope docs.
- `tests/contract/test_capability_matrix.py` freezes the read-side semantics and the existing permission-vocabulary bindings without introducing new action IDs such as `task.execute`.
- Write-path hardening remains intentionally deferred; current handler-role gaps and the broader upload split are follow-on work for `TASK-0078`, `TASK-0080`, and `TASK-0081`.
