---
id: TASK-0156
epic: EPIC-125
title: "Add the external cadence tick, single-node production-shaped deployment path, and operator runbook"
status: DONE
owners: ["backend", "ops"]
reviewers: ["qa"]
depends_on: ["TASK-0155"]
risk: medium
context_packs: ["codex/context/EPIC-125.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Why
After the local demo works, the repo needs a bounded continuous runtime posture for the first production-shaped environment.

## Scope
- add an idempotent repo-native cadence CLI tick for the supported weekly + daily loops
- document safe external invocation (cron/systemd/Kubernetes CronJob)
- document a single-node production-shaped deploy/runbook for the operator lane
- prove the cadence path is deterministic and replay-safe
- keep the architecture external-scheduler-first rather than embedding a new scheduler subsystem

## Out of scope
- multi-node orchestration
- broad SRE hardening
- unrelated deployment topology changes

## Acceptance signals
- the cadence tick can be invoked repeatedly without duplicating runs/tasks/artifacts
- the single-node production-shaped runbook is concrete enough to stand up the lane continuously
