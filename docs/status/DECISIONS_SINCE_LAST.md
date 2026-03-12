# DECISIONS_SINCE_LAST.md

Record any decisions made since the last session so a fresh Codex run can rehydrate quickly.

## 2026-03-12 (TASK-0066 execution-runtime hardening for compiled agent control traceability)
- Execution semantics evidence decision: Stage06 bounded execution now persists pinned immutable semantics artifacts (`execution.compiled_spec.json`, `execution.compile_source_manifest.json`) linked to canonical execution runtime objects; no second execution truth subsystem was introduced.
- Artifact-link subject decision: canonical artifact linkage validation now supports `execution_session`, `tool_execution`, and `policy_decision` subjects with workflow-scope checks resolved through existing execution/session relationships.
- Event safety decision: runtime event append now enforces registry-defined `required_links` semantics at write time (not only offline validation), and execution-session creation now emits an explicit `execution_spec` link required by the registry.
- Reuse decision: added a shared execution-evidence helper surface (`src/onetruth/application/services/execution_evidence.py`) that prepares pinned semantics artifacts and reusable execution-facet evidence links for future agent-trace slices.

## 2026-03-12 (TASK-0065 logistics-first Codex routing + secret hygiene)
- Routing decision: new agentic scheduling task intake now defaults to logistics weekly/live (`weekly_schedule_planning.v1 -> live_dispatch.v1`) across Codex/LLM routing docs; legacy `schedule_planning.v1` remains regression/reference-only.
- Secret hygiene decision: committed real OpenAI key material is removed from tracked repo content, and local `.codex.env` posture is documented as local-only placeholders with real-network gates defaulted off.
- Validation decision: `scripts/validate_repo.py` now scans tracked UTF-8 files for real OpenAI key patterns (`sk-proj-...` / `sk-...`) and fails validation on detection.
- CI gate posture decision: `.github/workflows/agent_api.yml` keeps current OpenAI gating and adds an explicit future weekly-agent real-network gate controlled by repository variable `ONETRUTH_RUN_WEEKLY_AGENT_E2E=1` plus `OPENAI_API_KEY` presence.

## 2026-03-09 (TASK-0068 composite-task subgraphs + drawer hardening)
- Human-task drill-down contract decision: keep `GET /api/v1/human-tasks/{id}` as the canonical detail seam and extend it with optional composite metadata (`is_composite`, `expansion_kind`, `subgraph_ref`) while keeping non-composite tasks unchanged.
- Task-subgraph endpoint decision: add `GET /api/v1/human-tasks/{id}/subgraph` for lazy, server-authored composite task process graphs; frontend loads this only when the operator chooses `Expand process`.
- Bounded rollout decision: composite expansion is enabled only for known logistics demo task kinds in this slice (`actual_hours_review`/`planning_feedback_review`, `dispatcher_review`/`dispatch_seed_intake`, `final_packet_review`/`finalize_reporting_packet`).
- Artifact boundary decision: task subgraph payloads remain reference-only (`artifact_version_id`, label, source label) and all bytes are still downloaded exclusively through canonical artifact download APIs.

## 2026-03-09 (TASK-0066 family-graph drilldown contract closure)
- Logistics story contract decision: `GET /api/v1/stories/logistics-three-workflow` now emits server-authored family-module drilldown metadata (`node_kind`, `drilldown_kind`, `drilldown_refs`, `artifact_refs`, `selection_summary`) so frontend drilldown does not guess run/artifact targets.
- Multiple-run disambiguation decision: when a module maps to more than one linked run in story scope, `drilldown_kind=run_group` and all candidate runs are returned in `drilldown_refs`; the backend does not silently choose one run.
- Artifact-reference decision: family-node artifact metadata stays reference-only (`artifact_version_id`, label, source label) and download bytes remain behind canonical artifact download APIs.

## 2026-03-09 (logistics drawer-first interaction hardening)
- Logistics-board interaction decision: in `/demo/logistics`, human-task board cards are now primary-click drawer surfaces; task inspection/action no longer uses `/runs/:workflowRunId` navigation as the primary path.
- Drawer action-surface decision: `DetailDrawer` now executes backend-authoritative human-task actions when present in `available_actions` (`claim`, `complete`, `run_stage06_agent_review`, `confirm_review`, `upload_attachment`) and keeps artifact download in-drawer.
- Secondary navigation decision: run-detail drill-down is retained only as a secondary drawer link from selected tasks; stale per-card run-detail links were removed from the unified board to reduce legacy-route confusion.

## 2026-03-09 (TASK-0064 logistics demo shell + legacy schedule demotion)
- Frontend primary-demo decision: `/demo/logistics` is now the preferred operator/demo entrypoint for the three-workflow logistics walkthrough; app root (`/`) redirects to this route.
- Composition decision: the logistics shell is backend-authored and story-driven only (`GET /api/v1/stories/logistics-three-workflow`); family graph, unified board lanes/items, linked runs, official-output summary, and handoff activity are rendered directly from canonical story payload sections.
- Task-interaction decision: task transitions are drawer-first for this demo slice; task cards/rows in logistics story and supporting queue surfaces open `DetailDrawer`, and canonical `claim`/`complete` actions execute from the drawer against authoritative task APIs.
- Supersession note: this drawer-first task-transition decision supersedes the earlier 2026-03-04 inline-task-action posture for `/board` and `/my-work`; inline attachment affordances remain unchanged.
- Legacy-surface decision: schedule-only board/workspace/runs/timeline views remain available for regression/internal use but are removed from primary navigation and treated as secondary/legacy surfaces via page-level notices.
- Scope-boundary decision: this frontend slice intentionally stays bounded to the canonical three-workflow story contract and does not introduce a generalized client-side family graph/query engine or a second UI truth store.

## 2026-03-09 (repo-truth alignment + capability certification matrix)
- Added `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md` as the snapshot-backed authority for current capability status (`implemented` / `partial` / `missing`) across schedule demo paths, logistics handoff slices, workspace/export surfaces, and projection coherence.
- Hardening decision: capability claims are considered certified only when matrix rows include all of: canonical command/entrypoint, authoritative tests, human-inspectable artifacts, and invariants.
- Scope-boundary decision: this alignment pass introduces no new runtime semantics; bounded slices and unresolved ambiguities are recorded explicitly instead of being promoted to DONE claims.

## 2026-03-09 (TASK-0063 three-workflow story seam closure)
- Added canonical three-workflow demo story contract source at `docs/planning/THREE_WORKFLOW_DEMO_STORY.yaml` plus aligned template/example artifacts under `templates/`.
- Added first backend-authored logistics story query seam `GET /api/v1/stories/logistics-three-workflow`; payload is derived from canonical runtime state only (compiled family graph + `edge_executions` summaries + linked runs + board-ready work + official outputs + freshness/coherence metadata).
- Demo-entrypoint decision: for logistics three-workflow walkthroughs the new story endpoint is primary; `/api/v1/board/schedule-planning` remains legacy/internal regression surface.
- Scope-boundary decision: this closure remains intentionally narrow to the first story slice (`weekly_schedule_planning`, `live_dispatch`, `dispatch_reporting` with `reporting_actuals_to_future_planning` `notify_only`), and does not claim a universal logistics composition engine.

## 2026-03-08 (TASK-0063 notify_only reporting->planning + TASK-0031 status closure)
- Status authority decision: TASK-0031 is DONE. Projection coherence authored/runtime surfaces now exist in-repo (`docs/planning/PROJECTION_COHERENCE_HARNESS.md`, `tests/runtime/test_projection_coherence.py`, and runtime `projection.coherence_failed` behavior over derived projection views).
- Composition runtime decision: TASK-0063 is DONE as a bounded first `notify_only` slice over existing `edge_executions` + compiled family edges; landed scope is `dispatch_reporting.Stage05 -> weekly_schedule_planning.Stage03` with deterministic typed transform usage, target run resolve/create, canonical target input materialization, exact input binding capture, and duplicate-notification idempotency.
- Scope-boundary decision: keep later logistics composition work (observability/query surfaces, additional edges) as future tranche work; do not represent TASK-0063 as a fully general finished composition engine.

## 2026-03-07 (TASK-0061 logistics control layer + method packages)
- Chosen control-layer authority boundary: compiled logistics control metadata drives only existing canonical runtime activation objects (`workflow_runs`, `task_runs`, `human_tasks`, `execution_sessions`, `tool_executions`); no second activation ontology/table set is introduced.
- Chosen method-package pinning posture: first-slice stages require authored method packages with deterministic replay fields, explicit stop policy, and a content digest; execution-spec identities are derived from these pinned package digests.
- Chosen fail-closed rule for first-slice control semantics: missing method package coverage for required first-slice stages, stage/pattern mismatches, or incomplete activation-input bindings are hard compile/validation failures.
- Chosen activation-request contract: activation requests are validated from compiled stage metadata plus canonical pointer-address inputs (`ptr/v1/...`) scoped by tenant/domain/partition; no hidden activation side state is permitted.
- Chosen bounded-stochastic rule for first-slice dispatch triage: deterministic ranking remains primary and optional LLM rationale is non-authoritative support only.

## 2026-03-04 (TASK-0057 workflow workspace projection + graph/actionability/demo bundle)
- Chosen workspace authority boundary: `GET /api/v1/workflow-runs/{workflow_run_id}/workspace` is a read-only derived projection over canonical run/task/approval/flag/artifact/pointer/event state; no second workflow-engine state path is introduced.
- Chosen graph posture for this slice: schedule-planning-specific minimal node set (Stage03 readiness through Stage07 delta publish) with explicit branch/loopback edges and canonically explainable statuses (`not_started`, `ready`, `in_progress`, `blocked`, `awaiting_approval`, `completed`, `warning`).
- Chosen actionability posture: workspace mutation affordances are server-computed (`available_actions`, `blocking_requirements`, `missing_required_inputs`) for tasks/approvals/flags; frontend does not infer completion or policy eligibility.
- Chosen information-request rule for workspace actionability: `information_request` tasks require at least one linked artifact before `complete` becomes available in workspace projection.
- Chosen Stage06 actionability rule: `run_stage06_agent_review` is exposed only when task scope/assignment and policy-role gate allow it.
- Chosen demo/export posture:
  - demo runner seeds canonical realistic state by delegating to the existing pilot runner/service and emits `workflow_run_id` plus recommended workspace URL,
  - export bundle is generated from canonical detail/workspace projections and includes mandatory JSON files + README summarizing scenario, graph status, first actions, upload-unblock signal, and OpenAI-path usage.

## 2026-03-04 (TASK-0058 frontend workspace page + live graph)
- Added a dedicated single-run workspace route `/runs/:workflowRunId/workspace` that keeps graph projection and actionable work in one polling query path.
- Chosen frontend contract boundary for this slice:
  - repository/API method `workflowRunsRepository.workspace(workflowRunId)` backed by `GET /api/v1/workflow-runs/{workflow_run_id}/workspace`,
  - workspace item actionability is driven by server fields `available_actions` and `missing_required_inputs`.
- Chosen graph rendering strategy: lightweight SVG + CSS components (`WorkflowGraph*`) with support for linear, branch, and loopback edges; no heavyweight graph library introduced.
- Chosen interaction model for workspace actions:
  - reuse existing task/approval/flag cards and attachment affordances,
  - keep detail depth in drawer,
  - render Stage06 AI action only when `run_stage06_agent_review` is present.
- Chosen refresh behavior: inline mutation success invalidates workspace and related queue/run queries so graph and actionable work stay visibly synchronized under polling.

## 2026-03-04 (TASK-0056 CI/hygiene stabilization + TASK-0031 status reconcile)
- Chosen hygiene posture: local editor/runtime/cache/build noise (`.DS_Store`, `.idea/`, `.tmp/`, `artifacts/`, frontend `node_modules`/`dist`, env/log cache files) is ignored and removed from Git index when previously tracked.
- Chosen CI posture: backend PR checks include `frontend-snapshots-check`; frontend PR checks run `npm ci`, typecheck, and non-watch frontend tests; OpenAI real-network tests remain gated in scheduled/dispatch workflow only.
- Historical note (superseded by 2026-03-08): at this date TASK-0031 was still tracked as TODO pending authored/runtime coherence harness delivery.

## 2026-03-04 (TASK-0055 stabilization pass 1 for frontend typecheck + snapshot determinism)
- Chosen path-sanitization rule for artifact ingress metadata: normalize separators to `/`, store repo-relative `fixtures/...` when the path includes `fixtures`, otherwise store only the file basename.
- Applied the same sanitization rule to `seed_source_path` metadata during ingress so scenario-backed snapshot exports cannot leak machine-local absolute paths.
- Added an explicit snapshot drift-check command target (`make frontend-snapshots-check`) and linked it into `make test` so deterministic snapshot enforcement is part of the primary CI/test gate.

## 2026-03-04 (TASK-0032 generator prototype for runbook + CompanyOS IR)
- Chosen prototype scope: generate only from repo-native Schedule Planning source (`WORKFLOW_CONTRACT`, `ARTIFACT_MAP`, `DECISION_CATALOG`, `EXECUTION_PROFILE`, `ACCEPTANCE_CRITERIA`) with no secondary authored semantics.
- Chosen output contract under `build/generated/`:
  - runbook markdown at `runbooks/schedule_planning.v1/runbook.md`,
  - CompanyOS-style IR JSON at `companyos_ir/schedule_planning.v1.json`,
  - lineage manifest at `lineage/schedule_planning.v1.lineage.json`.
- Chosen freshness strategy: deterministic runbook/IR render plus lineage source/output hash checks via `--check`; stale or drifted generated artifacts fail closed.
- Chosen no-invention guardrails in generator code:
  - reject unknown stage IDs, dataset keys, decision refs, evidence refs, and spawn-rule target stage IDs,
  - emit only authored IDs/keys into generated IR/runbook sections.
- Chosen CI integration posture: `make generated-check` now runs full repo validation plus generator `--check` freshness enforcement.

## 2026-03-04 (TASK-0030 artifact-store and schedule-delta design closure)
- Locked artifact-store authority boundary: canonical truth for artifacts is `artifact_versions` + `artifact_pointers` + `artifact_links` + timeline events; blob/object storage bytes remain non-authoritative payload storage.
- Locked Stage06/Stage07 schedule semantics:
  - Stage06 publishes immutable base schedule versions,
  - Stage07 publishes immutable ordered deltas and never mutates base artifacts in place,
  - operative live-day reconstruction is read-only from base pointer + ordered official Stage07 deltas.
- Locked ordered-delta lineage requirements: Stage07 deltas must carry explicit lineage (`supersedes_artifact_version_id`, `base_artifact_version_id`, `delta_sequence`) so reconstruction order/anomalies are auditable.
- Locked idempotency posture for artifact uploads/promotions: duplicate idempotency must not duplicate canonical effects; same-target promotion remains non-duplicating; pointer repoints require generation checks.
- Locked mismatch recovery rule: when blob bytes and canonical metadata disagree, metadata/events/pointers remain authoritative; remediation is new immutable version + explicit pointer move, never row mutation.
- Added explicit read-only reconstruction contract and named required helper surfaces/tests in `docs/planning/ARTIFACT_STORE_DESIGN.md` and `docs/planning/TEST_MATRIX.md`.

## 2026-03-04 (realistic Schedule Planning pilot + inspection packet milestone)
- Chosen pilot shape: three reproducible Schedule Planning scenarios (`stage06_publish_ready`, `stage06_needs_information`, `stage07_issue_replan`) executed through canonical handlers, seeded from the real corpus seed sets.
- Chosen Stage06 pilot execution posture: Stage06 review in pilot scenarios must use the bounded Stage06 agent path (`run_stage06_openai_review_sandbox`) so execution session/tool execution/policy decision rows and events are always part of the pilot truth.
- Chosen reproducibility/idempotency strategy for pilot runs: deterministic workflow/object IDs derived from `(pilot_key, pilot_id)` with run reuse on repeated pilot key invocation; repeat runs must not duplicate canonical side effects.
- Chosen inspection artifact contract: each pilot run exports `inspection_packet.json` and `inspection_packet.md` containing canonical IDs, lifecycle states, timeline events of interest, and suggested UI/API inspection routes.
- Chosen operator visibility rule: pilot packets are walkthrough artifacts only; authoritative truth remains canonical runtime rows/events/artifacts/pointers.

## 2026-03-04 (policy-gate state hardening and reconcile dedupe coverage)
- Chosen bounded Stage06 session posture: execution sessions now start in `WAITING_POLICY` and transition to `RUNNING` only after an explicit policy allow decision is persisted and emitted as authoritative evidence.
- Chosen policy-allow evidence rule: `evaluate_policy_decision` now emits `execution.session.state_changed` for allow transitions when session state changes (for example `WAITING_POLICY -> RUNNING`), not only for deny/require-approval branches.
- Chosen reconcile safety expectation: stale-session reconciliation may fail stale sessions, but it must not duplicate already-completed tool/evidence effects; runtime coverage now explicitly asserts no duplicate `tool.execution.completed` or `artifact.version.created` for completed tool outputs.

## 2026-03-04 (execution-session runtime and policy-gated sandbox hardening)
- Added canonical execution-runtime current-state tables: `execution_sessions`, `tool_executions`, and `policy_decisions`; execution truth is now persisted in runtime rows plus authoritative events, not implied by service-only side effects.
- Chosen Stage06 bounded execution ID strategy: deterministic IDs derived from `(workflow_run_id, task_run_id, base_idempotency_key)` for `execution_session_id`, `tool_execution_id`, and `policy_decision_id` to prevent duplicate canonical effects on replay.
- Chosen policy-gate rule for bounded Stage06 sandbox:
  - explicit policy decision is required before model execution,
  - default allows only trusted actor-role set (`dispatch_supervisor`, `operations_manager`, `system_worker`) or `system/service` actor types,
  - optional bounded override via request payload/env for testability (`allow|deny|require_approval`),
  - denied/require-approval paths fail closed with canonical denial evidence.
- Chosen failure mapping:
  - model/config/provider failures map to `tool_executions.state=FAILED` and `execution_sessions.state=FAILED` with emitted lifecycle events,
  - workflow-transition failure after a successful model call marks session failed without erasing already-canonical tool/evidence results.
- Chosen reconcile behavior for this slice: `maintenance reconcile-executions` marks stale open sessions and open tool requests as failed with visible timeout evidence, avoiding duplicate terminal effects on repeated runs.

## 2026-03-04 (example document corpus + canonical artifact ingress)
- Promoted template-pack completed examples into an executable corpus manifest at `fixtures/example_document_corpus/manifest.yaml`; fixture inputs are now stable by `fixture_id` and grouped by deterministic `seed_set_id`.
- Chosen corpus authority boundary: fixture files are test inputs only; authoritative truth remains canonical `artifact_versions` + `timeline_events` + audited pointers.
- Chosen ingress rule: example docs must enter through canonical artifact ingress (`artifacts ingest`, subject upload endpoints, or `artifacts seed-corpus`) with digest/byte-size metadata captured and `artifact.version.created` emitted in the same transaction.
- Added canonical `artifact_links` current-state table to represent attachment/linkage to `workflow_run`, `human_task`, `approval`, and `flag` subjects; no separate attachment truth subsystem is introduced.
- Chosen frontend inline attachment posture for v1: upload/download actions are inline on queue/board surfaces and delegate to canonical API endpoints; client stores no attachment workflow semantics.
- Chosen snapshot/corpus coupling rule: backend-owned frontend snapshots continue to be exported from real scenario-backed states seeded through canonical artifact ingress, not hand-authored mock documents.

## 2026-03-04 (bounded OpenAI Responses API Stage06 sandbox spike)
- Added a narrow OpenAI integration boundary under `src/onetruth/integrations/openai/` using the Responses API for new model work; no raw provider calls are scattered through handlers/routes.
- Locked the first real model-assisted use case to Stage06 `review_packet` outcome classification only, with strict structured output fields:
  - `outcome` in `{draft_is_publish_ready, review_requires_more_information, review_requests_changes}`
  - `rationale_summary`
  - `evidence_refs`
  - nullable schema-bound `suggested_follow_on_task_kind`
- Chosen canonical persistence path for model evidence: create immutable artifact versions (`artifact_kind=schedule.stage06.review_ai_evidence.json`) containing model metadata + input artifact refs; no log-only evidence path.
- Chosen workflow-authority rule for this spike: model output may select only existing canonical completion outcomes; follow-on truth still comes exclusively from existing `tasks.complete` completion/spawn handlers.
- Added bounded HTTP mutation endpoint `POST /api/v1/human-tasks/{human_task_id}/stage06-agent-review` with explicit scope checks and normalized config/provider error mapping.
- Added test strategy split:
  - always-on structural coverage (adapter schema/failure tests + runtime API sandbox path with mocked classifier),
  - gated real-network e2e slice under `tests/integration_openai/` requiring `ONETRUTH_RUN_OPENAI_E2E=1` and `OPENAI_API_KEY`.

## 2026-03-04 (frontend real API integration and board/list/detail hardening)
- Replaced frontend snapshot/mock repository reads with real HTTP adapters under `frontend/src/lib/api/` and repository implementations under `frontend/src/lib/repositories/`; frontend pages/components no longer read fixture files directly.
- Kept frontend presentation-only authority boundary: filters, drawer state, local selection, and visual affordances remain client-owned while workflow semantics and transition validity remain server-authoritative.
- Chosen frontend request-context model for dev/internal slice: Vite env-configured tenant/domain/actor headers (`VITE_ONETRUTH_*`) emitted by a centralized HTTP client.
- Chosen polling model: TanStack Query interval polling with explicit freshness indicator and query invalidation on successful mutations; no websocket/live-sync in this slice.
- Added thin API read routes `GET /api/v1/flags` and `GET /api/v1/timeline-events` plus runtime API contract tests so exceptions/timeline views stay API-backed rather than client-reconstructed mocks.
- Chosen frontend integration-test approach: contract-aligned MSW test server for `/api/v1` read/mutation surfaces, including claim/complete/respond round-trips and forbidden-response handling.

## 2026-03-04 (frontend snapshot fixtures for Stage06/Stage07)
- Added backend-owned frontend snapshot fixtures under `fixtures/frontend_contracts/` and made them derived from real Stage06/Stage07 scenario-backed runtime states, not hand-authored JSON.
- Chosen snapshot refresh workflow: `make frontend-snapshots` (runs `scripts/export_frontend_snapshots.py`) and deterministic drift check via `python3 scripts/export_frontend_snapshots.py --check`.
- Chosen snapshot stability approach: deterministic ID/timestamp tokenization during export so fixtures remain stable while preserving server-owned contract shapes and lane/state semantics.
- Added a contract guard (`tests/runtime/contracts/test_frontend_snapshot_fixtures.py`) that regenerates snapshots from runtime scenarios and asserts committed fixtures match.

## 2026-03-04 (first frontend shell + mock repository boundary)
- Chosen frontend stack for the first HITL UI slice: React + TypeScript + Vite + React Router + TanStack Query + Vitest/Testing Library.
- Chosen server-authoritative client posture: the frontend may manage only presentation state (filters, drawer visibility, selection, refresh affordances) and must not own workflow/task/approval/flag/pointer semantics.
- Chosen data-access seam: route pages consume repository interfaces (`humanTasksRepository`, `approvalsRepository`, `flagsRepository`, `workflowRunsRepository`, `pointersRepository`, `timelineRepository`, `boardRepository`) while fixture parsing remains centralized in `mockContractService`.
- Chosen interaction model lock for v1: explicit inline actions + inline attachment affordances + hidden-by-default descriptions with drawer-first detail; no drag-to-transition semantics.
- Chosen route surface for first operator workflows: `/board`, `/my-work`, `/approvals`, `/exceptions`, `/runs`, `/runs/:workflowRunId`, `/official-outputs`, `/timeline`.

## 2026-03-03 (Stage07 issue-scoped replan loop)
- Added canonical `flags` substrate with runtime states `open`, `triage`, `blocked`, `resolved`, `closed`, `waived`; transitions are enforced server-side and recorded via `flag.created` / `flag.state_changed`.
- Chosen Stage07 issue activation key and dedupe model: `(workflow_run_id, flag_id, task_kind, generation)`; duplicate wakeups/activation retries return existing canonical issue task instead of creating a second root issue task.
- Implemented Stage07 completion outcome mappings in the authoritative `tasks complete` transaction path:
  - `replan_requires_missing_information` -> Stage07 `information_request`
  - `resolution_creates_child_issue` -> Stage07 `exception_triage`
  - `major_replan_is_ready_for_review` -> Stage07 `final_review`
- Chosen major-replan approval gate: `pointers.promote` with `promotion_reason=official_major_replan` requires a canonical approved response and Stage07 approval scope; otherwise promotion fails closed.
- Chosen drift-detection rule for Stage07 promotion: compare `reviewed_base_artifact_version_id` against the current base pointer target (`base_pointer_key`, defaulting to `official:schedule.published_schedule.workbook`); emit `artifact.pointer.drift_detected` when stale, while allowing promotion.
- Chosen lease-expiry recovery behavior: reopen the same claimed human-task row (clear assignee/lease, increment reopen counters/version), emit `task.lease_expired`, and move task run `IN_PROGRESS -> READY` with `task.run.state_changed` evidence.
- Added Stage07 reconcile path to recover dropped wakeups by ensuring open flags have issue-root tasks via activation-key dedupe, without duplicating canonical root tasks.

## 2026-03-03 (HITL HTTP/query adapter + backlog reconciliation)
- Added the first thin HTTP adapter over canonical runtime/query surfaces under `src/onetruth/api/`; API routes delegate mutation semantics to existing canonical handlers (`claim_human_task_command`, `complete_human_task_command`, `respond_approval_command`) rather than reimplementing business lifecycle logic.
- Chosen board lane derivation rules for initial Schedule Planning board aggregate:
  - human tasks: `OPEN -> human_tasks.open`, `CLAIMED -> human_tasks.claimed`, `COMPLETED -> human_tasks.completed`
  - approvals: `PENDING -> approvals.pending`, `RESPONDED -> approvals.responded`
- Chosen board/query pagination strategy: offset/limit (`limit` default 100, max 500; `offset` default 0) for initial stable contracts.
- Chosen API auth-context approach for this internal/dev slice: explicit request headers `x-onetruth-tenant-id`, `x-onetruth-domain-id`, `x-onetruth-actor-id`, `x-onetruth-actor-type`, `x-onetruth-actor-roles` with mandatory server-side scope enforcement and no unscoped fallback.
- Chosen refresh model: polling-friendly stateless GET contracts first; websocket/live-sync intentionally deferred.
- Reconciled stale backlog status to match implemented runtime reality:
  - TASK-0029 moved to DONE (event emission matrix now implementation-backed in runtime handlers/tests)
  - TASK-0039 moved to DONE (scenario harness now implemented in fixtures/tests/docs)
  - TASK-0030 narrowed to remaining Stage07/base+delta artifact-store design work and moved to IN_PROGRESS.

## 2026-03-03 (Stage06 publish slice + scenario harness)
- Implemented the first narrow Schedule Planning Stage06 runtime behavior inside canonical `tasks complete`: parent completion can now create explicit child tasks in the same transaction with persisted lineage fields (`spawned_from_task_run_id`, `spawn_rule_id`, `spawn_cause_kind`, `spawn_cause_event_id`, `spawn_depth`, `spawn_budget_key`).
- Finalized first Stage06 completion outcome names in code:
  - `review_requires_more_information` -> child Stage06 `information_request`
  - `review_requests_changes` -> child Stage05 `work_item`
  - `draft_is_publish_ready` -> child Stage06 `final_review`
- Chosen retry behavior for parent completion replays remains explicit-failure idempotency: retrying the same completion command idempotency key fails with `duplicate_idempotency_key`, and no duplicate child task rows/events are emitted.
- Added implementation-backed Stage06 scenario fixtures and CLI-driven scenario harness tests; harness seeds synthetic template-pack completed examples into temp storage and registers canonical artifact versions before scenario steps.
- Query-contract stability approach is now test-backed via runtime contract tests that assert stable JSON row shapes for human task queue, approval queue, pointer summary, and workflow run summary surfaces.

## 2026-03-03 (approvals + artifact versions + pointer promotions substrate)
- Added canonical substrate tables for `approvals`, `artifact_versions`, and `artifact_pointers` with matching migration and SQLite bootstrap DDL support.
- Chosen minimal approval state set in the first implementation:
  - `PENDING`
  - `RESPONDED`
- Approval responses are single-finalization: only `PENDING -> RESPONDED` is allowed, and duplicate/conflicting second responses are rejected (`approval_not_respondable`).
- Chosen artifact-version idempotency behavior: `artifacts create-version` requires non-empty command `idempotency_key`; duplicate keys fail explicitly (`duplicate_idempotency_key`) with no duplicate canonical row and no duplicate `artifact.version.created` event.
- Chosen pointer conflict/race behavior:
  - first promotion wins for an uninitialized pointer key,
  - conflicting promotion without `expected_generation` fails closed (`pointer_conflict`),
  - repoint requires optimistic generation match (`pointer_generation_mismatch` on mismatch).
- Chosen minimal pointer policy gate: `promotion_reason=official_publish` requires `approved_by_approval_id` bound to a `RESPONDED` approval with `response_kind=approve`; otherwise promotion fails closed.
- Added stable CLI list/show read surfaces (`runs/tasks/approvals/artifacts/pointers`) and documented them as HITL query contracts to unblock parallel board/UI work without introducing a second truth path.

## 2026-03-03 (workflow/task core substrate + transactional lifecycle events)
- Added canonical current-state tables for the first workflow/task substrate slice: `workflow_runs`, `task_runs`, and `human_tasks` (with lineage-ready spawn fields on `task_runs`).
- Chosen minimal first-implementation states:
  - `workflow_runs`: `OPEN`, `COMPLETED`
  - `task_runs`: `READY`, `IN_PROGRESS`, `COMPLETED`
  - `human_tasks`: `OPEN`, `CLAIMED`, `COMPLETED`
- Lifecycle commands now commit canonical row changes and authoritative event appends in the same transaction for:
  - `runs create`
  - `tasks create`
  - `tasks claim`
  - `tasks complete`
- Claim and complete command idempotency keys are required and duplicate keys fail explicitly (`duplicate_idempotency_key`) with no duplicate canonical effect and no duplicate emitted lifecycle events.
- Completion flow is explicitly structured to support future same-transaction child task emission (`task.run.created`, `task.created`) without introducing a second truth path; full spawn-evaluator semantics remain out of scope for this slice.

## 2026-03-03 (runtime scaffold command boundary + smoke substrate)
- Added the first concrete runtime scaffold under `src/onetruth/`, `alembic/`, and `tests/runtime/` as TASK-0040.
- Established the first stable runtime CLI command boundary: `init-db`, `events append --json`, and `events list --json`.
- Chose explicit idempotency behavior for timeline append in this scaffold: duplicate `idempotency_key` fails with a machine-parseable error (`duplicate_idempotency_key`); no silent dedupe path is used.
- Local smoke tests use SQLite by default and initialize substrate tables through Alembic when available, with a SQLite bootstrap fallback when Alembic/SQLAlchemy are unavailable in constrained environments. PostgreSQL remains the primary target architecture.

## 2026-03-03 (conditional task spawning and step-run test planning)
- Stage 4 now explicitly allows **conditional follow-on task spawning**: completing a task may create one or more child task runs for information requests, re-review, final review, or issue-scoped child work.
- Child-task creation must stay inside the same workflow run and remain explicit through `task.run.created` / `task.created`; no new hidden side-effect path or separate `task.spawned` truth system is introduced.
- The first runtime implementation should create deterministically implied child tasks in the same transaction as the parent completion or approval response, reserving the decider/reconciler for timers, flags, and repair.
- Added `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` and TASK-0039 so future runtime work must include step-run tests where an agent executes each step and the test asserts authoritative truth.
- The workflow `template_pack/` folders already contain synthetic completed example artifacts and are now the planned seed inputs for runtime scenario tests; the validator now checks that both empty templates and completed examples exist.

## 2026-03-03 (runtime bootstrap locked for development)
- Stage 4 runtime will start as a **Python modular monolith** under `src/onetruth/`, not as an external workflow engine and not as early microservices.
- The canonical persistence substrate is **PostgreSQL current-state tables + append-only `timeline_events`**, with immutable artifact blobs stored behind a pluggable object-store adapter.
- `timeline_events` will also serve as the **outbox substrate** for derived consumers; wakeups may use notifications/polling, but consumer truth is a cursor over the canonical timeline.
- The first code slice is **core substrate + Schedule Planning Stage06 publish path**, followed by the Stage07 issue-scoped replan loop.
- `docs/planning/RUNTIME_BOOTSTRAP.md` and `docs/planning/FIRST_RUNTIME_SLICE.md` are now the authoritative implementation-architecture entrypoints for fresh-session Codex work.
- Completed TASK-0028 and refreshed stale routing/context so default runtime work no longer incorrectly points fresh agents to Payroll traces.

## 2026-03-03 (test-first harness adoption)
- Adopted a pytest-backed Stage 4 TDD harness rooted in schemas, golden traces, and acceptance scenario oracles rather than prose-only guidance.
- Added `docs/planning/TDD_IMPLEMENTATION_PLAN.md` so fresh-session Codex runs can start from a stable test-first workflow.
- Added a non-authoritative reference replay reducer and stable `AT-SCH-001` .. `AT-SCH-007` scenario catalog under `tests/helpers/` to make the existing traces executable.
- Added a dedicated `schedule_policy_gate_enforced.jsonl` trace so AT-SCH-007 (sandbox/policy gate) now has first-class trace coverage.
- Default verification flow for runtime work is now `make schema-validate`, `make contract`, `make replay`, `make acceptance`, then implementation-specific suites.

## 2026-03-02 (semantic closure before runtime planning)
- Added a shared governance vocabulary and machine-readable registry for actor taxonomy, approval response verbs, approval outcomes, and approval permission actions.
- Canonical actor taxonomy is now `human | agent | service | system`; stale `user` actor types were removed from authoritative schemas.
- Canonical approval permission actions are now `approval.request` and `approval.respond`; stale `approval.grant` wording was removed.
- Schedule Planning now carries explicit temporal partition semantics: service interval, logical date, timezone, catchup policy, backfill policy, and stage-rerun policy.
- Workflow contracts now distinguish `event_inventory.platform_required` from `event_inventory.workflow_required` so runtime/task/execution events are no longer implicit.
- Added a tool-class registry, workflow-pack schemas, runtime object schemas, event payload schemas, and a concrete sandbox policy schema.
- Added a repo validation harness (`scripts/validate_repo.py`) and Makefile targets so a fresh agent can validate contracts and traces before starting runtime work.
- Added Schedule Planning golden traces for happy path, fully-agentive whole flow, drift after review, lease expiry recovery, degraded mode survivability, and cross-scope denial.

## 2026-03-02 (schedule-first Stage 4 pivot)
- Stage 4 now treats `schedule_planning.v1` as the primary runtime/debug wedge.
- The primary Stage 4 acceptance objective is a fully-agentive Schedule Planning flow where designated agent principals can execute every in-scope task while preserving the same canonical task, approval, event, and pointer substrate.
- This fully-agentive objective is a debugging and validation posture, not permission to create a second agent-only truth system.
- Payroll remains in Stage 4 as the secondary reference workflow used to validate the shared substrate against a linear approval-heavy path.
- Added `docs/workflows/payroll/v1/OPERATING_MODEL.md` so both workflow packs now expose the full authored surface declared by the authority model.

## 2026-02-28
- Added `schedule_planning.v1` as a second Stage 4 workflow contract pack for a same-day delivery operator; at that point Payroll remained the primary implementation slice (later superseded by the 2026-03-02 schedule-first pivot).
- Schedule Planning is partitioned by `ScheduleDateID` (`SD-YYYY-MM-DD`) and uses the same `(tenant_id, domain_id)` scoping model as Payroll.
- Published schedules are treated as stable base plans; live-day changes must be recorded as new artifact versions / replan deltas rather than silent edits.
- Availability artifacts for scheduling may store coded leave/absence types, but must not store medical or disciplinary detail.

## 2026-02-28 (merger update)
- The repo now explicitly adopts one truth system: immutable objects + append-only events + audited pointers.
- The CompanyOS packet is preserved as philosophy, mathematics, threat model, and lowering target, not as a second authored workflow-definition system.
- Per-workflow authored semantics now include two repo-native execution-overlay files: `DECISION_CATALOG.yaml` and `EXECUTION_PROFILE.yaml`.
- Generated runbook packs, tool matrices, approval logs, and CompanyOS IR are treated as generated derivatives, not authoritative source.
- Business execution and agentic execution will share one event system, one approval model, and one run model.
