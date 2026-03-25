import type {
  WorkpageChecklistSection,
  WorkpageFormSection,
  WorkpageFormValue
} from "@/lib/types/workpages";

export type WorkpageFormState = Record<string, WorkpageFormValue>;

export interface WorkpageChecklistEntryState {
  selected: boolean;
  note: string;
}

export type WorkpageChecklistState = Record<string, WorkpageChecklistEntryState>;

export function buildFormState(section: WorkpageFormSection): WorkpageFormState {
  return Object.fromEntries(section.fields.map((field) => [field.key, field.value]));
}

export function buildChecklistState(section: WorkpageChecklistSection): WorkpageChecklistState {
  return Object.fromEntries(
    section.items.map((item) => [
      item.item_id,
      {
        selected: item.selected,
        note: item.note
      }
    ])
  );
}
