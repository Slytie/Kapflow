# Payroll v1 (secondary reference workflow)

> Compatibility note:
> `payroll.v1` remains the downstream payroll-finalization pack.
> The new adjacent pack `timecard_audit.v1` now owns the pre-payroll reconciliation wedge driven by dispatch actuals and payroll exports.

This folder contains the canonical authored workflow surface for the Payroll Stage 4 reference workflow.

- `WORKFLOW_CONTRACT.yaml` - workflow stages, approvals, triggers, and event inventory
- `ARTIFACT_MAP.yaml` - dataset keys mapped to the template pack
- `ACCEPTANCE_CRITERIA.md` - tests-as-spec guidance
- `OPERATING_MODEL.md` - domain assumptions, pay-period closure model, and review / lock semantics
- `DECISION_CATALOG.yaml` - canonical decision IDs and evidence requirements
- `EXECUTION_PROFILE.yaml` - canonical execution pattern and tool-class guidance

Template pack is in `fixtures/workflows/payroll/template_pack/`.
That template pack already includes both empty templates and synthetic completed examples that should seed future runtime scenario tests.

## Alignment rule
Any external runbook pack, tool registry matrix, approval log sheet, or CompanyOS IR for Payroll must be generated from the files in this folder and remain non-authoritative.
