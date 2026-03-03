---
pattern_id: PATTERN-005
title: "StackStorm \u2014 Automation packs, action runners, rules/trigger model for\
  \ controlled tool execution"
source_notes: docs/patterns/sources/converted/StackStorm_st2_Architecture_Pattern_Extraction.md
tags:
- automation
- rules
- triggers
- actions
- runners
- packs
- plugins
- rbac
applies_to_epics:
- EPIC-060
- EPIC-070
- EPIC-090
use_when:
- Designing the **automation/tool execution plane** (actions, runners, capability
  boundaries).
- Designing **policy gates** and audited approvals for automation execution.
- Thinking about **pack/plugin packaging** for customer/tenant specific automation.
last_updated: '2026-02-28'
status: candidate
---

# PATTERN-005 — StackStorm — Automation packs, action runners, rules/trigger model for controlled tool execution

**Why this matters for our Stage 4 MVP**

- This is a *reference pattern*, not a dependency: we borrow semantics and guardrails, not code.
- Read this card first; only open the full source notes if the task is directly touching the affected subsystem.

## When to consult this

- Designing the **automation/tool execution plane** (actions, runners, capability boundaries).
- Designing **policy gates** and audited approvals for automation execution.
- Thinking about **pack/plugin packaging** for customer/tenant specific automation.

## Key patterns to borrow

- *Spike 1 — `artifact.promoted` sensor → eligibility computation**
- *Spike 2 — Partitioned spawn budget guardrail**
- *Spike 3 — Promotion gate workflow (human approval)**
- --
- **Delivery/consistency semantics:** Consumers ACK in `finally`; durability relies on staged DB persistence + explicit replay. ⟦st2common/st2common/transport/consumers.py::StagedQueueConsumer.process⟧ ⟦st2reactor/st2reactor/container/utils.py::create_trigger_instance⟧ ⟦st2reactor/st2reactor/cmd/trigger_re_fire.py::_refire_trigger_instance⟧
- **Isolation/security:** process + pack virtualenv + ephemeral tokens via env vars; not a hardened sandbox. ⟦st2common/st2common/util/virtualenvs.py::setup_pack_virtualenv⟧ ⟦st2common/st2common/runners/base.py::ActionRunner._get_common_action_env_variables⟧ ⟦st2actions/st2actions/container/base.py::RunnerContainerBase._get_action_auth_token⟧
- **Packs for task types/validators:** schema-validated, versioned units with isolated deps is a strong template; harden by avoiding pickle and adding containerization. ⟦st2common/st2common/bootstrap/base.py::ResourceRegistrar.register_packs⟧ ⟦st2common/st2common/validators/api/action.py::validate_action_parameters⟧ ⟦st2common/st2common/transport/publishers.py::PoolPublisher.publish⟧
- **Policies/limits:** emulate pre-run hook + concurrency-by-attr; replace non-durable retry with durable scheduling; add rate limiting + circuit breakers. ⟦st2common/st2common/services/policies.py::apply_pre_run_policies⟧ ⟦st2actions/st2actions/policies/concurrency_by_attr.py::ConcurrencyByAttributeApplicator.apply_before⟧ ⟦st2actions/st2actions/policies/retry.py::RetryPolicy.post_run⟧

## Pitfalls / what *not* to copy

_No explicit anti-pattern list extracted; treat source notes as informational only._

## How we map this into our platform (guidance)

- **Artifact-first**: always bind actions to `(dataset_key, partition_key, artifact_version_id)` and record promotion events.
- **Audit timeline**: every state change must emit a strongly-linked TimelineEvent (authoritative, transactional).
- **Tenant + domain isolation**: any queue/topic/index/prefix must be tenant-scoped; add negative tests.
- **Automation safety**: tool execution must be policy/approval gated and sandboxed.

## Source notes

- Full extraction: `docs/patterns/sources/converted/StackStorm_st2_Architecture_Pattern_Extraction.md`
