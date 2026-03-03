# STAGE07_RUNTIME_MODEL.md

Implementation-backed Stage07 model for the current runtime slice.

## Scope
This slice implements Stage07 issue-scoped replan behavior on the canonical substrate:
- canonical `flags` current-state rows + `flag.created` / `flag.state_changed`,
- issue-scoped activation in the same `workflow_run_id`,
- completion-driven Stage07 child-task spawning with lineage,
- major-replan approval gating for promotion,
- delta artifact + pointer promotion semantics,
- lease-expiry recovery + Stage07 reconcile.

Stage06 base schedule remains immutable; Stage07 operates via delta artifacts and audited pointer updates.

## Flag lifecycle
Implemented states:
- `open`
- `triage`
- `blocked`
- `resolved`
- `closed`
- `waived`

Implemented transition policy:
- `open -> triage|blocked|resolved|closed|waived`
- `triage -> blocked|resolved|closed|waived`
- `blocked -> triage|resolved|closed|waived`
- `resolved -> closed`
- terminal: `closed`, `waived`

Illegal transitions fail closed with `illegal_flag_transition`.

## Issue activation key and dedupe
Stage07 root issue activation key:
- `(workflow_run_id, flag_id, task_kind, generation)`
- concrete format: `"{workflow_run_id}|{flag_id}|{task_kind}|{generation}"`

Implemented root task kind:
- `exception_triage`

Activation dedupe behavior:
- if a task run already exists for the activation key, command returns existing canonical rows (`deduped=true`) instead of creating duplicates.
- retries/reconcile wakeups therefore do not duplicate root issue tasks.

## Completion-driven child spawn mapping
For Stage07 task completion:
- `replan_requires_missing_information` -> child Stage07 `information_request`
  - `spawn_rule_id=stage07_request_issue_information`
- `resolution_creates_child_issue` -> child Stage07 `exception_triage`
  - `spawn_rule_id=stage07_follow_on_exception_triage`
- `major_replan_is_ready_for_review` -> child Stage07 `final_review`
  - `spawn_rule_id=stage07_final_replan_review`

Children are created in the same transaction as parent completion and persist lineage fields:
- `spawned_from_task_run_id`
- `spawned_from_flag_id`
- `spawn_rule_id`
- `spawn_cause_kind=task_completion`
- `spawn_cause_event_id`
- `spawn_depth`
- `spawn_budget_key`

## Spawn budget and bounds
Implemented bounds:
- max spawn depth: `5`
- max children per issue decision: `4` (current mapping emits one child per supported outcome)

## Major-replan approval gate
Implemented gate:
- `pointers.promote` with `promotion_reason=official_major_replan` requires `approved_by_approval_id`
- approval must belong to same workflow run and be `RESPONDED` with `response_kind=approve`
- Stage07-specific gate also requires approval scope to reference `Stage07`

Promotion without required approval fails closed (`approval_required_for_promotion` / `major_replan_approval_required`).

## Delta artifact linking model
Stage07 delta artifacts are created as immutable `artifact_versions` and can carry metadata links (scenario-backed in tests), including:
- `flag_id`
- `base_artifact_version_id`
- `delta_sequence`
- `supersedes_artifact_version_id`

No in-place mutation of Stage06 base artifact versions is performed.

## Pointer promotion and drift rule
Implemented drift detection for Stage07 promotions:
- `pointers.promote` accepts `reviewed_base_artifact_version_id` and optional `base_pointer_key`
- if reviewed base version differs from the current base pointer target at promotion time, emit `artifact.pointer.drift_detected`
- promotion remains allowed (visibility-required, not hard-blocked)

Legacy reviewed-vs-promoted drift check remains supported when `reviewed_artifact_version_id` is used.

## Lease expiry and reconcile
Implemented maintenance commands:
- `maintenance sweep-leases`
- `maintenance reconcile-stage07`

Lease-expiry behavior:
- detect expired claimed human tasks,
- reopen the same human task row (clear assignee/lease, increment reopen counters/version),
- emit `task.lease_expired`,
- move task run `IN_PROGRESS -> READY` with `task.run.state_changed` evidence.

Reconcile behavior:
- for open Stage07 flags, ensure root issue task exists via activation-key dedupe,
- recover dropped wakeups without creating duplicate root tasks.
