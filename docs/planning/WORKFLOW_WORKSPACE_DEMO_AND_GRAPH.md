# WORKFLOW_WORKSPACE_DEMO_AND_GRAPH.md

This note defines the backend-first workflow workspace slice for a single workflow run demo.

## A. Single-run workspace concept
- The workspace is scoped to one `workflow_run_id`.
- The top surface is a minimal workflow graph that visibly advances as canonical state changes.
- The lower surface is actionable work for the current actor (`user_work`) plus run-blocking work.
- The detail drawer remains the deep inspection surface for timeline/event/artifact/approval/flag details.
- Refresh model is polling-friendly HTTP reads; no live socket protocol is required in this slice.

## B. Derived graph law
- Graph nodes and statuses are derived from canonical `workflow_runs`, `task_runs`, `human_tasks`, `approvals`, `flags`, `artifact_versions`, and `artifact_pointers`.
- The graph is not authoritative state and is not a second workflow engine.
- Every graph status must be explainable from canonical records and timeline evidence.
- When graph and canonical rows disagree, canonical rows/events/pointers are authoritative by definition.

## C. Actionability law
- Mutation affordances in workspace are server-computed via `available_actions` and requirement checks.
- UI must not invent allowed actions or completion preconditions.
- “Upload a document to unblock work” is represented canonically as artifact ingress + subject linkage, then reflected as changed server-computed actionability.
- Existing canonical mutation handlers remain the only mutation authority (claim/complete/respond/upload/transition).

## D. Initial minimal graph node set for `schedule_planning.v1`
Initial node IDs:
1. `stage03_inputs_ready`
2. `stage04_capacity_ready`
3. `stage05_draft_triage`
4. `stage06_review`
5. `stage06_publish_approval`
6. `stage06_base_published`
7. `stage07_exception_control`
8. `stage07_replan_approval`
9. `stage07_delta_published`

Initial status vocabulary:
- `not_started`
- `ready`
- `in_progress`
- `blocked`
- `awaiting_approval`
- `completed`
- `warning`

Initial branch semantics:
- Stage05/Stage06 loopback is represented for information-request and rework returns.
- Stage07 branch coverage is represented for exception triage, major-replan approval gating, and ordered-delta publish.
- This is intentionally minimal and useful for demo progression, not a full BPMN clone.

## E. Demo runner + export bundle
- Demo runner seeds realistic canonical runs for:
  - `stage06_publish_ready`
  - `stage06_needs_information`
  - `stage07_major_replan`
- Seeding uses existing canonical handlers and the example corpus ingress path.
- Export bundle packages a human-reviewable snapshot of one run:
  - workspace projection payload,
  - workflow/task/approval/flag/execution/timeline/policy snapshots,
  - official outputs and graph node/edge extracts,
  - README with scenario/run context and first actions to take.
- The bundle is inspection evidence only; canonical runtime tables/events/pointers remain authority.
