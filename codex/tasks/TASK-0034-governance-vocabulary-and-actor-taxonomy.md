---
id: TASK-0034
epic: EPIC-060
title: "Canonicalize governance vocabulary and actor taxonomy"
status: DONE
owners:
- platform
reviewers:
- security
- qa
depends_on:
- TASK-0012
risk: high
context_packs: []
patterns: []
---

## Context
Approval responses, event outcomes, permission verbs, and actor types are still inconsistent across docs and schemas. That ambiguity will leak into runtime schemas and implementations unless it is resolved first.

## Objective
Create one canonical vocabulary and mapping for governance concepts: approval responses, recorded outcomes, permission actions, and actor taxonomy.

## Non-goals
- Do not redesign the approval model from scratch.
- Do not add new approval kinds unless the architecture requires it.
- Do not bury the canonical mapping inside prose only; validators must be able to enforce it later.

## Source files to read first
- `docs/architecture/approval_model.md`
- `docs/architecture/event_model.md`
- `schemas/policy/permissions.yaml`
- `schemas/events/envelope.schema.json`
- `schemas/artifacts/artifact_version_metadata.schema.json`
- `docs/templates/DECISION_CATALOG_TEMPLATE.yaml`
- `docs/workflows/*/v1/DECISION_CATALOG.yaml`

## Context packs / patterns to consult
- none required by default

## Source files to change
- vocabulary source doc(s) under `docs/architecture/`
- relevant schemas under `schemas/`
- decision catalog template and affected workflow packs

## Generated / downstream artifacts impacted
- approval packets
- generated runbook packs
- generated CompanyOS IR
- golden traces and replay fixtures

## Plan
1. Separate response verbs, recorded outcomes, permission verbs, and actor categories.
2. Choose canonical tokens and make the mapping explicit.
3. Update the source docs/templates/schemas that currently drift.
4. Leave follow-on validators and runtime schemas to consume that canonical source.

## Verification
- Enumerations line up across source docs and schemas.
- Example traces and approval examples use the canonical mapping.
- No doc uses `request_changes` and `changes_requested` as if they were the same layer of meaning.

## Acceptance criteria
- one canonical governance vocabulary exists and is authoritative
- actor taxonomy is stable enough for runtime schemas to use without guessing
- affected workflow packs and templates no longer drift on key enums

## Notes / decisions
This task should settle meaning, not implementation plumbing.


## Completion notes
- Completed in the repo-native semantic-closure tranche on 2026-03-02.
