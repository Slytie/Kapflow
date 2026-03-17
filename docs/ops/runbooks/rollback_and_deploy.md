# Rollback and deploy

This runbook applies to the first-user production/lab topology in [docs/ops/production_lab_topology.md](../production_lab_topology.md) and the substrate decision in [docs/adr/ADR-004-first-user-production-lab-topology.md](../../adr/ADR-004-first-user-production-lab-topology.md).

## Use rollback vs restore
- Use rollback when a release introduced a code/config regression but the current environment-specific DB file and artifact root are still trustworthy.
- Use restore when the DB file, artifact root, or both are missing, corrupt, or no longer trustworthy. In that case, follow [docs/ops/runbooks/backup_and_restore.md](./backup_and_restore.md) instead of treating the incident as an ordinary rollback.

## Before deploy
1. Confirm the deploy input is `release_source_bundle`, not `handoff_source_bundle`, `runtime_workspace_bundle`, or a raw workspace ZIP.
2. Confirm the release archive includes both `bundle_manifest.json` and `release_provenance.json`.
3. Confirm the target environment is either production or lab, with its own `ONETRUTH_DB_URL`, `ONETRUTH_ARTIFACT_ROOT`, and secrets.
4. Confirm no open authority-model migration or substrate change is being introduced without an ADR / sign-off.
5. Confirm the shared environment will run with `ONETRUTH_API_BOUNDARY_PROFILE=shared_env`.

## Deploy from release_source_bundle
1. Extract the new `release_source_bundle` into a clean versioned directory.
2. Create or refresh a Python 3.11 environment and install `python3.11 -m pip install -e ".[api]"`.
3. Build the frontend from the same bundle with `cd frontend && npm ci && npm run build`.
4. Point the environment at its own DB and artifact root:
   - `ONETRUTH_DB_URL`
   - `ONETRUTH_ARTIFACT_ROOT`
   - shared-env JWT settings
5. Start or restart `onetruth-api` against that environment-specific state.
6. Switch traffic to the new release and confirm the frontend and `/api/v1/viewer` come up under `shared_env`.

## If rollback is required
1. stop new deploy traffic
2. preserve the environment-specific DB file and artifact root before changing releases
3. keep authoritative events and artifacts intact; do not rewrite or delete historical runs
4. redeploy the previous `release_source_bundle` against the same environment-specific DB and artifact root
5. rebuild derived views and generated caches against the rolled-back code if needed
6. record decision and impact in `DECISIONS_SINCE_LAST.md`

## Special caution
A rollback must not reinterpret historical pinned execution artifacts under a new meaning without an explicit compatibility decision.
This runbook does not replace backup/restore. Use the backup/restore runbook when state recovery is needed.
