# Logistics workpages run surfaces - product brief

## Purpose
This brief defines the next step after the first artifact-backed EOD slice. The goal is to graduate workpages from curated demo-only surfaces into canonical **workflow-run-backed** application surfaces without forcing schedule into a premature write model.

## What this epic is
The next epic is **workflow-run-backed workpages**.

At the end of this epic, the canonical access model should be:

\[
(\text{workflow\_run\_id}, \text{workpage\_kind}) \longmapsto \text{authoritative workpage contract}
\]

with two concrete lanes:
- **schedule**: run-backed, composite, query/read-only review surface
- **EOD**: run-backed landing/latest-draft-resolution surface around the existing artifact-backed edit route

`TASK-0137` now freezes that posture in repo-native docs so backend and frontend work can proceed without guesswork.

## Why this is the right next move
The repo has already proven three things:
1. workpages can be modeled as server-authored contracts,
2. those contracts can power full-page routes in the logistics shell,
3. EOD can round-trip through immutable workbook artifacts.

What is still missing is the canonical **workflow-native access model**. Right now the active workpage experience is still discovered primarily through `/demo/logistics/workpages/*`.

The next product step is therefore not “more EOD polish” and not “schedule write-path work.” It is making workpages first-class **per workflow run**.

## What the operator should be able to do
### Schedule
Given a real `weekly_schedule_planning.v1` workflow run, the operator should be able to open a schedule workpage that is clearly tied to that run and reflects the run's real composite scheduling state.

### EOD
Given a real `dispatch_reporting.v1` workflow run, the operator should be able to:
1. open the run-backed EOD landing page,
2. see whether a draft workbook already exists,
3. create or reopen the latest draft,
4. continue editing through the existing artifact-backed route.

## Product boundary
This epic does **not** make every workpage artifact-backed.

- Schedule remains composite and query-backed.
- EOD keeps its existing artifact-backed edit route.
- The new product layer is the **run-backed landing / discovery / resolution** surface.

## User-visible route posture
Frozen canonical posture:
- `/runs/:workflowRunId/workpages/schedule-v0`
- `/runs/:workflowRunId/workpages/eod-v0`
- `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`

The current `/demo/logistics/workpages/*` routes remain curated aliases/entrypoints until the run-backed surfaces are implemented and proven.

## What remains out of scope
- no schedule artifact-backed write path
- no EOD final-packet / approval / pointer-promotion flow
- no broad workspace/human-task modernization epic folded in here
- no generic workpage builder/runtime
- no live-dispatch day-of editing console
- no per-keystroke autosave into `artifact_versions`

## Why schedule write-path work is deferred
Schedule is still the most important business-facing surface, but it is also still the least natural one-artifact candidate. It remains composite across multiple weekly-planning inputs and still sits adjacent to the live-dispatch boundary.

That makes **run-backed schedule review** the right next step and **artifact-backed schedule editing** a later epic.
