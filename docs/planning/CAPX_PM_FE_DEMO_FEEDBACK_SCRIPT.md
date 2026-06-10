# CAPX PM FE Demo Feedback Script

Use one fake project, preferably `P-104 Packaging Line Retrofit`.

For A/B/C concept testing, start at `/demo/capx/ui-versions`.

Use `/demo/capx/ui-versions/design-a` for the completed Design A build. Use deep links such as `/demo/capx/ui-versions/design-a/P17` and `/demo/capx/ui-versions/design-a/P20` when testing assumption closure, evidence policy, approvals, and blocked shortcuts. Designs B and C are still static source prototypes in this pass, so capture build-quality feedback for A separately from concept feedback across A/B/C.

Use `/demo/capx/ui-versions/k12-pm-cockpit` for the sanitized static DL1 PM cockpit. Review it as a standalone PM workspace pattern: dashboard, lifecycle, Gantt, decision board, document map, risk/issue board, supplier overview, and PMO reporting.

Ask the PM reviewer:

1. Which project would you open first?
2. What is the next action?
3. Who is blocking the project?
4. What changed in the timeline?
5. What changed in budget or orders?
6. Which supplier answer is missing?
7. Which site handoff is missing?
8. Can you send the project report today?
9. What would you remove?
10. What would you rename?

For the static DL1 cockpit, also ask:

1. Which navigation tab would you use first?
2. Is the Gantt detail panel useful enough for shutdown/readiness review?
3. Does the decision board separate decisions, risks, documents, and suppliers clearly?
4. Does the generated PMO report include the right sections for a management update?
5. Which parts should become real governed workpages versus staying as dashboard summaries?

Capture accepted UI patterns, rejected UI patterns, and future real product requirements separately. The demo branch should produce feedback and design decisions, not permanent runtime authority.
