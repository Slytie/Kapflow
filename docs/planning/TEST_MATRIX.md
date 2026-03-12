# TEST_MATRIX.md

This matrix is the **executable-spec index** for Stage 4.

It exists to make the platform's non-negotiable invariants *hard to regress* under:
- retries and durable waits
- multi-tenant isolation boundaries
- long-running orchestration
- progressive automation (assist -> suggest -> draft -> execute)
- fully-agentive debug runs that still preserve one truth system

It is intentionally written so a fresh-session Codex run can:
1) identify which tests must exist for a change, and
2) identify which evidence/security/ops checks a reviewer should demand.

---

## 1) Invariants -> required tests

| Invariant | Risk we are retiring | Required test types | Suggested suites / locations (repo) |
|---|---|---|---|
| I1 Durable workflow semantics + safe evolution | non-determinism, unsafe version drift, retries duplicate effects | unit + replay + property | `tests/unit/*reducer*`, `tests/replay/*golden*`, `tests/property/*history*` |
| I2 Artifact immutability + auditability | silent mutation, broken lineage, "latest file" ambiguity | unit + integration + property | `tests/unit/artifacts_*`, `tests/integration/artifact_store_*`, `tests/property/lineage_*` |
| I3 Tenant isolation + authorization | cross-tenant leakage, mixed projections, unsafe background consumers | integration + security + acceptance negatives | `tests/security/isolation/*`, `tests/integration/*scope*`, `tests/acceptance/*cross_tenant*` |
| I4 Automation safety (LLM/tools) | prompt/tool injection, unsafe side-effects, sandbox escape | security + contract + integration | `tests/security/agent/*`, `tests/contract/tool_plane_*`, `tests/integration/sandbox_*`, `tests/integration_openai/*` |
| I5 One truth system (authority chain) | "shadow truth" stores, summaries outrank evidence, drift in generated artifacts | schema + contract + policy tests | `tests/contract/*schema*`, CI check in `docs/ops/ci_required_checks.md` |
| I6 Fully-agentive debug slice preserves canonical authority | agent-only state, approval bypass, invisible stage work | replay + acceptance + security | `tests/replay/*schedule_agentive*`, `tests/acceptance/*schedule_agentive*`, `tests/security/agent/*approval_bypass*` |
| I7 Conditional task spawning stays explicit and bounded | hidden branching, duplicate child tasks on retry, runaway loops | unit + integration + runtime scenarios | `tests/unit/*spawn*`, `tests/integration/*idempotency*`, `tests/runtime/scenarios/*spawn*` |

> **Rule:** If a change touches an invariant, add or update the tests listed for that invariant.

---

## 2) Schedule Planning workflow stage coverage (implementation wedge)

Schedule Planning is the **runtime implementation wedge** for Stage 4.
The primary acceptance objective is a **fully-agentive whole-flow debug run** that still uses the canonical task, approval, artifact, and event substrate.

### Acceptance scenarios (IDs are stable)
| Scenario ID | Stages | What it proves | Negative / red-team variant required |
|---|---|---|---|
| AT-SCH-001 Happy path publish + replan | Stage03->Stage07 | durable waits, approvals, pointer promotions, additive delta semantics, audit timeline reconstructability | AT-SCH-001N: replay after restart does not duplicate tool effects or double-publish the base schedule |
| AT-SCH-002 Drift after review is visible | Stage06 / Stage07 | `artifact.pointer.drift_detected` is emitted and visible when promotion occurs after review on a stale base | AT-SCH-002N: attempt to promote an unreviewed or superseded version is blocked or explicitly flagged |
| AT-SCH-003 Fully-agentive whole-flow | Stage03->Stage07 | every in-scope task can be executed by agent-owned work while still emitting canonical task/approval/pointer events and explicit child-task lineage when follow-on work is spawned | AT-SCH-003N: an agent attempt to bypass approval/pointer/event rules is denied and leaves audit evidence |
| AT-SCH-004 Exception-task concurrency | Stage07 | issue-specific tasks, claim/lease rules, conditional child-task spawning, and escalations prevent silent stalls during intraday triage | AT-SCH-004N: lease expiry reopens or escalates work with visible evidence |
| AT-SCH-005 Degraded-mode survivability | any | timeline persistence survives exporter/indexer failure | AT-SCH-005N: projections degrade, but authoritative events still record the truth |
| AT-SCH-006 Cross-tenant negative | any | tenant/domain scoping enforced across API and background jobs | AT-SCH-006N: explicit attempt to read tenant B data returns 404/deny |
| AT-SCH-007 Sandbox/policy gate | Stage06 / Stage07 (if tools enabled) | execute requires policy + approval + budget | AT-SCH-007N: out-of-plan execute attempt without approval must be denied with event evidence |


### Stable oracle mapping
Each primary Schedule Planning acceptance scenario now has a dedicated golden trace and pytest oracle:
- `AT-SCH-001` -> `schedule_happy_path_publish_and_replan.jsonl`
- `AT-SCH-002` -> `schedule_drift_after_review.jsonl`
- `AT-SCH-003` -> `schedule_fully_agentive_whole_flow.jsonl`
- `AT-SCH-004` -> `schedule_lease_expiry_recovery.jsonl`
- `AT-SCH-005` -> `schedule_degraded_mode_survivability.jsonl`
- `AT-SCH-006` -> `schedule_cross_scope_denial.jsonl`
- `AT-SCH-007` -> `schedule_policy_gate_enforced.jsonl`

### Required event evidence (for acceptance oracles)
A passing acceptance run must be able to export an evidence set showing at minimum:
- `workflow.run.created`, `workflow.run.state_changed`
- `task.run.created`, `task.run.state_changed`
- `task.created`, `task.claimed`, `task.lease_expired` (when relevant), `task.completed`
- explicit child-task lineage for any spawned follow-on work
- `approval.requested`, `approval.responded` (`payload.response` and `payload.outcome` required)
- `artifact.version.created`, `artifact.pointer.promoted`, `artifact.pointer.drift_detected` (when drift occurs)
- `flag.created` and `flag.state_changed` (when flags are used)
- `execution.session.*` and `tool.execution.*` when agentive work is active
- `audit.degraded_mode.changed` (when degraded mode toggles)

---

## 3) Planned runtime scenario harness coverage

Once the runtime scaffold exists, add step-run tests where the agent executes each step through a stable interface and the test asserts only authoritative truth.

Current implemented runtime command-boundary coverage:
- `tests/runtime/test_cli_timeline_smoke.py`
- `tests/runtime/test_workflow_task_core_cli.py`
- `tests/runtime/test_approvals_artifacts_pointers_cli.py`
- `tests/runtime/scenarios/test_schedule_stage06_publish_steps.py`
- `tests/runtime/scenarios/test_schedule_stage06_request_more_information_steps.py`
- `tests/runtime/scenarios/test_schedule_stage06_retry_no_duplicate_child_tasks.py`
- `tests/runtime/scenarios/test_schedule_stage07_major_replan_happy.py`
- `tests/runtime/scenarios/test_schedule_stage07_missing_information_branch.py`
- `tests/runtime/scenarios/test_schedule_stage07_child_issue_branch.py`
- `tests/runtime/scenarios/test_schedule_stage07_duplicate_flag_retry.py`
- `tests/runtime/scenarios/test_schedule_stage07_lease_expiry_recovery.py`
- `tests/runtime/scenarios/test_schedule_stage07_drift_detected.py`
- `tests/runtime/test_logistics_handoff_runtime.py`
- `tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py`
- `tests/runtime/scenarios/test_logistics_reporting_to_planning_notify_only_golden_slice.py`
- `tests/runtime/scenarios/test_logistics_three_workflow_demo_story_seed.py`
- `tests/runtime/scenarios/test_workspace_graph_projection.py`
- `tests/runtime/contracts/test_hitl_query_contracts_stage06.py`
- `tests/runtime/contracts/test_hitl_query_contracts_stage07.py`
- `tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `tests/runtime/contracts/test_workspace_demo_export_bundle.py`
- `tests/runtime/test_projection_coherence.py`
- `tests/runtime/test_example_document_corpus_ingress.py`
- `tests/runtime/api/test_human_task_list_contract.py`
- `tests/runtime/api/test_approval_list_contract.py`
- `tests/runtime/api/test_flag_list_contract.py`
- `tests/runtime/api/test_artifact_attachment_api.py`
- `tests/runtime/api/test_workflow_run_detail_contract.py`
- `tests/runtime/api/test_timeline_contract.py`
- `tests/runtime/api/test_board_schedule_planning_contract.py`
- `tests/runtime/api/test_logistics_three_workflow_story_endpoint.py`
- `tests/runtime/api/test_human_task_claim_via_api.py`
- `tests/runtime/api/test_human_task_complete_via_api.py`
- `tests/runtime/api/test_human_task_subgraph_contract.py`
- `tests/runtime/api/test_approval_respond_via_api.py`
- `tests/runtime/api/test_flag_transition_via_api.py`
- `tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
- `tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `tests/runtime/api/test_workflow_run_workspace_endpoint.py`
- `tests/runtime/api/test_workspace_actionability.py`
- `tests/runtime/test_execution_session_runtime.py`
- `tests/runtime/test_weekly_stage04_execution_runtime.py`
- `tests/runtime/test_realistic_schedule_planning_pilot.py`
- `tests/runtime/api/test_cross_scope_api_denial.py`
- `tests/runtime/api/test_board_retry_stability.py`
- `tests/runtime/api/test_api_retry_stability.py`
- `tests/unit/test_openai_responses_adapter.py`
- `tests/unit/test_responses_agent_runner.py`
- `tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py`
- `tests/integration_openai/test_stage06_openai_real_e2e.py` (gated/opt-in)

Current runtime tests assert:
- canonical row creation for `workflow_runs`, `task_runs`, `human_tasks`
- lifecycle transitions for claim and completion
- authoritative event emission for lifecycle commands
- claim concurrency safety (single winner under race)
- explicit idempotency failure behavior on duplicate command keys
- negative lifecycle guards (for example unclaimed completion and duplicate run activation)
- canonical row creation and transitions for `approvals`, `artifact_versions`, and `artifact_pointers`
- approval response finalization guard (cannot respond twice)
- artifact-version idempotency guard (duplicate key fails with no duplicate canonical/event effect)
- pointer promotion conflict/race behavior (single winner, explicit loser failure)
- coherent cross-linkage chain assertions across workflow/task/artifact/approval/pointer lifecycle
- stable CLI list/show JSON contracts that intentionally support future parallel board/query UI work
- Stage06 completion outcome -> explicit child-task spawning with lineage fields persisted on canonical `task_runs`
- Stage06 scenario retries do not duplicate spawned children/events when parent completion idempotency key is retried
- first implementation-backed query-contract snapshots for human-task queue, approval queue, pointer summary, and workflow-run summary rows
- backend-owned frontend snapshot fixtures exported from real Stage06/Stage07 scenario states under `fixtures/frontend_contracts/` with deterministic refresh + drift-check coverage (`make frontend-snapshots-check`) and source-path sanitization (no local absolute machine paths in snapshot metadata)
- canonical example-document corpus ingress through artifact-backed storage/versioning (`artifacts ingest`, `artifacts seed-corpus`) with deterministic manifest seeding and digest/metadata round-trip checks
- canonical attachment linkage/query surfaces for human tasks, approvals, flags, and workflow runs via `artifact_links`
- API upload/list/show/download attachment visibility and cross-scope denial behavior for artifact-backed documents
- canonical Stage07 flag lifecycle/activation semantics with deduped issue-root activation keys and generation handling
- Stage07 completion outcome -> child spawn mappings (`information_request`, child `exception_triage`, `final_review`) with persisted lineage
- major-replan approval gate enforcement on pointer promotion (`official_major_replan`)
- lease-expiry reopen recovery with canonical `task.lease_expired` evidence and Stage07 reconcile repair path
- drift visibility for stale reviewed base at Stage07 promotion (`artifact.pointer.drift_detected`)
- first logistics weekly->live handoff runtime semantics:
  - explicit idempotent `edge_executions` state (`prepared -> activated`)
  - one logical Stage07 seed per transformed `ServiceDateID`
  - lazy `live_dispatch.v1` activation with exact canonical input bindings
- bounded logistics `notify_only` reporting->planning semantics:
  - compiled-edge gate (`handoff_mode=notify_only`, `writer_mode=source_only`)
  - deterministic target-run resolve/create and target input materialization
  - duplicate notification idempotency without target-side official output mutation
- canonical three-workflow story seam semantics:
  - seeded scenario composition links reporting, weekly, and live runs through both canonical edges in one lineage
  - backend story endpoint returns one authoritative payload (graph + handoffs + linked runs + board-ready work + official outputs + freshness/coherence)
- implementation-backed HTTP contract/mutation coverage for board-ready read surfaces (tasks/approvals/flags/workflow/timeline/pointers/board) and canonical HITL actions (`claim`, `complete`, `respond`, `flags.transition`)
- human-task composite expansion contracts:
  - detail payload always includes optional expansion metadata (`is_composite`, `expansion_kind`, `subgraph_ref`)
  - composite task kinds return lazy subgraph payloads via `GET /api/v1/human-tasks/{id}/subgraph` with reference-only artifact refs (no artifact bytes)
- frontend inline attachment controls are covered at component/repository contract level and remain delegated to canonical artifact endpoints (no client-side shadow attachment state)
- bounded Stage06 real-model sandbox path coverage (mock/contract path always-on + gated real OpenAI e2e path)
- single-run workspace projection coverage:
  - derived Schedule Planning graph node/edge/status projection over canonical run/task/approval/flag/artifact/pointer state
  - server-computed `available_actions` + blocking requirements for tasks/approvals/flags
  - read-only workspace endpoint envelope + cross-scope denial + freshness metadata
  - demo workspace runner and export bundle zip content/readme integrity
- first projection coherence harness coverage:
  - workspace official-output drift is visible (`warn_visible`) and emits `projection.coherence_failed`
  - approval-critical export packet drift is blocked (`block`) and emits `projection.coherence_failed`
  - handoff operator-view drift is visible (`warn_visible`) and emits `projection.coherence_failed`
- canonical execution-runtime lifecycle coverage for bounded agentive work:
  - `execution_sessions` / `tool_executions` / `policy_decisions` row creation and state transitions
  - explicit policy allow/deny gating before model/tool execution (including `WAITING_POLICY -> RUNNING` on allow)
  - retry/idempotency guard for duplicate execution requests
  - stale-session reconcile recovery without duplicate terminal effects
  - reconcile of partial sessions does not duplicate already-completed tool/evidence effects
- bounded Stage04 weekly agent function-calling coverage:
  - Responses API function-calling loop supports multiple function calls per turn with `call_id`-bound `function_call_output` continuation
  - Stage04 execution session semantics are pinned from compiled control metadata
  - only deterministic Stage04 tools are exposed; outputs remain draft-only
  - context packs, request/result turns, and execution traces are persisted as canonical evidence artifacts linked to execution runtime objects
- realistic pilot/operator-inspection coverage:
  - reproducible Stage06/Stage07 pilot runs seeded from corpus seed sets via canonical ingress
  - Stage06 bounded agent review path creates canonical execution/tool/policy/evidence links
  - inspection packets include canonical references and run/board/timeline/artifact/approval/flag inspection routes
  - repeated pilot runs with same pilot key do not duplicate canonical effects
- cross-scope API denial checks and retry-stability checks over repeated GET/mutation retries

Minimum required runtime scenario tests:
- `tests/runtime/scenarios/test_schedule_stage06_publish_steps.py`
- `tests/runtime/scenarios/test_schedule_stage07_major_replan_happy.py`
- `tests/runtime/scenarios/test_schedule_stage07_missing_information_branch.py`
- `tests/runtime/scenarios/test_schedule_stage07_child_issue_branch.py`
- `tests/runtime/scenarios/test_schedule_stage07_duplicate_flag_retry.py`
- `tests/runtime/scenarios/test_schedule_stage07_lease_expiry_recovery.py`
- `tests/runtime/scenarios/test_schedule_stage07_drift_detected.py`

Additional implemented logistics runtime scenarios (bounded composition slices):
- `tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py`
- `tests/runtime/scenarios/test_logistics_reporting_to_planning_notify_only_golden_slice.py`
- `tests/runtime/scenarios/test_logistics_three_workflow_demo_story_seed.py`

Each scenario should:
- seed initial artifact inputs from `fixtures/workflows/*/template_pack/*_Example_COMPLETED.*`
- execute the workflow through CLI/API commands, not by calling hidden internals
- assert parent `task.completed` plus child `task.run.created` / `task.created` evidence when follow-on work is spawned
- assert retrying the same parent completion does not duplicate child tasks

### Artifact-store and reconstruction implementation targets (TASK-0030 closure)
The following test files are now explicitly required for the artifact-store implementation tranche:
- `tests/runtime/test_artifact_store_base_immutability.py`
- `tests/runtime/test_stage07_ordered_delta_reconstruction.py`
- `tests/runtime/test_pointer_promotion_idempotency.py`
- `tests/runtime/test_stage07_drift_visibility.py`
- `tests/runtime/test_artifact_blob_metadata_mismatch.py`
- `tests/runtime/test_stage07_superseded_delta_handling.py`
- `tests/runtime/test_stage07_major_replan_approval_gate.py`

Required helper surfaces these tests should exercise:
- reconstruction service helper (planned): `src/onetruth/application/services/schedule_reconstruction.py`
- authoritative promotion-history query helper (planned): `src/onetruth/infrastructure/repositories/artifact_promotions.py` (or equivalent)
- read-only inspection boundary (planned CLI/API): schedule reconstruction by `workflow_run_id` and optional `as_of` cursor

## 4) Payroll coverage (secondary reference workflow)


Payroll is the **secondary reference workflow** for Stage 4.
It remains important because it validates the same substrate against:
- linear approval-heavy progression,
- lock/finalize governance,
- artifact promotion under pay-period semantics.

Minimum required evidence for the current phase:
- Payroll workflow pack exposes the full authored surface, including `OPERATING_MODEL.md`
- Payroll contract pack is internally consistent (schemas + registry)
- Stage IDs, decision refs, artifact keys, and approval actions remain aligned across the pack
- Payroll acceptance scenarios remain available as a secondary corpus once runtime work reaches that wedge

---

## 5) Epic -> test deliverables mapping (high-level)

| Epic | Test deliverables it must produce or enable |
|---|---|
| EPIC-010 Scope/AuthZ | isolation negative tests; policy unit tests for scope checks |
| EPIC-020 Timeline/Outbox | schema validation; payload-contract validation; outbox atomicity integration tests; degraded-mode tests |
| EPIC-030 Artifact store | immutability + lineage property tests; drift detection tests |
| EPIC-040 Orchestrator | reducer determinism unit tests; replay tests on golden histories |
| EPIC-050 Human tasks | lease/concurrency tests; "claim once" negative tests; agent-owned task execution tests |
| EPIC-060 Approvals | approval binding tests; reject/changes_requested cases; agent-principal approval-path tests |
| EPIC-070 Sandbox | containment regression tests; tool-call schema validation tests |
| EPIC-080 Ops | CI required checks; workflow-pack validation; smoke tests + alert rule tests |
| EPIC-090 Acceptance | AT-SCH-001..007 acceptance suite + replay regression corpus + Payroll reference corpus |

---

## 6) CI gate linkage
CI requirements live in `docs/ops/ci_required_checks.md`.

**Pre-merge should block** on:
- schema/contract validation (event envelope, event registry, workflow packs)
- unit tests (reducers/policy validators)
- replay smoke tests (if workflow logic changed)

**Post-merge / nightly** should include:
- integration tests with real dependencies
- isolation suite
- adversarial injection corpus (if tools enabled)
- gated real OpenAI sandbox e2e: `ONETRUTH_RUN_OPENAI_E2E=1 PYTHONPATH=src pytest -q tests/integration_openai`
