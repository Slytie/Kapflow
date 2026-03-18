# Workflow Lab Promotion Gate

This doc is the authoritative repo-native reference for the promotion gate `G` and for the current status of readiness gates `G1` and `G2`.

The healthy path remains:

- `lab evidence + review/certification + tagged release -> production deploy`
- `lab evidence + review/certification + candidate release + tagged release + production deploy`

## What `G` is
The promotion gate `G` is the release-mediated bridge between Workflow Lab evidence and production.

It is a reviewed process over:
- normalized Workflow Lab evidence
- operator review and certification evidence
- a candidate release
- a tagged release
- production deploy from `release_source_bundle`

`release_source_bundle` is the only promotion/deploy artifact in this bridge.

## What `G` is not
`G` is **not**:
- a third runtime service
- a public Workflow Lab control plane
- not live runtime mutation from lab into prod
- workspace or handoff bundle sharing
- a mechanism for moving live lab state into production

## Evidence that counts at the gate
The promotion gate may consider:
- Workflow Lab normalized reports and review packets such as `workflow_lab_run_report.json` and `workflow_lab_review_packet.md`
- current capability certification manifests and scenario evidence
- release-bundle provenance, including `bundle_manifest.json` and `release_provenance.json`
- operator review, certification, and release records

These inputs may support review and release decisions, but they do not themselves mutate production truth.

## Inputs that do not count as promotion truth
The following are explicitly not promotion/deploy truth:
- `handoff_source_bundle`
- `runtime_workspace_bundle`
- raw workspace archives
- direct lab runtime state
- raw prod-state cloning

## Recording gate clearance
Future sessions must not claim `G1` or `G2` is satisfied by implication.

When a gate actually clears, update:
1. this document
2. `docs/status/CURRENT_FOCUS.md`
3. `docs/status/DECISIONS_SINCE_LAST.md`

Only after those updates should later blocked Workflow Lab tasks be treated as unblocked.

## G1 — before TASK-0121 / B2
Overall status: `UNCLEARED`

A gate criterion is not met merely because design docs exist. Where operational evidence is required, operational evidence must be recorded explicitly.

| Criterion | Required evidence | Current repo status |
| --- | --- | --- |
| 1. production is deployed via the official release path | repo-native evidence that production was deployed from `release_source_bundle` through the reviewed release path | `UNCLEARED` — no repo-native evidence currently records production deployment through the official release path |
| 2. frontend identity is server-derived in `shared_env` | repo-native docs/tests showing `GET /api/v1/viewer`-based shared-env identity | contract basis exists in repo, but gate remains uncleared until the overall gate is explicitly recorded |
| 3. `local_dev` non-loopback bind is blocked | repo-native docs/tests for the guarded `onetruth-api` startup path | contract basis exists in repo, but gate remains uncleared until the overall gate is explicitly recorded |
| 4. prod and lab are separate environments with separate state | repo-native topology/deploy docs showing separate DBs, artifact roots, and secrets | contract basis exists in repo, but gate remains uncleared until the overall gate is explicitly recorded |
| 5. backup/restore/rollback have been rehearsed | recorded restore rehearsal evidence, not just runbooks | `UNCLEARED` — runbooks and rehearsal basis exist, but actual restore rehearsal evidence is still missing |
| 6. basic observability exists | repo-native docs/tests for health, readiness, and safe metrics | contract basis exists in repo, but gate remains uncleared until the overall gate is explicitly recorded |

Result:
- `TASK-0121` remains blocked until `G1` is explicitly recorded as cleared here.

## G2 — before TASK-0122 / B3
Overall status: `UNCLEARED`

`G2` is intentionally higher than a documentation threshold. It is about demonstrated production stability and repeated need, not design completeness.

| Criterion | Required evidence | Current repo status |
| --- | --- | --- |
| 1. at least one user is stable in production | recorded production-usage evidence | `UNCLEARED` |
| 2. there have been one or two clean production release cycles | recorded release-history evidence | `UNCLEARED` |
| 3. lab reports are already useful in practice | recorded examples of lab evidence informing real review/certification/release work | `UNCLEARED` |
| 4. there is repeated demand to compare multiple candidates across repeatable conditions | explicit repeated operator or product need recorded in repo memory/docs | `UNCLEARED` |
| 5. there is an explicit workflow-version coexistence strategy if semantic promotion is going to be routine | repo-native coexistence strategy docs | `UNCLEARED` |

Result:
- `TASK-0122` remains blocked until `G2` is explicitly recorded as cleared here.

## Current default
Until a gate is explicitly cleared:
- promote candidates by reviewed release, not direct runtime mutation
- keep Workflow Lab evidence-only and non-authoritative
- keep `TASK-0121` and `TASK-0122` blocked
