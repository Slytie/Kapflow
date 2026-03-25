import type { WorkpageViewModel } from "@/lib/types/workpages";

function cloneWorkpage<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

const SCHEDULE_WORKPAGE_EXAMPLE: WorkpageViewModel = {
  workpage_id: "schedule_workpage_v0_example",
  version: 2,
  title: "Weekly schedule review",
  mode: "example",
  workflow_id: "weekly_schedule_planning.v1",
  dataset_key: "planning.input_bundle.doc",
  source_artifact_version_id: null,
  source_examples: {
    route_slot_requirements:
      "docs/workflows/weekly_schedule_planning/v1/examples/route_slot_requirements_actual_ops_lab_v2.yaml",
    approved_availability:
      "docs/workflows/weekly_schedule_planning/v1/examples/approved_availability_actual_ops_lab_v1.yaml",
    driver_capabilities:
      "docs/workflows/weekly_schedule_planning/v1/examples/driver_capabilities_actual_ops_lab_v1.yaml",
    actual_hours_snapshot:
      "docs/workflows/weekly_schedule_planning/v1/examples/actual_hours_snapshot_actual_ops_lab_v1.yaml",
    stage04_input_bundle:
      "docs/workflows/weekly_schedule_planning/v1/examples/stage04_input_bundle_actual_ops_lab_v2.yaml"
  },
  summary: {
    planning_week_id: "PW-2026-W13",
    operational_week_start: "2026-03-22",
    service_area: "Pitt Meadows",
    station_code: "DVC4",
    total_routes_required: 134,
    drivers_in_scope: 51,
    on_call_target_per_day: 4,
    excess_capacity_target_per_day: 3,
    planner_note:
      "Holdout schedule contributed route totals only; staffing cells were intentionally excluded from the normalized example package."
  },
  sections: [
    {
      kind: "summary_cards",
      title: "Week summary",
      cards: [
        { key: "planning_week", label: "Planning week", value: "PW-2026-W13" },
        { key: "total_routes", label: "Required routes", value: 134 },
        { key: "drivers", label: "Drivers in scope", value: 51 },
        { key: "on_call_target", label: "Daily on-call target", value: 4 },
        { key: "excess_capacity_target", label: "Daily excess-capacity target", value: 3 }
      ]
    },
    {
      kind: "table",
      title: "Daily demand and coverage posture",
      table_id: "day_demand",
      columns: [
        { key: "service_date", label: "Service date" },
        { key: "planned_route_count", label: "Planned routes" },
        { key: "on_call_target", label: "On-call target" },
        { key: "excess_capacity_target", label: "Excess-capacity target" },
        { key: "note", label: "Note" }
      ],
      rows: [
        {
          service_date: "2026-03-22",
          planned_route_count: 16,
          on_call_target: 4,
          excess_capacity_target: 3,
          note: "Holdout route total override"
        },
        {
          service_date: "2026-03-23",
          planned_route_count: 23,
          on_call_target: 4,
          excess_capacity_target: 3,
          note: "Highest-demand day in the example week"
        },
        {
          service_date: "2026-03-24",
          planned_route_count: 20,
          on_call_target: 4,
          excess_capacity_target: 3,
          note: "Selected-day preview slice for early FE review"
        },
        {
          service_date: "2026-03-25",
          planned_route_count: 19,
          on_call_target: 4,
          excess_capacity_target: 3,
          note: "Stable mid-week posture"
        },
        {
          service_date: "2026-03-26",
          planned_route_count: 21,
          on_call_target: 4,
          excess_capacity_target: 3,
          note: "Elevated route load"
        },
        {
          service_date: "2026-03-27",
          planned_route_count: 18,
          on_call_target: 4,
          excess_capacity_target: 3,
          note: "Standard Friday posture"
        },
        {
          service_date: "2026-03-28",
          planned_route_count: 17,
          on_call_target: 4,
          excess_capacity_target: 3,
          note: "Weekend closeout"
        }
      ]
    },
    {
      kind: "table",
      title: "Selected-day preview",
      table_id: "selected_day_preview",
      columns: [
        { key: "service_date", label: "Selected day" },
        { key: "routes_required", label: "Routes required" },
        { key: "drivers_available", label: "Drivers available" },
        { key: "projected_on_call_needed", label: "On-call needed" },
        { key: "open_questions", label: "Open questions" }
      ],
      rows: [
        {
          service_date: "2026-03-24",
          routes_required: 20,
          drivers_available: 24,
          projected_on_call_needed: 4,
          open_questions: "Confirm late requests and final on-call posture before day-of handoff."
        }
      ]
    },
    {
      kind: "table",
      title: "Driver roster excerpt",
      table_id: "driver_roster",
      columns: [
        { key: "driver_name", label: "Driver" },
        { key: "employment_type", label: "Employment" },
        { key: "preferred_route_slot_classes", label: "Preferred slot" },
        { key: "target_shifts_per_week", label: "Target shifts" },
        { key: "on_call_eligible", label: "On-call eligible" },
        { key: "previous_week_minutes", label: "Previous-week minutes" },
        { key: "availability_summary", label: "Availability summary" }
      ],
      rows: [
        {
          driver_name: "Parampreet Singh",
          employment_type: "full_time",
          preferred_route_slot_classes: "cycle1_standard",
          target_shifts_per_week: 5,
          on_call_eligible: true,
          previous_week_minutes: 1200,
          availability_summary: "preferred 4 days; on-call-only 1 day; avoid-if-possible 2 days"
        },
        {
          driver_name: "Balwinder Singh",
          employment_type: "part_time",
          preferred_route_slot_classes: "cycle1_standard",
          target_shifts_per_week: 1,
          on_call_eligible: false,
          previous_week_minutes: 0,
          availability_summary: "avoid-if-possible all week in the normalized example"
        },
        {
          driver_name: "Navjot Singh",
          employment_type: "part_time",
          preferred_route_slot_classes: "cycle1_standard",
          target_shifts_per_week: 1,
          on_call_eligible: false,
          previous_week_minutes: 0,
          availability_summary: "available by heuristic upgrade in the normalized example"
        }
      ]
    },
    {
      kind: "note_panel",
      title: "Boundary note",
      body: "This page is a weekly-planning review surface. Any selected-day controls below are local what-if inputs for the prototype and do not replace live_dispatch.v1 day-of truth."
    },
    {
      kind: "form",
      title: "Selected-day what-if inputs",
      form_id: "selected_day_what_if",
      fields: [
        {
          key: "scenario_sick_calls",
          label: "Scenario sick calls",
          input: "multi_select",
          options: ["Parampreet Singh", "Balwinder Singh", "Navjot Singh"],
          value: []
        },
        {
          key: "scenario_on_call_assignments",
          label: "Scenario on-call assignments",
          input: "multi_select",
          options: ["Parampreet Singh", "Brahmvir Singh", "Sachin Goyal"],
          value: []
        },
        {
          key: "scenario_added_routes",
          label: "Scenario added routes",
          input: "integer",
          value: 0
        },
        {
          key: "scenario_dropped_routes",
          label: "Scenario dropped routes",
          input: "integer",
          value: 0
        },
        {
          key: "scenario_note",
          label: "Planner note",
          input: "textarea",
          value: ""
        }
      ]
    },
    {
      kind: "history_stub",
      title: "History",
      entries: [
        { label: "Previous week actual-hours snapshot", value: "available for comparison" },
        { label: "Rescue / fairness trend", value: "future slice" }
      ]
    }
  ],
  validation: {
    status: "informational",
    warnings: [
      "This fixture is excerpted for FE work. It is not yet tied to a backend artifact projection contract.",
      "Selected-day controls are local what-if inputs only and do not claim ownership of live dispatch truth."
    ]
  }
};

const END_OF_DAY_WORKPAGE_EXAMPLE: WorkpageViewModel = {
  workpage_id: "eod_report_workpage_v0_example",
  version: 2,
  title: "End-of-day report",
  mode: "example",
  workflow_id: "dispatch_reporting.v1",
  dataset_key: "reporting.upd_draft.workbook",
  source_artifact_version_id: null,
  source_examples: {
    eos_route_rows:
      "docs/workflows/dispatch_reporting/v1/examples/eos_route_rows_2026_03_16_qdci_partial_example.yaml",
    normalized_actuals:
      "docs/workflows/dispatch_reporting/v1/examples/normalized_actuals_2026_03_16_qdci_partial_example.yaml",
    upd_candidates:
      "docs/workflows/dispatch_reporting/v1/examples/upd_candidate_2026_03_16_qdci_partial_example.yaml"
  },
  summary: {
    service_date: "2026-03-16",
    station_code: "DVC4",
    dsp_name: "QDCI",
    total_routes_actual: 36,
    packages_dispatched: 5339,
    actual_dispatched: 5338,
    packages_delivered: 5282,
    packages_returned: 56,
    delivered_pct: 98.93,
    return_pct: 1.05,
    average_route_time: "8:41:14",
    formula_integrity_warning: true,
    warning_note:
      "Source workbook summary sheets contained broken formulas; row-level actuals remain the primary truth."
  },
  sections: [
    {
      kind: "summary_cards",
      title: "Daily summary",
      cards: [
        { key: "total_routes", label: "Total routes actual", value: 36 },
        { key: "packages_dispatched", label: "Packages dispatched", value: 5339 },
        { key: "packages_delivered", label: "Packages delivered", value: 5282 },
        { key: "packages_returned", label: "Packages returned", value: 56 },
        { key: "delivered_pct", label: "Delivered %", value: "98.93%" },
        { key: "average_route_time", label: "Average route time", value: "8:41:14" }
      ]
    },
    {
      kind: "note_panel",
      title: "Formula-integrity warning",
      body: "Source workbook summary tabs showed #REF!, #VALUE!, and #N/A failures. The v0 workpage should surface this warning instead of reproducing the broken formulas."
    },
    {
      kind: "table",
      title: "Route actuals",
      table_id: "route_actuals",
      columns: [
        { key: "route_id", label: "Route" },
        { key: "driver_name", label: "Driver" },
        { key: "packages_dispatched", label: "Dispatched" },
        { key: "packages_delivered", label: "Delivered" },
        { key: "planned_window", label: "Planned" },
        { key: "actual_window", label: "Actual" },
        { key: "actual_minutes", label: "Minutes" },
        { key: "returns", label: "Returns" },
        { key: "return_reasons", label: "Return reasons" },
        { key: "upd_candidate", label: "UPD?" }
      ],
      rows: [
        {
          route_id: "CX100",
          driver_name: "Brahamvir Singh",
          packages_dispatched: 286,
          packages_delivered: 286,
          planned_window: "11:50 - 18:40",
          actual_window: "11:50 - 22:27",
          actual_minutes: 637,
          returns: 0,
          return_reasons: "",
          upd_candidate: true
        },
        {
          route_id: "CX95",
          driver_name: "Tarandeep Singh",
          packages_dispatched: 292,
          packages_delivered: 290,
          planned_window: "11:50 - 18:20",
          actual_window: "11:50 - 21:37",
          actual_minutes: 587,
          returns: 2,
          return_reasons: "BC,FDD",
          upd_candidate: false
        },
        {
          route_id: "CX99",
          driver_name: "Yong-Kyoon Kim",
          packages_dispatched: 208,
          packages_delivered: 207,
          planned_window: "11:55 - 18:30",
          actual_window: "11:55 - 20:52",
          actual_minutes: 537,
          returns: 1,
          return_reasons: "NSL",
          upd_candidate: false
        }
      ]
    },
    {
      kind: "form",
      title: "Manual closeout",
      form_id: "closeout_details",
      fields: [
        {
          key: "sick_calls",
          label: "Sick calls",
          input: "multi_select",
          options: ["Brahamvir Singh", "Tarandeep Singh", "Yong-Kyoon Kim"],
          value: []
        },
        {
          key: "unavailable_drivers",
          label: "Not available",
          input: "multi_select",
          options: ["Brahamvir Singh", "Tarandeep Singh", "Yong-Kyoon Kim"],
          value: []
        },
        {
          key: "working_devices",
          label: "Working devices / rabbits",
          input: "text",
          value: ""
        },
        {
          key: "rescues",
          label: "Rescues",
          input: "repeater",
          value: []
        },
        {
          key: "incidents",
          label: "Incidents",
          input: "repeater",
          value: []
        },
        {
          key: "last_driver_clockout",
          label: "Last driver clock-out",
          input: "time",
          value: "22:27"
        },
        {
          key: "dispatcher_comment",
          label: "Dispatcher comment",
          input: "textarea",
          value: ""
        },
        {
          key: "manager_note",
          label: "Manager note",
          input: "textarea",
          value: ""
        }
      ]
    },
    {
      kind: "checklist",
      title: "UPD candidate review",
      checklist_id: "upd_candidates",
      items: [
        {
          item_id: "upd-candidate-cx100",
          title: "Brahamvir Singh · CX100",
          detail: ">600 minutes actual time",
          selected: false,
          note: "",
          tags: ["637 minutes"]
        },
        {
          item_id: "upd-candidate-cx95",
          title: "Tarandeep Singh · CX95",
          detail: "Below 600 minutes",
          selected: false,
          note: "",
          tags: ["587 minutes"]
        }
      ]
    },
    {
      kind: "history_stub",
      title: "History",
      entries: [
        { label: "Previous daily reports", value: "future slice" },
        { label: "Weekly / monthly summaries", value: "future slice" }
      ]
    }
  ],
  validation: {
    status: "informational",
    warnings: [
      "This fixture is a planning/test example only and is not yet backed by a backend artifact projection or submit contract.",
      "The 2026-03-16 reporting example pack is intentionally partial and exists to keep the prototype aligned to one consistent source family."
    ]
  }
};

export function buildScheduleWorkpageViewModel(): WorkpageViewModel {
  return cloneWorkpage(SCHEDULE_WORKPAGE_EXAMPLE);
}

export function buildEndOfDayWorkpageViewModel(): WorkpageViewModel {
  return cloneWorkpage(END_OF_DAY_WORKPAGE_EXAMPLE);
}
