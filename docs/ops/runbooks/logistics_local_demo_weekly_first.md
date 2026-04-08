# Logistics Local Demo (Weekly First)

## Goal
- Run the first serious local logistics operator walkthrough from the weekly-first seed.
- Use the canonical runtime, workspace, artifact, approval, and pointer surfaces only.
- Treat this runbook as the start of demo-feedback collection, not EPIC-126 hardening.

If you want the deterministic canonical-workpage validation path without OpenAI or the full weekly/live/reporting loop, use `docs/ops/runbooks/logistics_canonical_workpage_demo.md` instead.

## Preconditions
1. Export a real `OPENAI_API_KEY` before the weekly Stage04 build step.
2. Use the supported local API entrypoint and the repo frontend dev server.
3. Keep the upload pack rooted at `fixtures/logistics/local_demo_upload_pack/`.

## Startup Commands
Backend terminal:
```bash
PYTHONPATH=src onetruth-api \
  --db-url sqlite:///./.tmp/logistics-local-demo.db \
  --host 127.0.0.1 \
  --port 8080 \
  --api-boundary-profile local_dev
```

Seeder terminal:
```bash
test -n "$OPENAI_API_KEY"
PYTHONPATH=src python3.11 scripts/run_logistics_local_demo.py \
  --db-url sqlite:///./.tmp/logistics-local-demo.db \
  --output-json .tmp/logistics-local-demo.json
cat .tmp/logistics-local-demo.json
```

Frontend terminal:
```bash
PYTHONPATH=src python3.11 scripts/run_logistics_demo_frontend.py \
  --demo-json .tmp/logistics-local-demo.json
```

The frontend launcher applies the canonical logistics local-dev request context so the seeded
`tenant-logistics / domain-hub` runtime state is visible in the browser.

Expected seeder output:
- `recommended_story_url`
- `weekly_workspace_url`
- `reporting_workspace_url`
- `live_workspace_url` as `null` before weekly publish
- `prepare_live_dispatch_path`
- `upload_pack_root`
- `openai_api_key_present`

## Upload Pack
- Weekly intake:
  - `fixtures/logistics/local_demo_upload_pack/weekly/weekly_route_slot_requirements.xlsx`
  - `fixtures/logistics/local_demo_upload_pack/weekly/weekly_approved_availability.xlsx`
  - `fixtures/logistics/local_demo_upload_pack/weekly/weekly_driver_capabilities.xlsx`
  - optional `fixtures/logistics/local_demo_upload_pack/weekly/weekly_actual_hours_snapshot_optional.xlsx`
  - `fixtures/logistics/local_demo_upload_pack/weekly/weekly_manager_review.docx`
- Live replan:
  - `fixtures/logistics/local_demo_upload_pack/live/live_route_delta_small_change.xlsx`
  - `fixtures/logistics/local_demo_upload_pack/live/live_dispatcher_review.docx`
- Reporting:
  - `fixtures/logistics/local_demo_upload_pack/reporting/reporting_eos_raw.xlsx`
  - `fixtures/logistics/local_demo_upload_pack/reporting/reporting_manager_review.docx`

## Walkthrough
1. Open `http://127.0.0.1:5173/demo/logistics?planning_week_id=PW-2026-W10&service_date_id=SD-2026-03-06`.
2. Click `Open weekly workspace`.
3. Claim `Weekly Input Intake`.
4. Upload the three required weekly workbooks, then optionally upload `weekly_actual_hours_snapshot_optional.xlsx`.
5. Complete the intake task.
6. Claim `Run Stage04 Build`.
7. Click `Run Stage04 Build` and wait for the OpenAI-backed run to succeed. The runtime will do one bounded finalize-only recovery if the model finishes without the required `finalize_weekly_stage04_draft_outputs` call, but it still fails closed if finalize never occurs.
8. Complete the Stage04 build task.
9. Claim `Final Review`.
10. Open the schedule workpage from the review task, make at least one bounded edit, and submit the new draft.
11. Return to the workspace, upload `weekly_manager_review.docx`, confirm review against the latest draft, and complete the review task.
12. Approve the Stage06 publish approval.
13. Return to `/demo/logistics` and click `Prepare service day`.
14. Click `Open live dispatch workspace`.
15. Claim `Prepare Live Day Inputs`.
16. Upload `live_route_delta_small_change.xlsx` and complete the intake task.
17. Claim `Review Live Replan`.
18. Upload `live_dispatcher_review.docx`, confirm review against the latest route-delta artifact, and complete the review task.
19. Return to `/demo/logistics` and click `Open reporting workspace`.
20. Claim `EOS Input Intake`.
21. Upload `reporting_eos_raw.xlsx` and complete the intake task.
22. Claim `Final Packet Review`.
23. Open the EOD workpage from the review task, make at least one bounded edit, and submit the new draft.
24. Return to the workspace, upload `reporting_manager_review.docx`, confirm review against the latest draft, and complete the review task.
25. Approve the Stage04 reporting approval.

## Expected End State
- Weekly truth has `planning.published_weekly_schedule.workbook`.
- Live truth has `dispatch.official_replan_delta.workbook`.
- Reporting truth has `reporting.final_packet.workbook`.
- `/demo/logistics` shows the prior reporting feedback edge from seed time plus the current weekly/live/reporting progression you just completed.

## Feedback Boundary
- Record demo friction, naming confusion, or missing affordances under `TASK-0157`.
- Do not treat this runbook as permission to start EPIC-126 hardening or widen product scope mid-demo.
