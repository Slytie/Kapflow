---
pattern_id: PATTERN-009
title: "Taiga Front \u2014 UI patterns: boards, detail pages with timelines, polling/real-time\
  \ strategies"
source_notes: docs/patterns/sources/converted/Taiga_Front_UI_Architecture_Extraction_for_Ops_Console.md
tags:
- ui
- ops-console
- state-management
- timelines
- polling
- permissions
applies_to_epics:
- EPIC-080
use_when:
- Designing **operator-facing UI** for case/run detail pages with a timeline.
- Designing **real-time / polling** update strategies without overwhelming the backend.
last_updated: '2026-02-28'
status: candidate
---

# PATTERN-009 — Taiga Front — UI patterns: boards, detail pages with timelines, polling/real-time strategies

**Why this matters for our Stage 4 MVP**

- This is a *reference pattern*, not a dependency: we borrow semantics and guardrails, not code.
- Read this card first; only open the full source notes if the task is directly touching the affected subsystem.

## When to consult this

- Designing **operator-facing UI** for case/run detail pages with a timeline.
- Designing **real-time / polling** update strategies without overwhelming the backend.

## Key patterns to borrow

- *Operator UI**
- `/ops/pipelines` → `PipelinesIndexPage` (search + saved views)
- `/ops/pipelines/:pipelineId/overview` → `PipelineOverviewGridPage`
- `PartitionStatusGrid` (normalized store + batching + lazy details)
- `GridFiltersBar` (URL-synced include/exclude filters; saved presets)
- `/ops/pipelines/:pipelineId/partitions/:partitionKey` → `PartitionDetailPage`
- `DatasetsAndVersionsPanel`, `RunsList` (cursor pagination + infinite scroll)
- `PartitionActions` (rerun/backfill/promote guarded)
- `/ops/runs/:runId` → `RunDetailPage`
- `RunInputsOutputsPanel`, `RunLogsPanel`, `ChildRunsPanel`

## Pitfalls / what *not* to copy

_No explicit anti-pattern list extracted; treat source notes as informational only._

## How we map this into our platform (guidance)

- **Artifact-first**: always bind actions to `(dataset_key, partition_key, artifact_version_id)` and record promotion events.
- **Audit timeline**: every state change must emit a strongly-linked TimelineEvent (authoritative, transactional).
- **Tenant + domain isolation**: any queue/topic/index/prefix must be tenant-scoped; add negative tests.
- **Automation safety**: tool execution must be policy/approval gated and sandboxed.

## Source notes

- Full extraction: `docs/patterns/sources/converted/Taiga_Front_UI_Architecture_Extraction_for_Ops_Console.md`
