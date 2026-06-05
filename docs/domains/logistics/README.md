# Logistics Domain Docs

This directory classifies logistics-specific documentation so it cannot be mistaken for CAPEX or platform-generic source.

## Current Sources
- `domain.yaml` is the ready-state domain runtime inventory for existing logistics workflows, workpages, and side effects. It is descriptive inventory, not a behavior-registration or activation surface.
- `current-state/` contains logistics docs that still describe supported runtime, workpage, or operator behavior.
- Authoritative workflow semantics remain in `docs/workflows/*/v1/` and are listed in `DOC_INVENTORY.yaml`.
- Operator runbooks remain in `docs/ops/runbooks/` and are listed as descriptive current-state docs.

## Archive
- `archive/` preserves older plans, briefs, closeout notes, and audits as historical context.
- Archived docs do not override workflow contracts, schemas, task records, or current status docs.
