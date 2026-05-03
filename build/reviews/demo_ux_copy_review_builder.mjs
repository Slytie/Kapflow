import fs from "node:fs/promises";
import path from "node:path";

import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const ROOT = process.cwd();
const OUTPUT_DIR = path.join(ROOT, "build", "reviews");
const OUTPUT_FILE = path.join(OUTPUT_DIR, "demo_ux_copy_review.xlsx");

const INVENTORY_COLUMNS = [
  "route_group",
  "page_variant",
  "ui_region",
  "component_or_snapshot",
  "source_ref",
  "state_variant",
  "control_type",
  "current_copy",
  "action",
  "proposed_copy",
  "reason",
  "severity",
  "notes"
];

const ROUTE_ORDER = [
  "Shared Shell",
  "Demo Shell",
  "Shared Workpage Chrome",
  "Shared Schedule Tools",
  "Schedule Landing",
  "Schedule Artifact",
  "Schedule Quick Edit",
  "Route Demand Landing",
  "Route Demand Artifact",
  "Route Demand Quick Edit",
  "Driver Preferences Landing",
  "Driver Preferences Artifact",
  "Driver Preferences Quick Edit",
  "EOD Landing",
  "EOD Artifact",
  "Dispatch Closeout Modal"
];

const SNAPSHOT_CONFIGS = [
  {
    file: "fixtures/frontend_contracts/workpage_schedule_v0_run_state.json",
    routeGroup: "Schedule Landing",
    pageVariant: "Landing",
    component: "workpage_schedule_v0_run_state.json",
    stateVariant: "run_snapshot"
  },
  {
    file: "fixtures/frontend_contracts/workpage_schedule_v0_artifact_state.json",
    routeGroup: "Schedule Artifact",
    pageVariant: "Artifact",
    component: "workpage_schedule_v0_artifact_state.json",
    stateVariant: "artifact_snapshot"
  },
  {
    file: "fixtures/frontend_contracts/workpage_route_demand_v0_run_state.json",
    routeGroup: "Route Demand Landing",
    pageVariant: "Landing",
    component: "workpage_route_demand_v0_run_state.json",
    stateVariant: "run_snapshot"
  },
  {
    file: "fixtures/frontend_contracts/workpage_route_demand_v0_artifact_state.json",
    routeGroup: "Route Demand Artifact",
    pageVariant: "Artifact",
    component: "workpage_route_demand_v0_artifact_state.json",
    stateVariant: "artifact_snapshot"
  },
  {
    file: "fixtures/frontend_contracts/workpage_driver_preferences_v0_run_state.json",
    routeGroup: "Driver Preferences Landing",
    pageVariant: "Landing",
    component: "workpage_driver_preferences_v0_run_state.json",
    stateVariant: "run_snapshot"
  },
  {
    file: "fixtures/frontend_contracts/workpage_driver_preferences_v0_artifact_state.json",
    routeGroup: "Driver Preferences Artifact",
    pageVariant: "Artifact",
    component: "workpage_driver_preferences_v0_artifact_state.json",
    stateVariant: "artifact_snapshot"
  },
  {
    file: "fixtures/frontend_contracts/workpage_eod_v0_run_state.json",
    routeGroup: "EOD Landing",
    pageVariant: "Landing",
    component: "workpage_eod_v0_run_state.json",
    stateVariant: "run_snapshot"
  },
  {
    file: "fixtures/frontend_contracts/workpage_eod_v0_artifact_state.json",
    routeGroup: "EOD Artifact",
    pageVariant: "Artifact",
    component: "workpage_eod_v0_artifact_state.json",
    stateVariant: "artifact_snapshot"
  }
];

function row(
  routeGroup,
  pageVariant,
  uiRegion,
  componentOrSnapshot,
  sourceRef,
  stateVariant,
  controlType,
  currentCopy
) {
  return {
    route_group: routeGroup,
    page_variant: pageVariant,
    ui_region: uiRegion,
    component_or_snapshot: componentOrSnapshot,
    source_ref: sourceRef,
    state_variant: stateVariant,
    control_type: controlType,
    current_copy: currentCopy.trim(),
    action: "",
    proposed_copy: "",
    reason: "",
    severity: "",
    notes: "",
    theme: ""
  };
}

const STATIC_ROWS = [
  row("Shared Shell", "Shell", "viewer_state", "AppShell", "frontend/src/app/AppShell.tsx:526", "loading", "state_title", "Loading viewer session"),
  row("Shared Shell", "Shell", "viewer_state", "AppShell", "frontend/src/app/AppShell.tsx:527", "loading", "state_detail", "Resolving server-derived viewer/bootstrap context."),
  row("Shared Shell", "Shell", "viewer_state", "AppShell", "frontend/src/app/AppShell.tsx:537", "error", "state_title", "Viewer session failed to load"),
  row("Shared Shell", "Shell", "viewer_state", "AppShell", "frontend/src/app/AppShell.tsx:548", "error", "state_title", "Viewer session missing"),
  row("Shared Shell", "Shell", "viewer_state", "AppShell", "frontend/src/app/AppShell.tsx:550", "error", "state_detail", "Viewer/bootstrap session did not resolve."),
  row("Shared Shell", "Shell", "identity", "AppShell", "frontend/src/app/AppShell.tsx:435", "default", "brand_label", "Logistics Demo"),
  row("Shared Shell", "Shell", "identity", "AppShell", "frontend/src/app/AppShell.tsx:420", "default", "metadata_label", "Viewer session"),
  row("Shared Shell", "Shell", "quick_actions", "AppShell", "frontend/src/app/AppShell.tsx:463", "default", "button_text", "Drivers"),
  row("Shared Shell", "Shell", "quick_actions", "AppShell", "frontend/src/app/AppShell.tsx:479", "default", "button_text", "Edit weekly schedule"),
  row("Shared Shell", "Shell", "quick_actions", "AppShell", "frontend/src/app/AppShell.tsx:495", "default", "button_text", "Edit route demand"),
  row("Shared Shell", "Shell", "quick_actions", "AppShell", "frontend/src/app/AppShell.tsx:514", "default", "button_text", "Upload route activity"),
  row("Shared Shell", "Shell", "menu", "AppShell", "frontend/src/app/AppShell.tsx:531", "default", "button_text", "Menu"),
  row("Shared Shell", "Shell", "menu", "AppShell", "frontend/src/app/AppShell.tsx:46", "default", "nav_link", "My Work"),
  row("Shared Shell", "Shell", "menu", "AppShell", "frontend/src/app/AppShell.tsx:47", "default", "nav_link", "Approvals"),
  row("Shared Shell", "Shell", "menu", "AppShell", "frontend/src/app/AppShell.tsx:48", "default", "nav_link", "Exceptions"),
  row("Shared Shell", "Shell", "menu", "AppShell", "frontend/src/app/AppShell.tsx:49", "default", "nav_link", "Official Outputs"),
  row("Shared Shell", "Shell", "secondary_routes", "AppShell", "frontend/src/app/AppShell.tsx:52", "default", "nav_link", "Run Details"),
  row("Shared Shell", "Shell", "secondary_routes", "AppShell", "frontend/src/app/AppShell.tsx:551", "default", "info_title", "Secondary detail routes"),
  row("Shared Shell", "Shell", "secondary_routes", "AppShell", "frontend/src/app/AppShell.tsx:552", "default", "info_detail", "Open secondary logistics detail destinations without taking extra header space."),
  row("Shared Shell", "Shell", "shell_fallback", "AppShell", "frontend/src/app/AppShell.tsx:451", "error", "empty_state", "Logistics family nav unavailable."),
  row("Shared Shell", "Shell", "shell_fallback", "AppShell", "frontend/src/app/AppShell.tsx:452", "loading", "loading_detail", "Loading logistics family nav..."),
  row("Shared Shell", "Shell", "freshness", "FreshnessBanner", "frontend/src/components/FreshnessBanner.tsx:16", "empty", "status_text", "Waiting for first API payload"),
  row("Shared Shell", "Shell", "freshness", "FreshnessBanner", "frontend/src/components/FreshnessBanner.tsx:21", "default", "status_text", "Polling every {n}s"),
  row("Shared Shell", "Shell", "freshness", "FreshnessBanner", "frontend/src/components/FreshnessBanner.tsx:23", "loading", "button_text", "Refreshing..."),
  row("Shared Shell", "Shell", "freshness", "FreshnessBanner", "frontend/src/components/FreshnessBanner.tsx:23", "default", "button_text", "Refresh"),
  row("Shared Shell", "Shell", "shared_state", "StatePanel", "frontend/src/components/StatePanel.tsx:16", "error", "button_text", "Retry"),

  row("Demo Shell", "Launcher", "task_board", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:382", "default", "section_title", "Editorial Task Board"),
  row("Demo Shell", "Launcher", "task_board", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:384", "default", "helper_text", "active tasks and approvals across weekly, live, and reporting work"),
  row("Demo Shell", "Launcher", "task_board", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:397", "default", "button_text", "Hide task board"),
  row("Demo Shell", "Launcher", "task_board", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:397", "default", "button_text", "Show task board"),
  row("Demo Shell", "Launcher", "task_board", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:406", "empty", "empty_state", "No active work in lane."),
  row("Demo Shell", "Launcher", "task_board", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:422", "default", "badge_label", "Task"),
  row("Demo Shell", "Launcher", "task_board", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:424", "default", "badge_label", "Approval"),
  row("Demo Shell", "Launcher", "task_board", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:425", "default", "badge_label", "Flag"),
  row("Demo Shell", "Launcher", "task_board", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:443", "collapsed", "helper_text", "The compact task strip stays pinned in the shell. Expand this board when you need the full lane view."),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:51", "default", "button_text", "Open schedule workpage"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:54", "default", "button_text", "Open EOD workpage"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:56", "default", "button_text", "Open full workspace"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:61", "default", "helper_text", "This demo shell now launches the canonical weekly schedule workpage for the selected run instead of editing drafts inline."),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:64", "default", "helper_text", "This demo shell now launches the canonical end-of-day workpage for the selected run instead of creating or submitting drafts inline."),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:66", "default", "helper_text", "This family module stays workspace-first in the current slice. Use the canonical workspace and run detail for intake, review, and approval."),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:93", "default", "eyebrow", "Workspace-first launcher"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:93", "default", "eyebrow", "Canonical launcher"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:111", "default", "metadata_label", "Workflow"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:115", "default", "metadata_label", "Workflow run"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:119", "default", "metadata_label", "Status"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:123", "default", "metadata_label", "Version"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:124", "default", "metadata_value", "unknown"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:141", "default", "button_text", "Open full workspace"),
  row("Demo Shell", "Launcher", "module_card", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:144", "default", "button_text", "Open run detail (secondary)"),
  row("Demo Shell", "Launcher", "state", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:353", "loading", "state_title", "Loading logistics demo story"),
  row("Demo Shell", "Launcher", "state", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:354", "loading", "state_detail", "Fetching canonical three-workflow story payload."),
  row("Demo Shell", "Launcher", "state", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:363", "error", "state_title", "Logistics story failed to load"),
  row("Demo Shell", "Launcher", "state", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:371", "empty", "empty_state", "No logistics story payload available"),
  row("Demo Shell", "Info Dialog", "module_info", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:459", "default", "info_detail", "Family-node metadata, run drill-down, and artifact access for the selected logistics module."),
  row("Demo Shell", "Info Dialog", "module_info", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:464", "default", "section_title", "Selected module"),
  row("Demo Shell", "Info Dialog", "module_info", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:465", "default", "helper_text", "Summary and technical node metadata for the current family module."),
  row("Demo Shell", "Info Dialog", "module_info", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:480", "default", "metadata_label", "Partition kind"),
  row("Demo Shell", "Info Dialog", "module_info", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:484", "default", "metadata_label", "Activation policy"),
  row("Demo Shell", "Info Dialog", "module_info", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:492", "default", "metadata_label", "Drill-down mode"),
  row("Demo Shell", "Info Dialog", "module_info", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:500", "default", "metadata_label", "Downloadable artifacts"),
  row("Demo Shell", "Info Dialog", "artifacts", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:510", "default", "section_title", "Artifacts"),
  row("Demo Shell", "Info Dialog", "artifacts", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:511", "default", "helper_text", "Family-level artifacts stay available here without occupying the launcher surface."),
  row("Demo Shell", "Info Dialog", "artifacts", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:515", "empty", "empty_state", "No family-node artifacts linked."),
  row("Demo Shell", "Info Dialog", "artifacts", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:521", "default", "button_text", "View family node artifacts"),
  row("Demo Shell", "Info Dialog", "drilldown", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:530", "default", "section_title", "Workflow Run Drill-Down"),
  row("Demo Shell", "Info Dialog", "drilldown", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:531", "default", "helper_text", "Choose the linked workflow run that should drive the launcher surface and drill-down graph."),
  row("Demo Shell", "Info Dialog", "drilldown", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:534", "empty", "empty_state", "No drill-down runs available."),
  row("Demo Shell", "Info Dialog", "drilldown", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:538", "default", "helper_text", "Single linked run selected automatically."),
  row("Demo Shell", "Info Dialog", "drilldown", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:543", "default", "helper_text", "Choose a workflow run to open drill-down."),
  row("Demo Shell", "Info Dialog", "drilldown", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:564", "default", "section_title", "Secondary detail routes"),
  row("Demo Shell", "Launcher", "drilldown", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:586", "empty", "state_title", "Choose a workflow run"),
  row("Demo Shell", "Launcher", "drilldown", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:587", "empty", "state_detail", "Pick a linked run in the summary above to load launcher links and drill-down here."),
  row("Demo Shell", "Launcher", "drilldown", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:608", "empty", "empty_state", "Select a family node to inspect metadata."),
  row("Demo Shell", "Drill-Down", "graph", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:617", "default", "section_title", "Workflow Run Graph Drill-Down"),
  row("Demo Shell", "Drill-Down", "graph", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:623", "loading", "state_title", "Loading workflow drill-down"),
  row("Demo Shell", "Drill-Down", "graph", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:624", "loading", "state_detail", "Fetching workflow-run workspace graph projection."),
  row("Demo Shell", "Drill-Down", "graph", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:630", "error", "state_title", "Workflow drill-down failed to load"),
  row("Demo Shell", "Insights", "official_outputs", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:670", "default", "section_title", "Official Outputs Summary"),
  row("Demo Shell", "Insights", "handoff", "LogisticsDemoPageContent", "frontend/src/components/logistics/LogisticsDemoPageContent.tsx:684", "default", "section_title", "Handoff Activity"),
  row("Demo Shell", "Shell Nav", "task_strip", "familyStory", "frontend/src/lib/logistics/familyStory.ts:275", "default", "lane_label", "To Do"),
  row("Demo Shell", "Shell Nav", "task_strip", "familyStory", "frontend/src/lib/logistics/familyStory.ts:276", "default", "lane_label", "In Progress"),
  row("Demo Shell", "Shell Nav", "task_strip", "familyStory", "frontend/src/lib/logistics/familyStory.ts:277", "default", "lane_label", "Waiting Review"),
  row("Demo Shell", "Shell Nav", "task_strip", "taskDocumentUi", "frontend/src/lib/workspace/taskDocumentUi.ts:138", "default", "status_text", "Missing inputs:"),
  row("Demo Shell", "Shell Nav", "task_strip", "taskDocumentUi", "frontend/src/lib/workspace/taskDocumentUi.ts:146", "default", "status_text", "linked artifacts"),
  row("Demo Shell", "Drawer", "task_drawer", "familyStory", "frontend/src/lib/logistics/familyStory.ts:307", "default", "helper_text", "Inspect context and run authoritative task actions from the centered task modal without leaving the logistics shell."),
  row("Demo Shell", "Drawer", "task_drawer", "familyStory", "frontend/src/lib/logistics/familyStory.ts:317", "default", "button_text", "Open Workspace"),
  row("Demo Shell", "Drawer", "approval_drawer", "familyStory", "frontend/src/lib/logistics/familyStory.ts:333", "default", "helper_text", "Approval context and response evidence remain in the shared detail drawer."),
  row("Demo Shell", "Drawer", "flag_drawer", "familyStory", "frontend/src/lib/logistics/familyStory.ts:347", "default", "helper_text", "Exceptions stay in the contextual rail, but the full runtime context still opens in the shared drawer."),
  row("Demo Shell", "Drawer", "graph_drawer", "runWorkspaceGraph", "frontend/src/lib/workspace/runWorkspaceGraph.ts:80", "default", "status_text", "Latest task:"),
  row("Demo Shell", "Drawer", "graph_drawer", "runWorkspaceGraph", "frontend/src/lib/workspace/runWorkspaceGraph.ts:84", "default", "status_text", "Claimed by"),
  row("Demo Shell", "Drawer", "graph_drawer", "runWorkspaceGraph", "frontend/src/lib/workspace/runWorkspaceGraph.ts:90", "default", "status_text", "Can claim:"),
  row("Demo Shell", "Drawer", "graph_drawer", "runWorkspaceGraph", "frontend/src/lib/workspace/runWorkspaceGraph.ts:103", "default", "status_text", "No active claimant"),
  row("Demo Shell", "Drawer", "graph_drawer", "runWorkspaceGraph", "frontend/src/lib/workspace/runWorkspaceGraph.ts:233", "default", "helper_text", "Graph node status is projected by the server workspace endpoint."),

  row("Shared Workpage Chrome", "Shared", "metadata", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:66", "default", "helper_text", "Canonical workpage projection served from backend-owned workflow artifacts and runtime truth."),
  row("Shared Workpage Chrome", "Shared", "hero", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:75", "default", "button_text", "Back to logistics demo"),
  row("Shared Workpage Chrome", "Shared", "info_dialog", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:78", "default", "info_title", "Workpage info"),
  row("Shared Workpage Chrome", "Shared", "metadata", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:83", "default", "metadata_value", "Composite source bundle"),
  row("Shared Workpage Chrome", "Shared", "metadata", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:99", "default", "section_title", "Source grounding"),
  row("Shared Workpage Chrome", "Shared", "metadata", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:111", "default", "metadata_label", "Workflow"),
  row("Shared Workpage Chrome", "Shared", "metadata", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:115", "default", "metadata_label", "Dataset key"),
  row("Shared Workpage Chrome", "Shared", "metadata", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:119", "default", "metadata_label", "Mode"),
  row("Shared Workpage Chrome", "Shared", "metadata", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:123", "default", "metadata_label", "Source mode"),
  row("Shared Workpage Chrome", "Shared", "metadata", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:127", "default", "metadata_label", "Primary dataset"),
  row("Shared Workpage Chrome", "Shared", "metadata", "WorkpageContent", "frontend/src/components/workpages/WorkpageContent.tsx:131", "default", "metadata_label", "Source version"),
  row("Shared Workpage Chrome", "Shared", "form", "WorkpageFormSection", "frontend/src/components/workpages/WorkpageFormSection.tsx:26", "empty", "empty_state", "No entries yet."),
  row("Shared Workpage Chrome", "Shared", "form", "WorkpageFormSection", "frontend/src/components/workpages/WorkpageFormSection.tsx:43", "default", "button_text", "Remove"),
  row("Shared Workpage Chrome", "Shared", "form", "WorkpageFormSection", "frontend/src/components/workpages/WorkpageFormSection.tsx:51", "default", "button_text", "Add entry"),
  row("Shared Workpage Chrome", "Shared", "checklist", "WorkpageChecklistSection", "frontend/src/components/workpages/WorkpageChecklistSection.tsx:46", "default", "field_label", "Manager note"),
  row("Shared Workpage Chrome", "Shared", "version_history", "DraftVersionTimeline", "frontend/src/components/workpages/DraftVersionTimeline.tsx:72", "default", "chip_label", "Current"),
  row("Shared Workpage Chrome", "Shared", "version_history", "DraftVersionTimeline", "frontend/src/components/workpages/DraftVersionTimeline.tsx:75", "default", "chip_label", "Latest"),
  row("Shared Workpage Chrome", "Shared", "version_history", "DraftVersionTimeline", "frontend/src/components/workpages/DraftVersionTimeline.tsx:77", "default", "chip_label", "Superseded"),
  row("Shared Workpage Chrome", "Shared", "version_history", "DraftVersionTimeline", "frontend/src/components/workpages/DraftVersionTimeline.tsx:90", "default", "status_text", "Current draft"),
  row("Shared Workpage Chrome", "Shared", "version_history", "DraftVersionTimeline", "frontend/src/components/workpages/DraftVersionTimeline.tsx:93", "default", "status_text", "Previous draft"),
  row("Shared Workpage Chrome", "Shared", "version_history", "DraftVersionTimeline", "frontend/src/components/workpages/DraftVersionTimeline.tsx:95", "default", "status_text", "Draft"),
  row("Shared Workpage Chrome", "Shared", "version_history", "DraftVersionTimeline", "frontend/src/components/workpages/DraftVersionTimeline.tsx:124", "default", "button_text", "Viewing"),
  row("Shared Workpage Chrome", "Shared", "version_history", "DraftVersionTimeline", "frontend/src/components/workpages/DraftVersionTimeline.tsx:124", "default", "button_text", "Open"),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:36", "default", "section_title", "Artifact lineage"),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:37", "default", "helper_text", "Technical lineage and raw workbook context stay available here while the main surface focuses on live metrics and version rails."),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:40", "default", "metadata_label", "Current artifact"),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:44", "default", "metadata_label", "Workflow run"),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:48", "default", "metadata_label", "Artifact kind"),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:52", "default", "metadata_label", "Latest in chain"),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:56", "default", "metadata_label", "Supersedes"),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:60", "default", "metadata_label", "Superseded by"),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:57", "default", "metadata_value", "Initial Stage04 draft"),
  row("Shared Workpage Chrome", "Shared", "advanced_info", "ScheduleArtifactAdvancedInfo", "frontend/src/components/workpages/ScheduleArtifactAdvancedInfo.tsx:61", "default", "metadata_value", "Current latest"),

  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:237", "default", "section_title", "Accepted history"),
  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:238", "default", "eyebrow", "Accepted series"),
  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:239", "default", "helper_text", "Accepted navigation stays on accepted weekly history only and never traverses draft lineage."),
  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:240", "empty", "empty_state", "No accepted schedule history is available for this surface yet."),
  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:250", "default", "button_text", "Previous accepted"),
  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:251", "default", "button_text", "Next accepted"),
  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:282", "default", "section_title", "Draft lineage"),
  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:283", "default", "eyebrow", "Draft rail"),
  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:284", "default", "helper_text", "Draft navigation stays within backend-authored draft lineage for this immutable schedule surface."),
  row("Shared Schedule Tools", "Shared", "history", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:285", "empty", "empty_state", "No draft lineage is available on this surface yet."),
  row("Shared Schedule Tools", "Shared", "status", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:253", "default", "section_title", "Dependency status"),
  row("Shared Schedule Tools", "Shared", "status", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:289", "default", "section_title", "Checks"),
  row("Shared Schedule Tools", "Shared", "status", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:280", "empty", "empty_state", "No dependency metadata available."),
  row("Shared Schedule Tools", "Shared", "status", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:315", "empty", "empty_state", "No checks emitted yet."),
  row("Shared Schedule Tools", "Shared", "status", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:309", "default", "status_text", "Blocking"),
  row("Shared Schedule Tools", "Shared", "status", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:309", "default", "status_text", "Advisory"),
  row("Shared Schedule Tools", "Shared", "status", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:415", "loading", "status_text", "Recalculating"),
  row("Shared Schedule Tools", "Shared", "status", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:417", "default", "status_text", "Preview applied"),
  row("Shared Schedule Tools", "Shared", "status", "ScheduleWorkpageSurface", "frontend/src/components/workpages/ScheduleWorkpageSurface.tsx:418", "default", "status_text", "No unsaved preview"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:351", "default", "eyebrow", "Weekly planning grid"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:359", "read_only", "helper_text", "Server-authoritative schedule heatmap. Edit controls stay on draft artifact pages."),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:360", "editable", "helper_text", "Click a filled cell to start moving planned work."),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:370", "default", "section_title", "Legend"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:406", "default", "column_label", "Roster"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:411", "default", "column_label", "Hours"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:415", "default", "column_label", "Routes"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:419", "default", "column_label", "On call"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:426", "default", "column_label", "Compliance"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:497", "default", "status_text", "Available on selected day"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:497", "default", "status_text", "Scheduled on selected day"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:498", "default", "status_text", "Compliance watch"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:261", "default", "status_text", "Open to work"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:264", "default", "status_text", "Prefer not to work"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:267", "default", "status_text", "Cannot work"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:269", "default", "status_text", "Unset"),
  row("Shared Schedule Tools", "Shared", "heatmap", "ScheduleHeatmapEditor", "frontend/src/components/workpages/ScheduleHeatmapEditor.tsx:110", "default", "helper_text", "driver only present in the current draft rows"),

  row("Schedule Landing", "Landing", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:466", "default", "hero_title", "Weekly Planning Review"),
  row("Schedule Landing", "Landing", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:467", "default", "hero_description", "A workflow-backed weekly planning review for bounded draft navigation, live schedule context, and backend-authored metrics."),
  row("Schedule Landing", "Landing", "info_dialog", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:482", "default", "info_title", "Weekly planning context"),
  row("Schedule Quick Edit", "Quick Edit", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:593", "loading", "state_title", "Loading weekly schedule editor"),
  row("Schedule Quick Edit", "Quick Edit", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:594", "loading", "state_detail", "Resolving the latest editable schedule draft for this weekly run."),
  row("Schedule Quick Edit", "Quick Edit", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:599", "error", "state_title", "Weekly schedule editor failed to load"),
  row("Schedule Quick Edit", "Quick Edit", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:618", "error", "state_title", "Weekly schedule editor is unavailable"),
  row("Schedule Quick Edit", "Quick Edit", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:619", "error", "state_detail", "No editable schedule draft is available for this weekly run yet."),
  row("Schedule Landing", "Route Guard", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:638", "error", "state_title", "Schedule draft route is unavailable"),
  row("Schedule Landing", "Route Guard", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:639", "error", "state_detail", "Open schedule drafts from a canonical workflow-run route."),
  row("Schedule Landing", "Route Guard", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:648", "error", "state_title", "Schedule draft route is incomplete"),
  row("Schedule Landing", "Route Guard", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:649", "error", "state_detail", "An artifact version id is required for schedule draft workpages."),
  row("Schedule Landing", "Route Guard", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:670", "error", "state_title", "Schedule workpage route is unavailable"),
  row("Schedule Landing", "Route Guard", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:671", "error", "state_detail", "Open schedule workpages from a canonical workflow-run route."),
  row("Schedule Landing", "Landing", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:701", "loading", "state_title", "Loading schedule workpage"),
  row("Schedule Landing", "Landing", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:702", "loading", "state_detail", "Fetching the workflow-run-backed schedule workpage."),
  row("Schedule Landing", "Landing", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:711", "error", "state_title", "Schedule workpage failed to load"),
  row("Schedule Landing", "Landing", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:734", "default", "helper_text", "Workflow-run-backed schedule projection served from canonical weekly Stage04 source artifacts."),
  row("Schedule Landing", "Landing", "action_cluster", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:773", "loading", "button_text", "Creating preferences snapshot..."),
  row("Schedule Landing", "Landing", "callout", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:782", "read_only", "callout_body", "This landing page stays read-only. Open the backend-selected latest draft when you need live preview and save controls."),
  row("Schedule Landing", "Landing", "callout", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:783", "empty", "callout_body", "This landing page stays read-only. The Stage04 draft weekly schedule artifact is not available for this run yet."),

  row("Schedule Artifact", "Artifact", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1050", "loading", "state_title", "Loading schedule draft artifact"),
  row("Schedule Artifact", "Artifact", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1051", "loading", "state_detail", "Fetching the immutable Stage04 draft weekly schedule artifact projection."),
  row("Schedule Artifact", "Artifact", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1068", "error", "state_title", "Schedule draft artifact failed to load"),
  row("Schedule Artifact", "Artifact", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1105", "default", "hero_title", "Weekly Schedule Draft Artifact"),
  row("Schedule Artifact", "Artifact", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1106", "default", "hero_description", "A bounded Stage04 draft workbook edit lane with live backend preview and explicit save into a new immutable draft version."),
  row("Schedule Artifact", "Artifact", "info_dialog", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1123", "default", "info_title", "Schedule draft context"),
  row("Schedule Artifact", "Artifact", "info_dialog", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1124", "default", "info_detail", "Artifact-backed projection of an immutable Stage04 draft weekly schedule workbook. Save creates a new superseding draft artifact version without publishing."),
  row("Schedule Artifact", "Artifact", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1125", "default", "hero_title", "Weekly Schedule Draft"),
  row("Schedule Artifact", "Artifact", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1145", "loading", "button_text", "Saving draft..."),
  row("Schedule Artifact", "Artifact", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1145", "default", "button_text", "Save draft"),
  row("Schedule Artifact", "Artifact", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1153", "loading", "button_text", "Downloading draft JSON..."),
  row("Schedule Artifact", "Artifact", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1153", "default", "button_text", "Download draft JSON"),
  row("Schedule Artifact", "Artifact", "hero", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1157", "default", "helper_text", "Live preview recalculates in place. Save creates the next immutable draft in this weekly lineage."),
  row("Schedule Artifact", "Artifact", "callout", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1216", "conflict", "callout_title", "Latest draft already exists"),
  row("Schedule Artifact", "Artifact", "callout", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1217", "conflict", "callout_body", "This base schedule artifact has already been superseded. Keep your local edits for now, then reopen the latest draft artifact before saving again."),
  row("Schedule Artifact", "Artifact", "callout", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1233", "stale", "callout_title", "Latest draft available"),
  row("Schedule Artifact", "Artifact", "callout", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1234", "stale", "callout_body", "This artifact version is no longer the latest draft in the chain. Reopen the latest version before saving more changes."),
  row("Schedule Artifact", "Artifact", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1250", "error", "state_title", "Draft save failed"),
  row("Schedule Artifact", "Artifact", "state", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1258", "error", "state_title", "Draft JSON download failed"),
  row("Schedule Artifact", "Artifact", "modal", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1273", "default", "eyebrow", "Driver status"),
  row("Schedule Artifact", "Artifact", "modal", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1274", "default", "modal_title", "Mark Sick / No Show"),
  row("Schedule Artifact", "Artifact", "modal", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1281", "default", "field_label", "Optional note"),
  row("Schedule Artifact", "Artifact", "modal", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1285", "default", "placeholder", "Add context for the operations log."),
  row("Schedule Artifact", "Artifact", "modal", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1290", "error", "state_title", "Sick / No Show failed"),
  row("Schedule Artifact", "Artifact", "modal", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1307", "default", "button_text", "Cancel"),
  row("Schedule Artifact", "Artifact", "modal", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1316", "loading", "button_text", "Marking..."),
  row("Schedule Artifact", "Artifact", "modal", "LogisticsScheduleWorkpagePageContent", "frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx:1316", "default", "button_text", "Confirm Sick / No Show"),

  row("Route Demand Landing", "Landing", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:554", "error", "state_title", "Route demand route is incomplete"),
  row("Route Demand Landing", "Landing", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:555", "error", "state_detail", "A workflow run id is required for route-demand workpages."),
  row("Route Demand Landing", "Landing", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:564", "loading", "state_title", "Loading route demand workpage"),
  row("Route Demand Landing", "Landing", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:565", "loading", "state_detail", "Fetching the workflow-run-backed route-demand landing page."),
  row("Route Demand Landing", "Landing", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:574", "error", "state_title", "Route demand workpage failed to load"),
  row("Route Demand Landing", "Landing", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:595", "default", "hero_title", "Route Demand Landing"),
  row("Route Demand Landing", "Landing", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:596", "default", "hero_description", "A read-only weekly landing page for backend-owned route-demand truth. Open the latest immutable artifact when you need to edit final daily counts."),
  row("Route Demand Landing", "Landing", "info_dialog", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:612", "default", "info_title", "Route demand context"),
  row("Route Demand Landing", "Landing", "info_dialog", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:613", "default", "info_detail", "Workflow-run-backed route-demand projection served from the latest canonical Stage04 route-demand artifact for this weekly run."),
  row("Route Demand Landing", "Landing", "action_cluster", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:656", "loading", "button_text", "Adding week..."),
  row("Route Demand Landing", "Landing", "action_cluster", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:656", "default", "button_text", "Add a week"),
  row("Route Demand Landing", "Landing", "callout", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:664", "read_only", "callout_title", "Editable route demand available"),
  row("Route Demand Landing", "Landing", "callout", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:665", "read_only", "callout_body", "This landing page stays read-only. Open the latest immutable route-demand artifact to adjust final daily counts and create a new successor version."),
  row("Route Demand Landing", "Landing", "callout", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:671", "read_only", "button_text", "Open route demand editor"),

  row("Route Demand Artifact", "Artifact", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:796", "loading", "state_title", "Loading route demand artifact"),
  row("Route Demand Artifact", "Artifact", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:797", "loading", "state_detail", "Fetching the artifact-backed route-demand editor."),
  row("Route Demand Artifact", "Artifact", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:806", "error", "state_title", "Route demand artifact failed to load"),
  row("Route Demand Artifact", "Artifact", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:944", "default", "hero_title", "Route Demand Artifact"),
  row("Route Demand Artifact", "Artifact", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:945", "default", "hero_description", "A bounded route-demand editor over immutable weekly route-demand workbooks. Saving creates the next immutable route-demand version and never mutates schedule artifacts."),
  row("Route Demand Artifact", "Artifact", "info_dialog", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:961", "default", "info_title", "Route demand artifact context"),
  row("Route Demand Artifact", "Artifact", "info_dialog", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:962", "default", "info_detail", "Artifact-backed route-demand projection served from an immutable Stage04 route-demand workbook version."),
  row("Route Demand Artifact", "Artifact", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:963", "default", "hero_title", "Daily route demand"),
  row("Route Demand Artifact", "Artifact", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:978", "loading", "button_text", "Saving route demand..."),
  row("Route Demand Artifact", "Artifact", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:978", "default", "button_text", "Save route demand"),
  row("Route Demand Artifact", "Artifact", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:989", "loading", "button_text", "Agent working"),
  row("Route Demand Artifact", "Artifact", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:989", "default", "button_text", "Save and run scheduling agent"),
  row("Route Demand Artifact", "Artifact", "hero", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:994", "default", "helper_text", "Plus/minus controls adjust backend-owned daily route counts. Save creates a new route-demand artifact version and leaves schedule artifacts untouched."),
  row("Route Demand Artifact", "Artifact", "callout", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1016", "default", "callout_title", "Next addable week"),
  row("Route Demand Artifact", "Artifact", "callout", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1020", "default", "callout_body", "is the next operational week available for route-demand activation."),
  row("Route Demand Artifact", "Artifact", "callout", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1044", "stale", "callout_title", "Latest route demand available"),
  row("Route Demand Artifact", "Artifact", "callout", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1045", "stale", "callout_body", "This route-demand version is historical. Open the latest version in the chain before saving additional changes."),
  row("Route Demand Artifact", "Artifact", "callout", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1061", "blocked", "callout_title", "Editing is currently blocked"),
  row("Route Demand Artifact", "Artifact", "callout", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1070", "blocked", "button_text", "Continue from schedule"),
  row("Route Demand Artifact", "Artifact", "banner", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:129", "blocked", "helper_text", "This future week already has weekly schedule draft truth. Continue from the schedule workpage instead of editing route demand here."),
  row("Route Demand Artifact", "Artifact", "banner", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:132", "blocked", "helper_text", "This route-demand version is historical and can no longer be edited."),
  row("Route Demand Artifact", "Artifact", "impact_banner", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:181", "default", "status_text", "Latest schedule draft is aligned"),
  row("Route Demand Artifact", "Artifact", "impact_banner", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:186", "warning", "status_text", "Latest schedule draft is stale"),
  row("Route Demand Artifact", "Artifact", "impact_banner", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:191", "warning", "status_text", "Refresh follow-up is open"),
  row("Route Demand Artifact", "Artifact", "impact_banner", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:196", "empty", "status_text", "No schedule draft exists yet"),
  row("Route Demand Artifact", "Artifact", "impact_banner", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:205", "default", "status_text", "Schedule impact available"),
  row("Route Demand Artifact", "Artifact", "impact_banner", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:210", "default", "section_title", "Schedule impact"),
  row("Route Demand Artifact", "Artifact", "history", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:258", "default", "section_title", "Recent route demand versions"),
  row("Route Demand Artifact", "Artifact", "history", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:259", "default", "helper_text", "The history rail stays within backend-authored immutable route-demand workbook lineage for this weekly run."),
  row("Route Demand Artifact", "Artifact", "history", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:275", "default", "status_text", "Current route demand"),
  row("Route Demand Artifact", "Artifact", "history", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:277", "default", "status_text", "Route-demand version"),
  row("Route Demand Artifact", "Artifact", "history", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:283", "empty", "empty_state", "No route-demand history is available yet."),

  row("Route Demand Quick Edit", "Quick Edit", "modal", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1173", "default", "eyebrow", "Quick edit"),
  row("Route Demand Quick Edit", "Quick Edit", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1187", "loading", "state_title", "Loading route demand editor"),
  row("Route Demand Quick Edit", "Quick Edit", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1188", "loading", "state_detail", "Resolving the latest route-demand artifact for this weekly run."),
  row("Route Demand Quick Edit", "Quick Edit", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1193", "error", "state_title", "Route demand editor failed to load"),
  row("Route Demand Quick Edit", "Quick Edit", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1215", "error", "state_title", "Route demand editor is unavailable"),
  row("Route Demand Quick Edit", "Quick Edit", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1216", "error", "state_detail", "No editable route-demand artifact is available for this weekly run yet."),
  row("Route Demand Quick Edit", "Route Guard", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1235", "error", "state_title", "Route demand artifact route is incomplete"),
  row("Route Demand Quick Edit", "Route Guard", "state", "LogisticsRouteDemandWorkpagePage", "frontend/src/pages/LogisticsRouteDemandWorkpagePage.tsx:1236", "error", "state_detail", "Both the workflow run id and artifact version id are required."),

  row("Driver Preferences Landing", "Landing", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:813", "loading", "state_title", "Loading driver preferences workpage"),
  row("Driver Preferences Landing", "Landing", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:814", "loading", "state_detail", "Fetching the workflow-run-backed driver preferences landing page."),
  row("Driver Preferences Landing", "Landing", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:823", "error", "state_title", "Driver preferences workpage failed to load"),
  row("Driver Preferences Landing", "Landing", "hero", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:840", "default", "hero_title", "Driver Preferences"),
  row("Driver Preferences Landing", "Landing", "hero", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:841", "default", "hero_description", "A weekly Sunday-Saturday advisory snapshot surface for soft schedule cues and history."),
  row("Driver Preferences Landing", "Landing", "info_dialog", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:858", "default", "info_title", "Driver preferences context"),
  row("Driver Preferences Landing", "Landing", "info_dialog", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:859", "default", "info_detail", "Workflow-run-backed landing surface over the latest immutable preferences snapshot when one exists."),
  row("Driver Preferences Landing", "Landing", "hero", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:860", "default", "helper_text", "Preference snapshots stay advisory only and never create refresh tasks."),
  row("Driver Preferences Landing", "Landing", "action_cluster", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:866", "default", "button_text", "Open latest snapshot"),
  row("Driver Preferences Landing", "Landing", "action_cluster", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:880", "loading", "button_text", "Creating preferences snapshot..."),
  row("Driver Preferences Landing", "Landing", "action_cluster", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:880", "default", "button_text", "Create preferences snapshot"),
  row("Driver Preferences Landing", "Landing", "action_cluster", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:883", "default", "button_text", "Open schedule landing"),
  row("Driver Preferences Landing", "Landing", "callout", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:918", "default", "callout_title", "Snapshot lifecycle"),
  row("Driver Preferences Landing", "Landing", "callout", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:919", "default", "callout_body", "The first snapshot is created explicitly on demand. Seeded cells start with deterministic advisory posture and remain soft guidance only."),

  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:659", "default", "section_title", "Availability exceptions"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:660", "default", "helper_text", "Approved future exceptions are kept separate from the weekly preference grid."),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:671", "default", "section_title", "Add exception"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:674", "default", "field_label", "Driver"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:686", "default", "field_label", "Start date"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:695", "default", "field_label", "End date"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:704", "default", "field_label", "Reason"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:720", "default", "field_label", "Note"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:734", "warning", "helper_text", "Unsaved grid edits remain local."),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:739", "error", "state_title", "Exception save failed"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:749", "loading", "button_text", "Saving exception..."),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:749", "default", "button_text", "Save exception"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:754", "default", "section_title", "Upcoming approved"),
  row("Driver Preferences Landing", "Landing", "availability", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:772", "empty", "empty_state", "No approved availability exceptions yet."),

  row("Driver Preferences Quick Edit", "Quick Edit", "modal", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1003", "default", "eyebrow", "Quick edit"),
  row("Driver Preferences Quick Edit", "Quick Edit", "modal", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1004", "default", "modal_title", "Drivers"),
  row("Driver Preferences Quick Edit", "Quick Edit", "modal", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1005", "default", "helper_text", "Edit the current weekly driver-preferences snapshot without leaving this page."),
  row("Driver Preferences Quick Edit", "Quick Edit", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1017", "loading", "state_title", "Loading driver preferences"),
  row("Driver Preferences Quick Edit", "Quick Edit", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1018", "loading", "state_detail", "Resolving the latest driver-preferences snapshot for this weekly run."),
  row("Driver Preferences Quick Edit", "Quick Edit", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1023", "error", "state_title", "Driver preferences failed to load"),
  row("Driver Preferences Quick Edit", "Quick Edit", "callout", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1040", "empty", "callout_title", "Create the first preferences snapshot"),
  row("Driver Preferences Quick Edit", "Quick Edit", "callout", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1041", "empty", "callout_body", "Driver editing starts by creating the immutable weekly preferences snapshot for this run. Add-driver support is intentionally deferred to the next driver task."),
  row("Driver Preferences Quick Edit", "Quick Edit", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1049", "error", "state_title", "Snapshot create failed"),
  row("Driver Preferences Quick Edit", "Quick Edit", "action_cluster", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1065", "loading", "button_text", "Creating snapshot..."),
  row("Driver Preferences Quick Edit", "Quick Edit", "action_cluster", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1065", "default", "button_text", "Create preferences snapshot"),
  row("Driver Preferences Quick Edit", "Quick Edit", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1072", "error", "state_title", "Driver preferences are unavailable"),
  row("Driver Preferences Quick Edit", "Quick Edit", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1073", "error", "state_detail", "No editable driver-preferences snapshot is available for this weekly run yet."),
  row("Driver Preferences Quick Edit", "Route Guard", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1092", "error", "state_title", "Driver preferences snapshot route is incomplete"),
  row("Driver Preferences Quick Edit", "Route Guard", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1093", "error", "state_detail", "Both the workflow run id and artifact version id are required."),

  row("Driver Preferences Artifact", "Artifact", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1180", "loading", "state_title", "Loading driver preferences snapshot"),
  row("Driver Preferences Artifact", "Artifact", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1181", "loading", "state_detail", "Fetching the immutable driver-preferences snapshot projection."),
  row("Driver Preferences Artifact", "Artifact", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1190", "error", "state_title", "Driver preferences snapshot failed to load"),
  row("Driver Preferences Artifact", "Artifact", "hero", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1224", "default", "hero_title", "Driver Preferences Snapshot"),
  row("Driver Preferences Artifact", "Artifact", "hero", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1225", "default", "hero_description", "An artifact-backed weekly advisory snapshot lane with immutable history and explicit save into a new snapshot version."),
  row("Driver Preferences Artifact", "Artifact", "info_dialog", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1246", "default", "info_title", "Driver preferences snapshot context"),
  row("Driver Preferences Artifact", "Artifact", "info_dialog", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1247", "default", "info_detail", "Artifact-backed projection of an immutable weekly advisory preferences snapshot."),
  row("Driver Preferences Artifact", "Artifact", "hero", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1255", "loading", "button_text", "Saving snapshot..."),
  row("Driver Preferences Artifact", "Artifact", "hero", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1255", "default", "button_text", "Save snapshot"),
  row("Driver Preferences Artifact", "Artifact", "hero", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1258", "default", "helper_text", "Saving creates the next immutable driver-preferences snapshot and leaves schedule truth untouched."),
  row("Driver Preferences Artifact", "Artifact", "callout", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1286", "conflict", "callout_title", "Latest snapshot already exists"),
  row("Driver Preferences Artifact", "Artifact", "callout", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1287", "conflict", "callout_body", "This base preferences snapshot has already been superseded. Keep your local edits for now, then reopen the latest snapshot before saving again."),
  row("Driver Preferences Artifact", "Artifact", "callout", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1303", "stale", "callout_title", "Latest snapshot available"),
  row("Driver Preferences Artifact", "Artifact", "callout", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1304", "stale", "callout_body", "This snapshot version is no longer the latest in the chain. Reopen the latest version before saving more changes."),
  row("Driver Preferences Artifact", "Artifact", "state", "LogisticsDriverPreferencesWorkpagePage", "frontend/src/pages/LogisticsDriverPreferencesWorkpagePage.tsx:1319", "error", "state_title", "Snapshot save failed"),

  row("EOD Landing", "Route Guard", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:774", "error", "state_title", "End-of-day workpage route is unavailable"),
  row("EOD Landing", "Route Guard", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:775", "error", "state_detail", "Open dispatch-reporting workpages from a canonical workflow-run route."),
  row("EOD Landing", "Landing", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:807", "loading", "state_title", "Loading end-of-day workpage"),
  row("EOD Landing", "Landing", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:808", "loading", "state_detail", "Fetching the workflow-run-backed dispatch-reporting landing workpage."),
  row("EOD Landing", "Landing", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:817", "error", "state_title", "End-of-day workpage failed to load"),
  row("EOD Landing", "Landing", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:836", "default", "helper_text", "Workflow-run-backed dispatch-reporting landing with latest-draft resolution over a canonical reporting run."),
  row("EOD Landing", "Landing", "callout", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:856", "read_only", "callout_title", "Latest draft available"),
  row("EOD Landing", "Landing", "callout", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:857", "read_only", "callout_body", "This landing page already resolved the newest editable workbook-backed draft for this reporting run. Reopen that draft before making closeout or UPD review edits."),
  row("EOD Landing", "Landing", "callout", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:866", "read_only", "button_text", "Open latest draft"),
  row("EOD Landing", "Landing", "callout", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:877", "empty", "callout_title", "Create editable draft"),
  row("EOD Landing", "Landing", "callout", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:878", "empty", "callout_body", "This landing page is a read-only preview. Create an immutable workbook-backed draft before making closeout or UPD review edits."),
  row("EOD Landing", "Landing", "action_cluster", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:891", "loading", "button_text", "Creating draft..."),
  row("EOD Landing", "Landing", "action_cluster", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:891", "default", "button_text", "Create editable draft"),

  row("EOD Artifact", "Artifact", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:526", "loading", "state_title", "Loading artifact-backed EOD draft"),
  row("EOD Artifact", "Artifact", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:527", "loading", "state_detail", "Fetching the immutable workbook-backed EOD workpage projection."),
  row("EOD Artifact", "Artifact", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:536", "error", "state_title", "Artifact-backed EOD draft failed to load"),
  row("EOD Artifact", "Artifact", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:388", "default", "hero_title", "Dispatch Reporting Draft"),
  row("EOD Artifact", "Artifact", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:389", "default", "hero_description", "A bounded EOD workpage for route actual review, closeout capture, and UPD draft posture."),
  row("EOD Artifact", "Artifact", "info_dialog", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:404", "default", "info_title", "EOD draft context"),
  row("EOD Artifact", "Artifact", "info_dialog", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:575", "default", "info_detail", "Artifact-backed projection of an immutable Stage03 reporting workbook draft. Submit creates a new superseding workbook artifact version."),
  row("EOD Artifact", "Artifact", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:619", "loading", "button_text", "Submitting draft..."),
  row("EOD Artifact", "Artifact", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:619", "default", "button_text", "Submit draft"),
  row("EOD Artifact", "Artifact", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:627", "loading", "button_text", "Downloading workbook..."),
  row("EOD Artifact", "Artifact", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:627", "default", "button_text", "Download workbook"),
  row("EOD Artifact", "Artifact", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:633", "default", "button_text", "Back to query landing"),
  row("EOD Artifact", "Artifact", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:638", "default", "helper_text", "Submit creates a new immutable workbook artifact version. The current draft remains authoritative until you explicitly submit."),
  row("EOD Artifact", "Artifact", "history", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:652", "default", "section_title", "Recent draft versions"),
  row("EOD Artifact", "Artifact", "history", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:653", "default", "helper_text", "Backend-authored immutable `reporting.upd_draft.workbook` lineage for this reporting run. Use these links to reopen adjacent draft states without leaving the canonical EOD workpage surface."),
  row("EOD Artifact", "Artifact", "history", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:660", "empty", "empty_state", "No recent draft history is available for this reporting run yet."),
  row("EOD Artifact", "Artifact", "callout", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:688", "conflict", "callout_title", "Latest draft already exists"),
  row("EOD Artifact", "Artifact", "callout", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:689", "conflict", "callout_body", "This base artifact has already been superseded. Keep your local edits for now, then reopen the latest artifact-backed draft before submitting again."),
  row("EOD Artifact", "Artifact", "callout", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:720", "stale", "callout_title", "Latest draft available"),
  row("EOD Artifact", "Artifact", "callout", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:721", "stale", "callout_body", "This artifact version is no longer the latest draft in the chain. Reopen the latest version before submitting more changes."),
  row("EOD Artifact", "Artifact", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:748", "error", "state_title", "Draft submit failed"),
  row("EOD Artifact", "Artifact", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:756", "error", "state_title", "Workbook download failed"),
  row("EOD Artifact", "Route Guard", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1409", "error", "state_title", "Artifact-backed EOD route is unavailable"),
  row("EOD Artifact", "Route Guard", "state", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1410", "error", "state_detail", "Open EOD drafts from a canonical workflow-run route."),

  row("Dispatch Closeout Modal", "Modal", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1104", "default", "eyebrow", "Dispatch closeout"),
  row("Dispatch Closeout Modal", "Modal", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1105", "default", "modal_title", "Upload route activity"),
  row("Dispatch Closeout Modal", "Modal", "hero", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1106", "default", "helper_text", "Import the daily workbook, review the generated EOD draft, attach manager evidence, and complete the canonical approval loop without leaving the workpage."),
  row("Dispatch Closeout Modal", "Step 1", "import", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1118", "default", "section_title", "1. Import route activity"),
  row("Dispatch Closeout Modal", "Step 1", "import", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1119", "default", "helper_text", "Upload the raw EOS workbook to the Stage01 intake task. Completing intake seeds the latest immutable EOD draft for review."),
  row("Dispatch Closeout Modal", "Step 1", "import", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1125", "default", "field_label", "Route-activity workbook"),
  row("Dispatch Closeout Modal", "Step 1", "import", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1141", "loading", "button_text", "Importing workbook..."),
  row("Dispatch Closeout Modal", "Step 1", "import", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1141", "default", "button_text", "Import route activity"),
  row("Dispatch Closeout Modal", "Step 1", "import", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1147", "default", "status_text", "Latest draft ready:"),
  row("Dispatch Closeout Modal", "Step 1", "import", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1150", "empty", "empty_state", "No imported EOD draft is available for this run yet."),
  row("Dispatch Closeout Modal", "Step 1", "import", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1154", "error", "state_title", "Route-activity import failed"),
  row("Dispatch Closeout Modal", "Step 2", "draft", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1162", "default", "section_title", "2. Review and submit the latest draft"),
  row("Dispatch Closeout Modal", "Step 2", "draft", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1163", "default", "helper_text", "Work directly in the artifact-backed EOD editor. Each submit creates a new immutable draft version and keeps the closeout flow pinned to the newest artifact."),
  row("Dispatch Closeout Modal", "Step 2", "draft", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1171", "loading", "state_title", "Loading draft context"),
  row("Dispatch Closeout Modal", "Step 2", "draft", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1172", "loading", "state_detail", "Resolving the latest dispatch-reporting draft for this run."),
  row("Dispatch Closeout Modal", "Step 2", "draft", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1184", "empty", "state_title", "Draft not ready yet"),
  row("Dispatch Closeout Modal", "Step 2", "draft", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1185", "empty", "state_detail", "Import the workbook first, or wait for the latest EOD draft to resolve."),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1192", "default", "section_title", "3. Complete review packet handoff"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1193", "default", "helper_text", "Attach the manager review packet, confirm the latest draft review, and then complete the Stage04 review task to request manager approval."),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1201", "loading", "state_title", "Loading review task"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1202", "loading", "state_detail", "Resolving the latest Stage04 review task for this reporting run."),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1208", "default", "status_text", "Review task status:"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1211", "default", "status_text", "Manager review upload:"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1215", "default", "status_text", "Draft review confirmation:"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1211", "default", "status_text", "Required"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1211", "default", "status_text", "Attached or no longer required"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1215", "default", "status_text", "Confirmed"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1215", "default", "status_text", "Still required"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1219", "default", "field_label", "Manager review file"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1236", "loading", "button_text", "Uploading review..."),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1236", "default", "button_text", "Attach manager review"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1246", "loading", "button_text", "Confirming review..."),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1246", "default", "button_text", "Confirm latest draft review"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1256", "loading", "button_text", "Completing review..."),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1256", "default", "button_text", "Complete review task"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1262", "error", "state_title", "Manager review upload failed"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1272", "error", "state_title", "Review confirmation failed"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1282", "error", "state_title", "Review completion failed"),
  row("Dispatch Closeout Modal", "Step 3", "review", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1290", "empty", "empty_state", "The review task will appear here after Stage01 intake completes."),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1398", "default", "section_title", "4. Respond to manager approval"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1399", "default", "helper_text", "Approval stays canonical. Approving here finalizes the reporting packet and triggers the weekly-planning actual-hours handoff."),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1405", "default", "callout_title", "Closeout updated"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1416", "default", "status_text", "Pending approval:"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1420", "error", "state_title", "Approval role required"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1421", "error", "state_detail", "The current viewer session cannot respond to this approval. Switch to an actor with the required manager role to finish closeout in this popup."),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1424", "default", "field_label", "Approval note"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1431", "default", "placeholder", "Optional note for the approval response"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1446", "loading", "button_text", "Submitting approval..."),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1446", "default", "button_text", "Approve final packet"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1457", "default", "button_text", "Request changes"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1474", "default", "button_text", "Reject"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1478", "error", "state_title", "Approval response failed"),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1488", "waiting", "empty_state", "Waiting for the pending approval to refresh."),
  row("Dispatch Closeout Modal", "Step 4", "approval", "DispatchReportWorkpagePage", "frontend/src/pages/DispatchReportWorkpagePage.tsx:1489", "waiting", "empty_state", "Complete the review task to request manager approval.")
];

const GLOSSARY_ROWS = [
  ["canonical", "main or current", "Use when the product is distinguishing the main demo path from secondary/detail pages.", "Avoid exposing platform authority-model language to demo users."],
  ["workpage", "page", "Use in navigation, titles, buttons, and helper text.", "Only keep 'workpage' in internal docs or APIs."],
  ["artifact", "saved version or workbook", "Use when the UI needs to explain that edits create a new saved copy.", "Avoid raw 'artifact' unless the audience is technical."],
  ["workflow run", "run or process", "Use when operators need to know they are looking at a specific schedule or reporting run.", "Avoid 'workflow-run-backed' and raw ids in primary UI copy."],
  ["immutable", "saved as a new version", "Use when explaining save/submit behavior.", "Avoid 'immutable' in operator-facing callouts."],
  ["projection", "view", "Use for read-only pages that show data pulled from other sources.", "Avoid 'projection' in hero text and warnings."],
  ["lineage", "version history", "Use in history rails or adjacent-version navigation.", "Avoid 'lineage' outside technical tools."],
  ["drift or stale", "out of date", "Use when a draft or snapshot no longer matches the latest input.", "Prefer plain status language over runtime semantics."],
  ["source grounding or dataset key", "data source", "Use in info dialogs only when operators truly need source context.", "Hide raw dataset keys, refs, and source versions from default views."],
  ["Stage03 or Stage04", "draft stage or planning stage", "Use only if stage language is necessary for support or troubleshooting.", "Prefer business steps over numbered stages."],
  ["UPD", "UPD (over-600 review)", "Use where the operator likely knows UPD but may need a reminder.", "Avoid unexplained acronyms in first-view copy."],
  ["route demand", "planned routes or route needs", "Use when you want plainer wording for non-specialists.", "Keep 'route demand' only where the audience already uses that term daily."],
  ["advisory or soft", "for guidance only", "Use on preference-only surfaces that do not block schedule actions.", "Avoid 'soft drift' and similar internal phrasing."],
  ["authoritative truth", "current source data", "Use sparingly in info dialogs or support text.", "Do not present authority-model language in the main task flow."]
];

const TECHNICAL_TABLE_COLUMNS = new Map([
  ["Route Slot Id", { action: "remove", proposed: "Remove from demo table", reason: "Raw slot ids are system-facing identifiers and do not help an operator complete the task.", severity: "high", theme: "Raw system metadata" }],
  ["Assigned Driver Id", { action: "rewrite", proposed: "Assigned driver", reason: "Use names instead of internal ids in operator-facing tables.", severity: "high", theme: "Raw system metadata" }],
  ["Assignment Status", { action: "rewrite", proposed: "Assignment", reason: "The technical status phrasing is more detailed than operators need on the demo surface.", severity: "medium", theme: "Technical versioning detail" }],
  ["Projected Minutes", { action: "rewrite", proposed: "Planned minutes", reason: "This label is clearer for operators and avoids model-oriented wording.", severity: "medium", theme: "Operator-friendly as is" }],
  ["Baseline Template State", { action: "remove", proposed: "Remove from demo table", reason: "Template-state internals are implementation detail, not operator copy.", severity: "high", theme: "Raw system metadata" }],
  ["Planned Driver Day State", { action: "remove", proposed: "Remove from demo table", reason: "The phrase is internal planning vocabulary and would confuse demo users.", severity: "high", theme: "Internal platform jargon" }],
  ["New Agreement Required", { action: "remove", proposed: "Remove from demo table", reason: "This internal change-management detail is not understandable without product training.", severity: "high", theme: "Raw system metadata" }],
  ["New Agreement Trigger Reason", { action: "remove", proposed: "Remove from demo table", reason: "Trigger-reason detail is internal logic that should not appear in a demo table.", severity: "high", theme: "Raw system metadata" }],
  ["Template State Preservation Fit", { action: "remove", proposed: "Remove from demo table", reason: "Preservation-fit wording is technical and not operator-friendly.", severity: "high", theme: "Internal platform jargon" }],
  ["Candidate Delta Id", { action: "remove", proposed: "Remove from demo table", reason: "Raw delta ids are system metadata.", severity: "high", theme: "Raw system metadata" }],
  ["Source Bundle Id", { action: "remove", proposed: "Remove from demo table", reason: "Bundle ids are implementation detail.", severity: "high", theme: "Raw system metadata" }],
  ["Iteration Index", { action: "remove", proposed: "Remove from demo table", reason: "Iteration counters are model-debug detail, not operator copy.", severity: "high", theme: "Technical versioning detail" }],
  ["Delta Kind", { action: "remove", proposed: "Remove from demo table", reason: "Delta categories are internal planning terminology.", severity: "high", theme: "Technical versioning detail" }],
  ["Previous Week Stability", { action: "rewrite", proposed: "Compared with last week", reason: "The concept may be useful, but the current label is too abstract.", severity: "medium", theme: "Boundary explanation is too technical" }],
  ["Route Id", { action: "remove", proposed: "Remove from demo table", reason: "Internal route ids add noise when a route name or number is not also shown.", severity: "high", theme: "Raw system metadata" }],
  ["Phase", { action: "remove", proposed: "Remove from demo table", reason: "Phase is too vague and technical without more context.", severity: "medium", theme: "Stage/workflow codes" }],
  ["Availability State", { action: "rewrite", proposed: "Availability", reason: "The concept is useful, but the wording is overly technical.", severity: "medium", theme: "Internal platform jargon" }],
  ["Rationale Code", { action: "remove", proposed: "Remove from demo table", reason: "Codes should not be shown without user-friendly explanations.", severity: "high", theme: "Raw system metadata" }],
  ["Assignment Action", { action: "rewrite", proposed: "Change", reason: "Use plainer language for demo users.", severity: "low", theme: "Operator-friendly as is" }],
  ["Batch Id", { action: "remove", proposed: "Remove from demo table", reason: "Internal batch identifiers are not operator copy.", severity: "high", theme: "Raw system metadata" }],
  ["Pressure Group Id", { action: "remove", proposed: "Remove from demo table", reason: "Internal optimization ids should not surface in the demo.", severity: "high", theme: "Raw system metadata" }],
  ["Batch Size", { action: "remove", proposed: "Remove from demo table", reason: "Optimization batch size is technical and not useful to the operator.", severity: "high", theme: "Technical versioning detail" }],
  ["Route Slot Ids", { action: "remove", proposed: "Remove from demo table", reason: "Lists of slot ids are raw system metadata.", severity: "high", theme: "Raw system metadata" }],
  ["Assigned Route Slot Ids", { action: "remove", proposed: "Remove from demo table", reason: "Lists of raw ids add noise and no operator value.", severity: "high", theme: "Raw system metadata" }],
  ["Uncovered Route Slot Ids", { action: "remove", proposed: "Remove from demo table", reason: "This is too technical for demo users.", severity: "high", theme: "Raw system metadata" }],
  ["Moved Route Slot Ids", { action: "remove", proposed: "Remove from demo table", reason: "Movement ids are internal mechanics, not operator-facing copy.", severity: "high", theme: "Raw system metadata" }],
  ["Accepted Move Reasons", { action: "rewrite", proposed: "Accepted move reasons", reason: "This may be useful, but it needs plainer supporting copy if shown.", severity: "medium", theme: "Boundary explanation is too technical" }],
  ["Candidate Evaluation Count", { action: "remove", proposed: "Remove from demo table", reason: "Evaluation counts are model-debug detail.", severity: "high", theme: "Technical versioning detail" }],
  ["Coverage After", { action: "rewrite", proposed: "Coverage after change", reason: "If retained, it should be phrased in plain English.", severity: "medium", theme: "Boundary explanation is too technical" }],
  ["Coverage Before", { action: "rewrite", proposed: "Coverage before change", reason: "If retained, it should be phrased in plain English.", severity: "medium", theme: "Boundary explanation is too technical" }],
  ["Covered Route Slot Count After Iteration", { action: "remove", proposed: "Remove from demo table", reason: "This is too detailed and technical for a demo surface.", severity: "high", theme: "Technical versioning detail" }],
  ["Preference Fit Delta", { action: "remove", proposed: "Remove from demo table", reason: "Delta language is model-oriented and not operator-friendly.", severity: "high", theme: "Technical versioning detail" }],
  ["Pressure Service Area", { action: "remove", proposed: "Remove from demo table", reason: "Pressure diagnostics are internal optimization detail.", severity: "high", theme: "Technical versioning detail" }],
  ["Pressure Service Date", { action: "remove", proposed: "Remove from demo table", reason: "Pressure diagnostics are internal optimization detail.", severity: "high", theme: "Technical versioning detail" }],
  ["Pressure Station Code", { action: "remove", proposed: "Remove from demo table", reason: "Station codes without plain-language context are raw metadata.", severity: "high", theme: "Raw system metadata" }],
  ["Rejected Move Reasons", { action: "rewrite", proposed: "Rejected move reasons", reason: "This needs plain-language explanation if it remains visible.", severity: "medium", theme: "Boundary explanation is too technical" }],
  ["Repair Move Count", { action: "remove", proposed: "Remove from demo table", reason: "Optimization counts are too technical for the demo.", severity: "high", theme: "Technical versioning detail" }],
  ["Soft Objective After", { action: "remove", proposed: "Remove from demo table", reason: "Optimization-objective language should not appear in the demo.", severity: "high", theme: "Technical versioning detail" }],
  ["Soft Objective Before", { action: "remove", proposed: "Remove from demo table", reason: "Optimization-objective language should not appear in the demo.", severity: "high", theme: "Technical versioning detail" }],
  ["Soft Objective Delta", { action: "remove", proposed: "Remove from demo table", reason: "Optimization-objective language should not appear in the demo.", severity: "high", theme: "Technical versioning detail" }],
  ["Stability Delta", { action: "remove", proposed: "Remove from demo table", reason: "Delta wording is too technical for a demo table.", severity: "high", theme: "Technical versioning detail" }],
  ["Target Shift Gap Delta", { action: "remove", proposed: "Remove from demo table", reason: "This sounds like optimizer output, not operator copy.", severity: "high", theme: "Technical versioning detail" }],
  ["Uncovered Route Slot Count After Iteration", { action: "remove", proposed: "Remove from demo table", reason: "The wording is too technical and detailed for the demo.", severity: "high", theme: "Technical versioning detail" }]
]);

const EXACT_COPY_OVERRIDES = new Map([
  ["Canonical workpage projection served from backend-owned workflow artifacts and runtime truth.", { action: "rewrite", proposed: "This page shows the current data for this run.", reason: "The sentence is accurate but packed with platform-specific terminology.", severity: "high", theme: "Internal platform jargon" }],
  ["Composite source bundle", { action: "remove", proposed: "Hide from default view", reason: "This is implementation vocabulary and not useful to an operator.", severity: "high", theme: "Raw system metadata" }],
  ["Source grounding", { action: "rewrite", proposed: "Data source", reason: "Plain language is clearer than internal provenance wording.", severity: "medium", theme: "Internal platform jargon" }],
  ["Dataset key", { action: "remove", proposed: "Hide from default view", reason: "Raw dataset keys are technical metadata.", severity: "high", theme: "Raw system metadata" }],
  ["Mode", { action: "remove", proposed: "Hide from default view", reason: "The generic label does not help a demo user without deeper product context.", severity: "medium", theme: "Raw system metadata" }],
  ["Source mode", { action: "remove", proposed: "Hide from default view", reason: "Operators do not need projection-mode vocabulary in the main UI.", severity: "high", theme: "Raw system metadata" }],
  ["Primary dataset", { action: "remove", proposed: "Hide from default view", reason: "This is technical metadata, not operator copy.", severity: "high", theme: "Raw system metadata" }],
  ["Source version", { action: "remove", proposed: "Hide from default view", reason: "Version metadata is useful for debugging, not for demo users.", severity: "high", theme: "Technical versioning detail" }],
  ["Artifact lineage", { action: "rewrite", proposed: "Version history", reason: "Version history is clearer than artifact-lineage language.", severity: "medium", theme: "Technical versioning detail" }],
  ["Current artifact", { action: "rewrite", proposed: "Current saved version", reason: "Use plain version language instead of artifact language.", severity: "medium", theme: "Technical versioning detail" }],
  ["Artifact kind", { action: "remove", proposed: "Hide from default view", reason: "Type metadata belongs in support/debug views, not the demo flow.", severity: "high", theme: "Raw system metadata" }],
  ["Latest in chain", { action: "rewrite", proposed: "Latest saved version", reason: "This is a version-history concept that needs simpler wording.", severity: "medium", theme: "Technical versioning detail" }],
  ["Supersedes", { action: "rewrite", proposed: "Replaces", reason: "Plain-English versioning language is easier to understand.", severity: "medium", theme: "Technical versioning detail" }],
  ["Superseded by", { action: "rewrite", proposed: "Replaced by", reason: "Plain-English versioning language is easier to understand.", severity: "medium", theme: "Technical versioning detail" }],
  ["Initial Stage04 draft", { action: "rewrite", proposed: "First planning draft", reason: "Avoid numbered stage vocabulary in operator-facing UI.", severity: "medium", theme: "Stage/workflow codes" }],
  ["Current latest", { action: "rewrite", proposed: "Latest version", reason: "Current latest is awkward and technical.", severity: "low", theme: "Technical versioning detail" }],
  ["Workflow", { action: "rewrite", proposed: "Process", reason: "Workflow is understandable, but process is plainer for demo users.", severity: "low", theme: "Internal platform jargon" }],
  ["Workflow run", { action: "rewrite", proposed: "Current run", reason: "Use run language instead of workflow-run terminology.", severity: "medium", theme: "Internal platform jargon" }],
  ["Version", { action: "remove", proposed: "Hide from default view", reason: "Version numbers do not help operators on the demo surface.", severity: "medium", theme: "Technical versioning detail" }],
  ["unknown", { action: "remove", proposed: "Hide when empty", reason: "Generic unknown labels make the demo feel unfinished and unhelpful.", severity: "medium", theme: "Operator-friendly as is" }],
  ["Open run detail (secondary)", { action: "rewrite", proposed: "Open run details", reason: "Secondary is UI-internal wording and not needed on a button label.", severity: "low", theme: "Operator-friendly as is" }],
  ["This demo shell now launches the canonical weekly schedule workpage for the selected run instead of editing drafts inline.", { action: "rewrite", proposed: "This page opens the weekly schedule for the selected run instead of editing it here.", reason: "Canonical and workpage are internal terms, and the sentence can be shorter.", severity: "high", theme: "Internal platform jargon" }],
  ["This demo shell now launches the canonical end-of-day workpage for the selected run instead of creating or submitting drafts inline.", { action: "rewrite", proposed: "This page opens the end-of-day report for the selected run instead of editing it here.", reason: "The current wording is accurate but too platform-specific.", severity: "high", theme: "Internal platform jargon" }],
  ["This family module stays workspace-first in the current slice. Use the canonical workspace and run detail for intake, review, and approval.", { action: "rewrite", proposed: "Use the workspace and run details for intake, review, and approval on this step.", reason: "Slice and canonical are internal product terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Workspace-first launcher", { action: "rewrite", proposed: "Open workspace", reason: "Launcher labels should describe the action directly.", severity: "medium", theme: "Operator-friendly as is" }],
  ["Canonical launcher", { action: "rewrite", proposed: "Main page", reason: "Canonical is a platform term that will not help a demo user.", severity: "medium", theme: "Internal platform jargon" }],
  ["Loading logistics demo story", { action: "rewrite", proposed: "Loading demo overview", reason: "Story payload is internal implementation language.", severity: "medium", theme: "Internal platform jargon" }],
  ["Fetching canonical three-workflow story payload.", { action: "rewrite", proposed: "Loading the linked schedule, live, and reporting overview.", reason: "Payload and canonical are implementation terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Logistics story failed to load", { action: "rewrite", proposed: "Demo overview failed to load", reason: "Story is an internal narrative term, not operator-facing copy.", severity: "medium", theme: "Internal platform jargon" }],
  ["No logistics story payload available", { action: "rewrite", proposed: "No demo overview is available", reason: "Payload is an implementation term.", severity: "medium", theme: "Internal platform jargon" }],
  ["Editorial Task Board", { action: "rewrite", proposed: "Task board", reason: "Editorial is vague and unnecessary on an operator surface.", severity: "medium", theme: "Operator-friendly as is" }],
  ["The compact task strip stays pinned in the shell. Expand this board when you need the full lane view.", { action: "rewrite", proposed: "The task strip stays visible. Open the full board when you need more detail.", reason: "Shell and lane view are UI-framework terms rather than operator language.", severity: "medium", theme: "Internal platform jargon" }],
  ["Family-node metadata, run drill-down, and artifact access for the selected logistics module.", { action: "rewrite", proposed: "Details, downloads, and linked runs for the selected logistics step.", reason: "Family-node, drill-down, artifact, and module are internal product words.", severity: "high", theme: "Internal platform jargon" }],
  ["Summary and technical node metadata for the current family module.", { action: "rewrite", proposed: "Summary and support details for this logistics step.", reason: "Node metadata and family module are internal concepts.", severity: "high", theme: "Raw system metadata" }],
  ["Family-level artifacts stay available here without occupying the launcher surface.", { action: "rewrite", proposed: "Downloads stay here so the main page stays focused on the workflow.", reason: "Artifact and launcher surface are internal phrases.", severity: "medium", theme: "Internal platform jargon" }],
  ["Workflow Run Drill-Down", { action: "rewrite", proposed: "Choose a linked run", reason: "Drill-down is an interface term, not operator copy.", severity: "medium", theme: "Internal platform jargon" }],
  ["Choose the linked workflow run that should drive the launcher surface and drill-down graph.", { action: "rewrite", proposed: "Choose which linked run should power the main page and workflow graph.", reason: "Launcher surface and drill-down graph are internal UI terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Choose a workflow run to open drill-down.", { action: "rewrite", proposed: "Choose a run to open details.", reason: "Drill-down is an interface term.", severity: "medium", theme: "Internal platform jargon" }],
  ["Pick a linked run in the summary above to load launcher links and drill-down here.", { action: "rewrite", proposed: "Pick a linked run above to load the main links and details here.", reason: "Launcher links and drill-down are internal UI terms.", severity: "medium", theme: "Internal platform jargon" }],
  ["Select a family node to inspect metadata.", { action: "rewrite", proposed: "Select a workflow step to see details.", reason: "Family node and metadata are internal concepts.", severity: "medium", theme: "Internal platform jargon" }],
  ["Workflow Run Graph Drill-Down", { action: "rewrite", proposed: "Workflow graph details", reason: "Drill-down is an interface term.", severity: "medium", theme: "Internal platform jargon" }],
  ["Fetching workflow-run workspace graph projection.", { action: "rewrite", proposed: "Loading the workflow graph for this run.", reason: "Workspace graph projection is system-language, not operator copy.", severity: "high", theme: "Internal platform jargon" }],
  ["Workflow drill-down failed to load", { action: "rewrite", proposed: "Workflow graph failed to load", reason: "Drill-down is internal UI language.", severity: "medium", theme: "Internal platform jargon" }],
  ["Official Outputs Summary", { action: "rewrite", proposed: "Approved outputs", reason: "Official outputs is understandable but a little stiff for demo copy.", severity: "low", theme: "Operator-friendly as is" }],
  ["Handoff Activity", { action: "rewrite", proposed: "Workflow handoffs", reason: "This is slightly clearer for demo users.", severity: "low", theme: "Operator-friendly as is" }],
  ["Inspect context and run authoritative task actions from the centered task modal without leaving the logistics shell.", { action: "rewrite", proposed: "Review task details and take actions here without leaving the demo.", reason: "Authoritative, modal, and shell are internal UI terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Approval context and response evidence remain in the shared detail drawer.", { action: "rewrite", proposed: "Approval details and supporting files stay in this side panel.", reason: "Response evidence and shared detail drawer are technical UI terms.", severity: "medium", theme: "Internal platform jargon" }],
  ["Exceptions stay in the contextual rail, but the full runtime context still opens in the shared drawer.", { action: "rewrite", proposed: "Exception details stay in this side panel so you can keep your place in the demo.", reason: "Contextual rail, runtime context, and shared drawer are internal terms.", severity: "medium", theme: "Internal platform jargon" }],
  ["Latest task:", { action: "rewrite", proposed: "Latest step:", reason: "Task kind language can stay, but step is broader and easier to scan.", severity: "low", theme: "Operator-friendly as is" }],
  ["No active claimant", { action: "rewrite", proposed: "Not assigned", reason: "Claimant is overly technical for a demo user.", severity: "medium", theme: "Internal platform jargon" }],
  ["Graph node status is projected by the server workspace endpoint.", { action: "rewrite", proposed: "This status comes from the current workflow data.", reason: "Projected, server, workspace endpoint are technical implementation words.", severity: "high", theme: "Internal platform jargon" }],
  ["Accepted history", { action: "rewrite", proposed: "Approved history", reason: "Approved is plainer than accepted in this context.", severity: "low", theme: "Operator-friendly as is" }],
  ["Accepted series", { action: "rewrite", proposed: "Approved versions", reason: "Series is abstract; versions is clearer.", severity: "medium", theme: "Technical versioning detail" }],
  ["Accepted navigation stays on accepted weekly history only and never traverses draft lineage.", { action: "rewrite", proposed: "This history stays on approved weekly versions only and does not mix in drafts.", reason: "Navigation, accepted, and draft lineage are too technical together.", severity: "high", theme: "Technical versioning detail" }],
  ["No accepted schedule history is available for this surface yet.", { action: "rewrite", proposed: "No approved schedule history is available yet.", reason: "Surface is UI jargon and accepted is less clear than approved.", severity: "medium", theme: "Technical versioning detail" }],
  ["Draft lineage", { action: "rewrite", proposed: "Draft history", reason: "History is plainer than lineage.", severity: "low", theme: "Technical versioning detail" }],
  ["Draft rail", { action: "rewrite", proposed: "Draft history", reason: "Rail is a layout term, not operator wording.", severity: "medium", theme: "Internal platform jargon" }],
  ["Draft navigation stays within backend-authored draft lineage for this immutable schedule surface.", { action: "rewrite", proposed: "This history stays within saved schedule drafts for this run.", reason: "Backend-authored, lineage, immutable, and surface are all internal words.", severity: "high", theme: "Internal platform jargon" }],
  ["No draft lineage is available on this surface yet.", { action: "rewrite", proposed: "No draft history is available yet.", reason: "Surface and lineage are unnecessary technical terms.", severity: "medium", theme: "Internal platform jargon" }],
  ["Server-authoritative schedule heatmap. Edit controls stay on draft artifact pages.", { action: "rewrite", proposed: "This schedule grid is read-only here. Edit controls are available on the draft page.", reason: "Server-authoritative and artifact are technical platform terms.", severity: "high", theme: "Internal platform jargon" }],
  ["driver only present in the current draft rows", { action: "rewrite", proposed: "Only shown in the current draft", reason: "Row-level draft language is too technical for users.", severity: "low", theme: "Operator-friendly as is" }],
  ["Workflow-run-backed schedule projection served from canonical weekly Stage04 source artifacts.", { action: "rewrite", proposed: "This page shows the current weekly planning view for this run.", reason: "The whole sentence is built from internal platform terms.", severity: "high", theme: "Internal platform jargon" }],
  ["This landing page stays read-only. Open the backend-selected latest draft when you need live preview and save controls.", { action: "rewrite", proposed: "This page is read-only. Open the latest draft to preview changes and save updates.", reason: "Backend-selected and controls are UI/implementation wording.", severity: "high", theme: "Internal platform jargon" }],
  ["This landing page stays read-only. The Stage04 draft weekly schedule artifact is not available for this run yet.", { action: "rewrite", proposed: "This page is read-only. An editable weekly schedule draft is not available for this run yet.", reason: "Stage04 and artifact are internal workflow terms.", severity: "high", theme: "Stage/workflow codes" }],
  ["A workflow-backed weekly planning review for bounded draft navigation, live schedule context, and backend-authored metrics.", { action: "rewrite", proposed: "Review the weekly schedule, current coverage, and saved draft history for this run.", reason: "Workflow-backed, bounded, and backend-authored are internal terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Open schedule drafts from a canonical workflow-run route.", { action: "rewrite", proposed: "Open schedule drafts from a schedule run page.", reason: "Canonical workflow-run route is technical routing language.", severity: "medium", theme: "Internal platform jargon" }],
  ["An artifact version id is required for schedule draft workpages.", { action: "rewrite", proposed: "A draft version is required to open this page.", reason: "Artifact version id and workpages are internal terms.", severity: "high", theme: "Raw system metadata" }],
  ["Open schedule workpages from a canonical workflow-run route.", { action: "rewrite", proposed: "Open schedule pages from a schedule run page.", reason: "Canonical workflow-run route is technical routing language.", severity: "medium", theme: "Internal platform jargon" }],
  ["Fetching the workflow-run-backed schedule workpage.", { action: "rewrite", proposed: "Loading the schedule page for this run.", reason: "Workflow-run-backed and workpage are internal terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Weekly Schedule Draft Artifact", { action: "rewrite", proposed: "Weekly schedule draft", reason: "Artifact is technical and unnecessary in the title.", severity: "medium", theme: "Technical versioning detail" }],
  ["A bounded Stage04 draft workbook edit lane with live backend preview and explicit save into a new immutable draft version.", { action: "rewrite", proposed: "Edit the weekly schedule draft, preview changes, and save a new version.", reason: "Stage04, edit lane, backend preview, and immutable are internal terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Artifact-backed projection of an immutable Stage04 draft weekly schedule workbook. Save creates a new superseding draft artifact version without publishing.", { action: "rewrite", proposed: "This page shows a saved weekly schedule draft. Saving creates a new draft version without publishing it.", reason: "Artifact-backed, projection, immutable, Stage04, and superseding are too technical.", severity: "high", theme: "Technical versioning detail" }],
  ["Live preview recalculates in place. Save creates the next immutable draft in this weekly lineage.", { action: "rewrite", proposed: "Preview updates here right away. Saving creates the next draft version.", reason: "Immutable and lineage are technical versioning terms.", severity: "medium", theme: "Technical versioning detail" }],
  ["Latest draft already exists", { action: "rewrite", proposed: "A newer draft is already available", reason: "The title should explain the situation more clearly.", severity: "low", theme: "Technical versioning detail" }],
  ["This base schedule artifact has already been superseded. Keep your local edits for now, then reopen the latest draft artifact before saving again.", { action: "rewrite", proposed: "This draft is no longer current. Keep your edits for now, then reopen the latest draft before saving again.", reason: "Artifact and superseded are versioning jargon.", severity: "high", theme: "Technical versioning detail" }],
  ["This artifact version is no longer the latest draft in the chain. Reopen the latest version before saving more changes.", { action: "rewrite", proposed: "This draft is no longer the latest version. Reopen the newest draft before saving more changes.", reason: "Artifact version and chain are technical versioning terms.", severity: "high", theme: "Technical versioning detail" }],
  ["Draft JSON download failed", { action: "rewrite", proposed: "Draft download failed", reason: "JSON is an implementation detail that should not be in the user-facing error title.", severity: "medium", theme: "Raw system metadata" }],
  ["Mark Sick / No Show", { action: "rewrite", proposed: "Mark driver unavailable", reason: "The operator outcome is clearer than the specific internal state wording.", severity: "medium", theme: "Operator-friendly as is" }],
  ["Add context for the operations log.", { action: "rewrite", proposed: "Add a note", reason: "The note field does not need internal logging language.", severity: "low", theme: "Operator-friendly as is" }],
  ["Open route demand", { action: "rewrite", proposed: "Open route plan", reason: "Route plan is slightly plainer than route demand for general demo users.", severity: "low", theme: "Acronym or shorthand needs explanation" }],
  ["Create preferences snapshot", { action: "rewrite", proposed: "Save weekly preferences", reason: "Snapshot is technical save-state language.", severity: "medium", theme: "Technical versioning detail" }],
  ["Weekly route demand review", { action: "rewrite", proposed: "Weekly route plan", reason: "Route plan is plainer than route demand for a demo audience.", severity: "low", theme: "Acronym or shorthand needs explanation" }],
  ["This workflow-run-backed route demand page is built from the latest canonical Stage04 route-demand artifact for the selected run.", { action: "rewrite", proposed: "This page shows the latest planned route counts for the selected run.", reason: "The sentence is full of platform and stage terminology.", severity: "high", theme: "Internal platform jargon" }],
  ["Route-demand edits stay on a separate truth surface from schedule reassignment and recalculation.", { action: "rewrite", proposed: "Changes here only affect route counts. They do not reassign drivers or update the schedule.", reason: "Truth surface is internal platform language.", severity: "high", theme: "Internal platform jargon" }],
  ["This page edits route-demand truth only. Schedule reassignment, preview, and save stay on schedule-v0, and route-demand saves never auto-refresh schedule artifacts.", { action: "rewrite", proposed: "This page only changes route counts. Schedule edits and previews happen on the schedule page, and saving here does not update the schedule automatically.", reason: "Truth, schedule-v0, and artifacts are internal wording.", severity: "high", theme: "Internal platform jargon" }],
  ["This artifact-backed route demand page edits daily route-demand truth only. It does not mutate schedule assignments or auto-refresh schedule drafts.", { action: "rewrite", proposed: "This page only changes daily route counts. It does not change driver assignments or update schedule drafts automatically.", reason: "Artifact-backed, truth, and mutate are technical terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Route Demand Landing", { action: "rewrite", proposed: "Route plan", reason: "Landing is a navigation term and route plan is plainer.", severity: "medium", theme: "Operator-friendly as is" }],
  ["A read-only weekly landing page for backend-owned route-demand truth. Open the latest immutable artifact when you need to edit final daily counts.", { action: "rewrite", proposed: "This read-only page shows weekly route counts. Open the latest saved version when you need to edit final daily counts.", reason: "Backend-owned, truth, immutable, and artifact are internal terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Workflow-run-backed route-demand projection served from the latest canonical Stage04 route-demand artifact for this weekly run.", { action: "rewrite", proposed: "This page shows the latest route-count view for this weekly run.", reason: "Projection, canonical, Stage04, and artifact are too technical.", severity: "high", theme: "Internal platform jargon" }],
  ["This landing page stays read-only. Open the latest immutable route-demand artifact to adjust final daily counts and create a new successor version.", { action: "rewrite", proposed: "This page is read-only. Open the latest saved route-count version to adjust daily totals and save a new version.", reason: "Immutable, artifact, and successor version are technical versioning terms.", severity: "high", theme: "Technical versioning detail" }],
  ["A bounded route-demand editor over immutable weekly route-demand workbooks. Saving creates the next immutable route-demand version and never mutates schedule artifacts.", { action: "rewrite", proposed: "Edit weekly route counts here. Saving creates a new route-count version and does not change the schedule.", reason: "Immutable, mutates, and artifacts are platform terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Artifact-backed route-demand projection served from an immutable Stage04 route-demand workbook version.", { action: "rewrite", proposed: "This page shows a saved route-count version from planning.", reason: "Artifact-backed, projection, immutable, and Stage04 are too technical.", severity: "high", theme: "Internal platform jargon" }],
  ["Plus/minus controls adjust backend-owned daily route counts. Save creates a new route-demand artifact version and leaves schedule artifacts untouched.", { action: "rewrite", proposed: "Use plus and minus to change daily route counts. Saving creates a new version and does not change the schedule.", reason: "Backend-owned and artifact wording are technical.", severity: "medium", theme: "Internal platform jargon" }],
  ["Next addable week", { action: "rewrite", proposed: "Next available week", reason: "Addable is awkward product language.", severity: "low", theme: "Operator-friendly as is" }],
  ["This route-demand version is historical. Open the latest version in the chain before saving additional changes.", { action: "rewrite", proposed: "This route-count version is older. Open the latest version before saving more changes.", reason: "Historical and chain are stiff/technical in this context.", severity: "medium", theme: "Technical versioning detail" }],
  ["This future week already has weekly schedule draft truth. Continue from the schedule workpage instead of editing route demand here.", { action: "rewrite", proposed: "This future week already has a schedule draft. Continue from the schedule page instead of editing route counts here.", reason: "Truth and workpage are internal terms.", severity: "high", theme: "Internal platform jargon" }],
  ["This route-demand version is historical and can no longer be edited.", { action: "rewrite", proposed: "This route-count version is older and can no longer be edited.", reason: "Historical sounds archival rather than actionable.", severity: "medium", theme: "Technical versioning detail" }],
  ["Latest schedule draft is stale", { action: "rewrite", proposed: "Latest schedule draft is out of date", reason: "Out of date is plainer than stale.", severity: "low", theme: "Operator-friendly as is" }],
  ["Refresh follow-up is open", { action: "rewrite", proposed: "Schedule refresh is already in progress", reason: "Follow-up is vague; the user needs the actual status.", severity: "medium", theme: "Boundary explanation is too technical" }],
  ["A Stage04 refresh work item is already open for the stale schedule draft. Route-demand save did not mutate any schedule artifact.", { action: "rewrite", proposed: "A schedule refresh is already open for the out-of-date draft. Saving route counts did not update the schedule.", reason: "Stage04, work item, mutate, and artifact are technical terms.", severity: "high", theme: "Stage/workflow codes" }],
  ["The backend reported the latest schedule draft posture for this route-demand surface.", { action: "rewrite", proposed: "This reflects the latest schedule-draft status for this route-count page.", reason: "Backend, posture, and surface are implementation language.", severity: "medium", theme: "Internal platform jargon" }],
  ["The history rail stays within backend-authored immutable route-demand workbook lineage for this weekly run.", { action: "rewrite", proposed: "This history stays within saved route-count versions for this weekly run.", reason: "History rail, backend-authored, immutable, and lineage are technical.", severity: "high", theme: "Internal platform jargon" }],
  ["Route-demand version", { action: "rewrite", proposed: "Route-count version", reason: "Route-count is slightly plainer in version history.", severity: "low", theme: "Acronym or shorthand needs explanation" }],
  ["This workflow-run-backed driver preferences page uses the latest immutable weekly snapshot when one exists.", { action: "rewrite", proposed: "This page uses the latest saved weekly preferences when one exists.", reason: "Workflow-run-backed, immutable, and snapshot are technical terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Preference snapshots stay advisory only and do not become hard schedule truth or refresh tasks.", { action: "rewrite", proposed: "Saved preferences are for guidance only and do not block schedule work or trigger updates.", reason: "Advisory, hard truth, and refresh tasks are internal phrasing.", severity: "high", theme: "Internal platform jargon" }],
  ["This page stores a weekly Sunday-Saturday advisory snapshot only. It informs schedule highlighting and soft drift cues without becoming hard scheduling truth.", { action: "rewrite", proposed: "This page saves a weekly preference view from Sunday through Saturday. It helps highlight the schedule, but it does not control the schedule.", reason: "Advisory snapshot, soft drift cues, and hard truth are technical terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Weekly driver preferences", { action: "rewrite", proposed: "Weekly driver preferences", reason: "Keep as is. The term is understandable and consistent.", severity: "low", theme: "Operator-friendly as is" }],
  ["Create preferences snapshot", { action: "rewrite", proposed: "Save weekly preferences", reason: "Snapshot is technical save-state language.", severity: "medium", theme: "Technical versioning detail" }],
  ["A weekly Sunday-Saturday advisory snapshot surface for soft schedule cues and history.", { action: "rewrite", proposed: "Review weekly driver preferences and preference history.", reason: "Advisory snapshot surface and soft cues are internal phrasing.", severity: "high", theme: "Internal platform jargon" }],
  ["Workflow-run-backed landing surface over the latest immutable preferences snapshot when one exists.", { action: "rewrite", proposed: "This page shows the latest saved preferences for this run when they exist.", reason: "Workflow-run-backed, landing surface, immutable, and snapshot are technical.", severity: "high", theme: "Internal platform jargon" }],
  ["Preference snapshots stay advisory only and never create refresh tasks.", { action: "rewrite", proposed: "Saved preferences are for guidance only and do not trigger schedule updates.", reason: "Advisory and refresh tasks are internal terms.", severity: "medium", theme: "Internal platform jargon" }],
  ["The first snapshot is created explicitly on demand. Seeded cells start with deterministic advisory posture and remain soft guidance only.", { action: "rewrite", proposed: "Create the first saved preferences view when you need it. Starting values are suggestions only.", reason: "Snapshot, seeded cells, deterministic, and soft guidance are technical.", severity: "high", theme: "Internal platform jargon" }],
  ["Approved future exceptions are kept separate from the weekly preference grid.", { action: "rewrite", proposed: "Approved future exceptions are tracked separately from weekly preferences.", reason: "Grid is a layout term; preferences is enough.", severity: "low", theme: "Operator-friendly as is" }],
  ["Unsaved grid edits remain local.", { action: "rewrite", proposed: "Unsaved changes are only on this page for now.", reason: "Grid and local are a little too implementation-oriented.", severity: "low", theme: "Internal platform jargon" }],
  ["Edit the current weekly driver-preferences snapshot without leaving this page.", { action: "rewrite", proposed: "Edit the current weekly driver preferences without leaving this page.", reason: "Snapshot is technical save-state language.", severity: "low", theme: "Technical versioning detail" }],
  ["Resolving the latest driver-preferences snapshot for this weekly run.", { action: "rewrite", proposed: "Loading the latest saved driver preferences for this run.", reason: "Snapshot and weekly run language can be simpler.", severity: "medium", theme: "Technical versioning detail" }],
  ["Create the first preferences snapshot", { action: "rewrite", proposed: "Create the first saved preferences view", reason: "Snapshot is technical save-state language.", severity: "medium", theme: "Technical versioning detail" }],
  ["Driver editing starts by creating the immutable weekly preferences snapshot for this run. Add-driver support is intentionally deferred to the next driver task.", { action: "rewrite", proposed: "Start by creating the saved weekly preferences view for this run. Adding new drivers will come later.", reason: "Immutable and deferred are internal planning terms.", severity: "high", theme: "Technical versioning detail" }],
  ["No editable driver-preferences snapshot is available for this weekly run yet.", { action: "rewrite", proposed: "No editable weekly preferences are available for this run yet.", reason: "Snapshot is technical save-state language.", severity: "medium", theme: "Technical versioning detail" }],
  ["An artifact-backed weekly advisory snapshot lane with immutable history and explicit save into a new snapshot version.", { action: "rewrite", proposed: "Edit weekly preferences here and save a new version when needed.", reason: "Artifact-backed, advisory snapshot lane, immutable, and explicit save are all technical.", severity: "high", theme: "Internal platform jargon" }],
  ["Artifact-backed projection of an immutable weekly advisory preferences snapshot.", { action: "rewrite", proposed: "This page shows a saved weekly preferences version.", reason: "Artifact-backed, projection, immutable, and advisory snapshot are technical.", severity: "high", theme: "Internal platform jargon" }],
  ["Saving creates the next immutable driver-preferences snapshot and leaves schedule truth untouched.", { action: "rewrite", proposed: "Saving creates the next preferences version and does not change the schedule.", reason: "Immutable snapshot and schedule truth are internal phrases.", severity: "medium", theme: "Internal platform jargon" }],
  ["This base preferences snapshot has already been superseded. Keep your local edits for now, then reopen the latest snapshot before saving again.", { action: "rewrite", proposed: "This saved preferences version is no longer current. Keep your edits for now, then reopen the latest version before saving again.", reason: "Superseded and snapshot are versioning jargon.", severity: "high", theme: "Technical versioning detail" }],
  ["This snapshot version is no longer the latest in the chain. Reopen the latest version before saving more changes.", { action: "rewrite", proposed: "This saved preferences version is older. Reopen the latest version before saving more changes.", reason: "Snapshot and chain are technical versioning language.", severity: "medium", theme: "Technical versioning detail" }],
  ["This run-backed EOD landing is generated from canonical dispatch-reporting artifacts.", { action: "rewrite", proposed: "This page uses the latest dispatch reporting data for this run.", reason: "Run-backed, canonical, and artifacts are internal platform terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Submit creates a new immutable superseding reporting workbook artifact version.", { action: "rewrite", proposed: "Submitting saves a new reporting workbook version.", reason: "Immutable, superseding, and artifact version are technical versioning terms.", severity: "high", theme: "Technical versioning detail" }],
  ["This run-backed EOD landing is generated from canonical dispatch-reporting artifacts. Route actuals, closeout details, and UPD review stay grounded in the latest immutable draft.", { action: "rewrite", proposed: "This page uses the latest dispatch reporting draft for this run. Route actuals, closeout details, and UPD review stay tied to the latest draft.", reason: "Run-backed, canonical, grounded, and immutable are technical terms.", severity: "high", theme: "Internal platform jargon" }],
  ["This workpage is derived from an immutable reporting workbook artifact; the workbook remains authoritative truth.", { action: "rewrite", proposed: "This page is based on a saved reporting workbook, and the workbook remains the source record.", reason: "Workpage, immutable, artifact, and authoritative truth are technical terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Submit creates a new superseding workbook artifact version; no in-place workbook mutation occurs.", { action: "rewrite", proposed: "Submitting creates a new workbook version; it does not overwrite the current one.", reason: "Superseding, artifact version, and mutation are technical terms.", severity: "high", theme: "Technical versioning detail" }],
  ["This page is projected from an immutable Stage03 reporting workbook artifact. Quality warnings are surfaced from the workbook when present, and formulas are not recomputed.", { action: "rewrite", proposed: "This page is based on a saved reporting workbook draft. It shows any workbook warnings, and formulas are not recalculated here.", reason: "Projected, immutable, Stage03, and artifact are technical terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Total routes actual", { action: "rewrite", proposed: "Routes completed", reason: "The current label is awkward and not plain English.", severity: "medium", theme: "Operator-friendly as is" }],
  ["UPD?", { action: "rewrite", proposed: "UPD / over-600", reason: "The acronym needs a little context for demo users.", severity: "medium", theme: "Acronym or shorthand needs explanation" }],
  ["Not available", { action: "rewrite", proposed: "Drivers not available", reason: "The field label is too vague on its own.", severity: "low", theme: "Operator-friendly as is" }],
  ["Working devices / rabbits", { action: "rewrite", proposed: "Working devices / scanners", reason: "Rabbit is company-specific jargon that may confuse demo viewers.", severity: "medium", theme: "Acronym or shorthand needs explanation" }],
  ["Dispatch Reporting Draft", { action: "rewrite", proposed: "End-of-day draft", reason: "Shorter and plainer for demo users.", severity: "low", theme: "Operator-friendly as is" }],
  ["A bounded EOD workpage for route actual review, closeout capture, and UPD draft posture.", { action: "rewrite", proposed: "Review route actuals, capture closeout details, and work through the end-of-day draft.", reason: "Bounded workpage and posture are internal phrasing.", severity: "high", theme: "Internal platform jargon" }],
  ["Artifact-backed projection of an immutable Stage03 reporting workbook draft. Submit creates a new superseding workbook artifact version.", { action: "rewrite", proposed: "This page shows a saved reporting workbook draft. Submitting creates a new workbook version.", reason: "Artifact-backed, projection, immutable, Stage03, and superseding are technical.", severity: "high", theme: "Technical versioning detail" }],
  ["Submit creates a new immutable workbook artifact version. The current draft remains authoritative until you explicitly submit.", { action: "rewrite", proposed: "Submitting creates a new workbook version. The current draft stays in place until you submit.", reason: "Immutable artifact version and authoritative are technical terms.", severity: "high", theme: "Technical versioning detail" }],
  ["Backend-authored immutable `reporting.upd_draft.workbook` lineage for this reporting run. Use these links to reopen adjacent draft states without leaving the canonical EOD workpage surface.", { action: "rewrite", proposed: "This history shows saved reporting drafts for this run. Use these links to reopen nearby draft versions without leaving the end-of-day page.", reason: "Backend-authored, immutable, lineage, canonical, and workpage surface are technical.", severity: "high", theme: "Internal platform jargon" }],
  ["This base artifact has already been superseded. Keep your local edits for now, then reopen the latest artifact-backed draft before submitting again.", { action: "rewrite", proposed: "This saved draft is no longer current. Keep your edits for now, then reopen the latest draft before submitting again.", reason: "Artifact and superseded are versioning jargon.", severity: "high", theme: "Technical versioning detail" }],
  ["This artifact version is no longer the latest draft in the chain. Reopen the latest version before submitting more changes.", { action: "rewrite", proposed: "This draft is no longer the latest version. Reopen the newest draft before submitting more changes.", reason: "Artifact version and chain are technical versioning terms.", severity: "high", theme: "Technical versioning detail" }],
  ["Open dispatch-reporting workpages from a canonical workflow-run route.", { action: "rewrite", proposed: "Open reporting pages from a reporting run page.", reason: "Canonical workflow-run route is technical routing language.", severity: "medium", theme: "Internal platform jargon" }],
  ["Workflow-run-backed dispatch-reporting landing with latest-draft resolution over a canonical reporting run.", { action: "rewrite", proposed: "This page shows the latest end-of-day draft for this reporting run.", reason: "Workflow-run-backed, latest-draft resolution, and canonical are internal terms.", severity: "high", theme: "Internal platform jargon" }],
  ["This landing page already resolved the newest editable workbook-backed draft for this reporting run. Reopen that draft before making closeout or UPD review edits.", { action: "rewrite", proposed: "This page already found the newest editable draft for this reporting run. Reopen that draft before making closeout or UPD review changes.", reason: "Resolved and workbook-backed are implementation terms.", severity: "medium", theme: "Internal platform jargon" }],
  ["This landing page is a read-only preview. Create an immutable workbook-backed draft before making closeout or UPD review edits.", { action: "rewrite", proposed: "This page is read-only. Create a saved draft before making closeout or UPD review changes.", reason: "Immutable workbook-backed draft is technical versioning language.", severity: "high", theme: "Technical versioning detail" }],
  ["Import the daily workbook, review the generated EOD draft, attach manager evidence, and complete the canonical approval loop without leaving the workpage.", { action: "rewrite", proposed: "Import the daily workbook, review the end-of-day draft, attach the manager review, and finish approval without leaving this page.", reason: "Canonical approval loop and workpage are internal terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Upload the raw EOS workbook to the Stage01 intake task. Completing intake seeds the latest immutable EOD draft for review.", { action: "rewrite", proposed: "Upload the raw EOS workbook. Completing intake creates the latest end-of-day draft for review.", reason: "Stage01, intake task, seeds, and immutable are technical workflow terms.", severity: "high", theme: "Stage/workflow codes" }],
  ["No imported EOD draft is available for this run yet.", { action: "rewrite", proposed: "No end-of-day draft is available for this run yet.", reason: "Simplify the phrasing and remove extra detail.", severity: "low", theme: "Operator-friendly as is" }],
  ["Work directly in the artifact-backed EOD editor. Each submit creates a new immutable draft version and keeps the closeout flow pinned to the newest artifact.", { action: "rewrite", proposed: "Work directly in the end-of-day editor. Each submit creates a new draft version and keeps closeout on the newest draft.", reason: "Artifact-backed, immutable, and pinned are technical terms.", severity: "high", theme: "Technical versioning detail" }],
  ["Import the workbook first, or wait for the latest EOD draft to resolve.", { action: "rewrite", proposed: "Import the workbook first, or wait for the latest end-of-day draft to finish loading.", reason: "Resolve is implementation language.", severity: "low", theme: "Operator-friendly as is" }],
  ["Attach the manager review packet, confirm the latest draft review, and then complete the Stage04 review task to request manager approval.", { action: "rewrite", proposed: "Attach the manager review, confirm the latest draft review, and complete the review step to request manager approval.", reason: "Packet and Stage04 review task are more technical than necessary.", severity: "medium", theme: "Stage/workflow codes" }],
  ["The review task will appear here after Stage01 intake completes.", { action: "rewrite", proposed: "The review step will appear here after intake finishes.", reason: "Stage01 intake is an internal stage reference.", severity: "medium", theme: "Stage/workflow codes" }],
  ["Approval stays canonical. Approving here finalizes the reporting packet and triggers the weekly-planning actual-hours handoff.", { action: "rewrite", proposed: "Approving here finalizes the reporting packet and starts the weekly actual-hours handoff.", reason: "Canonical is an internal authority-model term.", severity: "high", theme: "Internal platform jargon" }],
  ["The current viewer session cannot respond to this approval. Switch to an actor with the required manager role to finish closeout in this popup.", { action: "rewrite", proposed: "Your current role cannot respond to this approval. Switch to a manager role to finish closeout in this pop-up.", reason: "Viewer session and actor are internal product terms.", severity: "medium", theme: "Internal platform jargon" }],
  ["Waiting for the pending approval to refresh.", { action: "rewrite", proposed: "Waiting for the approval status to update.", reason: "Refresh is UI-system language, not operator language.", severity: "low", theme: "Operator-friendly as is" }],
  ["Complete the review task to request manager approval.", { action: "rewrite", proposed: "Complete the review step to request manager approval.", reason: "Step is slightly plainer than task here.", severity: "low", theme: "Operator-friendly as is" }],
  ["Loading viewer session", { action: "rewrite", proposed: "Loading access details", reason: "Viewer session is internal session terminology.", severity: "medium", theme: "Internal platform jargon" }],
  ["Resolving server-derived viewer/bootstrap context.", { action: "rewrite", proposed: "Loading your access and page setup.", reason: "Server-derived, viewer, and bootstrap are implementation terms.", severity: "high", theme: "Internal platform jargon" }],
  ["Viewer session failed to load", { action: "rewrite", proposed: "Access details failed to load", reason: "Viewer session is internal session terminology.", severity: "medium", theme: "Internal platform jargon" }],
  ["Viewer session missing", { action: "rewrite", proposed: "Access details are missing", reason: "Viewer session is internal session terminology.", severity: "medium", theme: "Internal platform jargon" }],
  ["Viewer/bootstrap session did not resolve.", { action: "rewrite", proposed: "Access details did not load.", reason: "Viewer/bootstrap is implementation language.", severity: "high", theme: "Internal platform jargon" }],
  ["Waiting for first API payload", { action: "rewrite", proposed: "Waiting for the first update", reason: "API payload is technical system language.", severity: "medium", theme: "Internal platform jargon" }],
  ["Polling every {n}s", { action: "rewrite", proposed: "Auto-refresh every {n}s", reason: "Auto-refresh is more familiar than polling.", severity: "low", theme: "Operator-friendly as is" }],
  ["Official Outputs", { action: "rewrite", proposed: "Approved outputs", reason: "Approved is plainer than official here.", severity: "low", theme: "Operator-friendly as is" }],
  ["Run Details", { action: "rewrite", proposed: "Run details", reason: "Sentence case scans better alongside other menu items.", severity: "low", theme: "Operator-friendly as is" }],
  ["Open secondary logistics detail destinations without taking extra header space.", { action: "rewrite", proposed: "Open extra detail pages from here.", reason: "Destinations and extra header space are UI-framework language.", severity: "medium", theme: "Internal platform jargon" }],
  ["Logistics family nav unavailable.", { action: "rewrite", proposed: "Workflow navigation is unavailable.", reason: "Family nav is internal naming.", severity: "medium", theme: "Internal platform jargon" }],
  ["Loading logistics family nav...", { action: "rewrite", proposed: "Loading workflow navigation...", reason: "Family nav is internal naming.", severity: "medium", theme: "Internal platform jargon" }],
  ["Route-activity workbook", { action: "rewrite", proposed: "Route activity workbook", reason: "The hyphenated form is awkward in a form label.", severity: "low", theme: "Operator-friendly as is" }]
]);

function readJson(relativePath) {
  return fs.readFile(path.join(ROOT, relativePath), "utf8").then((content) => JSON.parse(content));
}

function snapshotRowsFromConfig(config, workpageState) {
  const rows = [];
  const workpage = workpageState.workpage ?? {};
  const actions = workpageState.actions ?? [];
  const sections = workpage.sections ?? [];
  const warnings = workpage.validation?.warnings ?? [];

  if (workpage.title) {
    rows.push(
      row(
        config.routeGroup,
        config.pageVariant,
        "title",
        config.component,
        `${config.file}#workpage.title`,
        config.stateVariant,
        "page_title",
        workpage.title
      )
    );
  }

  warnings.forEach((warning, index) => {
    rows.push(
      row(
        config.routeGroup,
        config.pageVariant,
        "warning_list",
        config.component,
        `${config.file}#workpage.validation.warnings[${index}]`,
        config.stateVariant,
        "warning_text",
        warning
      )
    );
  });

  actions.forEach((action, index) => {
    if (!action.label) {
      return;
    }
    rows.push(
      row(
        config.routeGroup,
        config.pageVariant,
        "action_cluster",
        config.component,
        `${config.file}#workpage_state.actions[${index}].label`,
        config.stateVariant,
        "button_text",
        action.label
      )
    );
    if (action.disabled_reason) {
      rows.push(
        row(
          config.routeGroup,
          config.pageVariant,
          "action_cluster",
          config.component,
          `${config.file}#workpage_state.actions[${index}].disabled_reason`,
          "blocked",
          "helper_text",
          action.disabled_reason
        )
      );
    }
  });

  sections.forEach((section, sectionIndex) => {
    if (section.title) {
      rows.push(
        row(
          config.routeGroup,
          config.pageVariant,
          `${section.kind}_section`,
          config.component,
          `${config.file}#workpage.sections[${sectionIndex}].title`,
          config.stateVariant,
          "section_title",
          section.title
        )
      );
    }
    if (section.body) {
      rows.push(
        row(
          config.routeGroup,
          config.pageVariant,
          `${section.kind}_section`,
          config.component,
          `${config.file}#workpage.sections[${sectionIndex}].body`,
          config.stateVariant,
          "body_text",
          section.body
        )
      );
    }
    (section.cards ?? []).forEach((card, cardIndex) => {
      rows.push(
        row(
          config.routeGroup,
          config.pageVariant,
          "summary_cards",
          config.component,
          `${config.file}#workpage.sections[${sectionIndex}].cards[${cardIndex}].label`,
          config.stateVariant,
          "summary_card_label",
          card.label
        )
      );
    });
    (section.columns ?? []).forEach((column, columnIndex) => {
      rows.push(
        row(
          config.routeGroup,
          config.pageVariant,
          "table",
          config.component,
          `${config.file}#workpage.sections[${sectionIndex}].columns[${columnIndex}].label`,
          config.stateVariant,
          "table_header",
          column.label
        )
      );
    });
    (section.fields ?? []).forEach((field, fieldIndex) => {
      rows.push(
        row(
          config.routeGroup,
          config.pageVariant,
          "form",
          config.component,
          `${config.file}#workpage.sections[${sectionIndex}].fields[${fieldIndex}].label`,
          config.stateVariant,
          "field_label",
          field.label
        )
      );
    });
    (section.items ?? []).forEach((item, itemIndex) => {
      rows.push(
        row(
          config.routeGroup,
          config.pageVariant,
          "checklist",
          config.component,
          `${config.file}#workpage.sections[${sectionIndex}].items[${itemIndex}].title`,
          config.stateVariant,
          "item_title",
          item.title
        )
      );
      if (item.detail) {
        rows.push(
          row(
            config.routeGroup,
            config.pageVariant,
            "checklist",
            config.component,
            `${config.file}#workpage.sections[${sectionIndex}].items[${itemIndex}].detail`,
            config.stateVariant,
            "body_text",
            item.detail
          )
        );
      }
    });
    if (section.empty_message) {
      rows.push(
        row(
          config.routeGroup,
          config.pageVariant,
          `${section.kind}_section`,
          config.component,
          `${config.file}#workpage.sections[${sectionIndex}].empty_message`,
          "empty",
          "empty_state",
          section.empty_message
        )
      );
    }
  });

  return rows;
}

function replacementNotes(routeGroup) {
  if (routeGroup.startsWith("Schedule")) {
    return "Keep the weekly-planning boundary clear; do not imply day-of dispatch control.";
  }
  if (routeGroup.startsWith("Route Demand")) {
    return "Keep route-count editing separate from schedule editing and auto-refresh behavior.";
  }
  if (routeGroup.startsWith("Driver Preferences")) {
    return "Keep preferences advisory and non-blocking.";
  }
  if (routeGroup.startsWith("EOD") || routeGroup === "Dispatch Closeout Modal") {
    return "Keep the reporting draft/review boundary clear; do not imply final-output ownership too early.";
  }
  return "";
}

function operatorFriendlyLabel(text) {
  return text
    .replace(/\bworkflow-run-backed\b/gi, "current-run")
    .replace(/\brun-backed\b/gi, "current-run")
    .replace(/\bworkpage\b/gi, "page")
    .replace(/\bartifact-backed\b/gi, "saved")
    .replace(/\bartifact\b/gi, "saved version")
    .replace(/\bimmutable\b/gi, "saved")
    .replace(/\bcanonical\b/gi, "main")
    .replace(/\bprojection\b/gi, "view")
    .replace(/\blineage\b/gi, "history")
    .replace(/\bworkflow run\b/gi, "run")
    .replace(/\broute-demand\b/gi, "route-count")
    .replace(/\bUPD\b/g, "UPD")
    .replace(/\s+/g, " ")
    .trim();
}

function defaultReview(rowData) {
  const text = rowData.current_copy;
  const columnOverride = TECHNICAL_TABLE_COLUMNS.get(text);
  if (columnOverride && rowData.control_type === "table_header") {
    return columnOverride;
  }

  const exactOverride = EXACT_COPY_OVERRIDES.get(text);
  if (exactOverride) {
    return exactOverride;
  }

  if (["History", "Week summary", "Daily summary", "Route actuals", "Manual closeout", "Planning week", "Required routes", "Drivers in scope", "Driver", "Route", "Delivered %", "Average route time", "Packages dispatched", "Packages delivered", "Packages returned", "Service date", "Planned routes", "On-call target", "Excess-capacity target", "Routes required", "Drivers available", "Open questions", "Employment", "Target shifts", "On-call eligible", "Availability summary", "Daily route demand", "Preferences summary", "Recorded preferences", "Incidents", "Rescues", "Sick calls", "Dispatcher comment", "Manager note", "Route demand summary", "Daily route demand", "End-of-day report", "Week summary", "Daily summary", "Driver roster excerpt", "Selected-day preview", "Route assignments", "Reserve posture", "Import status", "Boundary note", "Route demand boundary", "Preferences boundary", "Driver roster"].includes(text)) {
    return {
      action: "keep",
      proposed: text,
      reason: "This copy is already short and understandable for operators.",
      severity: "low",
      theme: "Operator-friendly as is"
    };
  }

  if (text === "UPD candidate review") {
    return {
      action: "rewrite",
      proposed: "UPD / over-600 review",
      reason: "Keep the familiar acronym but add a plain-English hint.",
      severity: "medium",
      theme: "Acronym or shorthand needs explanation"
    };
  }

  if (text === "UPD?") {
    return {
      action: "rewrite",
      proposed: "UPD / over-600",
      reason: "The acronym needs context for non-expert demo viewers.",
      severity: "medium",
      theme: "Acronym or shorthand needs explanation"
    };
  }

  if (text === "Working devices / rabbits") {
    return {
      action: "rewrite",
      proposed: "Working devices / scanners",
      reason: "Rabbit is company-specific jargon.",
      severity: "medium",
      theme: "Acronym or shorthand needs explanation"
    };
  }

  if (text === "Not available") {
    return {
      action: "rewrite",
      proposed: "Drivers not available",
      reason: "The label is too vague on its own.",
      severity: "low",
      theme: "Operator-friendly as is"
    };
  }

  const technicalRegex =
    /\b(canonical|artifact|immutable|workflow-run-backed|run-backed|projection|dataset|source version|source mode|workpage|authoritative|lineage|supersed|Stage0[0-9]|workflow run|payload|bootstrap|viewer session|drill-down|rail|surface|truth|backend-authored|backend-owned|runtime)\b/i;
  if (technicalRegex.test(text)) {
    return {
      action: "rewrite",
      proposed: operatorFriendlyLabel(text),
      reason: "The current wording includes platform or implementation terminology that will confuse demo users.",
      severity: text.length > 40 ? "high" : "medium",
      theme: "Internal platform jargon"
    };
  }

  const metadataRegex = /\b(id|kind|version|code|index)\b/i;
  if (
    rowData.control_type === "metadata_label" &&
    metadataRegex.test(text)
  ) {
    return {
      action: "remove",
      proposed: "Hide from demo view",
      reason: "This is technical metadata rather than operator copy.",
      severity: "high",
      theme: "Raw system metadata"
    };
  }

  if (rowData.control_type === "button_text" && /^Open /.test(text) && /artifact|draft|snapshot/i.test(text)) {
    return {
      action: "rewrite",
      proposed: text
        .replace("artifact", "saved version")
        .replace("draft", "draft")
        .replace("snapshot", "saved preferences"),
      reason: "The action is useful, but the current noun choice is too technical for a demo.",
      severity: "low",
      theme: "Technical versioning detail"
    };
  }

  return {
    action: "keep",
    proposed: text,
    reason: "This copy is already concise and understandable in context.",
    severity: "low",
    theme: "Operator-friendly as is"
  };
}

function normalizeReview(rowData) {
  const review = defaultReview(rowData);
  return {
    ...rowData,
    action: review.action,
    proposed_copy: review.proposed,
    reason: review.reason,
    severity: review.severity,
    notes: replacementNotes(rowData.route_group),
    theme: review.theme
  };
}

function routeOrderIndex(routeGroup) {
  const index = ROUTE_ORDER.indexOf(routeGroup);
  return index >= 0 ? index : ROUTE_ORDER.length + 1;
}

function sortInventory(rows) {
  return [...rows].sort((left, right) => {
    const routeCompare = routeOrderIndex(left.route_group) - routeOrderIndex(right.route_group);
    if (routeCompare !== 0) {
      return routeCompare;
    }
    const variantCompare = left.page_variant.localeCompare(right.page_variant);
    if (variantCompare !== 0) {
      return variantCompare;
    }
    const regionCompare = left.ui_region.localeCompare(right.ui_region);
    if (regionCompare !== 0) {
      return regionCompare;
    }
    const sourceCompare = left.source_ref.localeCompare(right.source_ref);
    if (sourceCompare !== 0) {
      return sourceCompare;
    }
    return left.current_copy.localeCompare(right.current_copy);
  });
}

function uniqueRows(rows) {
  const seen = new Set();
  return rows.filter((item) => {
    const key = [
      item.route_group,
      item.page_variant,
      item.ui_region,
      item.component_or_snapshot,
      item.source_ref,
      item.state_variant,
      item.control_type,
      item.current_copy
    ].join("|");
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function colLetter(index) {
  let value = index;
  let label = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    value = Math.floor((value - 1) / 26);
  }
  return label;
}

function rangeAddress(rowIndex, colIndex, rowCount, colCount) {
  const startCol = colLetter(colIndex);
  const endCol = colLetter(colIndex + colCount - 1);
  const startRow = rowIndex;
  const endRow = rowIndex + rowCount - 1;
  return `${startCol}${startRow}:${endCol}${endRow}`;
}

function writeMatrix(sheet, rowIndex, colIndex, matrix) {
  if (matrix.length === 0 || matrix[0].length === 0) {
    return;
  }
  sheet.getRange(rangeAddress(rowIndex, colIndex, matrix.length, matrix[0].length)).values = matrix;
}

function applyHeaderStyle(range) {
  range.format.fill = "accent1";
  range.format.font = { color: "lt1", bold: true };
  range.format.wrapText = true;
  range.format.borders = { preset: "outside", style: "thin", color: "#1F2937" };
}

function actionFill(action) {
  if (action === "remove") {
    return { type: "solid", color: "#FDE2E1" };
  }
  if (action === "rewrite") {
    return { type: "solid", color: "#FEF1D4" };
  }
  return { type: "solid", color: "#E5F5EA" };
}

function severityFill(severity) {
  if (severity === "high") {
    return { type: "solid", color: "#FDE2E1" };
  }
  if (severity === "medium") {
    return { type: "solid", color: "#FEF1D4" };
  }
  return { type: "solid", color: "#EEF2F7" };
}

function buildInventorySheet(workbook, inventory) {
  const sheet = workbook.worksheets.add("Inventory");
  const data = [
    INVENTORY_COLUMNS,
    ...inventory.map((item) => INVENTORY_COLUMNS.map((column) => item[column] ?? ""))
  ];
  writeMatrix(sheet, 1, 1, data);

  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(2);

  applyHeaderStyle(sheet.getRange(`A1:${colLetter(INVENTORY_COLUMNS.length)}1`));
  sheet.getRange(`A1:${colLetter(INVENTORY_COLUMNS.length)}${data.length}`).format.wrapText = true;
  sheet.getRange(`A2:${colLetter(INVENTORY_COLUMNS.length)}${data.length}`).format.verticalAlignment = "top";
  sheet.getRange(`A1:${colLetter(INVENTORY_COLUMNS.length)}${data.length}`).format.borders = {
    preset: "outside",
    style: "thin",
    color: "#CBD5E1"
  };

  const widths = {
    A: 130,
    B: 110,
    C: 140,
    D: 180,
    E: 280,
    F: 110,
    G: 120,
    H: 340,
    I: 90,
    J: 340,
    K: 280,
    L: 90,
    M: 240
  };
  Object.entries(widths).forEach(([column, widthPx]) => {
    sheet.getRange(`${column}:${column}`).format.columnWidthPx = widthPx;
  });

  for (let index = 0; index < inventory.length; index += 1) {
    const rowNumber = index + 2;
    sheet.getRange(`I${rowNumber}`).format.fill = actionFill(inventory[index].action);
    sheet.getRange(`L${rowNumber}`).format.fill = severityFill(inventory[index].severity);
  }

  return sheet;
}

function buildGlossarySheet(workbook) {
  const sheet = workbook.worksheets.add("Glossary");
  const data = [
    ["internal_term", "recommended_copy", "when_to_use", "avoid_notes"],
    ...GLOSSARY_ROWS
  ];
  writeMatrix(sheet, 1, 1, data);
  sheet.freezePanes.freezeRows(1);
  applyHeaderStyle(sheet.getRange("A1:D1"));
  sheet.getRange(`A1:D${data.length}`).format.wrapText = true;
  sheet.getRange(`A2:D${data.length}`).format.verticalAlignment = "top";
  sheet.getRange("A:A").format.columnWidthPx = 160;
  sheet.getRange("B:B").format.columnWidthPx = 180;
  sheet.getRange("C:C").format.columnWidthPx = 320;
  sheet.getRange("D:D").format.columnWidthPx = 320;
  sheet.getRange(`A1:D${data.length}`).format.borders = {
    preset: "outside",
    style: "thin",
    color: "#CBD5E1"
  };
  return sheet;
}

function buildSummarySheet(workbook, inventory) {
  const sheet = workbook.worksheets.add("Summary");
  sheet.getRange("A1:H1").merge();
  sheet.getRange("A2:H3").merge();
  sheet.getRange("A1").values = [["Demo UX Copy Review"]];
  sheet.getRange("A2").values = [[
    "Operator-facing review workbook for the demo shell, run-scoped workpages, artifact/edit variants, shared chrome, and the dispatch closeout modal."
  ]];
  sheet.getRange("A1:H1").format.fill = "accent1";
  sheet.getRange("A1:H1").format.font = { color: "lt1", bold: true, size: 16 };
  sheet.getRange("A2:H3").format.fill = { type: "solid", color: "#EEF2F7" };
  sheet.getRange("A2:H3").format.wrapText = true;

  const totalRows = inventory.length;
  const keepCount = inventory.filter((item) => item.action === "keep").length;
  const rewriteCount = inventory.filter((item) => item.action === "rewrite").length;
  const removeCount = inventory.filter((item) => item.action === "remove").length;

  writeMatrix(sheet, 5, 1, [
    ["Metric", "Count"],
    ["Inventory rows", totalRows],
    ["Keep", keepCount],
    ["Rewrite", rewriteCount],
    ["Remove", removeCount]
  ]);
  applyHeaderStyle(sheet.getRange("A5:B5"));

  const byRoute = ROUTE_ORDER.map((routeGroup) => {
    const rows = inventory.filter((item) => item.route_group === routeGroup);
    return [
      routeGroup,
      rows.length,
      rows.filter((item) => item.action === "keep").length,
      rows.filter((item) => item.action === "rewrite").length,
      rows.filter((item) => item.action === "remove").length
    ];
  }).filter((rowData) => rowData[1] > 0);

  writeMatrix(sheet, 5, 4, [
    ["Route Group", "Rows", "Keep", "Rewrite", "Remove"],
    ...byRoute
  ]);
  applyHeaderStyle(sheet.getRange("D5:H5"));

  const themeCounts = new Map();
  inventory
    .filter((item) => item.action !== "keep")
    .forEach((item) => {
      themeCounts.set(item.theme, (themeCounts.get(item.theme) ?? 0) + 1);
    });
  const themeRows = Array.from(themeCounts.entries())
    .sort((left, right) => right[1] - left[1])
    .slice(0, 8)
    .map(([theme, count]) => [theme, count]);

  writeMatrix(sheet, 12, 1, [
    ["Top Confusion Themes", "Count"],
    ...themeRows
  ]);
  applyHeaderStyle(sheet.getRange("A12:B12"));

  const coverageRows = ROUTE_ORDER.map((routeGroup) => {
    const covered = inventory.some((item) => item.route_group === routeGroup);
    return [routeGroup, covered ? "Covered" : "Missing"];
  });
  writeMatrix(sheet, 12, 4, [
    ["Expected Surface", "Coverage"],
    ...coverageRows
  ]);
  applyHeaderStyle(sheet.getRange("D12:E12"));

  sheet.getRange("A:A").format.columnWidthPx = 220;
  sheet.getRange("B:B").format.columnWidthPx = 90;
  sheet.getRange("D:D").format.columnWidthPx = 220;
  sheet.getRange("E:E").format.columnWidthPx = 90;
  sheet.getRange("F:H").format.columnWidthPx = 90;
  sheet.getRange("A1:H30").format.wrapText = true;
  sheet.getRange("A5:H30").format.borders = {
    preset: "outside",
    style: "thin",
    color: "#CBD5E1"
  };
  return sheet;
}

function verifyCoverage(inventory) {
  const missingRouteGroups = ROUTE_ORDER.filter(
    (routeGroup) => !inventory.some((item) => item.route_group === routeGroup)
  );
  if (missingRouteGroups.length > 0) {
    throw new Error(`Missing coverage for route groups: ${missingRouteGroups.join(", ")}`);
  }
}

async function buildInventory() {
  const snapshotPayloads = await Promise.all(
    SNAPSHOT_CONFIGS.map(async (config) => ({
      config,
      json: await readJson(config.file)
    }))
  );
  const snapshotRows = snapshotPayloads.flatMap(({ config, json }) =>
    snapshotRowsFromConfig(config, json.workpage_state ?? {})
  );
  const merged = uniqueRows([...STATIC_ROWS, ...snapshotRows]).map(normalizeReview);
  const sorted = sortInventory(merged);
  verifyCoverage(sorted);
  return sorted;
}

async function main() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });

  const inventory = await buildInventory();
  const workbook = Workbook.create();
  buildSummarySheet(workbook, inventory);
  buildInventorySheet(workbook, inventory);
  buildGlossarySheet(workbook);

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(OUTPUT_FILE);

  const inspection = await workbook.inspect({
    kind: "sheet,region",
    maxChars: 3000,
    tableMaxRows: 8,
    tableMaxCols: 8
  });

  console.log(
    JSON.stringify(
      {
        output_file: OUTPUT_FILE,
        inventory_rows: inventory.length,
        action_counts: {
          keep: inventory.filter((item) => item.action === "keep").length,
          rewrite: inventory.filter((item) => item.action === "rewrite").length,
          remove: inventory.filter((item) => item.action === "remove").length
        },
        inspection
      },
      null,
      2
    )
  );
}

await main();
