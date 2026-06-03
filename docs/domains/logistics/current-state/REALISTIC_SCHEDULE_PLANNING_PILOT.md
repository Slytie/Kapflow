> Document classification: descriptive logistics current-state source. See `docs/domains/logistics/DOC_INVENTORY.yaml`.

# REALISTIC_SCHEDULE_PLANNING_PILOT.md

## Purpose
Define the first operator-inspectable Schedule Planning pilot slice that runs on canonical runtime truth:
- canonical workflow/task/approval/flag/artifact/pointer rows,
- canonical execution session/tool/policy rows for Stage06 bounded agent review,
- authoritative timeline evidence,
- derived UI/query surfaces only for inspection.

This is an experiential milestone: the goal is to make a realistic service-day run easy to inspect end-to-end, not to generalize a demo framework.

## Pilot scenarios
The pilot runner executes three scenarios.

### 1) `stage06_publish_ready`
Intent:
- Stage06 review packet is processed by the bounded Stage06 agent path.
- Agent classifies outcome as `draft_is_publish_ready`.
- Final review, approval, and official publish pointer are completed.

Expected branch:
- Stage06 `review_packet` task -> spawned Stage06 `final_review` task -> publish approval -> official published pointer.

### 2) `stage06_needs_information`
Intent:
- Stage06 review packet is processed by the bounded Stage06 agent path.
- Agent classifies outcome as `review_requires_more_information`.

Expected branch:
- Stage06 `review_packet` task -> spawned Stage06 `information_request` task (open).
- No publish approval or official Stage06 publish pointer promotion in this branch.

### 3) `stage07_issue_replan`
Intent:
- Start from a published-base context.
- Trigger a realistic issue flag and run Stage07 issue activation/review.
- Produce and promote a replan delta with approval.

Expected branch:
- Stage07 flag creation -> issue activation -> triage -> final review -> major replan approval -> delta pointer promotion -> resolved flag.

## Seed sets used
The runner seeds from `fixtures/example_document_corpus/manifest.yaml` through canonical ingress.

- `stage06_publish_ready`:
  - primary seed set: `stage06_review_ready_example_set`
  - plus Stage06 publish workbook fixture for official output creation.

- `stage06_needs_information`:
  - primary seed set: `stage06_needs_information_example_set`

- `stage07_issue_replan`:
  - primary seed set: `stage07_issue_replan_example_set`

No fixture bypass path is allowed.

## Bounded agent stage
Bounded agent execution is only used in Stage06 `review_packet` tasks.

The pilot runner must execute Stage06 through:
1. claimed human task,
2. bounded Stage06 OpenAI review service,
3. canonical execution session/tool execution/policy decision rows,
4. canonical evidence artifact creation,
5. canonical task completion/spawn behavior.

No agent execution is introduced for Stage07 in this pilot.

## Expected artifacts and evidence
Per run, expected canonical artifacts/evidence include:

- input artifacts seeded from corpus as immutable `artifact_versions`,
- Stage06 agent evidence artifact (`schedule.stage06.review_ai_evidence.json`) for Stage06 scenarios,
- Stage06 official publish artifact + pointer for publish-ready scenario,
- Stage07 base and delta artifact lineage and pointer promotion for issue/replan scenario,
- approval rows/events when publish or major replan gates apply,
- flag rows/events for Stage07 issue activation and resolution.

Expected execution evidence (Stage06 scenarios):
- `execution_sessions` row linked to Stage06 task run,
- `tool_executions` row linked to session,
- `policy_decisions` row linked to tool execution,
- `execution.session.*` and `tool.execution.*` events in timeline.

## Operator inspection checklist
The inspection packet should point operators to derived surfaces while preserving canonical references.

### Board (`/board`)
Inspect:
- lane placement of open/claimed/completed Stage06/Stage07 tasks,
- approval cards where required,
- exception/flag cards for Stage07 issue flow.

Good signs:
- publish-ready path shows approval/publish progress,
- needs-information path shows open information request,
- Stage07 issue path shows issue card lifecycle and no silent transitions.

### Run detail (`/runs/{workflow_run_id}`)
Inspect:
- task lineage (including spawned children),
- approvals, artifacts, pointers, flags grouped for one run,
- summary consistency against packet JSON.

Good signs:
- object links are coherent (task/approval/artifact/pointer/flag references resolve),
- no missing canonical row needed to explain outcome.

### Timeline (`/timeline` with run filter)
Inspect:
- ordered lifecycle events for run,
- explicit `task.*`, `approval.*`, `artifact.*`, `flag.*` evidence,
- explicit `execution.session.*`/`tool.execution.*` for Stage06 agent paths.

Good signs:
- no hidden branch transitions,
- policy allow/deny state changes visible before tool completion,
- pointer promotions auditable with approval linkage when required.

### Artifacts and pointers
Inspect:
- immutable artifact versions and metadata,
- official pointer targets for Stage06 publish and Stage07 delta,
- Stage07 delta supersedes/base references.

Good signs:
- published base artifact remains immutable,
- Stage07 delta is additive and pointer-mediated.

### Approvals
Inspect:
- required approval rows and responses for Stage06 publish and Stage07 major replan.

Good signs:
- approvals include scope/action/required role,
- response is explicit and linked to resulting promotion.

### Flags/exceptions
Inspect:
- Stage07 flag lifecycle (`open` -> resolved/closed as appropriate),
- issue activation and task linkage.

Good signs:
- one coherent issue path per activation key,
- no duplicate root issue tasks for same activation.

## Correct-enough outcomes for this pilot
The pilot is considered correct enough when:

1. Each scenario is reproducible from the same pilot key without duplicating canonical effects.
2. Stage06 scenarios create auditable execution session/tool/policy/evidence records before/around bounded agent execution.
3. Publish-ready scenario results in Stage06 official pointer promotion with approval evidence.
4. Needs-information scenario results in explicit open Stage06 information-request child task.
5. Stage07 scenario results in coherent flag/task/approval/artifact/pointer timeline for issue/replan.
6. Inspection packets provide enough references (IDs + routes + event summaries) for an operator to validate behavior without reading source code.
7. Frontend/API inspection remains derived from canonical runtime truth; packet claims map back to canonical IDs/events.

## Output contract
For each scenario run, write:
- `inspection_packet.json` (machine-readable canonical references)
- `inspection_packet.md` (human walkthrough summary)

And write suite-level summary:
- `pilot_summary.json`
- `pilot_summary.md`

Suggested output root:
- `artifacts/pilot_runs/<pilot_key>/`
