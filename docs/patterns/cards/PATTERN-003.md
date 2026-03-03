---
pattern_id: PATTERN-003
title: "Dagster \u2014 Partition/time-window semantics + cursor-based consumers +\
  \ run-key idempotency"
source_notes: docs/patterns/sources/converted/Dagster_Architecture_Pattern_Extraction.md
tags:
- partitions
- time-windows
- cursors
- event-log
- idempotency
- run-keys
applies_to_epics:
- EPIC-020
- EPIC-040
- EPIC-090
use_when:
- Defining partition keys and **time-window** semantics (DST-safe).
- Designing **eligibility** from event logs using cursors (monotonic consumer positions).
- Implementing **idempotent run submission** (run keys / reserved IDs).
last_updated: '2026-02-28'
status: candidate
---

# PATTERN-003 — Dagster — Partition/time-window semantics + cursor-based consumers + run-key idempotency

**Why this matters for our Stage 4 MVP**

- This is a *reference pattern*, not a dependency: we borrow semantics and guardrails, not code.
- Read this card first; only open the full source notes if the task is directly touching the affected subsystem.

## When to consult this

- Defining partition keys and **time-window** semantics (DST-safe).
- Designing **eligibility** from event logs using cursors (monotonic consumer positions).
- Implementing **idempotent run submission** (run keys / reserved IDs).

## Key patterns to borrow

- Use an explicit **TimeWindow** partition model (start/end, timezone/DST-safe) instead of ad-hoc strings.
- Use **cursor-based consumers** over a monotonic event log (e.g., `storage_id`) to compute eligibility safely.
- Use **run keys / reserved IDs** to make run submission idempotent and race-safe.

## Pitfalls / what *not* to copy

_No explicit anti-pattern list extracted; treat source notes as informational only._

## How we map this into our platform (guidance)

- **Artifact-first**: always bind actions to `(dataset_key, partition_key, artifact_version_id)` and record promotion events.
- **Audit timeline**: every state change must emit a strongly-linked TimelineEvent (authoritative, transactional).
- **Tenant + domain isolation**: any queue/topic/index/prefix must be tenant-scoped; add negative tests.
- **Automation safety**: tool execution must be policy/approval gated and sandboxed.

## Source notes

- Full extraction: `docs/patterns/sources/converted/Dagster_Architecture_Pattern_Extraction.md`
