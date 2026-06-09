# CAPEX Source Occurrence Context And Trust Contract

## Status
Accepted planning contract for `TASK-0652` and `SME-RP-G004`.

## Purpose
Source occurrence context is observed source truth, not reviewed project truth.
CAPEX evidence-driven modules need a shared occurrence-context profile and
source-trust taxonomy before they can claim SME-RP readiness.

This is a planning contract only. It does not add ingestion runtime, external
connector activation, schemas, migrations, APIs, routes, frontend behavior, raw
corpus import, or CAPEX product activation.

## Source occurrence separation
Source occurrence, SourceRef, evidence binding, review, approval, and official
adoption remain separate.

- A source occurrence records where observed material came from.
- A SourceRef points at a meaningful source occurrence.
- Evidence binding links a claim to reviewed source context.
- Review records whether the evidence is accepted, rejected, partial,
  contradictory, obsolete, insufficient, or accepted with residual risk.
- Approval records a governed decision by an authorized actor or policy path.
- Official adoption happens only through canonical artifacts, audited events,
  and promotion pointers.

No source occurrence field, imported metadata value, external status, generated
artifact, AI output, workpage state, raw file, or local folder state can overwrite
CAPEX state directly.

## Required context profile
Every future source occurrence context profile must preserve at least:

- `source_occurrence_id`
- `tenant_id`
- `domain`
- `project_id`
- `capex_scope_ref`
- `source_ref`
- `original_source_role`
- `package_workstream_ref`
- `source_state_hint`
- `extraction_state`
- `redaction_state`
- `source_origin_mode`
- `evidence_source_trust_mode`
- `observed_at`
- `custody_ref`

These fields are context for review and governance. They are not official
project status, closure state, permission, approval, or adoption state by
themselves.

## Source origin modes
The source origin mode vocabulary is exactly:

1. `primary`
2. `derivative`
3. `generated`
4. `external`
5. `imported`

## Evidence-source trust modes
The evidence-source trust mode vocabulary is exactly:

1. `observed`
2. `referenced`
3. `imported`
4. `reviewed`
5. `officially_adopted`

Trust mode describes the current evidence-source posture. It does not replace
the evidence-link status vocabulary, residual-risk acceptance, waiver state, or
approval state.

## Officialness guardrails
Raw files, external status, imported status, generated artifacts, AI output,
workpage state, local folder state, PR/PO/invoice state, supplier statements,
and handover notes cannot become official CAPEX claims without canonical
artifact, event, pointer, SourceRef, evidence-review, and approval evidence.

`officially_adopted` is permitted only after the source-backed claim has been
reviewed and adopted through the canonical one-truth substrate. It must not be
inferred from source import, external system status, generated content, or
operator-facing workpage projection state.

## Activation rule
Evidence-driven workflow, workpage, closure, projection, snapshot/export, and
external observation surfaces must not claim SME-RP readiness until they
preserve this context profile and trust taxonomy or record an explicit waiver.

External observation mode taxonomy under `SME-RP-G011` remains later scope; this
contract only prevents external or imported source posture from overwriting
CAPEX state.
