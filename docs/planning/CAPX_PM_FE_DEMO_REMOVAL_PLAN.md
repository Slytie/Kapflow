# CAPX PM FE Demo Removal Plan

This demo is removable by deleting the isolated frontend folder and removing the route mount.

## Remove Demo Runtime

- Delete `frontend/src/pages/capx-pm-fe-demo/`.
- Delete `frontend/src/pages/capx-pm-fe-demo-v2/`.
- Delete `frontend/src/pages/capx-ui-versions-demo/`.
- Delete `frontend/public/capx-ui-versions/`.
- Remove the `CapxPmFeDemoRoot` import from `frontend/src/app/App.tsx`.
- Remove the `CapxPmFeDemoV2Root` import from `frontend/src/app/App.tsx`.
- Remove the `CapxDesignAWorkbenchPage` import from `frontend/src/app/App.tsx`.
- Remove the `CapxK12PmCockpitPage` import from `frontend/src/app/App.tsx`.
- Remove the `CapxUiVersionsDemoPage` import from `frontend/src/app/App.tsx`.
- Remove the `/demo/capx/pm/*` route from `frontend/src/app/App.tsx`.
- Remove the `/demo/capx/pm-v2/*` route from `frontend/src/app/App.tsx`.
- Remove the `/demo/capx/ui-versions` route from `frontend/src/app/App.tsx`.
- Remove the `/demo/capx/ui-versions/design-a` and `/demo/capx/ui-versions/design-a/:pageId` routes from `frontend/src/app/App.tsx`.
- Remove the `/demo/capx/ui-versions/k12-pm-cockpit` route from `frontend/src/app/App.tsx`.

## Remove Review Docs

- Delete `docs/ops/runbooks/capx_pm_fe_demo.md`.
- Delete `docs/planning/CAPX_PM_FE_DEMO_FEEDBACK_SCRIPT.md`.
- Delete `docs/planning/CAPX_PM_FE_DEMO_REMOVAL_PLAN.md`.

## Verify Removal

```bash
git diff --check
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

The demo has no backend API, schema, generated snapshot, task-index, or production navigation removal step.
