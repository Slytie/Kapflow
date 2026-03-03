---
pattern_id: PATTERN-006
title: "Piston \u2014 Secure code execution service patterns (resource limits, isolation,\
  \ logging)"
source_notes: docs/patterns/sources/converted/Piston_Secure_Code_Execution_Architecture_Report.md
tags:
- sandbox
- code-execution
- resource-limits
- isolation
- logging
- multi-tenant-safety
applies_to_epics:
- EPIC-070
- EPIC-090
use_when:
- Defining the **minimum sandbox posture** for any script/tool execution.
- Designing **resource caps** and default-deny egress for untrusted execution.
- Designing for **forensic logging** of executions (inputs/outputs, hashes, policy
  decisions).
last_updated: '2026-02-28'
status: candidate
---

# PATTERN-006 — Piston — Secure code execution service patterns (resource limits, isolation, logging)

**Why this matters for our Stage 4 MVP**

- This is a *reference pattern*, not a dependency: we borrow semantics and guardrails, not code.
- Read this card first; only open the full source notes if the task is directly touching the affected subsystem.

## When to consult this

- Defining the **minimum sandbox posture** for any script/tool execution.
- Designing **resource caps** and default-deny egress for untrusted execution.
- Designing for **forensic logging** of executions (inputs/outputs, hashes, policy decisions).

## Key patterns to borrow

- Treat the execution plane as a security boundary: **resource limits**, **isolation**, and **auditable provenance** are mandatory.
- Default-deny network egress; allowlist by integration/tool.
- Persist execution metadata (hashes, image version, input/output artifact IDs) for forensics.

## Pitfalls / what *not* to copy

_No explicit anti-pattern list extracted; treat source notes as informational only._

## How we map this into our platform (guidance)

- **Artifact-first**: always bind actions to `(dataset_key, partition_key, artifact_version_id)` and record promotion events.
- **Audit timeline**: every state change must emit a strongly-linked TimelineEvent (authoritative, transactional).
- **Tenant + domain isolation**: any queue/topic/index/prefix must be tenant-scoped; add negative tests.
- **Automation safety**: tool execution must be policy/approval gated and sandboxed.

## Source notes

- Full extraction: `docs/patterns/sources/converted/Piston_Secure_Code_Execution_Architecture_Report.md`
