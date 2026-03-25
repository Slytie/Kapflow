import type {
  WorkpageChecklistSection,
  WorkpageFormSection,
  WorkpageFormValue,
  WorkpageViewModel
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

export function buildEditableSectionResetKey(
  workpage: Pick<WorkpageViewModel, "workpage_id" | "version">,
  sourceVersion: string,
  section: WorkpageFormSection | WorkpageChecklistSection
): string {
  if (section.kind === "form") {
    return [
      workpage.workpage_id,
      workpage.version,
      sourceVersion,
      section.kind,
      section.form_id,
      section.fields.map((field) => field.key).join(",")
    ].join("|");
  }

  return [
    workpage.workpage_id,
    workpage.version,
    sourceVersion,
    section.kind,
    section.checklist_id,
    section.items.map((item) => item.item_id).join(",")
  ].join("|");
}
