# SME-RP Approval-With-Conditions Sign-Off

## Status
Planning closeout wording for `TASK-0648` and `SME-RP-G001`.

## Sign-off wording
SME-RP acceptance is conditional and module-specific. It confirms that the
subject-matter target, acceptance conditions, and first real-project fixture
expectations are understood well enough to plan the affected module only.

This sign-off is not implementation approval. It is not CAPEX runtime
activation, product activation, public route approval, migration approval, raw
corpus import approval, or production/pilot readiness approval.

## Approval limits
- `conditional`: conditions remain open until each affected module records its
  own readiness evidence.
- `module_specific`: approval applies only to the named module, workflow,
  workpage family, projection family, snapshot/export surface, or external
  observation surface.
- `non_activation`: no runtime behavior, route, migration, deployment,
  public workpage, or raw corpus flow is authorized by this sign-off.
- `affected_module_only`: a blocked SME-RP condition blocks the affected module
  only; independent platform work may continue when it does not claim readiness
  for the blocked module.

## Required interpretation
No AI output, external status, workpage row, local folder state, file presence,
PR/PO/invoice, handover note, supplier statement, or generated artifact becomes
official CAPEX truth from this sign-off. Officialness still requires canonical
artifact, approval, task, event, and pointer evidence.

## Non-activation boundary
This document closes planning wording only. It does not add schemas, runtime
state, APIs, migrations, public routes, frontend behavior, raw K12/K3/blind
corpora, or CAPEX product activation.
