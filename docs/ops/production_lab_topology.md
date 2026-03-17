# Production and lab topology

This is the operator-facing reference for the first-user deployment shape.
It defines what production is, what lab is, and what may be promoted between them.

## What production is
Production is one user-facing single-node deployment of the current runtime kernel.
It serves the built frontend and the `onetruth-api` backend in `shared_env` mode over one environment-specific state set:
- one `ONETRUTH_DB_URL`
- one `ONETRUTH_ARTIFACT_ROOT`
- one shared-env identity secret set

## What lab is
Workflow Lab is one separate internal-only single-node deployment of the same code/release discipline.
It is not a public product surface, not a second authority chain, and not a shortcut into production.

Lab uses its own:
- `ONETRUTH_DB_URL`
- `ONETRUTH_ARTIFACT_ROOT`
- secrets
- internal-only access path

Prod and lab do not share live DBs, artifact roots, or secrets.
Tenant/domain separation inside one runtime instance is not an acceptable replacement for separate environments.

## What gets deployed
The only deploy input is `release_source_bundle`.
Do not deploy from:
- `handoff_source_bundle`
- `runtime_workspace_bundle`
- raw workspace archives
- ad hoc manual ZIPs

Those artifacts are review or evidence surfaces, not operator deploy artifacts.

## Single-node recipe
Each environment follows the same recipe:
1. Extract `release_source_bundle` into a clean versioned directory.
2. Create a Python 3.11 environment and install the runtime with `python3.11 -m pip install -e ".[api]"`.
3. Build the frontend from the same bundle on Node 20 with `cd frontend && npm ci && npm run build`.
4. Configure environment-specific runtime settings:
   - `ONETRUTH_DB_URL`
   - `ONETRUTH_ARTIFACT_ROOT`
   - `ONETRUTH_API_BOUNDARY_PROFILE=shared_env`
   - `ONETRUTH_SHARED_ENV_JWT_ISSUER`
   - `ONETRUTH_SHARED_ENV_JWT_AUDIENCE`
   - `ONETRUTH_SHARED_ENV_JWT_PUBLIC_KEY_PEM`
5. Start `onetruth-api` and serve the built frontend on the same node.

The reverse proxy or static-server choice is intentionally vendor-neutral in this tranche.
This doc defines the deploy contract, not a mandatory platform stack.

## Separation rules
- Never point lab at the production database.
- Never point lab at the production artifact root.
- Never reuse production JWT/OpenAI secrets in lab.
- Never deploy shared environments with `local_dev`.
- Never treat a lab runtime mutation as production promotion.

## Promotion gate
The promotion gate `G` is a reviewed release process:
- candidate release + lab evidence + review
- tagged release
- production deploy

It is not a third runtime service and it does not move live runtime state from lab into production.
