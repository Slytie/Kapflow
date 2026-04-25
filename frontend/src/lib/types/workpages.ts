export type WorkpageMode = "example";
export type WorkpageValidationStatus = "informational" | "warning" | "error";
export type WorkpageScalar = string | number | boolean | null;
export type WorkpageFormInput = "multi_select" | "integer" | "textarea" | "text" | "repeater" | "time";
export type WorkpageFormValue = string | number | string[];

export interface WorkpageSummaryCard {
  key: string;
  label: string;
  value: string | number;
}

export interface WorkpageTableColumn {
  key: string;
  label: string;
}

export type WorkpageTableRow = Record<string, WorkpageScalar>;

export interface WorkpageFormField {
  key: string;
  label: string;
  input: WorkpageFormInput;
  options?: string[];
  value: WorkpageFormValue;
}

export interface WorkpageChecklistItem {
  item_id: string;
  title: string;
  detail: string;
  selected: boolean;
  note: string;
  tags: string[];
}

export interface WorkpageHistoryEntry {
  label: string;
  value: string;
}

export interface WorkpageSummaryCardsSection {
  kind: "summary_cards";
  title: string;
  cards: WorkpageSummaryCard[];
}

export interface WorkpageTableSection {
  kind: "table";
  title: string;
  table_id: string;
  columns: WorkpageTableColumn[];
  rows: WorkpageTableRow[];
}

export type WorkpageScheduleHeatmapCellState = "assigned" | "on_call" | "empty";

export interface WorkpageScheduleHeatmapDate {
  service_date: string;
  label: string;
  weekday_label: string;
  is_selected_day?: boolean;
}

export interface WorkpageScheduleHeatmapCell {
  service_date: string;
  state: WorkpageScheduleHeatmapCellState;
  row_kind: "assignment" | "reserve" | null;
  route_slot_id: string | null;
  projected_minutes: number | null;
  assignment_status: string | null;
  planned_driver_day_state: string | null;
  manual_override: boolean;
  preference_state?: string;
  availability_state?: string | null;
  availability_reason_code?: string | null;
  availability_source_ref?: string | null;
}

export interface WorkpageScheduleHeatmapPerson {
  driver_id: string;
  driver_name: string;
  employment_type: string;
  on_call_eligible: boolean;
  previous_week_minutes: number;
  availability_summary: string;
  cells: WorkpageScheduleHeatmapCell[];
}

export interface WorkpageScheduleHeatmapSection {
  kind: "schedule_heatmap";
  title: string;
  subtitle?: string;
  service_dates: WorkpageScheduleHeatmapDate[];
  people: WorkpageScheduleHeatmapPerson[];
}

export interface WorkpageNotePanelSection {
  kind: "note_panel";
  title: string;
  body: string;
}

export interface WorkpageFormSection {
  kind: "form";
  title: string;
  form_id: string;
  fields: WorkpageFormField[];
}

export interface WorkpageChecklistSection {
  kind: "checklist";
  title: string;
  checklist_id: string;
  items: WorkpageChecklistItem[];
}

export interface WorkpageHistorySection {
  kind: "history_stub";
  title: string;
  entries: WorkpageHistoryEntry[];
}

export type WorkpageScheduleDependencyState =
  | "aligned"
  | "drifted"
  | "missing"
  | "not_available"
  | "not_pinned"
  | "resolved";

export interface WorkpageScheduleArtifactState {
  state_kind: string;
  artifact_kind: string;
  editable: boolean;
  current_artifact_version_id: string | null;
  latest_artifact_version_id: string | null;
  accepted_artifact_version_id: string | null;
}

export interface WorkpageScheduleDependency {
  dependency_key: string;
  artifact_kind: string;
  artifact_version_id: string | null;
  impact_class: string;
  state: WorkpageScheduleDependencyState;
  source_ref: string | null;
}

export interface WorkpageScheduleCalculationTopBarDay {
  service_date: string;
  weekday_label: string;
  routes_required: number;
  routes_scheduled?: number;
  on_call_target: number;
  on_call_drivers?: number;
  total_staff?: number;
  excess_capacity?: number;
  excess_capacity_target?: number;
  available_driver_count?: number;
  capacity_state?: string;
}

export interface WorkpageScheduleSelectedDay {
  service_date: string;
  routes_required: number;
  routes_scheduled?: number;
  on_call_target?: number;
  on_call_drivers?: number;
  available_driver_count?: number;
  available_driver_ids?: string[];
  available_preference_buckets?: {
    open_to_work: string[];
    prefer_not_to_work: string[];
    definitely_can_not_work: string[];
    unset: string[];
  };
  drivers_available?: number;
  projected_on_call_needed?: number;
  open_questions?: string;
}

export interface WorkpageScheduleDriverMetric {
  driver_id: string;
  driver_name: string;
  scheduled_hours: number;
  scheduled_routes: number;
  on_call_shifts: number;
  preference_state: string;
  availability_state: string;
  compliance_state: string;
  issues: string[];
}

export interface WorkpageScheduleCheck {
  check_id: string;
  label: string;
  state: string;
  blocking: boolean;
  affected_service_dates?: string[];
  affected_driver_ids?: string[];
}

export interface WorkpageScheduleCalculations {
  top_bar: {
    days: WorkpageScheduleCalculationTopBarDay[];
  };
  selected_day: WorkpageScheduleSelectedDay;
  driver_metrics: WorkpageScheduleDriverMetric[];
  checks: WorkpageScheduleCheck[];
}

export interface WorkpageScheduleDraftLineageEntry {
  artifact_version_id: string;
  supersedes_artifact_version_id: string | null;
}

export interface WorkpageScheduleDraftLineage {
  current_artifact_version_id: string | null;
  latest_artifact_version_id: string | null;
  previous_artifact_version_id: string | null;
  recent_versions: WorkpageScheduleDraftLineageEntry[];
}

export interface WorkpageArtifactHistoryEntry {
  artifact_version_id: string;
  workflow_run_id: string;
  artifact_kind: string;
  created_at: string;
  lineage_note: string | null;
  supersedes_artifact_version_id: string | null;
  route: string;
}

export interface WorkpageArtifactHistory {
  current_artifact_version_id: string | null;
  latest_artifact_version_id: string | null;
  previous_artifact_version_id: string | null;
  next_artifact_version_id: string | null;
  entries: WorkpageArtifactHistoryEntry[];
}

export interface WorkpageScheduleAcceptedSeriesEntry {
  artifact_version_id: string;
  workflow_run_id: string;
  partition_key: string;
  logical_date: string;
  artifact_kind: string;
  route: string;
}

export interface WorkpageScheduleAcceptedSeries {
  series_key: string | null;
  current_artifact_version_id: string | null;
  previous_artifact_version_id: string | null;
  next_artifact_version_id: string | null;
  entries: WorkpageScheduleAcceptedSeriesEntry[];
}

export interface WorkpageActionRefSubject {
  subject_kind: "human_task" | "approval";
  subject_id: string;
}

export interface WorkpageActionRef {
  action_id: string;
  workpage_kind: string;
  workflow_run_id: string;
  artifact_version_id: string | null;
  subject: WorkpageActionRefSubject | null;
}

export type WorkpageScheduleActionKind =
  | "open_latest_draft"
  | "preview_recalc"
  | "submit_artifact"
  | "mark_sick_no_show";

export interface WorkpageScheduleAction {
  action_id: string;
  kind: WorkpageScheduleActionKind;
  label: string;
  state: "available" | "blocked" | "unavailable";
  workpage_kind: string;
  artifact_version_id: string | null;
  route?: string | null;
  preview_path?: string | null;
  submit_path?: string | null;
  sick_no_show_path?: string | null;
  action_ref: WorkpageActionRef | null;
  disabled_reason?: string | null;
}

export interface WorkpageSchedulePreview {
  workflow_run_id: string;
  artifact_version_id: string;
  dirty: boolean;
  dependency_state: string;
  dependencies: WorkpageScheduleDependency[];
  calculations: WorkpageScheduleCalculations;
}

export interface WorkpageRouteDemandDayCard {
  service_date: string;
  weekday_label: string;
  planned_route_count: number;
  standard_slot_count: number;
  standard_early_slot_count: number;
  standard_late_slot_count: number;
  rescue_slot_count: number;
  overflow_slot_count: number;
  on_call_target: number;
  excess_capacity_target: number;
  delta_from_previous_version: {
    planned_route_count_delta: number;
  } | null;
}

export interface WorkpageRouteDemandCalculations {
  day_cards: WorkpageRouteDemandDayCard[];
}

export interface WorkpageRouteDemandRefreshTask {
  human_task_id: string;
  task_run_id: string;
  state: string;
  owner_role: string | null;
  activation_key: string;
  blocked_on_kind: string | null;
  blocked_on_ref: string | null;
}

export interface WorkpageRouteDemandScheduleImpact {
  latest_schedule_draft_artifact_version_id: string | null;
  latest_route_demand_artifact_version_id?: string | null;
  dependency_state: string;
  schedule_state: string;
  refresh_task: WorkpageRouteDemandRefreshTask | null;
}

export type WorkpageRouteDemandActionKind = "open_latest" | "save";

export interface WorkpageRouteDemandAction {
  action_id: string;
  kind: WorkpageRouteDemandActionKind;
  label: string;
  state: "available" | "blocked" | "unavailable";
  workpage_kind: string;
  artifact_version_id: string | null;
  route?: string | null;
  submit_path?: string | null;
  action_ref: WorkpageActionRef | null;
  disabled_reason?: string | null;
}

export interface WorkpageDriverPreferencesDriverRow {
  driver_id: string;
  driver_name: string;
  employment_type: string;
  on_call_eligible: boolean;
  preferences_by_weekday: {
    sun: string | null;
    mon: string | null;
    tue: string | null;
    wed: string | null;
    thu: string | null;
    fri: string | null;
    sat: string | null;
  };
}

export interface WorkpageDriverPreferencesGrid {
  service_dates: WorkpageScheduleHeatmapDate[];
  weekdays: Array<"sun" | "mon" | "tue" | "wed" | "thu" | "fri" | "sat">;
  drivers: WorkpageDriverPreferencesDriverRow[];
}

export interface WorkpageDriverPreferencesScheduleImpact {
  latest_schedule_draft_artifact_version_id: string | null;
  latest_driver_preferences_artifact_version_id?: string | null;
  dependency_state: string;
  schedule_state: string;
}

export interface WorkpageDriverAvailabilityException {
  exception_id: string;
  driver_id: string;
  driver_name: string;
  start_date: string;
  end_date: string;
  reason_code:
    | "wedding"
    | "vacation"
    | "medical"
    | "family"
    | "appointment"
    | "sick_no_show"
    | "other";
  reason_note: string;
  status: "approved";
  source_workflow_run_id: string;
  source_artifact_version_id: string;
  affected_planning_week_ids: string[];
}

export interface WorkpageDriverAvailabilityExceptions {
  items: WorkpageDriverAvailabilityException[];
}

export type WorkpageDriverPreferencesActionKind =
  | "open_latest"
  | "create_snapshot"
  | "save"
  | "add_availability_exception";

export interface WorkpageDriverPreferencesAction {
  action_id: string;
  kind: WorkpageDriverPreferencesActionKind;
  label: string;
  state: "available" | "blocked" | "unavailable";
  workpage_kind: string;
  artifact_version_id: string | null;
  route?: string | null;
  create_path?: string | null;
  submit_path?: string | null;
  action_ref: WorkpageActionRef | null;
  disabled_reason?: string | null;
}

export type WorkpageEodActionKind = "submit_artifact";

export interface WorkpageEodAction {
  action_id: string;
  kind: WorkpageEodActionKind;
  label: string;
  state: "available" | "blocked" | "unavailable";
  workpage_kind: string;
  artifact_version_id: string | null;
  submit_path?: string | null;
  action_ref: WorkpageActionRef | null;
  disabled_reason?: string | null;
}

export type WorkpageAction =
  | WorkpageScheduleAction
  | WorkpageRouteDemandAction
  | WorkpageDriverPreferencesAction
  | WorkpageEodAction;

export type WorkpageSection =
  | WorkpageSummaryCardsSection
  | WorkpageTableSection
  | WorkpageScheduleHeatmapSection
  | WorkpageNotePanelSection
  | WorkpageFormSection
  | WorkpageChecklistSection
  | WorkpageHistorySection;

export interface WorkpageViewModel {
  workpage_id: string;
  version: number;
  title: string;
  mode: WorkpageMode;
  workflow_id: string;
  dataset_key: string;
  source_artifact_version_id: string | null;
  source_examples: Record<string, string>;
  summary: Record<string, WorkpageScalar>;
  sections: WorkpageSection[];
  validation: {
    status: WorkpageValidationStatus;
    warnings: string[];
  };
}
