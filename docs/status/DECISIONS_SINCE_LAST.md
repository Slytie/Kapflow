# DECISIONS_SINCE_LAST.md

Record any decisions made since the last session so a fresh Codex run can rehydrate quickly.

## 2026-03-26 (TASK-0138 workflow-run-backed schedule route and snapshot)
- Route implementation decision: the first canonical EPIC-122 backend surface is now live at `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0`; the existing demo schedule route remains in place as a curated alias/input surface until the frontend migration tranche.
- Projection-source decision: the run-backed schedule workpage now builds from the latest canonical Stage04 run artifacts on a real `weekly_schedule_planning.v1` workflow run (`planning.route_slot_requirements.workbook`, `planning.driver_capabilities.workbook`, optional `planning.approved_availability.workbook`, optional `planning.actual_hours_snapshot.workbook`) rather than serving a planning fixture verbatim or depending on the logistics story summary.
- Composite-contract decision: the run-backed schedule response uses `source.mode=run_projection`, keeps `source.primary_dataset_key=null`, keeps both `source_artifact_version_id` fields null, exposes `run_context`, leaves `draft_resolution=null`, and uses `freshness.source_kind=workflow_run_projection` plus `freshness.source_version=bundle.bundle_id` so local UI what-if state only resets when canonical source artifacts change.
- Failure-posture decision: unsupported workpage kinds and non-weekly workflow families fail closed as `404 workpage_not_found`, while weekly runs missing required Stage04 inputs now fail cleanly as `409 workpage_projection_unavailable` with explicit missing dataset keys instead of silently falling back to demo defaults.
- Snapshot decision: backend-owned frontend contract fixtures now include `fixtures/frontend_contracts/workpage_schedule_v0_run_state.json`, generated from a real seeded weekly run over canonical Stage04 artifact truth.

## 2026-03-26 (TASK-0137 workflow-run-backed workpage contract, alias posture, and draft-resolution freeze)
- Next-epic decision: after the first artifact-backed EOD slice closed through `TASK-0136`, the next workpage epic is **EPIC-122 workflow-run-backed workpages**, not schedule write-path work, not deeper EOD finalization, and not broader workspace/task modernization.
- Route-family decision: the canonical backend run-backed family is `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}` plus `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`; the existing artifact-backed EOD read/submit routes remain unchanged.
- Frontend-route decision: the canonical frontend posture is `/runs/:workflowRunId/workpages/schedule-v0`, `/runs/:workflowRunId/workpages/eod-v0`, and `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`, with `/demo/logistics/workpages/*` retained as curated aliases until the canonical routes are proven.
- Contract decision: run-backed workpages keep the existing body/source/freshness contract and add optional `run_context`; only the run-backed EOD landing adds `draft_resolution`, and `artifact_context` remains reserved for artifact-projection responses.
- Scope decision: schedule stays query-backed/composite, the EOD run-backed landing stays distinct from artifact-backed editing, this epic does not add a generic `actions` blob, and final-packet/approval semantics remain out of scope.

## 2026-03-25 (TASK-0136 demo entrypoints, recent draft history, and EPIC-121 close-out)
- Demo-shell entrypoint decision: `/demo/logistics` now exposes `Open EOD preview` and `Create editable EOD draft` in the existing backend-demo-workpages header group; the dispatch-reporting family-node detail card remains a separate reporting/story surface and does not claim that it is already the same artifact-draft lane.
- Landing-page decision: `/demo/logistics/workpages/eod-v0` remains preview/create-only. We still do not invent frontend-local "open latest draft" discovery there without canonical run truth.
- History-surface decision: the artifact-backed EOD page now reuses `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts` for recent-version discovery, with the frontend filtering to `reporting.upd_draft.workbook` plus `demo_workpage_id=eod-v0` when metadata is present, rather than adding a new history route or client-only version list.
- Artifact-list decision: `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts` must surface the canonical EOD draft chain for the bounded demo run so the recent-version panel reads authoritative workflow-run/artifact truth instead of older subject-attachment-only data.
- Epic-closure decision: EPIC-121's first bounded slice is now complete. The next decision should be framed as a new epic choice (deeper dispatch-reporting/workspace integration versus a future schedule artifact boundary), not as hidden widening inside this slice.

## 2026-03-25 (TASK-0135 frontend EOD artifact route migration)
- Route-posture decision: `/demo/logistics/workpages/eod-v0` remains the query-backed EOD landing page, but it is now preview-only with an explicit create-draft affordance; active EOD edits now live only on `/demo/logistics/workpages/eod-v0/artifacts/{artifact_version_id}`.
- Frontend-contract decision: the frontend workpage contract now preserves optional `artifact_context` so the same page composition can render both query-backed landing payloads and artifact-backed EOD state without inventing a second local schema.
- Mutation decision: draft creation and artifact submit now flow through dedicated frontend repository methods with generated idempotency keys, and successful create/submit navigation follows the backend-owned `route` field rather than reconstructing client-side paths.
- Conflict-handling decision: `workpage_artifact_conflict` now preserves current local edits in memory, surfaces an inline reopen panel, and avoids client-side merge/rebase logic in this tranche.
- Lineage/download decision: the first artifact-backed EOD page exposes only bounded lineage truth from `artifact_context` plus workbook download through the existing artifact binary route; richer recent-history discovery remains deferred to `TASK-0136`.

## 2026-03-25 (TASK-0134 backend EOD artifact draft/create/read/submit slice)
- Route-surface decision: the first artifact-backed EOD slice now exists as `POST /api/v1/workpages/demo/eod-v0/drafts`, `GET /api/v1/workpages/artifacts/{artifact_version_id}`, and `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`, while the existing query-backed `GET /api/v1/workpages/demo/eod-v0` landing page remains in place until the frontend migration tranche.
- Canonical-run decision: demo EOD draft creation now resolves or creates exactly one bounded `dispatch_reporting.v1` run for the known `SD-2026-03-16` demo slice using activation key `dispatch_reporting.v1:SD-2026-03-16:eod-v0:artifact-draft`; the backend does not invent a runless workbook lane.
- Artifact-truth decision: the first draft is seeded from `dispatch_reporting.stage03.upd_draft.workbook.empty.v1` and persisted as a normal immutable `artifact_version` with truthful metadata for template provenance, demo workpage scope, service date, station, DSP, and workbook file naming.
- Projection decision: artifact-backed EOD reads keep the existing wrapper and section/field ids stable for the frontend, but authoritative freshness now comes from `artifact_version` lineage and `source.mode=artifact_projection` rather than the older query-only seam.
- Submit decision: EOD submit now creates a new immutable superseding workbook artifact version, maps only bounded UI-backed edits into `ManualCloseout` and `UpdCandidates`, appends a server-managed changelog row, and fails closed with `409 workpage_artifact_conflict` when the base artifact already has a newer descendant.
- Snapshot decision: backend-owned frontend contract fixtures now include committed create/read/submit snapshots for the artifact-backed EOD slice so `TASK-0135` can switch the UI over without inventing frontend-local artifact payloads.

## 2026-03-25 (TASK-0133 reporting template pack, multi-registry support, and EOD workbook adapter)
- Template-pack decision: `dispatch_reporting.v1` now has a real repo-native `template_pack/` tree with a bounded Stage03 `reporting.upd_draft.workbook` workbook pair plus inert authored placeholders for the remaining dispatch-reporting `ARTIFACT_MAP` template paths so assurance can stay honest.
- Registry decision: template discovery is now multi-workflow and deterministic across `fixtures/workflows/*/template_registry.v1.yaml`, while `template_id` uniqueness is enforced across the full catalog and schedule consumers continue to pin `workflow_id="schedule_planning.v1"` explicitly.
- API-surface decision: `GET /api/v1/templates` now reports `registries[]` for the matching workflow packs and only populates singular `registry` metadata when the filtered response resolves to exactly one workflow registry.
- Workbook-seam decision: the first real workbook adapter remains workflow-specific and bounded to `dispatch_reporting.v1` Stage03 semantics; it projects workbook bytes into the EOD semantic tables and materializes explicit edits back to new workbook bytes without becoming a generic editor runtime.
- Dependency decision: `openpyxl` is now a core runtime dependency for the first truthful `.xlsx` round-trip seam, but imports stay isolated to the dispatch-reporting workbook adapter module so package-root lazy imports do not regress.

## 2026-03-25 (TASK-0132 artifact-backed EOD contract and route-family freeze)
- Epic-boundary decision: after the query-backed `EPIC-120` tranche, the next workpage tranche is the **first artifact-backed vertical slice**, not more query/demo polish.
- First-write-path decision: the first artifact-backed workpage is **EOD only**, aligned to `dispatch_reporting.v1` Stage03 draft/review semantics (`reporting.upd_draft.workbook`).
- Route-family decision: keep the existing demo query routes, add `POST /api/v1/workpages/demo/eod-v0/drafts`, `GET /api/v1/workpages/artifacts/{artifact_version_id}`, and `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`, and keep workflow-run-backed workpages reserved for later.
- Canonical-anchoring decision: do **not** invent runless demo artifacts. The first EOD drafts must live inside a canonical `dispatch_reporting.v1` workflow run, even if that run is resolved or created by a deterministic demo helper for the known service-date example.
- Save-semantics decision: explicit submit/save creates a new immutable artifact version that `supersedes` the prior workbook version. No in-place workbook mutation and no per-keystroke autosave into `artifact_versions`.
- Schedule-boundary decision: the schedule page remains **query-backed and composite** in this epic; do not force schedule into a single-artifact write model yet.
- Template-registry decision: the repo currently has template-pack/registry support concentrated on `schedule_planning.v1`; `TASK-0133` is now the next tranche because this epic needs a bounded `dispatch_reporting.v1` template pack and enough multi-workflow registry support to instantiate `reporting.upd_draft.workbook` truthfully.
- Workflow-integration decision: this epic stops at the first artifact-backed EOD slice and demo-shell entrypoints. Human-task/workspace integration is a later epic unless a bounded existing dispatch-reporting lane already supports it without broadening scope.

## 2026-03-25 (TASK-0131 HTTP-backed frontend workpage migration and local freshness)
- Frontend data-seam decision: the active `/demo/logistics/workpages/schedule-v0` and `/demo/logistics/workpages/eod-v0` routes now read backend demo query contracts through `onetruthApi.getDemoWorkpage()` and `workpagesRepository.schedule()` / `workpagesRepository.eod()` instead of frontend-local example adapters.
- Wrapper-visibility decision: the frontend now keeps the backend workpage wrapper visible instead of stripping it to the inner `WorkpageViewModel`; workpage pages render local `source` / `freshness` metadata because `AppShell` intentionally hides the global shell freshness banner on `/demo/logistics/*`.
- Local-state decision: workpage form/checklist edits remain local-only and are now reset only when the meaningful base contract identity changes; `freshness.generated_at` alone must not wipe local edits during refresh.
- Test-fixture decision: frontend MSW workpage handlers now serve the committed backend-owned snapshots from `fixtures/frontend_contracts/`, not hand-built inline workpage payloads.

## 2026-03-25 (TASK-0130 EOD demo workpage query route and snapshot)
- Query-surface decision: `GET /api/v1/workpages/demo/eod-v0` now exists as the second implemented backend-owned workpage route, reusing the shared `workpages.demo.detail` family instead of introducing a new EOD-specific route seam.
- Source-build decision: the EOD workpage payload is built from the consistent partial 2026-03-16 QDCI/DVC4 dispatch-reporting example family, not by serving `fixtures/logistics/workpages/eod_report_workpage_v0_view_model_example.yaml`.
- Partial-honesty decision: because the sanctioned EOD source family is intentionally partial, the backend contract now surfaces source-derived partial totals plus formula-integrity warnings instead of carrying the fixture's older full-day summary numbers into the authoritative query surface.
- Snapshot decision: `fixtures/frontend_contracts/workpage_eod_v0_state.json` is now a committed backend-generated contract fixture produced through the shared frontend snapshot export/check path.

## 2026-03-25 (TASK-0129 schedule demo workpage query route and snapshot)
- Query-surface decision: `GET /api/v1/workpages/demo/schedule-v0` is now the first implemented backend-owned workpage route, and it remains a read-only derived surface with request-context enforcement but no DB dependency.
- Compatibility decision: the wrapped inner workpage object still keeps `mode=example` and `dataset_key=planning.input_bundle.doc` for the current frontend `WorkpageViewModel` seam, while authoritative query semantics live in the top-level `source` and `freshness` wrapper.
- Source-build decision: the schedule workpage payload is built from the actual-ops weekly Stage04 normalized example pack through the existing schedule-control bundle builder, not by serving `fixtures/logistics/workpages/schedule_workpage_v0_view_model_example.yaml`.
- Snapshot decision: `fixtures/frontend_contracts/workpage_schedule_v0_state.json` is now a committed backend-generated contract fixture produced through the shared frontend snapshot export/check path.

## 2026-03-25 (TASK-0128 workpage query contract and snapshot policy freeze)
- Phase-boundary decision: once the frontend-only workpage tranche was complete, the next batch moved to **server-authoritative query contracts** before any submit/materialize path.
- Route-family decision: the workpage API family now reserves separate subfamilies for `demo`, `artifacts`, and potentially `workflow-runs` because the schedule page is composite and may later be run-oriented while EOD is the better first artifact-backed candidate.
- Composite-source decision: the shared workpage contract must support `primary_dataset_key` plus `source_dataset_keys[]`; a single `dataset_key` is not rich enough for the schedule page.
- Snapshot-policy decision: once backend workpage demo routes exist, their generated contract fixtures belong in `fixtures/frontend_contracts/` because they are backend-owned API snapshots, while the human-authored workpage YAML fixtures remain planning/oracle artifacts under `fixtures/logistics/workpages/`.
- Future-artifact decision: the first artifact-backed workpage should be **EOD**, not schedule, because `dispatch_reporting.v1` has the cleaner single-packet/workbook fit and the schedule page is intentionally composite.

## 2026-03-25 (EPIC-120 logistics workpages v0 implementation)
- Workpage-seam decision: the first workpage contract is an example-backed frontend `WorkpageViewModel` + `workpagesRepository`, not a fake `/api/v1/workpages/*` server contract.
- Route-structure decision: workpages are sibling full-page routes under `AppShell`, and logistics-shell behavior now treats `/demo/logistics/*` as logistics routes rather than matching only the exact `/demo/logistics` path.
- Discovery decision: primary navigation stays unchanged; workpage discoverability comes from the primary `/demo/logistics` shell and preserved logistics secondary-nav treatment across the `/demo/logistics/*` prefix.
- Schedule-boundary decision: the first schedule workpage remains a **weekly planning review + selected-day preview** surface. Any day-of controls in v0 are local what-if inputs only; day-of replan remains owned by `live_dispatch.v1`.
- EOD-boundary decision: the first end-of-day workpage is aligned to **dispatch-reporting draft/review semantics** and anchors to `reporting.upd_draft.workbook`, not `reporting.final_packet.workbook`.
- Fixture-consistency decision: the repo now carries a single partial 2026-03-16 QDCI/DVC4 reporting example family so the EOD prototype no longer mixes one source day's summary with another source day's route rows.
- Fixture-class decision: workpage fixtures remain human-authored planning/test artifacts under `fixtures/logistics/workpages/` and stay distinct from backend-owned generated `fixtures/frontend_contracts/` snapshots.

## 2026-03-17 (next package planning: productization lane + Workflow Lab lane)
- Planning decision: the next package is split into a leading **production lane** (`EPIC-100`) and a thinner **Workflow Lab lane** (`EPIC-110`) instead of treating productionization and experimentation as one blended platform task.
- Promotion decision: until explicit multi-version coexistence is proven, the default promotion model remains `lab evidence + review + tagged release -> production deploy`, not direct runtime transfer of candidate workflows into production.
- Lab-boundary decision: Workflow Lab Phase 0/1 may start now as docs/schemas/normalization over existing outputs, but heavier execution/comparison work is gated on explicit readiness checks (`G1`, `G2`) recorded in `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`.

## 2026-03-17 (TASK-0110 runtime dependency honesty and lazy package boundaries)
- Dependency-honesty decision: `PyYAML` is a core runtime dependency because repo-authoritative YAML is read by runtime modules under `src/onetruth/`; it must not be hidden behind the `dev` extra.
- Package-boundary decision: bare imports of `onetruth.infrastructure.definitions`, `onetruth.infrastructure.generation`, and `onetruth.integrations.openai` now stay lazy and load their heavy YAML-backed submodules only when exported symbols are actually accessed.
- Workflow Lab prerequisite decision: future thin lab/runtime surfaces should inherit this honest baseline rather than relying on transitive hidden dependencies from package-root imports.

## 2026-03-17 (TASK-0111 server-derived viewer bootstrap and shared-env frontend identity migration)
- Viewer-bootstrap decision: `GET /api/v1/viewer` is now the one read-only backend contract for frontend viewer/bootstrap state, derived directly from the resolved request context plus the frozen API boundary profile.
- Frontend-identity decision: browser-set `x-onetruth-*` identity headers remain available only for `local_dev` and `ci_test`; after shared-env viewer bootstrap, ordinary frontend API requests no longer send browser-owned identity/scope headers.
- UI-surface decision: the AppShell active-user switcher is now explicitly local-dev/demo-only, while shared environments render the server-derived viewer identity instead of implying browser-owned production identity.

## 2026-03-17 (TASK-0112 local_dev loopback guard and unsafe override contract)
- Startup-posture decision: the supported `onetruth-api` startup path now enforces `local_dev` loopback-only binds and refuses non-loopback hosts unless `ONETRUTH_UNSAFE_ALLOW_LOCAL_DEV_NON_LOOPBACK_BIND=1` is set.
- Scope decision: this task hardens the blessed CLI seam only; it does not redefine request-context trust semantics or claim to normalize every ad hoc raw `uvicorn onetruth.api.main:app` invocation style.
- Operator-guidance decision: repo docs now treat non-loopback `local_dev` binds as a controlled unsafe test escape hatch rather than a normal development or shared-environment posture.

## 2026-03-17 (TASK-0113 production/lab topology ADR and single-node deploy reference)
- Topology decision: first-user production and lab are now defined as separate single-node environments over the current implemented substrate (`SQLite + local filesystem artifacts`), not as one runtime with tenant/domain separation.
- Deploy-input decision: `release_source_bundle` is the only operator deploy artifact; `handoff_source_bundle`, `runtime_workspace_bundle`, and raw workspace archives remain non-deploy surfaces.
- Promotion-gate decision: the lab-to-prod connection remains a reviewed release process, not a third runtime/control-plane service, and Workflow Lab remains internal-only/non-authoritative in this tranche.

## 2026-03-17 (TASK-0114 backup/restore/rollback runbooks and rehearsal basis)
- Recovery-unit decision: the first-user recoverable unit is now frozen as the environment-specific SQLite DB file, the environment-specific artifact root, the matching `release_source_bundle` plus `bundle_manifest.json` / `release_provenance.json`, and secret/config references needed to rehydrate that environment.
- Operator-flow decision: rollback and restore are now explicitly separate operations, where rollback means redeploying a previous release against preserved current state, and restore means recovering DB/artifact state from a known backup set before reattaching it to the matching release bundle.
- Gate-honesty decision: the repo now documents a restore rehearsal basis, but it does not claim G1 is satisfied until real rehearsal evidence exists.

## 2026-03-18 (TASK-0115 observability baseline with health/readiness and safe metrics)
- Operability-surface decision: the thin API shell now exposes internal JSON operator endpoints at `GET /api/v1/ops/health`, `GET /api/v1/ops/readiness`, and `GET /api/v1/ops/metrics` without requiring request headers or shared-env principal resolution.
- Readiness decision: first-user readiness now fails only on core substrate unavailability (missing/unusable SQLite DB file or artifact root), while degraded-mode and projection-coherence visibility surface as warnings rather than redefining the node as unavailable.
- Metrics-safety decision: route metrics are process-local aggregates keyed only by `route_name`, `method`, and `status_family`; they intentionally omit request ids, tenant/domain values, actor identity, paths, route params, headers, and payload-derived data.

## 2026-03-18 (TASK-0117 Workflow Lab Phase 0 authority boundary and phased plan)
- Phase-0-boundary decision: Workflow Lab now has an explicit `docs/workflow_lab/` entrypoint, authority boundary, and phased-plan recap, and that Phase 0 surface is docs-only/non-authoritative by design.
- Authority decision: Workflow Lab outputs may exist as evidence or derived material, but they must not become workflow-defining semantics, promotion truth, direct production state, or a second semantics compiler.
- Gating decision: the repo now states more plainly that schema-first TASK-0118 is next, while TASK-0121 and TASK-0122 remain gated on `G1` and `G2`.

## 2026-03-18 (TASK-0118 Workflow Lab report/freshness and core schema pack)
- Schema-pack decision: Workflow Lab now has a thin machine-readable schema family for `freshness`, `variant_spec`, `run_profile`, `world_instance`, `run_report_core`, and `compare_report`, giving future normalization work a stable evidence contract without creating a lab runtime platform.
- Boundary decision: `VariantSpec` is now explicitly reserved for execution variation under fixed semantics, while `RunProfile`, `WorldInstance`, and `CompareReport` stay metadata-only shells rather than submission policy, world-materialization, or semantic-version engines.
- Validation decision: repo schema validation now covers `schemas/workflow_lab/*`, and the next non-gated Workflow Lab step is TASK-0119 normalization over existing Stage04/scheduling/certification outputs.

## 2026-03-18 (TASK-0119 Workflow Lab normalization over existing outputs)
- Normalization decision: the repo now emits adjacent `workflow_lab_run_report.json` and `workflow_lab_review_packet.md` artifacts from three existing output families: weekly Stage04 pilot packets, realistic schedule-planning pilot packets, and current capability certification scenarios.
- Certification-scope decision: capability certification normalization is per scenario row, not one aggregate certification-level `run_report_core`, so each scenario keeps its own evidence/report boundary.
- Boundary decision: TASK-0119 added no `compare_report` generation, no execution adapters, no freshness guards, no public Workflow Lab surface, and no `src/onetruth/workflow_lab/` package; the next Workflow Lab step is TASK-0120 gate/release documentation.

## 2026-03-18 (TASK-0120 Workflow Lab promotion gate and G1/G2 freeze)
- Gate-contract decision: `docs/workflow_lab/PROMOTION_GATE.md` is now the authoritative repo-native reference for the release-mediated promotion gate `G` and the current status of readiness gates `G1` and `G2`.
- Gate-honesty decision: both `G1` and `G2` remain explicitly uncleared; the repo now says plainly that contract/docs alone do not clear an operational gate and that recorded evidence is required where specified.
- Routing decision: `TASK-0121` and `TASK-0122` now point directly at `docs/workflow_lab/PROMOTION_GATE.md` as the first proof source for unblocking, so later Workflow Lab work cannot quietly bypass the recorded-gate requirement.

## 2026-03-18 (TASK-0116 GitHub perimeter hardening and mock-vs-live OpenAI split)
- Workflow-provenance decision: repo-managed GitHub Actions workflows now pin external actions to verified full commit SHAs instead of floating major tags.
- Perimeter-workflow decision: pull requests now have an explicit `dependency_review` workflow, and Python plus JavaScript/TypeScript code scanning now lives in a dedicated `codeql` workflow for pull_request / push-to-main / schedule.
- OpenAI-lane decision: `agent_api.yml` is now the scheduled/manual mock lane over `ci-fast-backend`, while `agent_api_live.yml` is the manual gated real OpenAI workflow that expects live secrets and preserves the existing weekly Stage04 dual gate.

## 2026-03-17 (TASK-0108 structured API boundary logging)
- Boundary-observability decision: the API shell now emits compact JSON-line records through logger `onetruth.api.boundary` with three fixed event names: `request_started`, `request_finished`, and `request_failed`.
- Safety decision: boundary logs keep a strict allowlist of request-context and mutation-correlation fields only, and intentionally do not log bodies, bearer tokens, raw headers, actor roles, large payload fields, `actor_id`, or exception text.
- Correlation decision: finish logs reuse existing route metadata plus existing receipt-backed mutation ids when those ids are already present in API responses, while `x-request-id` remains a header-only seam and is not propagated into JSON payloads or timeline-event correlation.

## 2026-03-17 (TASK-0109 assurance-domain split and truthful validator entrypoints)
- Assurance-structure decision: `scripts/validate_repo.py` remains the one umbrella entrypoint, but the implementation now lives under `scripts/repo_assurance/` with explicit `schema_governance`, `repo_metadata`, `release`, `secrets`, and `traces` modules plus a small shared `core`.
- CLI-truth decision: repo assurance now exposes a repeatable `--domain` selector for exactly `schema`, `governance`, `metadata`, `release`, `secrets`, and `traces`; `--schemas-only`, `--traces-only`, and `--secrets-only` remain compatibility aliases, `make assurance-fast` is the preferred non-trace aggregate, and `make schema-validate` remains an alias for that fast path.
- Release-portability decision: release validation now preflights for a live git checkout, a resolvable git toplevel, and a committed `HEAD`, and reports stable `release validation unavailable: ...` failures instead of surfacing raw clone/git mechanics; this does not relax `release_source_bundle` policy or add support for arbitrary unpacked trees as full release inputs.

## 2026-03-17 (TASK-0107 route-registry modularization)
- Control-plane structure decision: route metadata now lives in resource-scoped `src/onetruth/api/route_specs/*.py` modules plus a tiny shared `_core.py`, while `src/onetruth/api/route_registry.py` remains the single public assembly point for `ROUTES` and `match_route`.
- Parity decision: the assembled registry preserves the exact global route order, suffix precedence, request-body policy metadata, and the current permissive-vs-strict path quirks; no handler, payload, or trust-boundary semantics changed in this tranche.
- Fitness decision: contract coverage now forbids route-spec modules from importing each other, `api.main`, or `route_registry.py`, forbids `route_registry.py` from importing route handlers directly, and keeps route modules plus `main.py` from depending on `route_specs` directly.

## 2026-03-14 (TASK-0101 shared_env JWT principal resolver)
- Shared-env identity decision: when `ONETRUTH_SHARED_ENV_JWT_ISSUER`, `ONETRUTH_SHARED_ENV_JWT_AUDIENCE`, and `ONETRUTH_SHARED_ENV_JWT_PUBLIC_KEY_PEM` are all configured and no explicit resolver is injected, `shared_env` now resolves request context from `Authorization: Bearer <JWT>` using offline `RS256` verification.
- Boundary decision: `local_dev` and `ci_test` keep the existing trusted-header path unchanged, trusted-header CORS remains local-dev-only, and conflicting `x-onetruth-*` headers are ignored in `shared_env`.
- Scope decision: the shared-env attested resolver uses one fixed claim mapping (`sub`, `tenant_id`, `domain_id`, `actor_type`, `actor_roles`) and intentionally does not add JWKS fetch, token introspection, or broader authz changes in this tranche.

## 2026-03-14 (TASK-0100 release bundle only distribution path)
- Distribution-path decision: `release_source_bundle` is now the only endorsed operator/share source artifact; `handoff_source_bundle` remains internal review/Codex-only and raw workspace/manual zips are explicitly non-release.
- Provenance decision: release exports now include a deterministic repo-owned `release_provenance.json` sidecar with bundled-file digests, curated manifest/lockfile entries, and archive/commit metadata instead of escalating to a full SPDX/CycloneDX rollout.
- Operator-path decision: `make clean-source-bundle` now points at the release export path, while `make handoff-source-bundle` preserves the internal working-tree-sensitive review snapshot.

## 2026-03-14 (TASK-0099 CI topology split and security required gates)
- CI-lane decision: pull-request feedback now splits into parallel fast required backend lanes (`lint`, `contract`, `unit`, `security`), one separate `runtime-required` lane, and the standalone `frontend` lane instead of one monolithic backend job.
- Guardrail-workflow decision: `secret_hygiene` remains a separate PR-capable workflow boundary rather than being folded into the main workflow's `security` job, while `release-confidence` is reserved for `push` to `main` and `workflow_dispatch`.
- Aggregate-target decision: local/CI Make truth now uses `ci-fast-backend` and `ci-runtime-required`, `ci-backend` remains the aggregate alias over both, and `agent_api.yml` now reuses only the fast backend aggregate before the existing gated OpenAI tests.

## 2026-03-14 (TASK-0098 frontend transport v2 cutover and clean-install truth)
- Frontend transport decision: frontend/client download flows now call sibling `.bin` routes directly and do not keep a silent client-side fallback to the legacy JSON `/download` endpoints.
- Client-boundary decision: binary download handling now relies on attachment headers (`content-disposition`, `content-type`, `content-length`, `x-request-id`) through a narrow `requestBinary()` seam, while backend error behavior remains the existing JSON `ApiError` envelope.
- Install-truth decision: clean `npm ci` from `frontend/package-lock.json` is the only documented/supported frontend install baseline; vendored `node_modules` is not treated as runnable source truth.

## 2026-03-14 (TASK-0097 binary artifact/template download transport v2)
- Transport-shape decision: binary download v2 ships as sibling `.bin` routes for artifacts and templates, while the existing `/download` JSON+base64 routes remain explicit compatibility surfaces in this tranche.
- Boundary decision: binary success responses now return raw bytes with attachment headers, but failure behavior remains the existing JSON error envelope so scope/cross-tenant denial and not-found contracts stay stable.
- Scope-boundary decision: this tranche improves download transport only; it does not redesign uploads, migrate frontend callers, or reopen artifact metadata, pointer, provenance, or trust semantics.

## 2026-03-14 (TASK-0096 deterministic API payload hardening)
- Boundary-contract decision: JSON POST routes now enforce deterministic media-type and size contracts at the shell boundary, so non-empty wrong/missing media type returns `415 unsupported_media_type`, oversize envelopes return `413 payload_too_large`, and existing empty-body/malformed-body `400` contracts remain intact once those checks pass.
- Route-policy decision: the declarative API route registry now carries explicit request body policies instead of a loose `body_mode`, with a bounded `256 KiB` ceiling for ordinary JSON command routes and a bounded `2 MiB` ceiling for JSON artifact-ingress routes.
- Scope-boundary decision: this tranche hardens JSON boundary parsing only; it does not redesign artifact transport, add multipart/binary upload support, or change trust/profile semantics.

## 2026-03-14 (TASK-0095 declarative route registry)
- Shell-structure decision: API route metadata, match order, body expectations, and dispatch targets now live in one ordered declarative registry instead of parallel handwritten `_match_route()` and `_dispatch_route()` switches.
- Parity decision: the registry preserves current route precedence and the existing permissive-vs-strict slash behavior for selected suffix routes such as `/claim`, `/respond`, `/transition`, and `/timeline`; this tranche does not tighten path semantics.
- Scope-boundary decision: the refactor stays framework-free and shell-only, with no endpoint-module rewrites, no JSON payload changes, no trust-boundary changes, and no request-id/event-correlation expansion.

## 2026-03-14 (TASK-0094 API shell characterization and request-id seam)
- Shell decision: the current hand-rolled API shell now has focused characterization coverage for route misses, malformed JSON, unsupported scopes, and internal-error fallback before any route-registry refactor.
- Correlation decision: every API response now emits a header-only `x-request-id` seam, with safe incoming values echoed and missing/unusable values replaced by generated `httpreq_<hex>` ids.
- Scope-boundary decision: this tranche does not add request ids to JSON payloads, does not propagate them into timeline-event `correlation_id`, and does not change the frozen `shared_env` trust posture.

## 2026-03-14 (TASK-0093 human-task mutation family extraction)
- Extraction decision: `claim_human_task_command`, `complete_human_task_command`, and `confirm_human_task_review_command` now live in `src/onetruth/application/handlers/human_tasks.py` behind lazy compatibility wrappers in `workflow_task_lifecycle.py`.
- Helper-seam decision: the extracted family depends on the neutral command-boundary seam plus a private `src/onetruth/application/handlers/_shared/artifact_effects.py` helper closure for confirm-review support, so no extracted module needs to re-import the legacy hotspot.
- Scope-boundary decision: this tranche moved only the human-task mutation family and its private confirm-review support helpers; read-side task queries, public artifact commands, caller modules, and capability semantics remain unchanged.

## 2026-03-14 (TASK-0092 neutral command-boundary helper seam)
- Helper-seam decision: the extracted approvals family now depends on `src/onetruth/application/handlers/_shared/command_boundary.py` for shared command-boundary primitives instead of importing them from `workflow_task_lifecycle.py`.
- Compatibility decision: `workflow_task_lifecycle.py` remains import-compatible through helper re-exports and lazy approval wrappers, but extracted handlers and `_shared/` modules must not re-import the legacy hotspot directly.
- Scope-boundary decision: only the receipt/error/scope/event-envelope helper cluster moved in this tranche; no additional handler family extraction and no approval/capability semantics changed.

## 2026-03-14 (TASK-0091 dependency automation, secret scanning, and operator-only follow-ups)
- Automation decision: repo-native update automation now exists for the actual mutable dependency surfaces in this repo: Python (`pip` at `/`), frontend (`npm` at `/frontend`), and GitHub Actions metadata.
- Secret-scan decision: tracked-file secret hygiene now has a dedicated workflow boundary via the repo validator's secret-only mode; the current preferred invocation is `python scripts/validate_repo.py --domain secrets`, with `--secrets-only` retained as a compatibility alias.
- Operator-boundary decision: secret revocation confirmation, Git history rewrite, and hosted GitHub push-protection/settings changes remain operator/admin follow-ups and must not be treated as Codex code-task completion.

## 2026-03-14 (TASK-0090 bootstrap/install truth closure and tracked build-artifact ban)
- Baseline decision: the repo’s validated package metadata now matches the established dev/CI baseline exactly, so `pyproject.toml` requires Python `>=3.11,<3.12` instead of claiming a broader support floor.
- Install-path decision: local bootstrap guidance, CI workflows, and the compatibility `requirements.txt` shim now all converge on one authoritative backend install path: `python3.11 -m pip install -e ".[api,dev]"`.
- Source-boundary decision: tracked `*.egg-info` content is now explicitly forbidden by repo validation and excluded from release source bundles, while intentionally tracked generated outputs under `build/generated/` remain unchanged.

## 2026-03-13 (truth-alignment backlog sync)
- Numbering-source decision: the external truth-alignment prompt pack is canonical for the new tranche, so `TASK-0076` is board/query-surface stability and `TASK-0077` is the capability-lattice freeze task.
- Backlog-hygiene decision: the duplicate historical cleanup trio was renumbered to `TASK-0087` / `TASK-0088` / `TASK-0089`, while `TASK-0071` / `TASK-0072` / `TASK-0073` now refer only to the Stage04 progression.
- Alias decision: renumbered historical task briefs keep short deprecated-alias notes so future sessions can map old references without reopening the duplicate-ID ambiguity.
- Validation decision: backlog validation now needs to fail on duplicate task-file IDs and duplicate task-index rows so this class of drift cannot hide behind prefix collisions.

## 2026-03-13 (TASK-0086 approvals-first hotspot extraction)
- Extraction decision: the first controlled hotspot move pulls only the approvals family out of `src/onetruth/application/handlers/workflow_task_lifecycle.py` into `src/onetruth/application/handlers/approvals.py`; task, flag, artifact, and execution families stay in place for later tranches.
- Compatibility decision: existing callers keep importing approval commands from `workflow_task_lifecycle.py`, which now re-exports the moved behavior through thin lazy wrappers so the physical extraction proves out without caller churn.
- Characterization decision: direct unit coverage now compares the legacy wrapper surface and the new module surface against the same in-memory runtime substrate, freezing approval request/respond row shapes, event payloads, and forbidden-error semantics before any later helper or import cleanup.

## 2026-03-13 (TASK-0085 bootstrap truth, CI honesty, and governance cleanup)
- Bootstrap decision: `scripts/doctor.py` is now the single blessed local entrypoint for lightweight deterministic environment checks; there is no parallel shell bootstrap path in this tranche.
- Python-baseline decision: the validated dev/CI baseline is Python `3.11`, but the task does not change the broader package metadata support floor; doctor verifies that a Python 3.11 interpreter is available even when the invoking `python3` is older.
- CI-honesty decision: `make lint`, `make ci-backend`, `make frontend-ci`, and `make ci` now describe distinct real check slices instead of overloading lint with contract tests or rerunning blanket `pytest -q` in scheduled OpenAI CI.
- Governance decision: CODEOWNERS now uses only existing root-anchored paths with a real temporary owner target (`@tylerclark`), and the repo now carries explicit MIT and Node 20 declarations via `LICENSE` and `.nvmrc`.

## 2026-03-13 (TASK-0084 explicit bundle kinds and exported-payload validation)
- Bundle-classification decision: source/export packaging now uses three explicit bundle kinds: `handoff_source_bundle` for working-tree-sensitive review/handoff snapshots, `release_source_bundle` for clean tracked commit snapshots, and `runtime_workspace_bundle` for run inspection/evidence exports over canonical runtime truth.
- Release-contract decision: `release_source_bundle` always exports tracked files only, requires `HEAD`, and fails closed unless the tracked worktree is clean under `git status --untracked-files=no` semantics.
- Manifest decision: both source bundles and runtime workspace bundles now write a `bundle_manifest.json` so downstream consumers can classify the archive without inferring semantics from the script name alone.
- Validation decision: `scripts/validate_repo.py` now inspects a real exported `release_source_bundle` payload from a temporary clean clone of `HEAD`, so full-repo validation can verify the actual archive contents without being blocked by a dirty development worktree.

## 2026-03-13 (TASK-0082 scoped command receipts and replay)
- Retry-contract decision: canonical CLI/API command-boundary retries now resolve through scoped `command_receipts`, so same-scope retries with the same normalized request replay committed success with `idempotent_replay=true` and stable `receipt` metadata instead of surfacing `duplicate_idempotency_key`.
- Mismatch decision: reusing the same `(command_name, scope_key, idempotency_key)` tuple with a different normalized request now fails closed as `command_receipt_mismatch` (`409`) rather than replaying or mutating again.
- Scope decision: the same client `idempotency_key` may be reused safely across different command scopes; receipt uniqueness is `(command_name, scope_key, idempotency_key)` rather than a single global key.
- Boundary decision: raw `events append` keeps explicit event-store duplicate failure semantics (`duplicate_idempotency_key`), so receipt replay changes only the public mutation boundary and not low-level event append behavior.

## 2026-03-13 (TASK-0083 shared read-model seam and route-boundary fitness)
- Layering decision: the five shared HITL list/query helpers (`workflow_runs`, `human_tasks`, `approvals`, `flags`, `pointers`) now live under `src/onetruth/api/queries/` instead of being borrowed from sibling route modules.
- Fitness decision: contract coverage now fails if any module under `src/onetruth/api/routes/` imports another route module directly, closing the specific layering smell without introducing a broader API framework.
- Scope decision: this task moved only the shared read-helper seam; board card assembly, logistics story composition, workspace/detail shaping, and public payload contracts remain unchanged, with the logistics story still primary and the schedule-only board still legacy/internal.

## 2026-03-13 (TASK-0081 shared HTTP artifact ingress split)
- Boundary decision: shared HTTP artifact ingress (`/api/v1/artifacts/ingest` and subject upload endpoints) now accepts request bytes only and rejects caller-controlled `source_path` and `storage_root`.
- Provenance decision: shared HTTP ingress records `metadata_json.ingress_kind=request_bytes` and strips caller-supplied `seed_source_path` / `ingress_source_path`, while CLI/scenario/internal local seeding keeps normalized source-path metadata with `ingress_kind=local_source_path`.
- Compatibility decision: CLI `artifacts ingest`, `artifacts seed-corpus`, and scenario-backed local seeding remain on the same canonical artifact path and were not removed or redesigned in this task.

## 2026-03-13 (TASK-0080 write-boundary capability enforcement)
- Enforcement decision: claim, complete, confirm-review, approval respond, and flag transition now consume the frozen shared capability decisions at the canonical write boundary before mutating rows or appending events.
- Error-honesty decision: capability/principal denials now return explicit forbidden codes (`task_claim_forbidden`, `task_complete_forbidden`, `task_confirm_review_forbidden`, `approval_respond_forbidden`, `flag_transition_forbidden`) with structured `capability_id` / `reason_codes` / `reasons`, while state-machine conflicts remain on the existing conflict codes.
- Caller-contract decision: role-gated non-HTTP callers (CLI/scenario/pilot/certification paths) must now pass explicit `actor_roles`; the runtime no longer relies on implicit role inference for `tasks.claim`, `approvals.respond`, or `flags.transition`.
- Collaboration decision: artifact upload remains an intentionally broader collaboration/evidence surface; this task hardens other writes without introducing a new `artifact_upload_forbidden` path.

## 2026-03-13 (TASK-0076 board stability and query-surface classification)
- Compatibility decision: `GET /api/v1/board/schedule-planning` now uses the current pointer-query contract and returns the documented board payload without redesigning that endpoint.
- Surface-classification decision: `GET /api/v1/stories/logistics-three-workflow` and frontend route `/demo/logistics` remain the primary logistics surfaces; the schedule-only board stays legacy/internal regression coverage.
- Layering decision: the route-to-route import seam remains a known smell and is explicitly deferred to `TASK-0083` rather than being broadened inside this board-stability patch.

## 2026-03-13 (TASK-0077 capability lattice freeze)
- Lattice decision: routing, claim, complete, specialized execute, collaborate/upload, approval response, and flag transition are now frozen as distinct capability axes, with one authoritative matrix in `docs/architecture/human_task_semantics.md`.
- Role-semantics decision: `candidate_roles` gate human-task claim and act as fallback approval routing only; `required_role` wins for approval response when present; assignee state anchors completion and specialized execute attempts.
- Drift decision: current write handlers and some role lists are still less strict than the frozen lattice, and that mismatch remains intentionally deferred to `TASK-0078`, `TASK-0080`, and `TASK-0081` rather than being hardened in this semantics-only tranche.

## 2026-03-13 (TASK-0078 API boundary profiles and principal resolver seam)
- Boundary-profile decision: the thin HTTP adapter now has explicit `local_dev`, `ci_test`, and `shared_env` trust profiles, with `shared_env` as the default when nothing is configured.
- Fail-closed decision: `shared_env` no longer falls back to ambient trusted headers; it returns `503 principal_resolver_unavailable` unless a non-header principal resolver is injected at app creation.
- Local-affordance decision: trusted `x-onetruth-*` headers remain available only in `local_dev` and `ci_test`, and trusted-header CORS is reflected only for loopback local-dev origins.
- Test-harness decision: runtime API helpers now opt into `ci_test` explicitly so existing ASGI tests preserve their current semantics while the production/default API posture becomes fail closed.

## 2026-03-13 (TASK-0073 weekly Stage04 live TPM compaction and bounded 429 recovery)
- Model-surface decision: the Stage04 runtime now keeps the same deterministic tool set and canonical artifact/evidence chain, but the model sees compact Stage04 context summaries and compact tool-output deltas instead of repeated full context packs, route allocations, coverage lists, or finalize candidate payloads.
- Evidence decision: full deterministic tool outputs remain persisted verbatim in `runtime.tool_result.json` and execution traces, while the Responses continuation loop records a separate compact `model_output_json` for the `function_call_output` payload actually sent back to the model.
- Retry-safety decision: `rate_limit_exceeded` handling is now narrowly retried inside the same Responses turn with bounded `Retry-After`/message-derived backoff, preserving idempotency by not executing deterministic tools until a model response succeeds.
- Traceability decision: per-turn request evidence and failed execution traces now record retry attempts/history plus the last failed request details so fresh-live 429 failures stay reviewable and distinguishable from deterministic Stage04 failures.

## 2026-03-13 (TASK-0072 weekly Stage04 iterative deterministic allocation)
- Planner-ownership decision: Stage04 weekly allocation remains deterministic-code-owned truth, but now advances through an explicit partial-schedule loop with adaptive 5-10 route batches instead of a single global top-pick pass.
- Repair-boundary decision: bounded local repair moves are allowed inside the deterministic allocator to free capacity or preserve continuity, but repairs stay narrowly scoped to already-selected local assignments rather than broad weekly rewrites.
- Hard-rule decision: driver-day availability state, overlap/rest protection, max shifts, and rolling-7 limits are now evaluated against the evolving partial schedule, not only against static source artifacts.
- Stability decision: previous-week continuity is now a first-class scored term carried through candidate evaluation, final selections, validation summaries, and draft schedule artifacts so week-to-week churn is explicit and reviewable.
- Artifact-shape decision: Stage04 keeps the same final artifact keys (`planning.input_bundle.doc`, `planning.candidate_schedule_delta.workbook`, `planning.validation_summary.doc`, `planning.draft_weekly_schedule.*`), but their payloads now expose per-iteration deltas, coverage gaps, churn/repair counts, and score tradeoffs.

## 2026-03-13 (TASK-0071 weekly Stage04 over-capacity realistic handoff refresh)
- Fixture-contract decision: the default realistic weekly Stage04 pilot now uses the over-capacity `PW-2026-W12` hard case (40 active drivers, 139 route slots, positive daily feasible surplus) instead of the prior `PW-2026-W10` shortage-style fixture.
- Adapter decision: the realistic Stage04 source-material path is now grounded in repo-authored over-capacity example YAMLs and may add deterministic helper fields for bridge/runtime use without changing workflow IDs, stage IDs, or final Stage04 artifact keys.
- Compatibility decision: the tiny two-driver smoke fixture remains unchanged for lightweight deterministic/runtime regression coverage while the realistic contract moves to explicit day-level availability/history semantics.

## 2026-03-13 (TASK-0071 weekly Stage04 realistic artifacts and fixtures bundle)
- Bridge-payload decision: weekly Stage04 keeps the same canonical artifact kinds, but the payloads now support richer day-resolution planning context including per-driver planning-week states, prior-week state, rolling-7 snapshots, daily demand summaries, and policy signals.
- Backward-compatibility decision: the existing tiny two-driver Stage04 scenario and pilot remain the smoke/regression baseline; richer payload parsing is additive and defaults cleanly when those new fields are absent.
- Shared-fixture decision: one deterministic realistic source-material fixture under `fixtures/logistics/weekly_stage04_realistic_source_material.yaml` now drives both the new hard-case pilot seed path and richer test coverage so the 40-driver day-resolution input shape stays reproducible.
- Scope decision: the realistic slice still uses the same Stage04 deterministic build/runtime architecture, draft-only artifact path, and bounded Responses tool loop; no new workflow IDs, stage IDs, truth paths, or iterative planner behavior were introduced.

## 2026-03-13 (TASK-0073 weekly Stage04 iterative agent loop and analysis)
- Tool-boundary decision: weekly Stage04 now exposes iterative deterministic tools (`context`, `preview`, `apply`, `validation`, `iteration_analysis`, `finalize`) instead of a one-shot build tool, and the model remains an orchestration/search controller rather than a schedule allocator.
- Finalization decision: Stage04 draft artifacts are materialized only through an explicit deterministic finalize tool call; the runtime no longer performs unconditional post-loop build/finalization after the model stops requesting tools.
- Evidence decision: canonical runtime evidence now persists per turn/iteration via repeated `runtime.tool_request.json` and `runtime.tool_result.json` artifacts plus an execution trace that links turn evidence refs, progress state, and finalize outcome.
- Stop-policy decision: authored Stage04 `no_progress_ticks` from compiled control metadata is now enforced at runtime, so repeated context/inspection-only turns fail closed with visible evidence instead of silently spinning.
- Inspection-packet decision: realistic weekly pilot packets now surface iteration-level route allocations, uncovered-route carryover, repair moves, runtime turn summaries, and fallback tradeoff notes derived from canonical artifacts/evidence rather than only listing IDs.

## 2026-03-13 (TASK-0089 Stage06 compiled-control alignment and tool-class vocabulary cleanup)
- Control-alignment decision: the bounded Stage06 sandbox now derives its pinned execution semantics from the authored `schedule_planning.v1` Stage06 execution profile plus a registry-backed runtime tool binding instead of a hardcoded `execution_spec_id`.
- Vocabulary decision: authored `allowed_tool_classes` remain capability-level execution-profile vocabulary, while `tool_execution.tool_class` remains the concrete engine/runtime identifier for the bounded executor; these are related through explicit runtime tool bindings, not by reusing the same string set.
- Safety decision: the Stage06 OpenAI runtime binding is validated to use only authored capability classes already allowed by the Stage06 execution profile and fails closed if the binding drifts outside that authored allowlist.
- Scope decision: the legacy Stage06 sandbox remains a regression/reference-only bounded single-call review path; this cleanup aligns metadata and audit shape without broadening Stage06 autonomy or re-promoting `schedule_planning.v1` as the primary agent surface.

## 2026-03-13 (TASK-0074 weekly Stage04 input-resolution hardening)
- Binding-resolution decision: weekly Stage04 bridge inputs are now resolved through an explicit typed dataset-key registry (`route_slot_requirements`, `driver_capabilities`, `approved_availability`, `actual_hours`, `route_horizon`) rather than suffix-scanning `required_evidence_keys`.
- Authored-source decision: the Stage04 input registry is validated against repo-native weekly workflow source (`WORKFLOW_CONTRACT.yaml`, `ARTIFACT_MAP.yaml`, `EXECUTION_PROFILE.yaml`) so control/runtime drift fails closed.
- Control-spec safety decision: compiled Stage04 metadata now rejects missing required bridge bindings and alias-equivalent conflicting keys (for example mixed `planning.*` and `dispatch.*` bridge keys for the same slot) instead of silently picking one by suffix.
- Runtime safety decision: the bounded weekly Stage04 agent still resolves the latest matching artifact version per exact dataset key, but now returns explicit `stage04_input_artifact_missing` errors when required bridge artifacts are absent.

## 2026-03-13 (TASK-0087 repo hygiene cleanup for local state and tracked outputs)
- Repo-boundary decision: the default runtime evidence root (`.onetruth_artifacts/`), local SQLite DBs, `.DS_Store`, and Codex handoff zips are local machine outputs and must not be tracked as repo source.
- Fixture-boundary decision: the tracked `.onetruth_artifacts/` contents audited in this cleanup were live execution evidence only, not golden fixtures; any future reusable evidence must move into an explicit `fixtures/` path.
- Ignore-rule decision: Git ignore coverage now explicitly blocks `.onetruth_artifacts/`, local DB files/journals, and `codex_handoff_packet_*.zip` so local runs stop re-polluting the repo.
- Diff-hygiene decision: normalized the small formatting-only noise spot in `src/onetruth/integrations/openai/responses_agent_runner.py` so the cleanup diff stays `git diff --check` clean.

## 2026-03-12 (TASK-0070 weekly Stage04 pilot + real-network gate hardening)
- Pilot reproducibility decision: added a dedicated logistics weekly Stage04 pilot service/runner (`run_logistics_weekly_agent_pilot_suite`, `scripts/run_logistics_weekly_agent_pilot.py`) with deterministic IDs keyed by `(pilot_key, pilot_id)`, canonical workflow/task/artifact execution, and no ad hoc side-channel state.
- Weekly Stage04 pilot execution posture decision: pilot runs support `--openai-mode mock|real`; mock mode uses a deterministic bounded Responses function-calling runner, and real mode is explicitly key-gated without introducing a second runtime path.
- Inspection packet authority decision: weekly pilot outputs now include canonical-reference-heavy inspection packets (`inspection_packet.json` + `.md`) that center workflow/task/execution/tool/policy/artifact IDs, evidence-by-kind coverage, timeline events of interest, and canonical CLI query commands for debugging.
- Real-network gate decision: weekly Stage04 real e2e coverage now lives in `tests/integration_openai/test_weekly_stage04_openai_real_e2e.py` and requires both `ONETRUTH_RUN_OPENAI_E2E=1` and `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1` (plus `OPENAI_API_KEY`), preserving existing Stage06 real-network coverage.
- CI posture decision: `agent_api.yml` now runs `tests/integration_openai` under one gated step, with weekly Stage04 e2e controlled by the additional weekly env gate rather than a permanently-empty future test directory path.

## 2026-03-12 (TASK-0069 weekly Stage04 OpenAI agent runtime)
- Bounded Stage04 agent-loop decision: weekly Stage04 now runs a synchronous OpenAI Responses function-calling loop (`weekly_schedule_planning.v1`, `Stage04`) with multi-call-per-turn support and `call_id`-bound `function_call_output` continuation semantics; no Assistants API and no background mode were introduced.
- Compiled-control pinning decision: Stage04 execution session semantics now resolve from compiled logistics control metadata (`compile_control_layer` + `derive_execution_session_payload`) rather than hardcoded execution-spec constants.
- Deterministic-tool boundary decision: the model can call only deterministic Stage04 tools (`get_stage04_context`, `materialize_weekly_stage04_draft_outputs`, `get_stage04_validation_summary`, `render_stage04_ops_packet`); no publish/pointer-promotion tool is exposed.
- Evidence traceability decision: context packs, turn-level request/response metadata, function calls, function-call outputs, usage totals, and execution traces are persisted as canonical artifact evidence linked to `execution_session`/`tool_execution`/`policy_decision`.
- API/actionability boundary decision: added one bounded human-task API mutation (`POST /api/v1/human-tasks/{id}/weekly-stage04-openai-agent`) and corresponding actionability affordance for claimed Stage04 work-item tasks without introducing a generalized public agent framework.

## 2026-03-12 (TASK-0068 deterministic weekly schedule-control services)
- Deterministic feasibility decision: Stage04 weekly schedule-control feasibility (route-slot expansion, candidate generation, hard-rule validation, and soft scoring) now lives in dedicated deterministic services under `src/onetruth/application/services/schedule_control/`; it is not owned by `workflow_task_lifecycle.py` and is not delegated to LLM output.
- Runtime execution decision: added bounded runtime command `schedule-control build-weekly` that resolves canonical Stage04 bridge artifacts, executes deterministic weekly build logic, and lowers machine-checkable Stage04 artifacts (`planning.input_bundle.doc`, `planning.candidate_schedule_delta.workbook`, `planning.validation_summary.doc`, `planning.draft_weekly_schedule.*`) idempotently.
- Replay-safety decision: Stage04 deterministic lowering now uses stable artifact identity/content derivation and provenance edges so retries return the same canonical output identities without duplicate truth rows.

## 2026-03-12 (TASK-0067 schedule-control authored semantics + canonical bridge artifacts)
- Artifact-authority decision: added canonical bridge artifact semantics for weekly/live schedule-control (`route_slot_requirements`, `driver_capabilities`, `input_bundle`, `candidate_schedule_delta`) and bounded Stage04/Stage02 validation evidence artifacts without introducing a second schedule truth path.
- Derived-view decision: current operative schedule remains a derived materialization from canonical base seed + ordered promoted deltas; it is explicitly non-authoritative.
- Exception-authority decision: open-exception packets remain derived from canonical `flags` and timeline state; no peer `planning.open_exceptions` store is authorized.
- Method-package decision: Stage04 weekly build and Stage02 live replan packages now reference shared schedule-control family refs while keeping deterministic hard/soft rule posture and bounded optional LLM rationale.

## 2026-03-12 (TASK-0066 execution-runtime hardening for compiled agent control traceability)
- Execution semantics evidence decision: Stage06 bounded execution now persists pinned immutable semantics artifacts (`execution.compiled_spec.json`, `execution.compile_source_manifest.json`) linked to canonical execution runtime objects; no second execution truth subsystem was introduced.
- Artifact-link subject decision: canonical artifact linkage validation now supports `execution_session`, `tool_execution`, and `policy_decision` subjects with workflow-scope checks resolved through existing execution/session relationships.
- Event safety decision: runtime event append now enforces registry-defined `required_links` semantics at write time (not only offline validation), and execution-session creation now emits an explicit `execution_spec` link required by the registry.
- Reuse decision: added a shared execution-evidence helper surface (`src/onetruth/application/services/execution_evidence.py`) that prepares pinned semantics artifacts and reusable execution-facet evidence links for future agent-trace slices.

## 2026-03-12 (TASK-0065 logistics-first Codex routing + secret hygiene)
- Routing decision: new agentic scheduling task intake now defaults to logistics weekly/live (`weekly_schedule_planning.v1 -> live_dispatch.v1`) across Codex/LLM routing docs; legacy `schedule_planning.v1` remains regression/reference-only.
- Secret hygiene decision: committed real OpenAI key material is removed from tracked repo content, and local `.codex.env` posture is documented as local-only placeholders with real-network gates defaulted off.
- Validation decision: `scripts/validate_repo.py` now scans tracked UTF-8 files for real OpenAI key patterns (`sk-proj-...` / `sk-...`) and fails validation on detection.
- CI gate posture decision: `.github/workflows/agent_api.yml` keeps current OpenAI gating and adds an explicit future weekly-agent real-network gate controlled by repository variable `ONETRUTH_RUN_WEEKLY_AGENT_E2E=1` plus `OPENAI_API_KEY` presence (later superseded in TASK-0070 by `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E` dual-gate posture).

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
- Default verification flow for runtime work is now `make assurance-fast`, `make contract`, `make replay`, `make acceptance`, then implementation-specific suites (`make schema-validate` remains a compatibility alias).

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

## 2026-03-14 — Planned next package after TASK-0101
- We are treating the next tranche as a **centrality + operability** package, not another trust-semantics package.
- Primary next risks are now:
  - residual centrality around `workflow_task_lifecycle.py`,
  - package-boundary leaks in `onetruth.api`,
  - control-plane framework creep around `route_registry.py`,
  - and assurance-kernel concentration in `scripts/validate_repo.py`.
- The next queued tasks are `TASK-0102` through `TASK-0109`.
- Explicit deferrals for this tranche:
  - no PostgreSQL/object-store migration,
  - no broader auth/policy redesign,
  - no streaming upload rewrite,
  - no large logistics-story or weekly-agent service decomposition yet.

## 2026-03-17 (TASK-0102 neutral read/error seam)
- Centrality-retirement decision: shared runtime reads now live in `src/onetruth/application/read_commands/` instead of being sourced only from `workflow_task_lifecycle.py`.
- Boundary decision: API/query/service layers now consume `CommandError` from `src/onetruth/application/handlers/_shared/command_boundary.py`, while read-side approvals still import from `src/onetruth/application/handlers/approvals.py` and legacy `workflow_task_lifecycle.py` stays import-compatible through thin wrappers.
- Guardrail decision: contract coverage now forbids API/query/service layers from importing shared read/error surfaces from the legacy hotspot, while allowing remaining mutation-family imports to retire in later tasks.

## 2026-03-17 (TASK-0103 flag and Stage07 extraction)
- Extraction decision: `create_flag_command`, `transition_flag_state_command`, `activate_stage07_issue_from_flag_command`, and `reconcile_stage07_command` now live in `src/onetruth/application/handlers/flags.py` behind thin compatibility wrappers in `workflow_task_lifecycle.py`.
- Caller decision: API flag routes, the realistic scheduling pilot, and the CLI now import the extracted flag family directly instead of routing those mutations through the legacy hotspot.
- Helper-seam decision: shared event-idempotency availability checks now live on `src/onetruth/application/handlers/_shared/command_boundary.py` so the extracted flag family can stay free of legacy imports without broadening semantics.

## 2026-03-17 (TASK-0104 artifact and pointer extraction)
- Extraction decision: artifact-version creation/ingress/download now live in `src/onetruth/application/handlers/artifacts.py`, and pointer promotion now lives in `src/onetruth/application/handlers/pointers.py`, behind thin compatibility wrappers in `workflow_task_lifecycle.py`.
- Helper-seam decision: shared artifact support remains explicit in `src/onetruth/application/handlers/_shared/artifact_effects.py` instead of leaving artifact lineage concerns embedded in the hotspot.
- Scope decision: the extraction stayed structural only; artifact officialness, pointer promotion semantics, release-bundle truth, and binary transport behavior were not reopened.

## 2026-03-17 (TASK-0105 execution runtime extraction)
- Extraction decision: `create_execution_session_command`, `request_tool_execution_command`, `evaluate_policy_decision_command`, `complete_tool_execution_command`, `transition_execution_session_state_command`, and `reconcile_executions_command` now live in `src/onetruth/application/handlers/execution_runtime.py` behind thin compatibility wrappers in `workflow_task_lifecycle.py`.
- Caller decision: `stage06_openai_sandbox.py`, `weekly_stage04_openai_agent.py`, CLI execution commands, and the direct execution runtime tests now import the extracted execution seam directly instead of routing those mutations through the legacy hotspot.
- Guardrail decision: contract coverage now forbids extracted handlers plus API/service/CLI layers from drifting back to legacy execution mutation imports, while execution read surfaces remain on `read_commands`.

## 2026-03-17 (TASK-0106 optional API import honesty)
- Packaging-boundary decision: `src/onetruth/api/__init__.py` and `src/onetruth/api/main.py` now keep `onetruth.api` imports lazy, so lightweight API modules no longer pull in optional `api` dependencies at import time.
- Dependency-localization decision: `src/onetruth/api/shared_env_principal_resolver.py` now imports `PyJWT` only when the configured shared-env JWT resolver path is actually activated.
- Compatibility decision: `from onetruth.api import app`, `from onetruth.api import create_app`, `from onetruth.api.main import app`, `from onetruth.api.main import create_app`, and `onetruth.api.main:app` remain supported surfaces.
- Scope decision: this task did not change boundary-profile defaults, attested-principal claim mapping, trusted-header rules, route behavior, or error payload semantics for valid configured runtimes.

## 2026-03-24 (Minimal on-call buffer rerun)
- Planner decision: Stage04 on-call demand is now allocated through the same deterministic candidate-generation, hard-validation, and ranking path as route demand, with an internal demand-kind marker rather than authored fixture-schema changes.
- Fairness decision: post-coverage soft-improvement moves now account for zero-shift drivers so the deterministic allocator does not trade away a driver's only shift to gain a small soft-score bump.
- Runtime-budget decision: the authored weekly Stage04 stop policy now allows `28` tool turns so the actual-ops mock/runtime slice can complete the longer deterministic rerun, finalize outputs, and return a final response without exhausting the control-plane budget.
