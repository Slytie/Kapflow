# Local Demo Upload Pack

This pack is the bounded file set for the weekly-first local logistics demo.

Contents:
- `weekly/weekly_route_slot_requirements.xlsx`
- `weekly/weekly_approved_availability.xlsx`
- `weekly/weekly_driver_capabilities.xlsx`
- `weekly/weekly_actual_hours_snapshot_optional.xlsx`
- `weekly/weekly_manager_review.docx`
- `live/live_route_delta_small_change.xlsx`
- `live/live_dispatcher_review.docx`
- `reporting/reporting_eos_raw.xlsx`
- `reporting/reporting_manager_review.docx`

Notes:
- The weekly workbook files are JSON-backed demo fixtures with `.xlsx` names so the current Stage04 bridge can ingest them through the bounded blob-to-JSON fallback.
- The reporting EOS workbook is a real `.xlsx` copied from the reporting template pack because the reporting build parses workbook bytes.
- The live small-change delta workbook is a bounded demo artifact for the linear no-approval path used in the first local walkthrough.
