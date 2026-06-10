# CAPX PM FE Demo Runbook

This is a disposable frontend-only design demo mounted under `/demo/capx/pm/*`.

## Run Locally

```bash
npm --prefix frontend run dev -- --host 127.0.0.1
```

Open:

- `/demo/capx/ui-versions`
- `/demo/capx/ui-versions/k12-pm-cockpit`
- `/capx-ui-versions/k12-pm-cockpit/index.html`
- `/demo/capx/ui-versions/design-a`
- `/demo/capx/ui-versions/design-a/P17`
- `/demo/capx/ui-one/home`
- `/demo/capx/pm`
- `/demo/capx/pm/projects`
- `/demo/capx/pm/projects/P-104`
- `/demo/capx/pm/projects/P-104/steps/documents`
- `/demo/capx/pm/projects/P-104/gantt`
- `/demo/capx/pm-v2/projects`
- `/demo/capx/pm-v2/projects/P-104`

The local review code is `capx-demo-local`. It is only a design-review speed bump and is not real security.

V2 is intentionally mounted separately under `/demo/capx/pm-v2/*` so the first PM demo remains available under `/demo/capx/pm/*`.

The A/B/C UI version review surface is mounted separately under `/demo/capx/ui-versions`. It embeds copied static source prototypes from `CAPEX_Compiled_All_Design_Artifacts_Master_Pack.zip` under `frontend/public/capx-ui-versions/`:

- Design A - Governed Workbench
- Design B - State Atlas
- Design C - Playbook OS

Design A also has a completed fixture-backed React build under `/demo/capx/ui-versions/design-a`, with page deep links such as `/demo/capx/ui-versions/design-a/P17`. It keeps all 31 Design A page contracts, source wireframes, allowed commands, blocked shortcuts, evidence drawer behavior, command receipts, and source markdown links available without backend mutation.

The side-by-side page links to the completed Design A build, the full copied source indexes, and all 12 A/B/C scenario routes for user testing. Designs B and C remain static source prototypes until their own build passes are completed.

The sanitized DL1 PM cockpit is mounted under `/demo/capx/ui-versions/k12-pm-cockpit` and embeds the static asset at `/capx-ui-versions/k12-pm-cockpit/index.html`. It is a sanitized copy of the user-supplied standalone HTML prototype, with fake project/supplier identifiers and no backend API calls.

## Review Posture

- Use fake local data only.
- Do not add real project numbers, suppliers, people, purchase orders, documents, or financial values.
- Remote previews must use server-side or platform-level protection.
- The demo does not call backend APIs and does not create official approvals, reports, or project updates.
