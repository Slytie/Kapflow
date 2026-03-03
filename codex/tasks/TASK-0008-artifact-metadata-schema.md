---
id: TASK-0008
epic: EPIC-030
title: "Add artifact metadata schema (version, hash, lineage hooks)"
status: DONE
owners: ["platform"]
reviewers: ["security", "qa"]
depends_on: ["TASK-0004"]
risk: medium
---

## Context
Implementation will need a stable artifact metadata contract: version IDs, hashes, pointer history references.

## Objective
- Create `schemas/artifacts/artifact_metadata.schema.json`.
- Include fields for content hash, size, created_at, created_by, dataset_key, partition_key, scope, and optional lineage pointers.

## Plan
1) Define required metadata fields for auditability.
2) Ensure scope fields are required.
3) Add optional integrity fields (hash, prev_version_id).

## Files to read first
- `schemas/artifacts/dataset_keys.yaml`
- `docs/architecture/invariants.md`

## Files to change
- `schemas/artifacts/artifact_metadata.schema.json`

## Commands to run
- (schema task)

## Acceptance criteria
- [ ] Schema exists and matches invariants.
- [ ] Security agrees scope and sensitivity hooks are represented.

## Completion note
Initial repo-native design deliverables landed in the merged repo update. Follow-on implementation work should use the newer merger tasks rather than reopening this task unless the source files materially change.
