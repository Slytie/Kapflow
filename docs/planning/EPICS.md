# EPICS.md - Stage 4 work breakdown

Current runtime/debug priority: **Schedule Planning**. Payroll remains the secondary reference workflow.

## Epic list (recommended order)

| Epic ID | Title | Primary artifacts | Depends on |
|---|---|---|---|
| EPIC-000 | Payroll workflow contract v1 (freeze) | S4-A01, S4-A07 | - |
| EPIC-005 | Schedule Planning workflow contract v1 + operating model (freeze) | S4-A08 | EPIC-000 |
| EPIC-015 | One truth system + authority model + vision preservation | S4-A09 | EPIC-000, EPIC-005 |
| EPIC-025 | Canonical execution overlay + generated derivative policy | S4-A10, S4-A11 | EPIC-015 |
| EPIC-010 | Scope model + AuthZ + Isolation harness | S4-A01, S4-A02, S4-A07 | EPIC-015 |
| EPIC-020 | Authoritative TimelineEvent + Outbox + Degraded mode | S4-A04 | EPIC-010, EPIC-015 |
| EPIC-030 | Artifact store + Promotion pointers + Drift visibility | S4-A03 | EPIC-020, EPIC-015 |
| EPIC-040 | Orchestrator core (runs pinned, WAIT, bounded exception handling) | S4-A01 | EPIC-020, EPIC-025, EPIC-030 |
| EPIC-050 | Human task queue (assignment, claim lease, SLA timer) | S4-A02 | EPIC-010, EPIC-020 |
| EPIC-060 | Approvals + Policy enforcement (server-side) | S4-A01 | EPIC-050, EPIC-025, EPIC-030 |
| EPIC-070 | Automation sandbox baseline (tool execution gating) | S4-A01 | EPIC-060, EPIC-025 |
| EPIC-080 | Ops readiness (CI/CD, dashboards, runbooks, generated checks) | S4-A05, S4-A06 | EPIC-020, EPIC-025 |
| EPIC-090 | Acceptance suite + golden traces (happy path + negatives) | S4-A07 | EPIC-000..080 |
| EPIC-100 | Production perimeter + substrate + release-mediated promotion discipline | viewer/bootstrap, deploy/runbook reference, production/lab topology | EPIC-010, EPIC-080 |
| EPIC-110 | Workflow Lab (thin, non-authoritative candidate-evaluation lane) | docs/schemas/normalizers for lab evidence and gated later execution adapters | EPIC-025, EPIC-080, EPIC-100 |
| EPIC-120 | Logistics workpages v0 (weekly schedule review + EOD draft/review, query-backed surfaces) | workpage plan/product brief, example source fixtures, initial full-page FE routes, backend workpage query contracts/snapshots | EPIC-025, EPIC-080 |
| EPIC-121 | First artifact-backed workpage slice (EOD draft/review on immutable workbook artifacts) | artifact-backed EOD brief/plan, dispatch-reporting template pack + registry support, EOD draft/projection/submit routes, artifact-backed FE page/lineage UX | EPIC-120, EPIC-030 |
| EPIC-122 | Workflow-run-backed workpages (canonical run-backed schedule review + EOD draft resolution) | run-surfaces brief/plan, workflow-run-backed workpage route family, run-backed schedule/EOD contracts, frontend `/runs/:workflowRunId/workpages/*` routes, demo/story drilldown entrypoints | EPIC-120, EPIC-121, EPIC-080 |
| EPIC-123 | Schedule draft artifact-backed workpages (Stage04 draft weekly schedule workbook lane) | schedule-artifact-path brief/plan, Stage04 draft workbook authority freeze, schedule artifact projection/submit over the generic artifact-backed workpage family, backend-owned snapshots, and canonical frontend schedule artifact route/page | EPIC-120, EPIC-122, EPIC-030 |
| EPIC-124 | Stage-linked workpages and requirement-aware artifact linkage | stage-linked workpage brief/plan, workspace `workpage_actions[]` contract freeze, relation-kind-aware subject-link semantics, backend action projection/snapshots, and frontend stage-linked CTA integration | EPIC-122, EPIC-123, EPIC-050, EPIC-060, EPIC-030 |
| EPIC-125 | Operational cadence demo (weekly planning + minimal daily replan + daily reporting first-user lane) | operational-cadence executive summary/plan, external cadence tick, weekly Friday intake + Stage04 build/review/publish loop, minimal manual live-dispatch delta loop, daily EOS->draft-review-finalize loop, local demo runbook, single-node production-shaped demo runbook | EPIC-124, EPIC-121, EPIC-122, EPIC-123, EPIC-030, EPIC-040, EPIC-100 |
| EPIC-131 | Schedule heatmap recalculation, route-demand separation, and versioned workpage navigation | EPIC-131 brief/plan/context pack, corrected SME boundary freeze, descriptor-backed calculated schedule contracts, route-demand/editor separation, accepted-series navigation, soft preferences | EPIC-123, EPIC-124, EPIC-125, EPIC-030 |
| EPIC-126 | Workpages v1 hardening and closeout | internal cleanup, canonical-route regression proof, fixture pruning, active-doc closeout, explicit Workpages v1 boundary and acceptance proof | EPIC-125, EPIC-131, EPIC-124, EPIC-100 |
| EPIC-132 | Workpage reliability settlement and repo-truth closeout | settlement plan/context packs, clean-baseline reconciliation, mutation smoke gate, canonical-only docs/fixtures truth, reproducible frontend verification | EPIC-131, EPIC-124, EPIC-100 |
| EPIC-133 | Workpage fragility reduction and extensibility hardening | backend-owned lineage/latest-draft/history seams, server-authored workpage actions, launcher-only demo-shell convergence, bounded-facade/source-budget guardrails | EPIC-132, EPIC-131, EPIC-124, EPIC-100 |
| EPIC-134 | Minimal canonical workpage demo enablement | demo-enablement plan/context packs, supported-env reporting/demo-smoke truth correction, deterministic workpage demo-prep script, canonical demo runbook/regression | EPIC-125, EPIC-131, EPIC-133 |
| EPIC-135 | Unified schedule replan popup and dynamic scheduling activation | unified replan plan/context packs, shared popup proposal/runtime-status contract, mirrored weekly/live contact bridge inputs, refresh-path replacement, weekly/live replan adapters, authored live-dispatch runtime surface, popup redesign, demo truth refresh | EPIC-125, EPIC-131, EPIC-133, EPIC-134, EPIC-070 |

Status note (2026-04-25): EPIC-131, EPIC-132, EPIC-133, and EPIC-134 are complete, the public workpage posture is canonical-only, and EPIC-135 is now the selected next app-facing product-expansion tranche.

| EPIC-136 | CAPEX intake, provenance, and source freeze | CAPEX intake, conversion map, gate/risk/decision map | EPIC-080 |
| EPIC-137 | CAPEX activation blockers and platform readiness | storage safety, transaction safety, invariant audit, readiness closeouts | EPIC-136, EPIC-080, EPIC-100 |
| EPIC-138 | CAPEX production/lab separation and deploy readiness | deploy gates, backup/restore evidence, branch rules | EPIC-137, EPIC-100 |
| EPIC-139 | CAPEX domain-boundary cleanup | domain manifests, approval side-effect cleanup, workpage descriptor registry | EPIC-137 |
| EPIC-140 | CAPEX project access and membership | project schema decisions, direct memberships, project child APIs, selector/dashboard scope, domain manifests | EPIC-137, EPIC-139 |
| EPIC-141 | CAPEX source occurrence and evidence | source occurrence register, extraction state, evidence refs | EPIC-140 |
| EPIC-142 | CAPEX artifact promotion and governance | artifact envelopes, promotion validators, closure and waiver models | EPIC-141 |
| EPIC-143 | CAPEX workflow catalog | workflow contracts, operating models, acceptance matrices | EPIC-140, EPIC-142 |
| EPIC-144 | CAPEX workpages and projections | workpage contracts, projections, projection consistency tests | EPIC-142, EPIC-143 |
| EPIC-145 | CAPEX K12/K3 fixture governance | fixture manifests, redaction policy, K12/K3 expected outputs | EPIC-141 |
| EPIC-146 | CAPEX three-project validation | three-project governance, validation protocol, fixture tiering | EPIC-145 |
| EPIC-147 | CAPEX blind/lab evaluation | blind baseline protocol, eval matrix, no-overfitting checkpoint | EPIC-146, EPIC-110 |
| EPIC-148 | CAPEX off-repo full-corpus runs | off-repo runbook, capacity and restore evidence, quarantine rules | EPIC-145, EPIC-138 |
| EPIC-149 | CAPEX QA/TDD and semantic tests | test catalog, semantic suites, TDD metrics | EPIC-141, EPIC-142, EPIC-143, EPIC-144 |
| EPIC-150 | CAPEX release governance | branch manifests, release gates, code review policy | EPIC-137, EPIC-149 |
| EPIC-151 | CAPEX transparency and snapshots | snapshot schemas, risk signal contracts, external observation queues | EPIC-142, EPIC-144 |
| EPIC-152 | CAPEX production preflight | production preflight memo, gate evidence, go/no-go record | EPIC-137, EPIC-146, EPIC-148, EPIC-150 |
## Update rules
- Keep epic files in `docs/planning/epics/`
- Keep task briefs in `codex/tasks/`
- If an epic changes the authority chain, update `AUTHORITY_MODEL.md`
- If an epic defers something subtle, record it in `MERGER_BACKLOG.md`
- Keep epic-specific pattern guidance and context-pack links current when architecture references change
