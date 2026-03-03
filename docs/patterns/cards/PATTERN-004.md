---
pattern_id: PATTERN-004
title: "Airflow \u2014 Scheduler semantics: DAG runs, retries, sensors, backfills,\
  \ and task-instance state"
source_notes: docs/patterns/sources/converted/Airflow_Scheduler_Semantics_Pattern_Extraction.md
tags:
- scheduler
- dag
- backfill
- retries
- sensors
- task-instance
- time
applies_to_epics:
- EPIC-040
- EPIC-050
- EPIC-090
use_when:
- Designing **scheduler/timer semantics** (especially for backfills and replays).
- Defining **retry policies** and preventing runaway retries.
- Thinking about **task instance states** and operational visibility.
last_updated: '2026-02-28'
status: candidate
---

# PATTERN-004 — Airflow — Scheduler semantics: DAG runs, retries, sensors, backfills, and task-instance state

**Why this matters for our Stage 4 MVP**

- This is a *reference pattern*, not a dependency: we borrow semantics and guardrails, not code.
- Read this card first; only open the full source notes if the task is directly touching the affected subsystem.

## When to consult this

- Designing **scheduler/timer semantics** (especially for backfills and replays).
- Defining **retry policies** and preventing runaway retries.
- Thinking about **task instance states** and operational visibility.

## Key patterns to borrow

- Model task instance state explicitly (queued/running/success/failed/retry-scheduled) to support operability.
- Separate “scheduler decisions” from execution and persist the scheduler’s view so retries/backfills are deterministic.
- Treat backfills as first-class runs with clear partition/time-window semantics.

## Pitfalls / what *not* to copy

_No explicit anti-pattern list extracted; treat source notes as informational only._

## How we map this into our platform (guidance)

- **Artifact-first**: always bind actions to `(dataset_key, partition_key, artifact_version_id)` and record promotion events.
- **Audit timeline**: every state change must emit a strongly-linked TimelineEvent (authoritative, transactional).
- **Tenant + domain isolation**: any queue/topic/index/prefix must be tenant-scoped; add negative tests.
- **Automation safety**: tool execution must be policy/approval gated and sandboxed.

## Source notes

- Full extraction: `docs/patterns/sources/converted/Airflow_Scheduler_Semantics_Pattern_Extraction.md`
