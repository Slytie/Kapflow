# ADR - EPIC-135 shared replan contact and runtime surfaces

## Status
Accepted on `2026-04-25`.

## Context
EPIC-135 reuses one shared `Edit Weekly Schedule` popup before and after publish, but the repo already has two authoritative backend lanes:
- `weekly_schedule_planning.v1` before publish
- `live_dispatch.v1` after publish

The initial EPIC-135 planning pass left two contract-level questions underspecified:
1. how driver phone/contact truth should exist without being embedded in driver capabilities
2. how a future post-publish live-dispatch agent/runtime surface can be added without inventing a popup-local or workflow-external execution path

Repo review also showed that:
- the current popup must reuse existing requirement/actionability/runtime truth rather than creating a second status vocabulary
- the current route-demand refresh-task creation path must be replaced before the manual scheduler CTA is removed
- there is no existing canonical contact dataset in the weekly/live workflow packs
- there is no existing live-dispatch equivalent of the weekly Stage04 specialized execute surface

## Decision

### 1. Driver contact truth is mirrored weekly/live bridge input, not capability truth
EPIC-135 adds mirrored workbook inputs:
- `planning.driver_contact_directory.workbook`
- `dispatch.driver_contact_directory.workbook`

These inputs are:
- separate from driver capabilities and approved availability
- workbook-only in this tranche
- read-side/operator-contact metadata only
- not hard eligibility truth

The shared popup may join those workbooks into candidate/replan projection so operators can contact recommended drivers, but scheduling validation and ranking continue to use the existing deterministic availability/capability/compliance substrate.

### 2. Live-dispatch bounded runtime must be authored before any endpoint exists
If `TASK-0230` remains in scope, it must first author the live-dispatch runtime surface in:
- the workflow pack
- execution-profile guidance
- capability/actionability semantics

Only after that authored surface exists may the repo add a bounded runtime entrypoint analogous to the weekly Stage04 runtime.

That runtime must:
- stay issue-scoped
- attach to canonical `task_run` / `human_task` / `execution_session` / `tool_execution` truth
- preserve deterministic Stage02 candidate generation as the default
- avoid becoming a popup-local or workflow-external execution system

## Consequences
- EPIC-135 planning/task memory must describe mirrored weekly/live contact inputs rather than a planning-only contact file.
- The shared popup contract must project status from existing requirement/actionability/runtime objects.
- The shared popup UI task (`TASK-0231`) can land before the later live-dispatch runtime task as long as weekly/live deterministic truth is already projected.
- Workflow-pack docs for weekly/live must be updated when these new contact inputs or future runtime surfaces are authored.
