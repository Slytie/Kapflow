# Workpage contract sketches — schedule-v0, route-demand-v0, driver-preferences-v0

These are sketches, not frozen schemas. Their purpose is to make the intended contract direction explicit for the implementing agent.

## 1. schedule-v0 artifact-backed contract sketch
```json
{
  "workpage": {
    "workpage_id": "schedule-v0",
    "workflow_id": "weekly_schedule_planning.v1",
    "version": 3,
    "title": "Weekly schedule",
    "source_artifact_version_id": "av-sched-draft-3"
  },
  "artifact_state": {
    "state_kind": "draft",
    "artifact_kind": "planning.draft_weekly_schedule.workbook",
    "editable": true,
    "accepted_artifact_version_id": "av-published-same-week"
  },
  "dependencies": [
    {
      "dependency_key": "route_slot_requirements",
      "artifact_version_id": "av-demand-9",
      "impact_class": "hard",
      "state": "aligned"
    },
    {
      "dependency_key": "driver_preferences",
      "artifact_version_id": "av-pref-2",
      "impact_class": "soft",
      "state": "aligned"
    }
  ],
  "calculations": {
    "top_bar": {
      "days": [
        {
          "service_date": "2026-03-22",
          "weekday_label": "Sun",
          "routes_required": 16,
          "routes_scheduled": 15,
          "on_call_drivers": 2,
          "total_staff": 17,
          "excess_capacity": 1,
          "available_driver_count": 4,
          "capacity_state": "ok"
        }
      ]
    },
    "driver_metrics": [
      {
        "driver_id": "drv-1",
        "driver_name": "Parampreet Singh",
        "scheduled_hours": 34.5,
        "scheduled_routes": 4,
        "on_call_shifts": 1,
        "preference_state": "open_to_work",
        "availability_state": "AVAILABLE",
        "compliance_state": "pass",
        "issues": []
      }
    ],
    "checks": [
      {
        "check_id": "working_hours_compliance",
        "label": "Working-hours compliance",
        "state": "pass",
        "blocking": true,
        "affected_driver_ids": []
      },
      {
        "check_id": "scheduled_capacity",
        "label": "Routes within scheduled capacity",
        "state": "warn",
        "blocking": true,
        "affected_service_dates": ["2026-03-24"]
      }
    ],
    "selected_day": {
      "service_date": "2026-03-24",
      "available_driver_count": 4,
      "available_driver_ids": ["drv-2", "drv-5", "drv-8", "drv-12"]
    }
  },
  "draft_lineage": {
    "current_artifact_version_id": "av-sched-draft-3",
    "latest_artifact_version_id": "av-sched-draft-3",
    "previous_artifact_version_id": "av-sched-draft-2",
    "recent_versions": []
  },
  "accepted_series": {
    "series_key": "weekly_schedule:scope-1",
    "current_artifact_version_id": "av-published-this-week",
    "previous_artifact_version_id": "av-published-prev-week",
    "next_artifact_version_id": null,
    "entries": []
  },
  "actions": [
    {
      "action_id": "schedule-v0:preview",
      "kind": "preview_recalc",
      "label": "Recalculate",
      "state": "available"
    },
    {
      "action_id": "schedule-v0:save-draft",
      "kind": "submit_artifact",
      "label": "Save draft",
      "state": "available"
    }
  ]
}
```

## 2. schedule-v0 preview request / response sketch
```json
{
  "action_id": "schedule-v0:preview",
  "rows": [],
  "reserve_rows": []
}
```

```json
{
  "calculations": {
    "top_bar": {},
    "driver_metrics": [],
    "checks": [],
    "selected_day": {}
  },
  "dependency_state": "aligned",
  "dirty": true
}
```

## 3. route-demand-v0 contract sketch
```json
{
  "workpage": {
    "workpage_id": "route-demand-v0",
    "workflow_id": "weekly_schedule_planning.v1",
    "version": 1,
    "title": "Route demand"
  },
  "artifact_state": {
    "state_kind": "draft_or_working",
    "artifact_kind": "planning.route_slot_requirements.workbook",
    "editable": true
  },
  "calculations": {
    "day_cards": [
      {
        "service_date": "2026-03-24",
        "routes_required": 16,
        "delta_from_previous": 1
      }
    ]
  },
  "actions": [
    {
      "action_id": "route-demand-v0:save",
      "kind": "submit_artifact",
      "label": "Save route demand",
      "state": "available"
    }
  ]
}
```

## 4. driver-preferences-v0 contract sketch
```json
{
  "workpage": {
    "workpage_id": "driver-preferences-v0",
    "workflow_id": "weekly_schedule_planning.v1",
    "version": 1,
    "title": "Driver preferences"
  },
  "artifact_state": {
    "state_kind": "snapshot",
    "editable": true
  },
  "sections": [
    {
      "kind": "preference_grid",
      "days": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
      "drivers": []
    }
  ]
}
```
