# Ops docs

This folder contains operational guidance for Stage 4:
- CI required checks
- degraded-mode definitions
- runbook skeletons

These docs assume one truth system:
operational views may degrade, but authoritative timeline and pointer writes may not silently disappear.

Topology and deploy reference:
- first-user production/lab topology: `docs/ops/production_lab_topology.md`
- release-bundle deploy and rollback: `docs/ops/runbooks/rollback_and_deploy.md`
- backup/restore and rehearsal basis: `docs/ops/runbooks/backup_and_restore.md`
- lab-only shared-env auth smoke and VM deploy: `docs/ops/runbooks/lab_auth_and_vm_deploy.md`
- continuous logistics cadence runbook: `docs/ops/runbooks/logistics_single_node_cadence.md`
- canonical workpage demo walkthrough: `docs/ops/runbooks/logistics_canonical_workpage_demo.md`
- internal ops visibility surface: `GET /api/v1/ops/health`, `GET /api/v1/ops/readiness`, `GET /api/v1/ops/metrics`

Internal ops endpoint note:
- `/api/v1/ops/health`, `/api/v1/ops/readiness`, and `/api/v1/ops/metrics` are safe-by-shape operator endpoints, not UI/public product features
- these routes intentionally do not rely on browser identity headers or shared-env principal derivation

Shared-env operator note:
- frontend viewer/bootstrap identity is server-derived via `GET /api/v1/viewer`
- browser actor switching is local-dev/demo only and is not a production/shared-env authority surface
- lab viewer smoke uses the existing RS256 `shared_env` JWT resolver and records no bearer token values

Local-dev startup note:
- the supported API entrypoint is `onetruth-api`
- `local_dev` binds must stay loopback-only unless `ONETRUTH_UNSAFE_ALLOW_LOCAL_DEV_NON_LOOPBACK_BIND=1` is set for a controlled test scenario
