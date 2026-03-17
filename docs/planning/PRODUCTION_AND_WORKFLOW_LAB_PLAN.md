# Production lane + Workflow Lab plan

## Why this plan exists
The repo is now strong enough internally that the next stage should not be framed as another semantics-cleanup tranche.

The system now needs to support **one stable first-user production lane** while also supporting **safe candidate workflow/process/task development outside production**.

The core model is:

- `P = stable production lane`
- `L = internal Workflow Lab lane`
- `G = promotion / release / certification gate`

The healthy relationship is:

- `L -> G -> P`

not direct mutation from lab into production.

## Non-negotiable invariants
- **One kernel, separate state:** prod and lab should share code and release discipline, but not live DBs, artifact roots, or secrets.
- **Workflow Lab is non-authoritative:** lab outputs are evidence about kernel behavior, not production truth.
- **Promotion is release-mediated:** the default promotion model is lab evidence + review + tagged release -> production deploy.
- **Execution variants are not semantic variants:** prompt/model/tool/run-profile changes are not the same as changing official workflow meaning, evidence requirements, or outputs.
- **No second semantics compiler:** Workflow Lab may derive views from workflow packs + compiled control, but must not become a peer authored workflow-definition surface.

## Current repo facts that matter
- Authoritative workflow semantics still live in `docs/workflows/*/v1/*`.
- Compiled control still lives in `src/onetruth/infrastructure/definitions/control_layer.py`.
- Runtime rows/events/artifacts/pointers remain canonical.
- Shared-env identity is now credible end to end: the frontend bootstraps from server-derived viewer state and no longer acts like the production identity surface.
- The first-user production/lab reference is now explicit as separate single-node environments over `SQLite + local filesystem artifacts`, deployed from `release_source_bundle`.
- Backup/restore/rollback docs and rehearsal basis now exist, but `G1` still requires actual restore rehearsal evidence rather than docs alone.
- Workflow Lab does not yet exist as a package or doc tree, which is good: it can start thin and clean.

## Lane A — productization
This lane leads.

### A0 / C0 — package/runtime honesty (immediate)
- finish runtime dependency honesty for core surfaces and any future lab package
- keep package `__init__` files lazy/minimal
- avoid adding lab runtime code on top of underdeclared dependencies

### A1 — production perimeter completion (immediate)
- add a server-derived viewer/bootstrap/session endpoint
- migrate the frontend away from browser-set identity in `shared_env`
- make actor switching strictly local-dev/demo only
- make `local_dev` loopback-only by executable guard, not just docs

### A2 — production substrate definition (next)
- define prod vs lab topology explicitly
- choose the actual deploy artifact and install flow
- document the first-user reference architecture as a **single-node production system** unless/until a broader substrate is explicitly chosen
- define backup / restore / rollback in concrete operator terms

### A3 — operability + perimeter hardening (next)
- observability baseline: metrics, health/readiness, degradation visibility
- GitHub perimeter: full-SHA action pinning, dependency review, CodeQL, mock-vs-live OpenAI split, hosted settings verification
- operator runbooks for deploy, rollback, restore, rotate secrets, and promote a candidate release

## Lane B — Workflow Lab
This lane starts now, but only in a thin form.

### B0 — Workflow Lab Phase 0 (immediate)
- docs only / schema-first
- authority boundary
- concepts and anti-patterns
- phased plan and readiness gates
- no runtime package required yet unless it stays dependency-light

### B1 — normalized evidence over current outputs (next)
Normalize what the repo already knows how to produce:
- weekly Stage04 inspection packets and pilot summaries
- realistic scheduling pilot outputs
- current capability certification outputs
- optionally exported runtime workspace bundles as future sanitized-world inputs

### B2 — first true lab execution layer (gated on G1)
Only after production clears G1:
- `VariantSpec`
- `RunProfile`
- freshness guards
- one narrow first execution adapter (weekly Stage04)
- a thin `KernelView` derived from workflow packs + compiled control

### B3 — worlds / compare / semantic-version work (gated on G2)
Only after there is real demand and at least one stable production user:
- `WorldFamily` / `WorldInstance`
- `CompareReport`
- later experiment specs and certification bridge
- only later any multi-version semantic coexistence machinery

## Readiness gates

### G1 — before B2
Do not start the first true lab execution layer until:
1. production is deployed via the official release path
2. frontend identity is server-derived in `shared_env`
3. `local_dev` non-loopback bind is blocked
4. prod and lab are separate environments with separate state
5. backup/restore/rollback have been rehearsed
   - runbooks and rehearsal basis alone do not satisfy this gate; actual restore rehearsal evidence must exist
6. basic observability exists

### G2 — before B3
Do not start worlds/compare/semantic-version work until:
1. at least one user is stable in production
2. there have been at least one or two clean production release cycles
3. lab reports are already useful in practice
4. there is repeated demand to compare multiple candidates across repeatable conditions
5. there is an explicit workflow-version coexistence strategy if semantic promotion is going to be routine

## Parallelization guidance
Run these in parallel first:
- productization perimeter work
- Workflow Lab Phase 0 docs/schemas
- package/runtime dependency honesty cleanup

Run these in parallel second:
- production topology / runbooks / deploy reference
- Workflow Lab normalization over current outputs
- perimeter hardening and observability baseline

Do **not** start heavy Workflow Lab execution/comparison machinery until G1/G2 are explicitly satisfied.

## What not to build yet
- no public Workflow Lab API
- no public Workflow Lab UI
- no generalized experiment platform
- no direct runtime push of candidate workflows into production
- no second semantics layer in Workflow Lab
- no raw production DB cloning into lab
- no broad infra migration just for elegance

## Promotion model to optimize for now
The default promotion mode should be:

- `candidate release + lab evidence + review -> tagged release -> production deploy`

not live mutation of production workflow truth.

## Task mapping
- EPIC-100 covers the productization lane.
- EPIC-110 covers Workflow Lab Phase 0/1 and the gated later phases.
- `TASK-0110` through `TASK-0116` are the productization/support package.
- `TASK-0117` through `TASK-0122` are the Workflow Lab package, with `TASK-0121` and `TASK-0122` explicitly gated.
