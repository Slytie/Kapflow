# Lab auth and VM deploy

This runbook covers the CAPEX PR010/PR011 lab-only lane. It is not a production deploy path, not CAPEX activation, not pilot approval, and not permission to use raw corpus files or real users.

The lab-only VM lane is implementation and smoke evidence for an isolated lab target only.

## Required operator values
- GCP project: lab-only project ID
- zone: lab VM zone
- instance: lab VM name
- remote release root: absolute lab path, for example `/srv/onetruth/lab/release-root`
- remote DB URL: absolute SQLite URL, for example `sqlite:////srv/onetruth/lab/runtime.db`
- remote artifact root: absolute lab path, for example `/srv/onetruth/lab/artifacts`
- service name: lab systemd unit, normally `onetruth-api`
- remote viewer-smoke token env var: env var name only, for example `LAB_VIEWER_SMOKE_TOKEN`
- shared-env JWT issuer, audience, and public key reference

## Lab JWT viewer smoke
`scripts/run_lab_auth_smoke.py` uses the existing `shared_env` RS256 JWT resolver. It does not add JWKS lookup, pilot-password fallback, browser-header identity trust, or actor switching.

Example:

```bash
python3 scripts/run_lab_auth_smoke.py \
  --db-url sqlite:////srv/onetruth/lab/runtime.db \
  --jwt-issuer "$LAB_JWT_ISSUER" \
  --jwt-audience "$LAB_JWT_AUDIENCE" \
  --jwt-public-key-pem-file /run/onetruth/lab-jwt-public-key.pem \
  --bearer-token-env LAB_VIEWER_SMOKE_TOKEN \
  --json
```

The report records `request_context_mode=server_derived`, `actor_switching_allowed=false`, and whether conflicting browser identity headers were ignored. It records token source metadata only; it must not print or persist bearer token values.

## Lab VM deploy plan
`scripts/deploy_lab_vm.py` validates the `release_manifest.json` and matching `release_source_bundle`, then emits a lab VM command plan. Dry-run planning is the default.

```bash
python3 scripts/deploy_lab_vm.py \
  --environment lab \
  --gcp-project "$LAB_GCP_PROJECT" \
  --zone "$LAB_GCP_ZONE" \
  --instance "$LAB_GCP_INSTANCE" \
  --release-source-bundle .tmp/companyos-release-source-bundle.zip \
  --release-manifest .tmp/release-image/release_manifest.json \
  --remote-release-root "$LAB_REMOTE_RELEASE_ROOT" \
  --remote-db-url "$LAB_REMOTE_DB_URL" \
  --remote-artifact-root "$LAB_REMOTE_ARTIFACT_ROOT" \
  --remote-service-name onetruth-api \
  --remote-viewer-token-env LAB_VIEWER_SMOKE_TOKEN \
  --json
```

The planned commands may use only `gcloud compute scp` and `gcloud compute ssh`. The lane does not use Cloud Run, Kubernetes, Terraform, production DB URLs, production artifact roots, production secrets, or raw project corpus files.

## Execute and smoke
Execution requires explicit operator confirmation that the target is lab-only and has no real users:

```bash
python3 scripts/deploy_lab_vm.py \
  --environment lab \
  --gcp-project "$LAB_GCP_PROJECT" \
  --zone "$LAB_GCP_ZONE" \
  --instance "$LAB_GCP_INSTANCE" \
  --release-source-bundle .tmp/companyos-release-source-bundle.zip \
  --release-manifest .tmp/release-image/release_manifest.json \
  --remote-release-root "$LAB_REMOTE_RELEASE_ROOT" \
  --remote-db-url "$LAB_REMOTE_DB_URL" \
  --remote-artifact-root "$LAB_REMOTE_ARTIFACT_ROOT" \
  --remote-service-name onetruth-api \
  --remote-viewer-token-env LAB_VIEWER_SMOKE_TOKEN \
  --execute \
  --confirm-lab-target \
  --confirm-no-real-users \
  --json
```

The remote command extracts into a versioned release dir, runs the validation-only predeploy backup manifest, installs `.[api]`, builds frontend assets, restarts the lab service, and smokes `/api/v1/ops/health`, `/api/v1/ops/readiness`, `/api/v1/viewer`, and artifact-root writability.

`TASK-0244` requires actual operator-supplied lab VM execute-and-smoke evidence before it can be marked `DONE`. A dry-run plan is implementation evidence only.
