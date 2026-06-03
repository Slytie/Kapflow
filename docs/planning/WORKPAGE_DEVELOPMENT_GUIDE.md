# Workpage Development Guide

## Registry Boundary
Generic workpage action projection lives in `src/onetruth/application/services/workpage_action_projection.py`.
It delegates domain-specific action rules to the default `WorkpageActionRegistry` instead of hard-coding workflow IDs, stage IDs, or workpage decisions.

The active domain pack is logistics:
- generic registry primitives: `src/onetruth/application/services/workpage_action_registry.py`
- active pack registration: `src/onetruth/application/services/workpage_action_registry_defaults.py`
- logistics rules and projection keys: `src/onetruth/application/services/logistics_workpage_action_registry.py`
- route/path/action metadata: `src/onetruth/application/services/workpage_descriptors.py`

## Adding A Domain Pack
Add future domain action rules by registering a `WorkpageActionPack` with projection builders and subject rules.
Do not add new domain workflow IDs, stage IDs, approval scope refs, or unavailable reasons to the generic projection facade.

New packs must preserve the public `workpage_actions` payload and must not activate CAPEX runtime behavior without the relevant task and gate evidence.

