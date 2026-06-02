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
- Current-code blocker mappings recorded for approval domain coupling, artifact auth-before-read, CAPEX project access, and source occurrence/evidence.
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

## Current-code blocker mappings
| Blocker | CAPEX task refs | Current repo surface |
|---|---|---|
| Approval response domain-hook extraction | `TASK-0257`, `TASK-0561`, `TASK-0576` | `src/onetruth/application/services/approval_response_hooks.py`, `src/onetruth/application/services/logistics_approval_response_hooks.py`, `docs/adr/ADR-005-approval-response-domain-hooks.md` |
| Artifact auth-before-read and storage confinement | `TASK-0235`, `TASK-0562`, `TASK-0577` | `src/onetruth/api/routes/artifacts.py`, `src/onetruth/application/handlers/artifacts.py`, `src/onetruth/infrastructure/artifacts/storage.py` |
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
| CAPEX project membership runtime | `TASK-0261`..`TASK-0263`, `TASK-0385`, `TASK-0386`, `TASK-0563` | future CAPEX project scope runtime |
| Source occurrence / SourceRef | `TASK-0268`, `TASK-0391`, `TASK-0407`, `TASK-0428`, `TASK-0564`, `TASK-0578` | future source occurrence and evidence resolver |

## Verification commands
- `python3 scripts/import_capex_v6_plan.py check --master-zip <CAPEX_v6_master_zip>`
- `python3 scripts/validate_repo.py`
- `make schema-validate`
- `git diff --check`
