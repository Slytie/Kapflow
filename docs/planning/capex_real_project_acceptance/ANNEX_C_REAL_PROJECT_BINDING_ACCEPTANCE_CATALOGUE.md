# Annex C - Real-Project Binding Acceptance Catalogue

K12 is the first binding real-project fixture slice. The `K12-T1` through
`K12-T10` IDs are fixture-case IDs used to stress general CAPEX acceptance
rules; they are not a K12-specific product model or top-level acceptance namespace.

| Fixture case | Real-project situation | Expected system behavior |
|---|---|---|
| `K12-T1` | Scope 1 closed, Scope 2 closed, Scope 3 budget build-up | System shows scope statuses separately and prevents false overall closure. |
| `K12-T2` | Handover completed, residual items open | Handover is visible, but project closure remains open or restricted. |
| `K12-T3` | Supplier says defect fixed; operation has not confirmed effectiveness | Defect status remains observation phase / effectiveness open. |
| `K12-T4` | PR/PO exists, invoice or controlling figure deviates | System shows commercial deviation and creates clarification work. |
| `K12-T5` | Quotation contains assumptions or exclusions | Assumptions are extracted, but only adopted as project status after SME review. |
| `K12-T6` | New revision makes old evaluation uncertain | Affected evidence and decisions are marked as requiring review. |
| `K12-T7` | Executive cockpit aggregates status with open assumptions | Cockpit shows blockers and residual risk, not only green status. |
| `K12-T8` | Safety briefing for contractor is missing before work | Work release remains blocked or generates escalation work. |
| `K12-T9` | Fault recurs after handover | Defect can be reopened and classified as a systematic fault. |
| `K12-T10` | Commercial settlement exists, technical effectiveness is open | System separates commercially settled from technically closed. |

Minimum rule: no fixture case may create false official project status.
