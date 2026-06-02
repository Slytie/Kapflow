# Backup and restore

This runbook applies to the first-user production/lab topology in [docs/ops/production_lab_topology.md](../production_lab_topology.md), the deploy contract in [docs/ops/runbooks/rollback_and_deploy.md](./rollback_and_deploy.md), and the substrate decision in [docs/adr/ADR-004-first-user-production-lab-topology.md](../../adr/ADR-004-first-user-production-lab-topology.md).

Use this runbook when environment state must be recovered from a known backup set. If code regressed but the current DB file and artifact root are still trustworthy, use the rollback runbook instead.

## Recoverable unit
One recoverable backup set is one environment-specific tuple:
- the SQLite DB file resolved from `ONETRUTH_DB_URL`
- the full artifact filesystem tree rooted at `ONETRUTH_ARTIFACT_ROOT`
- the exact `release_source_bundle` used for that environment, including `bundle_manifest.json` and `release_provenance.json`
- secret/config references needed to rehydrate the environment

Prod and lab backup sets are not interchangeable.
Do not treat tenant/domain separation inside one runtime as a substitute for separate prod-vs-lab recovery sets.

## Predeploy manifest skeleton
`scripts/prepare_predeploy_backup.py` and `make predeploy-backup-manifest` provide a validation-only predeploy backup skeleton.
It validates and records the DB/artifact/release tuple in `backup_manifest.json`, records secret/config references without secret values, and does not copy live state, archive artifact files, upload backups, restore data, or mutate the target environment.
This manifest is not restore proof; restore rehearsal remains a later gate.

## What must be backed up
1. The SQLite DB file for that environment.
2. The full artifact root for that environment.
3. The matching `release_source_bundle` for that environment.
4. The bundle sidecars:
   - `bundle_manifest.json`
   - `release_provenance.json`
5. Secret/config references for the environment, such as where the shared-env JWT material and API keys are managed.

## What must not be omitted
- Do not back up only the DB file and ignore the artifact root.
- Do not back up only the artifact root and ignore the DB file.
- Do not assume a newer or older `release_source_bundle` can stand in for the one that produced the state you are restoring.
- Do not store raw secret values inside repo-managed recovery notes or bundle artifacts.
- Do not reuse a production backup set as a normal lab seed or vice versa.

## Capture a consistent backup set
1. Label the target environment clearly as `prod` or `lab`.
2. Record the active release identifier and storage location for the matching `release_source_bundle`.
3. Quiesce writes before taking the backup set:
   - stop or drain `onetruth-api`, or
   - otherwise hold traffic and mutations long enough to capture the DB file and artifact root together.
4. Copy the SQLite DB file resolved from `ONETRUTH_DB_URL`.
5. Copy the full artifact filesystem tree rooted at `ONETRUTH_ARTIFACT_ROOT`.
6. Preserve the matching `release_source_bundle` and confirm it still includes both `bundle_manifest.json` and `release_provenance.json`.
7. Record secret/config references separately from the backup payload.
8. Store the resulting backup set outside the live runtime paths, with an environment label and capture timestamp.

## Verify the backup set is internally coherent
- Confirm the environment label is present and unambiguous.
- Confirm the copied DB file exists, is non-empty, and came from the intended `ONETRUTH_DB_URL`.
- Confirm the copied artifact tree exists and came from the intended `ONETRUTH_ARTIFACT_ROOT`.
- Confirm the preserved release archive is a `release_source_bundle`, not a `handoff_source_bundle` or `runtime_workspace_bundle`.
- Confirm both `bundle_manifest.json` and `release_provenance.json` are present with the bundle.
- Confirm secret/config references are recorded, without embedding secret values.
- If local policy allows, record digests or archive checksums for the DB file, artifact tree archive, and release bundle so the set can be validated later.

## Restore from a known backup set
1. Choose a target of the same environment class:
   - prod backup set -> prod restore
   - lab backup set -> lab restore
2. Keep the target environment out of traffic while restore is in progress.
3. Archive the currently damaged or suspect DB/artifact state before overwriting it, if it still exists.
4. Rehydrate secret/config values from the recorded secret references.
5. Install the matching `release_source_bundle` that belongs to the backup set.
6. Restore the SQLite DB file into the path resolved by `ONETRUTH_DB_URL` while the service is stopped.
7. Restore the artifact tree into the path rooted at `ONETRUTH_ARTIFACT_ROOT`.
8. Start `onetruth-api` and the built frontend from that same release bundle.

## Post-restore verification
- Confirm the environment is running the intended `release_source_bundle`.
- Confirm `/api/v1/viewer` responds successfully under the expected shared-env identity posture.
- Confirm core read surfaces load against restored state, such as workflow runs and pointers.
- Confirm at least one known artifact can still be read from the restored artifact root.
- Confirm the restored environment is still isolated from the other environment class.
- Record the restore outcome, checks run, and any discrepancies before returning traffic.

## Rehearsal basis
At minimum, rehearse restore in a non-production environment that uses the same single-node recipe:
1. Create a fresh backup set from a real lab or prod-like environment.
2. Restore that set into a clean target of the same environment class.
3. Run the post-restore verification checks.
4. Record rehearsal evidence.

The rehearsal record must capture:
- rehearsal date and operator
- source environment class
- backup-set identifier
- `release_source_bundle` identifier or storage reference
- `ONETRUTH_DB_URL` target path used for restore
- `ONETRUTH_ARTIFACT_ROOT` target path used for restore
- secret/config reference set used
- start and finish timestamps
- verification checks run and results
- pass/fail outcome and follow-up actions

Pass the rehearsal only if the environment is restored from the backup set end to end, the matching release bundle is used, and no canonical DB/artifact state is missing.

This runbook provides the rehearsal basis, not the rehearsal evidence itself. `G1` in `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md` remains unmet until an actual restore rehearsal record exists.
