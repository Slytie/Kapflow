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
