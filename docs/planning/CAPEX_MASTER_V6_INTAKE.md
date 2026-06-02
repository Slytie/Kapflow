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

## Current-code blocker mappings
| Blocker | CAPEX task refs | Current repo surface |
|---|---|---|
| Approval response domain coupling | `TASK-0257`, `TASK-0561`, `TASK-0576` | `src/onetruth/application/handlers/approvals.py` |
| Artifact auth-before-read and storage confinement | `TASK-0235`, `TASK-0562`, `TASK-0577` | `src/onetruth/api/routes/artifacts.py`, `src/onetruth/application/handlers/artifacts.py`, `src/onetruth/infrastructure/artifacts/storage.py` |
| Transaction composition safety | `TASK-0236` | `src/onetruth/application/handlers/schedule_control.py`, `src/onetruth/application/handlers/logistics_handoff.py` |
| CAPEX project membership runtime | `TASK-0261`..`TASK-0263`, `TASK-0385`, `TASK-0386`, `TASK-0563` | future CAPEX project scope runtime |
| Source occurrence / SourceRef | `TASK-0268`, `TASK-0391`, `TASK-0407`, `TASK-0428`, `TASK-0564`, `TASK-0578` | future source occurrence and evidence resolver |

## Verification commands
- `python3 scripts/import_capex_v6_plan.py check --master-zip <CAPEX_v6_master_zip>`
- `python3 scripts/validate_repo.py`
- `make schema-validate`
- `git diff --check`
