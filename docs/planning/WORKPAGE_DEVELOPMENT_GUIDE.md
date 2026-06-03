# Workpage Development Guide

## Registry Boundary
Generic workpage action projection lives in `src/onetruth/application/services/workpage_action_projection.py`.
It delegates domain-specific action rules to the default `WorkpageActionRegistry` instead of hard-coding workflow IDs, stage IDs, or workpage decisions.

Generic workpage descriptor lookup lives behind `WorkpageDescriptorRegistry`.
The public descriptor lookup helpers remain stable compatibility facades, but active domain descriptor registrations live in descriptor packs.

The active domain pack is logistics:
- generic registry primitives: `src/onetruth/application/services/workpage_action_registry.py`
- active pack registration: `src/onetruth/application/services/workpage_action_registry_defaults.py`
- logistics rules and projection keys: `src/onetruth/application/services/logistics_workpage_action_registry.py`
- generic descriptor primitives and route/path helpers: `src/onetruth/application/services/workpage_descriptors.py`
- descriptor registry primitives: `src/onetruth/application/services/workpage_descriptor_registry.py`
- active descriptor registration: `src/onetruth/application/services/workpage_descriptor_registry_defaults.py`
- logistics route/path/action metadata registrations: `src/onetruth/application/services/logistics_workpage_descriptors.py`

## Adding A Domain Pack
Add future domain action rules by registering a `WorkpageActionPack` with projection builders and subject rules.
Add future workpage descriptors by registering a `WorkpageDescriptorPack`.
Do not add new domain workflow IDs, stage IDs, approval scope refs, unavailable reasons, or descriptor tables to the generic projection or descriptor facades.

New packs must preserve the public `workpage_actions` payload and must not activate CAPEX runtime behavior without the relevant task and gate evidence.
