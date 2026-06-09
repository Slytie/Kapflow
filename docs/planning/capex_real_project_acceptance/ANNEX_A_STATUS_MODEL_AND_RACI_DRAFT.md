# Annex A - Status Model and RACI Draft

This annex is generalized under the `SME-RP` namespace. K12 motivated several
conditions, but these definitions are intended for CAPEX real-project modules.

## Authoritative contract refs

- `docs/architecture/CAPEX_RACI_ROLE_PERMISSION_MATRIX.md` records the accepted
  planning contract for RACI and role-permission posture under `SME-RP-G002`.
- `docs/architecture/CAPEX_EVIDENCE_STATUS_TRANSITION_CONTRACT.md` records the
  accepted planning contract for evidence-link status vocabulary and transition
  rules under `SME-RP-G004`.
- `docs/architecture/CAPEX_SOURCE_OCCURRENCE_CONTEXT_AND_TRUST_CONTRACT.md`
  records the accepted planning contract for source occurrence context and
  trust taxonomy under `SME-RP-G004`.
- `docs/architecture/CAPEX_WORKPAGE_TO_TASK_GENERATION_CONTRACT.md` records the
  accepted planning contract for workpage-to-task generation rules under
  `SME-RP-G005`.

## Evidence / evidence-link statuses

- `proposed`
- `under_review`
- `valid`
- `partly_valid`
- `contradictory`
- `obsolete`
- `invalid`
- `insufficient`
- `accepted_with_residual_risk`

## AI output statuses

- `ai_suggestion`
- `human_reviewed`
- `corrected`
- `rejected`
- `adopted_as_reviewed_state`
- `officially_adopted_via_pointer`

## Closure / handover statuses

- `open`
- `evidence_missing`
- `blocked`
- `eligible`
- `closed_satisfied`
- `closed_with_residuals`
- `observation_phase_active`
- `reopened`
- `superseded`

## RACI draft roles

- Project Manager
- Engineering SME
- Maintenance
- Production / Operator
- EHS
- Procurement
- Controlling
- Plant Management
- Technical Director
- CEO / Sponsor
- Supplier

## Decisions requiring RACI completion

- create source occurrence
- review evidence link
- approve decision package
- officially adopt project state
- close or reopen closure dimension
- waive evidence or residual risk
- escalate to CEO / Sponsor
