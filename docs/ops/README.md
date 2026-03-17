# Ops docs

This folder contains operational guidance for Stage 4:
- CI required checks
- degraded-mode definitions
- runbook skeletons

These docs assume one truth system:
operational views may degrade, but authoritative timeline and pointer writes may not silently disappear.

Shared-env operator note:
- frontend viewer/bootstrap identity is server-derived via `GET /api/v1/viewer`
- browser actor switching is local-dev/demo only and is not a production/shared-env authority surface
