# CAPEX Wave 1 Code Pattern Register

## Status
Accepted Wave 1 illustrative register. CAPEX runtime activation remains disabled.

## Scope
This register closes `TASK-0389` as non-production architecture guidance for current Wave 1 seams. All snippets in this register are illustrative and non-production. They are not source files, migrations, routes, runnable adapters, or activation hooks.

## Pattern Families

### Domain-Runtime Manifest Registry
Intent: compose domain manifest inventory through typed registry objects while keeping the CAPEX platform package neutral.

Illustrative snippet:

```python
# Pseudo-code only: keep registry construction explicit and platform-neutral.
registry = DomainRuntimeRegistry()
registry.register(load_domain_manifest(manifest_path))
report = registry.composition_report()
assert report.activation_allowed is False
```

Use this pattern when a future domain needs descriptive inventory. Do not use it to dynamically import domain packages, install plugins, execute hooks, register routes, or make CAPEX runnable.

### AuthorizedProjectsQuery And Direct Membership Visibility
Intent: derive backend project visibility from direct `project_memberships` and tenant/domain scope before broad reads.

Illustrative snippet:

```python
# Pseudo-code only: authorization is backend-owned and derived from direct grants.
authorized = AuthorizedProjectsQuery(connection).for_actor(scope=scope, actor=actor)
project_ids = authorized.active_project_ids()
rows = list_workflow_runs(scope=scope, visible_project_ids=project_ids)
```

Use this pattern for deterministic read visibility. Do not replace it with frontend-only auth filtering, global project list exposure, or domain-owned global queries.

### Storage Blob Custody Auth-Before-Download
Intent: preserve auth-before-download ordering by authorizing canonical artifact/project/workflow scope before resolving storage custody metadata or reading bytes.

Illustrative snippet:

```python
# Pseudo-code only: metadata and scope checks happen before storage reads.
artifact = load_artifact_version(artifact_version_id)
require_artifact_scope_visible(actor=actor, artifact=artifact)
blob = resolve_blob_custody_or_compatibility_uri(artifact)
return read_confined_bytes(blob)
```

Use this pattern for future custody-backed downloads. Do not treat blob presence as truth, bypass `ArtifactVersion`, target pointers at blobs, or read storage before scope authorization.

## Forbidden Overbuilds
- dynamic domain package loading
- frontend-only auth filtering
- global project list exposure
- blob truth bypassing `ArtifactVersion`
- pointer targets to blobs
- storage reads before scope authorization

## Explicit Non-Activation
This register does not add migrations, schema DDL, HTTP routes, frontend behavior, storage backend rollout, Postgres rollout, raw corpus approval, pilot readiness, production readiness, or CAPEX runtime activation.
