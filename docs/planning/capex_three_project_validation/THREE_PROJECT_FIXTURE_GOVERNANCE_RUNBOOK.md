# CAPEX Three-Project Fixture Governance Runbook

## Status
- Status: `AUTHORITATIVE_SOURCE`
- Owner task: `TASK-0589`
- Source task: `TP-TASK-001`
- Gate family: `TP-G01..TP-G12`
- Activation posture: `planning_only_no_capex_activation`

This runbook defines governance for the K12, K3, and blind validation fixture
tiers. It does not release fixtures, approve expected-output manifests, import
project corpus material, start blind runs, approve pilot readiness, approve
production readiness, or activate CAPEX runtime/product behavior.

## Fixture Tiers
| Tier | Role | Allowed repo evidence | Off-repo handling |
|---|---|---|---|
| K12 | First binding real-project fixture family after SME-RP catalogue approval | Sanitized fixtures, manifests, hashes, aggregate evidence, release approvals | raw/full corpora stay off-repo in quarantine; source traceability remains by hash and manifest |
| K3 | Mini and shadow regression family for generalization checks | Sanitized mini-fixtures, expected behavior catalogues, invariant summaries, aggregate evidence | raw/full corpora stay off-repo; shadow runs produce redacted reports only |
| blind validation | Holdout family for defect discovery and no-overfitting checks | Frozen protocol manifests, aggregate baseline reports, evaluator summaries, leak-scan evidence | raw/full corpora stay off-repo with restricted access until freeze and baseline rules are satisfied |

## Governance Rules
- Raw/full corpora stay off-repo for all three tiers.
- Repo commits may include sanitized fixtures, manifests, hashes, aggregate
  evidence, and human release approval records only.
- Every fixture release requires quarantine, sensitivity review, redaction
  review, leak-scan, and release approval evidence.
- No-overfitting review is required after blind baseline evidence; changes must
  be classified as generalizable, fixture-specific, evidence-absent,
  deferred-module, or invalid expectation.
- No project-specific hardcoding is allowed in prompts, tests, source refs,
  retrieval recipes, task logic, or workpage logic.
- Agent Lab output is advisory only and cannot create official pointers,
  approvals, closure snapshots, or runtime truth mutations.

## Gate Mapping
| Gate | Governance meaning in this runbook |
|---|---|
| TP-G01 | Real-project quarantine and no repo/CI/log/generated-pack leakage baseline |
| TP-G02 | K12 sanitized slice release evidence before fixture use |
| TP-G03 | K12 MVP scenario evidence after fixture release |
| TP-G04 | K3 mini-fixture evidence after fixture release |
| TP-G05 | K3 shadow regression evidence from off-repo runs |
| TP-G06 | Blind validation freeze before first holdout run |
| TP-G07 | Blind baseline evidence before tuning |
| TP-G08 | No-overfitting review after blind baseline |
| TP-G09 | Agent Lab non-authority boundary |
| TP-G10 | Capacity realism from full off-repo corpus run evidence |
| TP-G11 | Cross-project invariant scorecard across released tiers |
| TP-G12 | Expected-output manifest versioning against schemas, policy, prompt/eval, and fixture compiler versions |

This `TP-TASK-001` runbook records governance structure only. It does not pass
all TP gates; later tasks must attach actual fixture, oracle, baseline,
scorecard, capacity, and expected-output evidence.

## Rollback/Recovery
- If fixture evidence is suspected of leaking restricted material, remove the
  fixture release, keep raw data quarantined, invalidate derived generated
  packs, and record a waiver or remediation task before reuse.
- If project-specific hardcoding is found, mark the affected evidence invalid,
  add no-overfitting review evidence, and rerun relevant cross-project checks.

## Non-Activation Boundary
Closing `TASK-0589` records fixture-governance planning evidence only. It is
not CAPEX runtime activation, product activation, public route approval,
workflow pack activation, corpus import approval, pilot approval, production
approval, or production-ready evidence.
