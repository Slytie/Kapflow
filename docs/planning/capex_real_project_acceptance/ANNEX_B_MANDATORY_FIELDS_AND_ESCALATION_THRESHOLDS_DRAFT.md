# Annex B - Mandatory Fields and Escalation Thresholds Draft

This annex defines required commercial and escalation fields for CAPEX
real-project modules. It does not turn CAPEX into an ERP or accounting ledger;
commercial data remains observed and reconciled evidence unless officially
adopted through the canonical project-state path.

## Procurement / decision package minimum fields

- `scope_id`
- `capex_scope`
- `capex_main_group`
- `level_2_group`
- `budget_line`
- `approved_budget`
- `forecast`
- `purchase_requisition`
- `purchase_order`
- `supplier`
- `quotation`
- `change_order`
- `invoice`
- `controlling_allocation`
- `deviation_amount`
- `deviation_category`
- `technical_risk`
- `schedule_impact`
- `residual_risk`
- `evidence_refs`
- `recommendation`
- `decision_maker`
- `escalation_reason`
- `outcome`
- `conditions`

## Escalation threshold families

Threshold values must be provided by SME / PM / Controlling sign-off. The
platform supplies fields, policies, tasks, and validation hooks, but must not
invent numeric thresholds.

- budget deviation
- schedule shift with production impact
- safety or quality impact
- residual risk acceptance
- supplier dispute or claim exposure
- decision despite incomplete evidence
- recurring defect / system-effectiveness risk
