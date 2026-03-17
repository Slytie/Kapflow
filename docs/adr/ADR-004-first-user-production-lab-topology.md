# ADR-004 - First-user production and lab topology

## Status
Accepted

## Decision
The first-user production and Workflow Lab reference topology is now:
- **separate single-node environments**, one for production and one for lab
- the same kernel and release discipline in both environments
- the currently implemented substrate: `SQLite + local filesystem artifacts`
- one user-facing production environment using `ONETRUTH_API_BOUNDARY_PROFILE=shared_env`
- one internal-only lab environment that must not become a public or authoritative surface

The operator deploy input is `release_source_bundle` only.
`handoff_source_bundle` and `runtime_workspace_bundle` remain explicitly non-deploy artifacts.

The first-user single-node recipe is:
- one extracted `release_source_bundle`
- one Python 3.11 environment with `python3.11 -m pip install -e ".[api]"`
- one Node 20 frontend build from the same bundle
- one environment-specific database configured by `ONETRUTH_DB_URL`
- one environment-specific artifact root configured by `ONETRUTH_ARTIFACT_ROOT`
- one environment-specific secret set, including shared-env identity configuration

The promotion gate `G` is a reviewed release process, not a third runtime or control-plane service.
Lab evidence influences production only through `lab evidence + review + tagged release -> production deploy`, not through direct runtime mutation.

This ADR supersedes the deploy-substrate portion of ADR-003 for the first-user production/lab reference while preserving ADR-003's modular-monolith and one-truth runtime decisions.

## Why
The repo already has strong release-bundle truth, shared-env identity discipline, and a viable single-node runtime substrate.
What it lacked was one operator-ready statement of:
- what production is
- what lab is
- what gets deployed
- how those environments are separated

Leaving ADR-003 and the newer productization docs both active without reconciliation would keep two contradictory substrate stories alive.

## Consequences
- production and lab must not share live DBs, artifact roots, or secrets
- tenant/domain separation inside one runtime is not an acceptable replacement for prod-vs-lab separation
- `local_dev` is not a shared-environment deployment profile
- lab must not clone or attach to the live production DB or production artifact root
- a broader substrate choice such as PostgreSQL/object storage, or a standardized platform vendor stack, would require a later ADR rather than being smuggled into this tranche
