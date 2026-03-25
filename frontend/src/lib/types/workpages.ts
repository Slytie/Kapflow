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
