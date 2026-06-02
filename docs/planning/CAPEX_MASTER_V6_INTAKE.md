# CAPEX Master Plan v6 Intake

Imported on `2026-06-01` as repo-native planning backlog memory.

## Source package
- Active package: `CAPEX_Master_Plan_Three_Project_Testing_Production_Preflight_Final_v6.zip`
- SHA256: `ea06571a2e4667487cac3ee870dd91a5489b4ed52edbff2cd96e4c0473d54b95`
- ZIP entries observed: 254
- ZIP files observed: 254
- ZIP uncompressed bytes observed: 1951212
- Supersedes: v5 and earlier CAPEX master planning packages for future conversion work.

## Validation row counts
| Register | Rows |
|---|---:|
| Task backlog | 374 |
| Acceptance gates | 270 |
| Risk register | 222 |
| Dependency register | 12 |
| Catalog | 139 |
| Open decisions | 23 |
| Traceability | 178 |

The v6 package reported zero CSV parse failures, zero JSON parse failures, zero duplicate ID failures, zero semantic coverage failures, and zero raw project filename hits.

## Repo integration status
- Converted source task rows: `374`.
- Repo task range: `TASK-0233` through `TASK-0606`.
- Repo epic range: `EPIC-136` through `EPIC-152`.
- Runtime/API/schema/DB/workpage changes in this import: none.
- All converted tasks start as `TODO`.
- CAPEX production-like activation remains blocked by the imported P0, three-project, data-governance, capacity/restore, release, and production-preflight gates.

## Project corpus provenance
Only aggregate ZIP-level metadata is recorded here. The project corpora remain outside the repo and must be mounted read-only only through an approved off-repo runbook.

| Assumed role | ZIP label | SHA256 | Files | Entries | ZIP bytes | Uncompressed bytes | Top extensions |
|---|---|---|---:|---:|---:|---:|---|
| K12 primary MVP fixture candidate | `Projektordner - Kopie-20260601T115514Z-3-001.zip` | `4cb59351dfbf618ac713cbf92e469b4e083c6dd50be4a7506e6a90802c1618ec` | 543 | 548 | 407676260 | 492024604 | .pdf:294, .xlsx:75, .csv:40, .docx:27, .cfg:19, .msg:15, .jpg:15, .ipt:13 |
| K3 shadow/regression fixture candidate | `Reference Project K3.zip` | `fdf11a2a378a446e2984cb6075f0e6eb64f839051ad7f4c53a648fb41fedf8fb` | 837 | 979 | 1502842547 | 1635719705 | .pdf:300, .pptx:184, .docx:138, .xlsx:81, .db:31, .jpeg:28, .doc:22, .lnk:16 |
| Blind/third-validation holdout candidate | `11639 OTC Alma Ruma Kanada.zip` | `9f098c8de46e05a9032d22460de304dd2e94de98356f77a7319d8900f6733a2c` | 2724 | 2908 | 690541632 | 970109741 | .pdf:1126, .doc:326, .psm:299, .xls:270, .cfg:213, .asm:207, .txt:99, .db:99 |

## Raw-data boundary
- Do not commit extracted project files, internal project paths, raw document text, screenshots, prompts, completions, or logs containing raw project content.
- Commit only sanitized fixtures, manifests, hashes, aggregate reports, and policy/evidence records approved by the relevant CAPEX fixture-governance task.
- Blind-validation outputs must not be inspected or tuned against before the freeze and baseline protocol tasks have completed.
- Workflow Lab outputs remain non-authoritative and cannot promote pointers, approve claims, close technical state, or mutate production truth.

## Generated companion artifacts
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`
- `docs/planning/epics/EPIC-136.md` through `docs/planning/epics/EPIC-152.md`
- `codex/context/EPIC-136.md` through `codex/context/EPIC-152.md`
- `codex/tasks/TASK-0233-*.md` through `codex/tasks/TASK-0606-*.md`

## TASK-0233 closeout evidence
Closed on `2026-06-01` as a planning/source-freeze task with no runtime/API/schema/DB/workpage activation.

Evidence recorded:
- CAPEX v6 source hash, package counts, row counts, and project ZIP aggregate provenance are recorded above.
- All `374` v6 source task rows are mapped to `TASK-0233` through `TASK-0606`.
- All `270` gates, `222` risks, and `23` open decisions are preserved in `docs/planning/CAPEX_V6_GATE_RISK_DECISION_MAP.csv`.
- CAPEX remains gated; production-like activation is still blocked by P0, three-project, raw-data governance, capacity/restore, release, and preflight gates.

Current-code blocker mappings:
- Approval response domain coupling is tracked by `TASK-0257`, `TASK-0561`, and `TASK-0576`; the current implementation surface is `src/onetruth/application/handlers/approvals.py`.
- Artifact download auth-before-read is tracked by `TASK-0235`, `TASK-0562`, and `TASK-0577`; the current implementation surfaces are `src/onetruth/api/routes/artifacts.py` and `src/onetruth/application/handlers/artifacts.py`.
- CAPEX project/membership runtime state is tracked by `TASK-0261` through `TASK-0263`, `TASK-0385`, `TASK-0386`, and `TASK-0563`.
- Source occurrence and SourceRef resolver work is tracked by `TASK-0268`, `TASK-0391`, `TASK-0407`, `TASK-0428`, `TASK-0564`, and `TASK-0578`.

Verification used for this closeout:
- `python3 scripts/import_capex_v6_plan.py check --master-zip /Users/tylerclark/Downloads/CAPEX_Master_Plan_Three_Project_Testing_Production_Preflight_Final_v6.zip`
- `python3 scripts/validate_repo.py`
- `make schema-validate`
- `git diff --check`
