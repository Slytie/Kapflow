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

## Current-code blocker mappings
| Blocker | CAPEX task refs | Current repo surface |
|---|---|---|
| Approval response domain coupling | `TASK-0257`, `TASK-0561`, `TASK-0576` | `src/onetruth/application/handlers/approvals.py` |
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
| CAPEX project membership runtime | `TASK-0261`..`TASK-0263`, `TASK-0385`, `TASK-0386`, `TASK-0563` | future CAPEX project scope runtime |
| Source occurrence / SourceRef | `TASK-0268`, `TASK-0391`, `TASK-0407`, `TASK-0428`, `TASK-0564`, `TASK-0578` | future source occurrence and evidence resolver |

## Verification commands
- `python3 scripts/import_capex_v6_plan.py check --master-zip <CAPEX_v6_master_zip>`
- `python3 scripts/validate_repo.py`
- `make schema-validate`
- `git diff --check`
