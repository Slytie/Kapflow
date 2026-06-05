# CAPEX Pilot Storage Gate Checklist

## Status
Gate result: `blocked_pending_evidence`.

This checklist closes `TASK-0388` as planning evidence only. It does not pass, waive, or execute the pilot storage gate.

## Required Decision Or Waiver
- [ ] Pilot DB topology selected.
- [ ] Postgres decision recorded, or explicit waiver recorded with scope and expiry.
- [ ] Blob custody backend selected.
- [ ] Blob backend decision or waiver reviewed by deployment/SRE/security owners.
- [ ] CAPEX remains disabled until every required item below is passed or explicitly waived.

## Custody And Restore Evidence
- [ ] Backup set includes DB state, artifact/blob state, release bundle, and secret/config references.
- [ ] Restore rehearsal completed in a non-production environment of the same class.
- [ ] Restored environment can read canonical project/workflow/artifact metadata.
- [ ] At least one restored artifact download proves auth-before-read after restore.
- [ ] Digest verification confirms restored bytes match canonical metadata.
- [ ] Missing/corrupt blob behavior fails closed without rewriting canonical metadata.

## Index And Rebuild Evidence
- [ ] Required DB indexes for project, workflow, artifact, pointer, source, and custody lookups are cataloged.
- [ ] Index rebuild rehearsal completed from restored state.
- [ ] Search/projection/index rebuild outputs are treated as derived, not authoritative.
- [ ] Rebuild evidence records duration, row counts, object counts, and mismatch handling.

## Capacity And Quota Evidence
- [ ] Expected pilot corpus size and growth assumptions are recorded without raw file names or raw content.
- [ ] DB capacity, blob capacity, and temporary workspace capacity are measured or waived.
- [ ] Quotas, retention policy, and cleanup/quarantine policy are documented.
- [ ] Alert thresholds exist for storage exhaustion, failed backup, failed restore, digest mismatch, and authorization denial spikes.

## Security And Configuration
- [ ] Secret/config references are recorded without secret values.
- [ ] Production and lab storage roots/backends are separate.
- [ ] Tenant/domain/project authorization is enforced before blob read.
- [ ] Direct object-store/blob access is not exposed to users as an authorization bypass.
- [ ] Raw project corpus content remains off-repo.

## Signoff
- [ ] Deployment reviewer signoff.
- [ ] SRE reviewer signoff.
- [ ] Security reviewer signoff.
- [ ] Architecture reviewer signoff.
- [ ] Explicit pass/waiver decision recorded in `docs/status/DECISIONS_SINCE_LAST.md`.

## Rollback And Recovery
Rollback posture is to leave runtime state inert or keep CAPEX disabled. Do not destructively delete governed DB state, artifact versions, pointers, events, blob references, replicas, or audit evidence as rollback.

## Non-Activation
This checklist does not create pilot readiness, production readiness, storage backend rollout, Postgres rollout, raw corpus approval, route/API changes, schema migrations, or CAPEX runtime activation.
