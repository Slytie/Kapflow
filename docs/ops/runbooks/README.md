# Runbooks

These are Stage 4 runbooks. Keep them concrete and tied to authoritative evidence. Most remain short skeletons; the beginner local-demo guide is intentionally more detailed.

Current runbooks:
- `audit_export_or_projection_degraded.md`
- `stuck_workflow_or_task.md`
- `backup_and_restore.md` - environment-state backup, restore, and rehearsal basis for the first-user single-node production/lab reference
- `rollback_and_deploy.md` - release-bundle deploy and rollback for the first-user single-node production/lab reference
- `lab_auth_and_vm_deploy.md` - lab-only shared-env JWT smoke and GCP VM deploy plan/execute lane; actual execute-and-smoke evidence is required before claiming lab deploy closure
- `generated_artifact_drift.md`
- `logistics_single_node_cadence.md` - external cadence tick and bounded continuous logistics operator runbook for the first-user single-node lane
- `logistics_local_demo_beginner.md` - primary beginner-friendly local logistics demo guide; OpenAI-backed `/demo/logistics` setup, seeding, reset, and troubleshooting over the combined seeded story
- `logistics_canonical_workpage_demo.md` - deterministic canonical workpage demo path over prep-script output and `/runs/:workflowRunId/workpages/*` routes
- `logistics_local_demo_weekly_first.md` - exact local startup, seed, upload-pack, and click path for the first weekly-first operator walkthrough
