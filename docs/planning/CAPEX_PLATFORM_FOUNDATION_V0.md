# CAPEX Platform Foundation v0

## Declaration
- Status: `DECLARED_FOR_REPO_PLATFORM_READINESS`
- Declaration date: `2026-06-02`
- Scope: CAPEX `PR000` through `PR007` platform-readiness gates are closed for repo engineering runtime work.
- This declaration is not CAPEX production activation, pilot approval, release/deploy approval, raw-corpus approval, pointer-promotion policy approval, or richer CAPEX workpage approval.

## PR000-PR007 Evidence Matrix
| Gate | Repo task | Status | Evidence |
|---|---|---|---|
| PR000 | TASK-0233 | closed | CAPEX v6 intake, source counts, blocker map, and conversion evidence recorded. |
| PR001 | TASK-0234 | closed | Release-bundle hygiene, repo-wide `node_modules/` exclusion, and no-secret Cloud Build PR skeleton. |
| PR002 | TASK-0235 | closed | Artifact storage confinement, auth-before-read ordering, and shared-env `inmem://` fail-closed posture. |
| PR003 | TASK-0236 | closed | Savepoint-aware command transactions used by schedule-control and logistics-handoff handlers. |
| PR004 | TASK-0237 | closed | CAPEX invariant audit harness reports hard gates and non-failing known gaps. |
| PR005 | TASK-0238 | closed | Canonical generated-artifact helper validates digest, partition, storage, replay, and conflict behavior. |
| PR006 | TASK-0239 | closed | Shared run/input/edge effect helpers and `LogisticsRunResolver` reject activation-key drift. |
| PR007 | TASK-0240 | closed | This PF0 declaration and branch gate matrix record allowed and blocked engineering runtime scope. |

## Branch Gate Matrix
| Branch class | Recommended branch | Allowed mutation scope | Required guardrails |
|---|---|---|---|
| Platform foundation | `foundation/ip5` | Shared platform helpers, safety checks, repo-native planning evidence, and focused logistics runtime safety regressions. | CAPEX invariant audit green for hard gates; `python3 scripts/validate_repo.py`; `make schema-validate`; no raw corpus files. |
| Logistics continuation | `codex/*` | Existing logistics weekly/live/workpage implementation focus when it preserves one-truth runtime semantics. | Focused runtime/API/workpage tests plus repo validation. |
| CAPEX runtime integration | blocked until later CAPEX gates | No production-like CAPEX activation in PF0. | Requires project/access, data-governance, release, capacity/restore, and preflight gates or explicit waiver. |
| Release/deploy | blocked until EPIC-138/EPIC-150 gates | No deploy commands, production secrets, image release, or production DB/artifact-root mutation. | Requires release pipeline, deployment review, backup/restore evidence, and operator-managed branch protection. |

## Explicitly Blocked Scopes
- CAPEX production activation and pilot readiness claims remain blocked.
- Raw K12, K3, and blind-validation corpus files, extracted filenames, screenshots, embedded text, OCR, and search output remain off-repo and out of CI.
- Release/deploy work, production secrets, production DB URLs, and production artifact-root mutation remain out of scope.
- CAPEX project child APIs, authorization projections, storage custody gates, domain manifests, and Wave 1 closeout evidence: the first project child API, selector/dashboard, project-scope helper, official pointer-family substrate, neutral domain-runtime skeleton, ready logistics manifest inventory, CAPEX incubation manifest, approval-effect registry shadow parity, project authorization CED, projection-backed `AuthorizedProjectsQuery`, rebuildable authorization projection runtime state, storage/blob custody CED, pilot storage gate checklist, W1 code pattern register, and W1 closeout review slices are closed. Pointer-promotion policy checks, real pilot storage evidence or waiver, richer CAPEX workpages/projections, raw-corpus governance dependencies, and runtime activation remain blocked until later governance tasks close.
- Source occurrence and SourceRef runtime foundation is present through `TASK-0564`; internal same-project source occurrence relation state and ingest batch/job/attempt/log state are present through `TASK-0392` and `TASK-0393`. Broader corpus ingest activation, locator unions, queue workers, extraction/OCR/search runtime, and evidence binding remain blocked until later EPIC-141 tasks close.
- Workflow handoff manifest, workpage projection/stale-command foundations, and internal workpage command activation/idempotency guards are present through `TASK-0566` and `TASK-0567`; authored CAPEX workflow packs, public CAPEX workpage APIs, frontend CAPEX workpage routes, projection hydration families, and runtime activation remain blocked until later EPIC-143/144 tasks close.
- CAPEX semantic test, red-team probe audit hard gates, and interface-burden foundations are present through `TASK-0568` and `TASK-0569`; hosted branch-protection enforcement, richer review-tier automation, public interface queues, workflow/workpage routing, raw-corpus governance dependencies, and runtime activation remain blocked until later tasks close.
- Hosted branch-protection settings remain external/operator-managed; this repo records expected posture but does not claim hosted settings are configured.

## Verification Contract
- `python3 scripts/import_capex_v6_plan.py check --master-zip <CAPEX_v6_master_zip>`
- `python3 scripts/run_capex_invariant_audit.py --output-root <tmp-output-root> --json`
- `python3 scripts/validate_repo.py`
- `make schema-validate`
- `git diff --check`
