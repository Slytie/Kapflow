# CAPEX Master v6 Intake

## Source package
- Active package: `CAPEX_Master_Plan_Three_Project_Testing_Production_Preflight_Final_v6.zip`
- SHA256: `ea06571a2e4667487cac3ee870dd91a5489b4ed52edbff2cd96e4c0473d54b95`
- Entries/files: 254 entries / 254 files
- Uncompressed bytes: 1951212
- Top extensions: .csv:133, .md:96, .py:14, .json:8, .template:1, .yml:1, .yaml:1
- Source-package role: active CAPEX planning baseline; v5 and earlier packages are superseded history.
- Runtime/API/schema/DB/workpage changes in this import: none.

## Imported planning counts
| Source table | Imported count | Repo handling |
|---|---:|---|
| MASTER_Task_Backlog.csv | 374 | `TASK-0233` through `TASK-0606` |
| MASTER_Acceptance_Gates.csv | 270 | reference map only |
| MASTER_Risk_Register.csv | 222 | reference map only |
| MASTER_Open_Decisions_Register.csv | 23 | reference map only |

## v5 carry-forward reconciliation
- CAPEX v6 is the active planning baseline; v5 and earlier source packages remain superseded history.
- `V5-TASK-*` rows embedded in the v6 task table are preserved as source-provenance rows only, not active backlog.
- Reconciled v5 rows are marked `DONE` with `source_lineage=v5_carried_forward`, `active_disposition=historical_alias`, and `canonical_task_refs` pointing at the v6/native task refs that own the remaining work.
- `V5-GATE-*`, `V5-RISK-*`, and `V5-OD-*` entries in the gate/risk/decision map are marked `historical_reference`.

## Raw-data boundary
- Raw K12, K3, and blind-validation corpora are not committed to the repo.
- Approved repo records are ZIP basenames, hashes, aggregate counts, fixture-role labels, quarantine policy, and derived planning tasks.
- Do not commit extracted documents, screenshots, raw filenames from inside project archives, embedded text, or OCR/search output from the raw corpora.

## Three project ZIP provenance
| Fixture role | ZIP basename | SHA256 | Entries | Files | Size bytes | Uncompressed bytes | Top extensions |
|---|---|---|---:|---:|---:|---:|---|
| K12 primary MVP fixture candidate | `Projektordner - Kopie-20260601T115514Z-3-001.zip` | `4cb59351dfbf618ac713cbf92e469b4e083c6dd50be4a7506e6a90802c1618ec` | 548 | 543 | 407676260 | 492024604 | .pdf:294, .xlsx:75, .csv:40, .docx:27, .cfg:19, .msg:15, .jpg:15, .ipt:13 |
| K3 shadow/regression fixture candidate | `Reference Project K3.zip` | `fdf11a2a378a446e2984cb6075f0e6eb64f839051ad7f4c53a648fb41fedf8fb` | 979 | 837 | 1502842547 | 1635719705 | .pdf:300, .pptx:184, .docx:138, .xlsx:81, .db:31, .jpeg:28, .doc:22, .lnk:16 |
| Blind/third-validation holdout candidate | `11639 OTC Alma Ruma Kanada.zip` | `9f098c8de46e05a9032d22460de304dd2e94de98356f77a7319d8900f6733a2c` | 2908 | 2724 | 690541632 | 970109741 | .pdf:1126, .doc:326, .psm:299, .xls:270, .cfg:213, .asm:207, .txt:99, .db:99 |

## TASK-0233 closeout evidence
- Imported CAPEX v6 planning source row count: 374 tasks, 270 gates, 222 risks, 23 open decisions.
- Current-code blocker mappings recorded for approval domain coupling, artifact auth-before-read, CAPEX project child APIs/authorization projections, domain-runtime manifests, storage custody gates, Wave 1 closeout evidence, and source occurrence/evidence; the first project child API, selector/dashboard, project-scope helper, official pointer-family substrate, neutral domain-runtime skeleton, ready logistics manifest inventory, CAPEX incubation manifest, approval-effect registry shadow parity, project authorization CED, projection-backed `AuthorizedProjectsQuery`, physical authorization projection runtime state, storage/blob custody CED, pilot storage gate checklist, W1 code pattern register, and W1 closeout review slices are now closed, while pointer-promotion policy checks, real pilot storage evidence or waiver, and later governance remain blocked.
- Verification basis: CAPEX conversion check, repo validation, schema validation, focused planning/import checks, and `git diff --check`.

## TASK-0234 closeout evidence
- Release/source-bundle hygiene excludes `node_modules/` directories repo-wide.
- Cloud Build PR validation skeleton is no-secret/no-deploy by contract.
- Tracked `node_modules` residue is removed from repo truth.

## TASK-0235 closeout evidence
- Artifact write paths sanitize file-name and workflow-run segments, resolve target paths, and reject any target outside the configured artifact root.
- Authoritative API artifact downloads now load artifact metadata and enforce workflow-run scope before blob reads; API and CLI download paths pass the DB-derived artifact root into blob reads.
- `shared_env` authoritative downloads reject `inmem://` storage URIs with a fail-closed forbidden response.
- Evidence: storage/API/shared-env artifact safety regressions passed on 2026-06-02.
- Closeout posture: `MP-PR002` is closed as a repo runtime safety gate; this is not CAPEX production activation.

## TASK-0236 closeout evidence
- The shared command-boundary module exposes `command_transaction(connection)`, which commits a command transaction or savepoint depending on caller context.
- Schedule-control output persistence and logistics handoff command handlers use the shared helper instead of local `BEGIN`/`BEGIN IMMEDIATE` transaction helpers.
- Evidence: transaction composition regressions passed on 2026-06-02, including outer-transaction execution and outer rollback of nested effects.
- Closeout posture: `MP-PR003` is closed as a repo runtime safety gate; this is not CAPEX production activation.

## TASK-0237 closeout evidence
- CAPEX invariant audit registry and CLI report resolved safety invariants as `hard_gate` and known CAPEX gaps as non-failing `known_gap` rows.
- Initial audit passed on 2026-06-02 with 4 hard gates green and 4 known gaps recorded.
- Evidence: focused invariant audit tests and direct `scripts/run_capex_invariant_audit.py` run passed.
- Closeout posture: `MP-PR004` is closed as a repo platform-readiness gate; this is not CAPEX production activation.

## TASK-0238 closeout evidence
- Shared generated-artifact helper canonicalizes JSON bytes, enforces expected digest and canonical partition validation, writes through root-confined blob storage, and emits canonical `artifact.version.created` events through existing artifact effects.
- Existing explicit artifact rows replay only when workflow, kind, digest, byte size, media type, role, and canonical partition fields match; conflicts raise `generated_artifact_conflict`.
- Evidence: focused generated-artifact helper tests passed on 2026-06-02.
- Closeout posture: `MP-PR005` is closed as a repo platform-readiness helper; broad generated-artifact migration remains later CAPEX scope.

## TASK-0239 closeout evidence
- Shared run/input/edge effect helpers centralize workflow-run resolution, workflow artifact input binding replay/conflict/replace semantics, and edge execution replay validation.
- `LogisticsRunResolver` rejects same-scope, same-partition activation-key drift before logistics handoff mutates target inputs or edge activation state.
- Evidence: focused helper tests, notify-only idempotency regression, and live-dispatch activation-key drift regression passed on 2026-06-02.
- Closeout posture: `MP-PR006` is closed as a repo platform-readiness/runtime safety gate; this is not CAPEX production activation.

## TASK-0240 closeout evidence
- `docs/planning/CAPEX_PLATFORM_FOUNDATION_V0.md` declares PF0 for repo platform readiness only and records the `foundation/ip5` branch gate matrix.
- PF0 keeps CAPEX runtime integration, raw corpus use, release/deploy work, project membership runtime, and SourceRef/source-occurrence runtime blocked until later gates close or receive explicit waivers.
- CAPEX invariant audit now reports ten hard gates green and four known gaps without turning known gaps permanently red.
- Closeout posture: `MP-PR007` is closed as a repo platform-readiness declaration; this is not CAPEX production activation, pilot readiness, or deployment approval.

## TASK-0241 closeout evidence
- Added an API-runtime `Dockerfile` for `onetruth-api` that defaults to `shared_env`, exposes `8080`, and carries no production secrets or deploy commands.
- `scripts/build_release_image.py` builds from `release_source_bundle`, optionally pushes to an operator-supplied image ref, records the digest-addressed image reference, and writes `release_manifest.json`.
- `schemas/release/release_manifest.schema.json` validates release image build evidence; focused release-image tests and release-readiness contract tests passed on 2026-06-02.
- Closeout posture: `MP-PR008` is closed as release-readiness build evidence only; this is not CAPEX production activation, pilot readiness, or deployment approval.

## TASK-0242 closeout evidence
- `scripts/prepare_predeploy_backup.py` validates the environment class, local SQLite DB, artifact root, release manifest, and secret-reference tuple before writing `backup_manifest.json`.
- The predeploy backup skeleton is `validate_only`; it records DB/artifact/release tuple evidence and secret/config references but does not copy live state, upload backups, restore data, or mutate runtime paths.
- `schemas/ops/backup_manifest.schema.json` validates backup manifest evidence; focused backup-manifest tests and release-readiness contract tests passed on 2026-06-02.
- Closeout posture: `MP-PR009` is closed as predeploy backup-manifest readiness only; restore proof and pilot readiness remain later CAPEX gates.

## TASK-0243 closeout evidence
- `scripts/run_lab_auth_smoke.py` runs a lab-only `/api/v1/viewer` smoke through the existing `shared_env` RS256 JWT resolver and sends conflicting browser identity headers.
- The smoke asserts server-derived identity wins, `request_context_mode=server_derived`, and `actor_switching_allowed=false`.
- `schemas/ops/lab_auth_smoke_report.schema.json` validates smoke evidence; focused auth-smoke tests and lab readiness contract tests passed on 2026-06-02.
- Closeout posture: `MP-PR010` is closed as lab-auth prototype readiness only; this is not CAPEX production activation, pilot approval, JWKS expansion, or pilot-password fallback.

## TASK-0244 blocked evidence
- `scripts/deploy_lab_vm.py` implements a lab-only GCP VM deploy plan/execute lane. Dry-run planning is default; execution requires `--execute --confirm-lab-target --confirm-no-real-users`.
- The lane validates release manifest/bundle coherence, lab SQLite/artifact-root arguments, and secret references, then permits only `gcloud compute scp` and `gcloud compute ssh`.
- Remote execute shape runs the validation-only predeploy backup manifest, installs `.[api]`, builds frontend assets, restarts the lab service, and smokes health/readiness/viewer/artifact-root posture.
- `schemas/ops/lab_vm_deploy_report.schema.json` validates deploy evidence; focused deploy-lane tests and lab readiness contract tests passed on 2026-06-02 with stubbed `gcloud`.
- CAPEX invariant audit reports PR011 pipeline implementation separately from live evidence: `live_deploy_evidence_recorded=false`.
- Blocker: no operator-supplied lab GCP project/zone/instance/remote paths/token env were available in this session, so no live lab VM execute-and-smoke run was performed. `MP-PR011` remains `BLOCKED` until that evidence exists.

## TASK-0245 closeout evidence
- `schedule-control.build-weekly` now uses the shared command receipt path with a workflow-run scope key, so identical requests replay from command receipt truth instead of mutating Stage04 outputs again.
- Weekly Stage04 output persistence now writes all six generated outputs through the canonical generated-artifact helper, producing root-confined `file://` storage URIs, byte sizes, content digests, and `artifact.version.created` events.
- Existing Stage04 provenance is preserved: every output links back to source input artifacts, and non-bundle outputs link back to the generated input bundle through explicit bundle-lowering edges.
- Evidence: focused schedule-control hardening and transaction composition regressions passed on 2026-06-02.
- Closeout posture: `MP-PR012` is closed as logistics domain/runtime safety hardening; this is not CAPEX production activation, raw-corpus use, or deployment approval.

## TASK-0246 closeout evidence
- Shared runtime effects now include a deterministic handoff effect scope with source artifact truth, target partition, policy version, and a stable scope key.
- Weekly seed materialization, live-dispatch activation/preparation, and notify-only handoff paths attach that scope metadata to edge execution state, workflow input binding metadata, and generated handoff artifact metadata.
- Evidence: focused runtime-effect helper tests and logistics handoff runtime regressions passed on 2026-06-02.
- Closeout posture: `MP-PR013` is closed as handoff scaffold/command-scope auditability only; behavior-complete weekly seed hardening, republish policy, and notify-only conflict tightening remain later EPIC-139 tasks.

## TASK-0247 closeout evidence
- Weekly seed materialization now writes service-day seed manifests through the canonical generated-artifact helper instead of authoritative `inmem://` seed rows.
- Full-week materialization creates seven `planning.daily_dispatch_seed.workbook` artifacts exactly once, with file-backed storage URIs, byte sizes, content digests, `artifact.version.created` events, parent/provenance links, handoff scope metadata, and EdgeExecution rows.
- Seed manifest content excludes volatile materialization idempotency keys so logical retries reuse the existing seed artifact and edge without digest conflicts.
- Evidence: focused runtime-effect helper tests and logistics handoff runtime regressions passed on 2026-06-02.
- Closeout posture: `MP-PR014` is closed as weekly seed materialization hardening; this is not CAPEX production activation, live deployment, or broader live-dispatch hardening.

## TASK-0248 closeout evidence
- Live-dispatch activation now detects when the weekly published artifact backing a prepared base seed has been superseded, records the edge as `stale`, and returns `live_dispatch_base_seed_republish_after_prepare` with `policy_state=late_weekly_republish_after_live_prepare`.
- Live-day preparation after `stage01.base_seed` is already bound now materializes the candidate seed and a stale policy edge instead of attempting to rebind the live input or falling through to `workflow_input_binding_conflict`.
- Target live-run lookup for the republish guard uses the logistics run resolver layer through `LogisticsRunResolver.find_live_dispatch(...)`.
- Evidence: focused logistics handoff runtime regressions passed on 2026-06-02.
- Closeout posture: `MP-PR015` is closed as live-dispatch republish hardening only; this is not CAPEX production activation, deployment approval, or broader planning-cycle policy completion.

## TASK-0249 closeout evidence
- Notify-only target input artifacts now write file-backed generated JSON manifests through the canonical generated-artifact helper rather than authoritative `inmem://` handoff rows.
- Reporting-to-planning late feedback in the default/shared-env path now fails closed with `late_reporting_handoff_conflict` before it can replace an existing weekly `stage03.actual_hours_snapshot` binding.
- Local compatibility merge-and-replace remains explicit to `ONETRUTH_API_BOUNDARY_PROFILE=local_dev` or `ci_test`; the safe/default path has `replace_on_conflict` disabled.
- Evidence: focused logistics handoff runtime regressions passed on 2026-06-02.
- Closeout posture: `MP-PR016` is closed as notify-only/reporting handoff hardening only; this is not CAPEX production activation, deployment approval, or planning-cycle policy completion.

## TASK-0250 closeout evidence
- `LogisticsCalendarPolicy` now defines same-week as `same_iso_planning_week`, records the deprecated `same_week` label as compatibility metadata, and maps reporting actuals to the next ISO planning week.
- The existing `service_day_to_future_planning_week` transform ID remains available but now resolves through the explicit calendar policy, including Sunday/year-end ISO rollover cases.
- Weekly seed and reporting-to-planning handoff scopes can carry deterministic `policy_context`; generated seed/notify artifacts and edge bindings record the relevant calendar policy evidence.
- Late weekly republish and late reporting decisions now carry named policy IDs while preserving their prior fail-closed error codes and compatibility `policy_state` values.
- Evidence: focused logistics calendar policy, handoff runtime, and runtime-effect helper regressions passed on 2026-06-02.
- Closeout posture: `MP-PR017` is closed as planning-cycle policy hardening only; this is not CAPEX production activation, deployment approval, raw-corpus use, or reconciler apply authorization.

## TASK-0251 closeout evidence
- Add-next-week route-demand workpage calls now route through canonical weekly-to-weekly carry-forward logic.
- Carry-forward creates or reuses the target weekly run once, ensures only `weekly_input_intake`, creates or reuses the target route-demand seed artifact, attaches it to intake, binds it as `stage04.route_slot_requirements`, records artifact provenance, and records a `weekly_to_weekly_carry_forward` EdgeExecution.
- The target seed payload is aligned to the target workflow run planning week, and weekly target run reuse now fails closed on activation-key drift.
- Regression coverage asserts there is no Stage04 work-item auto-spawn, execution session, or approval side effect during carry-forward.
- Evidence: focused add-next-week regression and full route-demand workpage API contract suite passed on 2026-06-02.
- Closeout posture: `MP-PR018` is closed as weekly-to-weekly input carry-forward only; this is not Stage04 auto-run, approval, CAPEX production activation, deployment approval, or reconciler apply authorization.

## TASK-0252 closeout evidence
- Added `logistics_reconciler_dry_run.v1`, a deterministic read-only report over weekly seed materialization, handoff edge integrity, notify-only target inputs, live target input bindings, and late reporting conflicts.
- Added CLI entrypoint `handoffs reconcile-dry-run`, which opens SQLite in read-only mode and exposes no apply/repair option.
- Findings include missing weekly daily seed artifacts/edges, stale edge executions, missing or drifted target run/input/artifact rows, and safe-profile late reporting input conflicts.
- Regression coverage snapshots canonical runtime table counts before and after dry runs and proves the missing-edge, stale-edge/missing-binding, and late-report conflict cases report findings without mutation.
- Evidence: focused reconciler regressions and the full logistics handoff runtime suite passed on 2026-06-02.
- Closeout posture: `MP-PR019` is closed as dry-run reporting only; this is not reconciler apply mode, CAPEX production activation, deployment approval, target-side repair authorization, or raw-corpus use.

## TASK-0253 closeout evidence
- App root `/` now renders an operator home surface instead of redirecting to `/demo/logistics`.
- Added `GET /api/v1/operator/home`, scoped by server-derived request context, to expose current viewer posture and the logistics reconciler dry-run failure-state report.
- Shared-env viewer posture now hides actor-switching controls entirely when `actor_switching_allowed=false`.
- The reconciler now reports missing file-backed artifact blobs without exposing local blob paths in findings.
- Failure-state fixtures cover missing seed, missing blob, late reporting conflict, and stale edge groups on the operator home surface.
- Evidence: focused backend operator-home/route-registry tests and frontend operator-home/viewer-bootstrap/root-route tests passed on 2026-06-02.
- Closeout posture: `MP-PR020` is closed as shared-env-safe operator visibility only; this is not CAPEX production activation, deployment approval, reconciler apply mode, target-side repair authorization, or raw-corpus use.

## TASK-0257 closeout evidence
- Generic `approval.respond` now records the approval row transition and emits `approval.responded`, then invokes the explicit approval-response hook registry.
- Weekly publish and dispatch-reporting finalize behavior moved to logistics hooks registered in `src/onetruth/application/services/approval_response_hooks.py` and implemented in `src/onetruth/application/services/logistics_approval_response_hooks.py`.
- `src/onetruth/application/handlers/approvals.py` no longer imports logistics handoff/build modules, artifact-version effect helpers, pointer-promotion effect helpers, or logistics publish/finalize constants.
- ADR-005 records the approval-response domain-hook boundary and rollback posture.
- CAPEX invariant audit now treats approval-response hook extraction as a hard gate instead of a known gap.
- Evidence: approval hook unit tests, handler import-boundary contract, CAPEX audit contract, approval CLI/API regressions, weekly publish approve/stale regressions, and dispatch-reporting finalize approve/stale regressions passed on 2026-06-02.
- Closeout posture: `CLEAN-001` is closed as domain-boundary cleanup only; this is not CAPEX production activation, deployment approval, raw-corpus use, or new CAPEX runtime behavior.

## TASK-0260 closeout evidence
- Added a repo-native `logistics_regression` pytest marker with classification truth in `tests/helpers/suite_markers.py`.
- `tests/conftest.py` applies the marker from the manifest at collection time, and `Makefile` exposes `platform-substrate-tests` plus `logistics-regression-tests`.
- `.github/workflows/main.yml` now surfaces both lanes as a visible `domain-boundary` CI matrix without weakening the existing broad required checks.
- Evidence: `tests/contract/test_platform_logistics_test_split.py` proves manifest coverage, logistics fixture-root classification, and Make/GitHub lane exposure.
- Closeout posture: `CLEAN-004` is closed as test/CI domain-boundary cleanup only; this is not broader `TASK-0492` marker taxonomy work and does not activate CAPEX runtime behavior.

## TASK-0369 closeout evidence
- Reconciled `RF-001` to the already-landed approval-response hook extraction from `TASK-0257`.
- Generic `approval.respond` remains limited to approval transition and event emission before registered domain hooks run in the same transaction.
- Evidence remains anchored in `ADR-005`, `src/onetruth/application/services/approval_response_hooks.py`, `src/onetruth/application/services/logistics_approval_response_hooks.py`, `tests/contract/test_handler_import_boundaries.py`, and `tests/unit/test_approval_response_hooks.py`.
- No new approval handler behavior was added for this reconciliation; `TASK-0561` is reconciled separately below.
- Closeout posture: `RF-001` is closed as duplicate-intent reconciliation only; this is not new CAPEX approval semantics or product activation.

## TASK-0370 closeout evidence
- Added a domain-neutral `WorkpageDescriptorRegistry` and `WorkpageDescriptorPack`.
- The active logistics schedule/EOD/route-demand/driver-preferences descriptor registrations now live in `LOGISTICS_WORKPAGE_DESCRIPTOR_PACK`; existing descriptor lookup helpers remain stable facades over the default registry.
- Workpage action subject-surface validation now consults registered workpage action rules for human-task and approval subjects instead of local schedule/EOD matrices.
- Evidence: descriptor registry unit tests, workpage action registry support checks, handler import-boundary contract, and workspace workpage action API regression passed on 2026-06-03.
- Closeout posture: `RF-002` is closed as domain-boundary extraction only; this is not a new public workpage API, CAPEX runtime activation, or product-route expansion.

## TASK-0561 closeout evidence
- Reconciled `NU-CB-P0-001` to the approval-response hook extraction already closed by `TASK-0257`, `TASK-0369`, and historical alias `TASK-0576`.
- Generic `approval.respond` remains limited to canonical approval transition and `approval.responded` event emission before registered domain hooks run in the same transaction.
- Evidence remains anchored in `ADR-005`, `src/onetruth/application/services/approval_response_hooks.py`, `src/onetruth/application/services/logistics_approval_response_hooks.py`, `tests/contract/test_handler_import_boundaries.py`, and `tests/unit/test_approval_response_hooks.py`.
- Focused approval-hook evidence passed again on 2026-06-03; no new approval handler behavior was added.
- Closeout posture: `NU-CB-P0-001` is closed as imported duplicate reconciliation only; this is not new CAPEX approval semantics, product activation, or deployment approval.

## TASK-0371 closeout evidence
- Added `onetruth.api.project_scope` to centralize project viewer resolution, caller role lookup, not-found project denial, project query decoration, project row stamping, path child parsing, optional workflow-run query checks, and workflow-run-in-project assertions.
- Refactored project child routes, broad workflow-run project filtering, artifact/timeline optional project checks, and dashboard counts to use the shared helper without changing project child API payloads or command names.
- Evidence: project-scope helper unit tests, CAPEX project child/access API regressions, route-registry tests, and route-layer boundary contracts passed on 2026-06-04.
- Closeout posture: `RF-003` is closed as source-of-truth hardening for project-scope APIs only; this is not CAPEX runtime activation, authorization projections, raw-corpus use, or richer workpage expansion.

## TASK-0265 closeout evidence
- Added CAPEX project official pointer family support on top of the existing canonical `artifact_pointers` promotion substrate, with no pointer ID format change and no migration.
- `project_id + pointer_family` maps to `scope_kind=capex_project`, `scope_ref={project_id}`, `pointer_key=official:{pointer_family}`, and `stream_key=capex-project:{project_id}:pointer-family:{pointer_family}` while reusing existing generation/CAS semantics.
- Officialness changes only through explicit promotion after project membership and project child-ownership checks; approval responses, approved approvals, and latest artifact rows do not move project official pointers by themselves.
- Evidence: official pointer family unit tests, project official pointer API tests, generic pointer-list regression, route-registry tests, and route-layer boundary contracts passed on 2026-06-04.
- Closeout posture: `PROJ-005` is closed as project official-pointer-family substrate only; pointer promotion request/policy checks, authorization projections, raw-corpus governance, richer CAPEX workpages, and activation remain later gated scope.

## TASK-0381 closeout evidence
- Added `onetruth.capex_platform.domain_runtime` with typed domain manifest dataclasses/loaders, duplicate-safe `DomainRuntimeRegistry`, ready/incubation/disabled grouping, and deterministic composition reports.
- Composition reports keep `activation_allowed=false`; this skeleton is composition inventory only, not CAPEX runtime activation.
- Added `schemas/domain_runtime/domain_manifest.schema.json` for Wave 1 domain manifests.
- Evidence: `tests/unit/test_domain_runtime_registry.py` proves empty composition, duplicate-domain rejection, readiness grouping, deterministic counts, and CAPEX platform import-boundary isolation.
- Closeout posture: `ARCH-W1-T001` is closed as neutral domain-runtime skeleton only; no domain behavior, route, schema migration, raw-corpus use, or CAPEX activation is implied.

## TASK-0382 closeout evidence
- Added `docs/domains/logistics/domain.yaml` as the ready-state logistics domain manifest inventory.
- The manifest mirrors `docs/workflows/logistics_ops_family/v1/WORKFLOW_FAMILY.yaml`, the active logistics workpage descriptor/action packs, logistics approval-response hooks, and workflow-family handoff edges.
- `DOC_INVENTORY.yaml` remains the logistics document-classification source; `domain.yaml` is runtime/domain inventory and does not register or execute behavior.
- Evidence: `tests/contract/test_domain_manifest_schema.py` validates schema compliance and raw-corpus exclusion; `tests/contract/test_logistics_domain_manifest.py` characterizes manifest rows against current logistics truth.
- Closeout posture: `ARCH-W1-T002` is closed as logistics inventory only; CAPEX incubation manifest, authorization projections, richer CAPEX workpages, raw-corpus governance, and activation remain later gated scope.

## TASK-0383 closeout evidence
- Added `docs/domains/capex/domain.yaml` as the incubation-state CAPEX domain manifest.
- The manifest intentionally inventories no workflows, workpages, or side effects because CAPEX workflow packs and workpage projections are not authored or accepted yet.
- Disabled-capability and readiness-prerequisite rows record project authorization evidence, plus remaining storage custody, source governance, workflow catalog, workpage projection, and production-preflight gates.
- Evidence: CAPEX domain manifest contract tests and domain manifest schema validation passed on 2026-06-05.
- Closeout posture: `ARCH-W1-T003` is closed as incubation inventory only; no CAPEX runtime activation, raw-corpus use, route, migration, or behavior registration is implied.

## TASK-0384 closeout evidence
- Added `ApprovalEffectRegistry` and `ApprovalEffectPack` behind the existing approval-response hook substrate.
- The default approval-effect registry remains empty and platform-neutral. Logistics hook selection remains available through the existing compatibility selector, which delegates to `LOGISTICS_APPROVAL_RESPONSE_EFFECT_REGISTRY`.
- Weekly planning and dispatch-reporting workflow IDs still receive the existing logistics hook tuple; CAPEX and unknown workflow IDs receive no hooks.
- Evidence: approval-effect registry unit tests, approval-response hook unit tests, handler import-boundary tests, logistics manifest characterization, and focused weekly/dispatch approval behavior regressions passed on 2026-06-05.
- Closeout posture: `ARCH-W1-T004` is closed as shadow-mode registry parity only; no new approval semantics, CAPEX hooks, API shape changes, routes, migrations, or activation behavior were added.

## TASK-0385 closeout evidence
- Added `docs/architecture/CAPEX_PROJECT_AUTHORIZATION_CED.md` as the accepted Wave 1 project authorization CED.
- The CED records `capex_projects.project_id` as the durable root, keeps `workflow_run_id` as an execution identity, and separates direct `project_memberships` from derived authorization projection/read-model concepts.
- `capex_project_authorization`, `capex_project_feature`, and `capex_user_project_view` remain derived projection concepts, not authoritative project truth.
- Evidence: project authorization CED contract tests passed on 2026-06-05.
- Closeout posture: `ARCH-W1-T005` is closed as design/CED evidence only; no projection tables, migration, route, frontend behavior, raw-corpus use, or activation behavior was added.

## TASK-0386 closeout evidence
- Added `AuthorizedProjectsQuery` as an internal backend-only prototype over existing direct project memberships.
- Existing project access helpers now delegate role lookup and read-visibility SQL/params through the prototype; project list payloads still return the existing row shape and `caller_role`.
- Non-members receive an empty authorized-project result, and project-bound broad reads continue hiding rows from same-tenant non-members while no-project rows remain readable.
- Evidence: authorized-project query unit tests and existing project visibility regressions passed on 2026-06-05.
- Closeout posture: `ARCH-W1-T006` is closed as query-prototype evidence only; physical authorization projection runtime state was later reconciled by `TASK-0563`, while policy expansion, raw-corpus use, and CAPEX runtime activation remain later gated scope.

## TASK-0563 closeout evidence
- Added additive `capex_project_authorization`, `capex_project_feature`, and `capex_user_project_view` runtime projection tables with SQLite bootstrap, Alembic migration, SQLAlchemy models, repositories, and runtime schemas.
- Migration backfills projection rows from existing `capex_projects` plus active `project_memberships`; direct membership remains authoritative source state.
- Added `refresh_project_authorization_projection`, `rebuild_project_authorization_projections`, and `ensure_project_feature_defaults` to keep authorization/user-view projections deterministic and repairable.
- Project create and membership grant commands refresh projections inside the same command transaction, and `AuthorizedProjectsQuery` now reads projection-backed rows while preserving project API payloads and no-project logistics/runtime visibility.
- `capex.runtime_activation` is seeded as `disabled` by default, so closing EPIC-140 does not activate CAPEX runtime/product behavior.
- Evidence: authorization projection unit tests, schema parity/backfill integration tests, existing project access regressions, CAPEX domain/invariant contracts, schema validation, and progress-data validation passed on 2026-06-05.
- Closeout posture: `NU-CB-P0-003` closes the final EPIC-140 task row. CAPEX activation, raw-corpus/source governance, workflow/workpage authoring, real pilot storage evidence or waiver, release/capacity, and production-preflight gates remain later work.

## TASK-0387 closeout evidence
- Added `docs/architecture/CAPEX_STORAGE_BLOB_CUSTODY_CED.md` as the accepted Wave 1 storage/blob custody schema-design boundary.
- The CED defines future concepts for `BlobRef`, `BlobReplica`, `BlobIngestSession`, `ArtifactVersionBlob`, `DerivedArtifact`, and `DownloadEvent`.
- The CED preserves one-truth artifact rules: `ArtifactVersion` remains canonical metadata, object/blob bytes are not authoritative alone, and `ArtifactPointer` targets `ArtifactVersion` only.
- Evidence: storage/blob custody CED contract tests passed on 2026-06-05.
- Closeout posture: `ARCH-W1-T007` is closed as design/CED evidence only; physical custody tables, migrations, routes, storage backend rollout, raw-corpus use, pilot readiness, and CAPEX runtime activation remain later gated scope.

## TASK-0388 closeout evidence
- Added `docs/planning/checklists/CAPEX_PILOT_STORAGE_GATE.md` with default gate result `blocked_pending_evidence`.
- The checklist covers Postgres decision or waiver, blob custody backend, backup/restore proof, digest verification, auth-before-read after restore, index rebuild proof, capacity/quota evidence, secret/config references, and reviewer signoffs.
- Evidence: pilot storage gate checklist contract tests passed on 2026-06-05.
- Closeout posture: `ARCH-W1-T008` is closed as checklist evidence only; the pilot storage gate is not passed, waived, or executed by this task, and CAPEX remains disabled.

## TASK-0389 closeout evidence
- Added `docs/architecture/CAPEX_W1_CODE_PATTERN_REGISTER.md` as the Wave 1 non-production code pattern register.
- The register covers exactly the current domain-runtime manifest registry, direct-membership project visibility, and storage/blob custody auth-before-download pattern families.
- It records forbidden overbuilds including dynamic domain package loading, frontend-only auth filtering, global project list exposure, blob truth bypassing `ArtifactVersion`, pointer targets to blobs, and storage reads before scope authorization.
- Evidence: W1 code pattern register contract tests passed on 2026-06-05.
- Closeout posture: `ARCH-W1-T009` is closed as illustrative architecture evidence only; snippets are not runnable source files and do not add migrations, routes, storage rollout, raw-corpus use, pilot readiness, or CAPEX runtime activation.

## TASK-0390 closeout evidence
- Added `docs/architecture/CAPEX_W1_CLOSEOUT_REVIEW.md` as the Wave 1 decision docket and closeout review.
- Gates `ARCH-W1-GATE-001` through `ARCH-W1-GATE-009` have repo evidence; `ARCH-W1-GATE-010` remains `blocked_pending_evidence` until real pilot storage evidence or an explicit waiver lands.
- The review records the overkill assessment, old-decision updates, and master patch posture as repo-native traceability text only.
- Evidence: W1 closeout review contract tests passed on 2026-06-05.
- Closeout posture: `ARCH-W1-T010` is closed as review evidence only; it does not grant pilot readiness, mutate the source ZIP, import raw project material, or activate CAPEX.

## TASK-0564 closeout evidence
- Added additive runtime state for `capex_content_identities` and `capex_source_occurrences`, including Alembic migration, SQLite bootstrap DDL, SQLAlchemy models, runtime schemas, repositories, and schema-parity coverage.
- Added `onetruth.capex_platform.source_refs` for canonical `source_occurrence:{source_occurrence_id}` resolution with tenant/domain/project scope checks, status checks, and meaningful-source-ref rejection for empty or presence-only evidence.
- Evidence: source occurrence resolver unit tests, schema-parity integration tests, schema validation, CAPEX domain/invariant contracts, and progress-data validation passed on 2026-06-08.
- Closeout posture: `NU-CB-P0-004` closes physical occurrence truth and resolver foundation only; corpus ingest, raw material handling, source occurrence relations, locator unions, extraction, and evidence binding remain later gated work.

## TASK-0565 closeout evidence
- Added additive runtime state for `capex_waivers`, `capex_closure_gate_evaluations`, and `capex_closure_snapshots`, including Alembic migration, SQLite bootstrap DDL, SQLAlchemy models, runtime schemas, repositories, and schema-parity coverage.
- Added `onetruth.capex_platform.closure_governance` with closure vector evaluation, explicit `satisfied_by_waiver` recording, failed-evaluation snapshot rejection, and a small recurrence rule registry that marks snapshots stale when basis refs change.
- Evidence: closure governance unit tests, schema-parity integration tests, schema validation, CAPEX domain/invariant contracts, and progress-data validation passed on 2026-06-08.
- Closeout posture: `NU-CB-P0-005` closes internal runtime primitives only; closure/promotion UI, public APIs, CAPEX runtime activation, generated artifact validators, and richer workpage command surfaces remain later gated work.

## TASK-0566 closeout evidence
- Added `capex.workflow_handoff_manifest.v1` and `onetruth.capex_platform.workflow_handoffs` as an internal handoff contract and validation guard.
- Handoff validation requires exact artifact version basis, pointer generation basis, meaningful SourceRefs, validation summaries, closure evaluation refs, current closure snapshot refs, and task/workpage handoff bindings.
- Evidence: handoff manifest unit and schema contract tests passed on 2026-06-08.
- Closeout posture: `NU-CB-P0-006` closes handoff manifest foundation only; authored CAPEX workflow packs, public workflow activation, and runtime/product activation remain later gated work.

## TASK-0567 closeout evidence
- Added `capex_workpage_projection_snapshots` and `capex_workpage_projection_rows`, including Alembic migration, SQLite bootstrap DDL, SQLAlchemy models, runtime schemas, repositories, and schema-parity coverage.
- Added signed projection cursor and typed command-envelope guards that reject invalid signatures, expired cursors, scope mismatch, stale/superseded snapshots, and basis mismatch before any mutation callback runs.
- Evidence: projection snapshot, command-envelope, schema-parity, and command receipt tests passed on 2026-06-08.
- Closeout posture: `NU-CB-P0-007` closes internal workpage projection/stale-command foundation only; public CAPEX workpage APIs, frontend workpage routes, hydration families, performance batteries, and activation remain later gated work.

## TASK-0568 closeout evidence
- Added `capex_semantic` as a repo-native pytest marker with auto-classification from `tests/helpers/suite_markers.py`.
- Added `docs/planning/CAPEX_CB2_SEMANTIC_TEST_BACKLOG.yaml` tracking `CB2-T001` through `CB2-T014` with current repo evidence or explicit future-phase disposition.
- Added `make capex-semantic-tests`, a visible `.github/workflows/main.yml` CAPEX semantic lane, and real-owner `.github/CODEOWNERS` entries.
- Evidence: CAPEX semantic manifest and CODEOWNERS gate contract tests passed on 2026-06-09.
- Closeout posture: `NU-CB-P0-008` closes quality-gate evidence only; hosted branch-protection settings, richer review-tier automation, public CAPEX routes, raw corpus use, and CAPEX runtime activation remain later or operator-managed scope.

## TASK-0569 closeout evidence
- Added `onetruth.capex_platform.interface_burden` with accepted states `owned`, `transferred`, `waived`, `accepted_residual`, and `open`.
- The helper fails closed when responsibility lacks an owner, transfer target, waiver, residual acceptance, traceable basis, or open follow-up owner, and returns deterministic follow-up task specs without creating runtime tasks.
- Added `docs/architecture/CAPEX_INTERFACE_BURDEN_POLICY.md` as the authoritative policy record.
- Evidence: interface-burden unit and document contract tests passed on 2026-06-09.
- Closeout posture: `NU-CB-P1-009` closes internal policy/prototype evidence only; public interface queues, workflow/workpage task routing, raw corpus use, and CAPEX runtime activation remain later gated work.

## TASK-0582 / TASK-0583 closeout evidence
- Added `docs/planning/capex_delivery/MASTER_Product_Goal_and_Metrics.md`, `Product_Goal_Metric_Stack.csv`, and `Vertical_Slice_Ladder.csv` as planning-governance evidence for `SD-TASK-001` and `SD-TASK-002`.
- Evidence: CAPEX delivery-governance semantic contract tests cover the product goal, required metric categories, no velocity-only metric bias, exact `VS-00` through `VS-05` ladder rows, valid metric refs, and non-activation posture.
- Closeout posture: `SD-TASK-001` and `SD-TASK-002` are planning-only closeouts. They do not activate CAPEX runtime/product behavior, public routes, workflow packs, raw corpus import, pilot readiness, production readiness, or product activation.

## TASK-0584 / TASK-0585 closeout evidence
- Added `docs/planning/capex_delivery/MASTER_Dependency_Register.csv` and `Risk_Based_Milestone_Model.csv` as planning-governance evidence for `SD-TASK-003`.
- Added `docs/planning/capex_delivery/Backlog_Taxonomy_and_Decomposition_Guide.md` and `docs/planning/capex_delivery/templates/` as planning-governance evidence for `SD-TASK-004`.
- Evidence: CAPEX delivery-governance semantic contract tests cover dependency ownership, needed-by milestones, mitigations, risk-if-late text, exact risk milestone names, valid dependency refs, production-ready blockers, singular backlog hierarchy, template requirements, no demo-only success criteria, raw-corpus boundary, and non-activation posture.
- Closeout posture: `SD-TASK-003` and `SD-TASK-004` are planning-only closeouts. They do not activate CAPEX runtime/product behavior, public routes, workflow packs, raw corpus import, pilot readiness, production readiness, delivery cadence, first-90-days overlay, DoR/DoD, or product activation.

## TASK-0586 / TASK-0587 closeout evidence
- Added `docs/planning/capex_delivery/MASTER_Delivery_Operating_Cadence.md` as planning-governance evidence for `SD-TASK-005`.
- Added `docs/planning/capex_delivery/MASTER_First_90_Days_Execution_Overlay.md` as planning-governance evidence for `SD-TASK-006`.
- Evidence: CAPEX delivery-governance semantic contract tests cover cadence rhythms, lean-governance/no-meeting-bloat guardrails, accepted inputs/outputs, decision records, range-based first-quarter planning, existing metric/slice/dependency/milestone refs, no false date precision, raw-corpus boundary, and non-activation posture.
- Closeout posture: `SD-TASK-005` and `SD-TASK-006` are planning-only closeouts. They do not activate CAPEX runtime/product behavior, public routes, workflow packs, raw corpus import, pilot readiness, production readiness, DoR/DoD, or product activation.

## TASK-0588 / TASK-0589 closeout evidence
- Added `docs/planning/capex_delivery/MASTER_Definition_of_Ready_Done.md` and patched `.github/pull_request_template.md` as planning-governance evidence for `SD-TASK-007`.
- Added `docs/planning/capex_three_project_validation/THREE_PROJECT_FIXTURE_GOVERNANCE_RUNBOOK.md` as planning-governance evidence for `TP-TASK-001`.
- Evidence: CAPEX delivery-governance and real-project acceptance contract tests cover task-class DoR/DoD, PR-template consistency, fixture tier handling for K12/K3/blind validation, TP gate references, no raw corpus leakage, no project-specific hardcoding policy, non-activation posture, and downstream-gate boundaries.
- Closeout posture: `SD-TASK-007` and `TP-TASK-001` are planning-only closeouts. They do not activate CAPEX runtime/product behavior, public routes, workflow packs, raw corpus import, fixture release, expected-output manifests, oracle manifests, blind baseline runs, pilot readiness, production readiness, or product activation.

## TASK-0590 / TASK-0591 closeout evidence
- Added `docs/planning/capex_three_project_validation/K12_EXPECTED_OUTPUT_MANIFEST.yaml` as sanitized planning evidence for `TP-TASK-002`.
- Added `docs/planning/capex_three_project_validation/K3_MINI_FIXTURE_EXPECTATION_CATALOG.yaml` as sanitized planning evidence for `TP-TASK-003`.
- Evidence: CAPEX real-project acceptance contract tests cover source package hashes, gate refs, K12 oracle rows, K12 hardening rows, K3 expectation rows, K3 freeze families, raw-data boundaries, and non-activation posture.
- Closeout posture: `TP-TASK-002` and `TP-TASK-003` are planning-only closeouts. They do not activate CAPEX runtime/product behavior, public routes, workflow packs, raw corpus import, fixture release, universal oracle manifest format, blind baseline runs, cross-project scorecard, pilot readiness, production readiness, or product activation.

## TASK-0592 / TASK-0593 closeout evidence
- Added `docs/planning/capex_three_project_validation/BLIND_VALIDATION_FREEZE_PROTOCOL.yaml` as planning evidence for `TP-TASK-004`.
- Added `docs/planning/capex_three_project_validation/CROSS_PROJECT_INVARIANT_SCORECARD.yaml` as planning evidence for `TP-TASK-005`.
- Evidence: CAPEX real-project acceptance contract tests cover freeze dimensions, access controls, baseline custody, leak-scan requirements, Agent Lab non-authority, scorecard tiers, invariant rows, status vocabulary, waiver requirements, raw-data boundaries, and non-activation posture.
- Closeout posture: `TP-TASK-004` and `TP-TASK-005` are planning-only closeouts. They do not activate CAPEX runtime/product behavior, public routes, workflow packs, raw corpus import, fixture release, blind baseline execution, `TP-G11` pass status, pilot readiness, production readiness, or product activation.

## TASK-0594 / TASK-0595 closeout evidence
- Added `docs/planning/capex_three_project_validation/AGENT_LAB_EVAL_MATRIX.yaml` as planning evidence for `TP-TASK-006`.
- Added `docs/planning/capex_three_project_validation/OFF_REPO_FULL_CORPUS_RUNBOOK.yaml` as planning evidence for `TP-TASK-007`.
- Evidence: CAPEX real-project acceptance contract tests cover Agent Lab fixture tiers, evidence refs, non-authority boundaries, advisory rollup posture, off-repo quarantine, read-only raw-corpus access, sanitized aggregate outputs, leak scan, teardown, rollback/remediation, capacity/restore placeholders, raw-data boundaries, and non-activation posture.
- Closeout posture: `TP-TASK-006` and `TP-TASK-007` are planning-only closeouts. They do not activate CAPEX runtime/product behavior, public routes, workflow packs, raw corpus import, fixture release, blind baseline execution, Agent Lab official authority, `TP-G10` or `TP-G11` pass status, pilot readiness, production readiness, or product activation.

## TASK-0596 / TASK-0597 closeout evidence
- Added `docs/planning/capex_three_project_validation/NO_OVERFITTING_REVIEW_CHECKPOINT.yaml` as planning evidence for `TP-TASK-008`.
- Added `docs/planning/capex_three_project_validation/PROJECT_ORACLE_MANIFEST_FORMAT.yaml` as planning evidence for `TP-TASK-009`.
- Evidence: CAPEX real-project acceptance contract tests cover no-overfitting classifications, required checkpoint fields, blocked-pending-baseline posture, cross-tier oracle row families, human oracle approval contract, compatibility refs from K12/K3 evidence files, raw-data boundaries, and non-activation posture.
- Closeout posture: `TP-TASK-008` and `TP-TASK-009` are planning-only closeouts. They do not activate CAPEX runtime/product behavior, public routes, workflow packs, raw corpus import, fixture release, blind baseline execution, blind tuning approval, `TP-G08`/`TP-G11` pass status, pilot readiness, production readiness, or product activation.

## Current-code blocker mappings
| Blocker | CAPEX task refs | Current repo surface |
|---|---|---|
| Approval response domain-hook extraction and registry shadow parity | `TASK-0257`, `TASK-0369`, `TASK-0384`, `TASK-0561` | `src/onetruth/application/services/approval_response_hooks.py`, `src/onetruth/application/services/logistics_approval_response_hooks.py`, `docs/adr/ADR-005-approval-response-domain-hooks.md` |
| Workpage descriptor/action domain boundary | `TASK-0258`, `TASK-0370` | `src/onetruth/application/services/workpage_action_registry.py`, `src/onetruth/application/services/workpage_descriptor_registry.py`, `src/onetruth/application/services/logistics_workpage_descriptors.py` |
| CAPEX domain-runtime manifest skeleton and domain inventories | `TASK-0381`, `TASK-0382`, `TASK-0383` | `src/onetruth/capex_platform/domain_runtime/`, `schemas/domain_runtime/domain_manifest.schema.json`, `docs/domains/logistics/domain.yaml`, `docs/domains/capex/domain.yaml`; CAPEX remains incubation and disabled |
| Platform/logistics test split | `TASK-0260` | `tests/helpers/suite_markers.py`, `tests/contract/test_platform_logistics_test_split.py`, `Makefile`, `.github/workflows/main.yml` |
| Artifact auth-before-read and storage confinement | `TASK-0235`, `TASK-0562` | `src/onetruth/api/routes/artifacts.py`, `src/onetruth/application/handlers/artifacts.py`, `src/onetruth/infrastructure/artifacts/storage.py` |
| Transaction composition safety | `TASK-0236` | `src/onetruth/application/handlers/schedule_control.py`, `src/onetruth/application/handlers/logistics_handoff.py` |
| Invariant audit harness | `TASK-0237` | `src/onetruth/application/services/capex_invariant_audit.py`, `scripts/run_capex_invariant_audit.py` |
| Canonical generated-artifact helper | `TASK-0238` | `src/onetruth/application/handlers/_shared/artifact_effects.py` |
| Shared run/input/edge helpers and logistics run resolver | `TASK-0239` | `src/onetruth/application/handlers/_shared/runtime_effects.py`, `src/onetruth/application/services/logistics_run_resolver.py` |
| Platform Foundation v0 declaration and branch gate | `TASK-0240` | `docs/planning/CAPEX_PLATFORM_FOUNDATION_V0.md` |
| Release image and manifest build evidence | `TASK-0241` | `scripts/build_release_image.py`, `schemas/release/release_manifest.schema.json`, `Dockerfile` |
| Validate-only predeploy backup manifest skeleton | `TASK-0242` | `scripts/prepare_predeploy_backup.py`, `schemas/ops/backup_manifest.schema.json` |
| Lab-only shared-env JWT viewer smoke | `TASK-0243` | `scripts/run_lab_auth_smoke.py`, `schemas/ops/lab_auth_smoke_report.schema.json` |
| Lab VM deploy pipeline implemented; live evidence pending | `TASK-0244` | `scripts/deploy_lab_vm.py`, `schemas/ops/lab_vm_deploy_report.schema.json`, `docs/ops/runbooks/lab_auth_and_vm_deploy.md` |
| Weekly Stage04 generated output hardening | `TASK-0245` | `src/onetruth/application/handlers/schedule_control.py`, `tests/runtime/test_schedule_control_hardening.py` |
| Handoff effect scopes with source truth/target partition/policy version | `TASK-0246` | `src/onetruth/application/handlers/_shared/runtime_effects.py`, `src/onetruth/application/handlers/logistics_handoff.py` |
| File-backed weekly seed materialization | `TASK-0247` | `src/onetruth/application/handlers/logistics_handoff.py`, `tests/runtime/test_logistics_handoff_runtime.py` |
| Live-dispatch republish-after-prepare policy guard | `TASK-0248` | `src/onetruth/application/handlers/logistics_handoff.py`, `src/onetruth/application/services/logistics_run_resolver.py`, `tests/runtime/test_logistics_handoff_runtime.py` |
| File-backed notify-only manifests and shared-env late-report guard | `TASK-0249` | `src/onetruth/application/handlers/logistics_handoff.py`, `tests/runtime/test_logistics_handoff_runtime.py` |
| Logistics reconciler dry-run report | `TASK-0252` | `src/onetruth/application/services/logistics_reconciler.py`, `src/onetruth/cli/__main__.py`, `tests/runtime/test_logistics_handoff_runtime.py` |
| Operator home failure-state surface | `TASK-0253` | `src/onetruth/api/routes/operator_home.py`, `frontend/src/pages/OperatorHomePage.tsx`, `frontend/src/app/AppShell.tsx` |
| CAPEX project child APIs and authorization projections | `TASK-0263`, `TASK-0371`, `TASK-0265`, `TASK-0385`, `TASK-0386`, `TASK-0563` | first project child APIs, selector/dashboard, project-scope helper, official pointer-family substrate, project authorization CED, projection-backed `AuthorizedProjectsQuery`, and physical authorization projection runtime state are closed; pointer-promotion policy checks, source governance, and activation remain blocked |
| CAPEX storage/blob custody and pilot storage gate | `TASK-0387`, `TASK-0388`, `TASK-0390` | storage/blob custody CED and pilot storage gate checklist are closed; real pilot storage evidence or explicit waiver, Postgres/blob backend rollout, and activation remain blocked |
| CAPEX Wave 1 pattern and closeout evidence | `TASK-0389`, `TASK-0390` | W1 code pattern register and closeout review are closed as non-production traceability; no runtime activation, source ZIP mutation, or pilot go decision is implied |
| Source occurrence / SourceRef | `TASK-0268`, `TASK-0391`, `TASK-0407`, `TASK-0428`, `TASK-0564` | `TASK-0564` adds physical occurrence truth and the first SourceRef resolver; broader corpus ingest, source occurrence relations, locator unions, and evidence binding remain future work |
| Closure and waiver runtime primitives | `TASK-0432`, `TASK-0436`, `TASK-0438`, `TASK-0443`, `TASK-0444`, `TASK-0565` | `TASK-0565` adds waiver/evaluation/snapshot state plus stale recurrence helpers; generated artifact validators, public closure commands, workpage surfaces, and activation remain future work |
| Workflow handoff manifest foundation | `TASK-0566`, `TASK-0581` | `TASK-0566` adds internal handoff manifest schema and validation guard; authored CAPEX workflow packs and activation remain future work |
| Workpage projection snapshot and stale-command foundation | `TASK-0451`, `TASK-0453`, `TASK-0460`, `TASK-0462`, `TASK-0567` | `TASK-0567` adds internal project-scoped projection snapshots, signed cursors, command envelopes, and stale-command guards; public APIs, frontend routes, hydration families, and activation remain future work |
| CAPEX semantic test and CODEOWNERS gate | `TASK-0568` | `capex_semantic` marker, CB2 backlog manifest, focused Make/GitHub lane, and real-owner CODEOWNERS entries are present; hosted branch protection and richer review automation remain external or later scope |
| Interface burden conservation | `TASK-0569` | `onetruth.capex_platform.interface_burden` and `docs/architecture/CAPEX_INTERFACE_BURDEN_POLICY.md` require responsibility to be owned, transferred, waived, accepted residual, or open with follow-up; public routing remains future work |

## Verification commands
- `python3 scripts/import_capex_v6_plan.py check --master-zip <CAPEX_v6_master_zip>`
- `python3 scripts/validate_repo.py`
- `make schema-validate`
- `git diff --check`
