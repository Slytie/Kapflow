import type { WorkpageChecklistSection as WorkpageChecklistSectionModel } from "@/lib/types/workpages";
import type { WorkpageChecklistState } from "@/lib/workpages/state";

interface WorkpageChecklistSectionProps {
  section: WorkpageChecklistSectionModel;
  values: WorkpageChecklistState;
  onToggle: (itemId: string, checked: boolean) => void;
  onNoteChange: (itemId: string, note: string) => void;
  readOnly?: boolean;
}

export function WorkpageChecklistSection({
  section,
  values,
  onToggle,
  onNoteChange,
  readOnly = false
}: WorkpageChecklistSectionProps): JSX.Element {
  return (
    <section className="workpage-panel">
      <header className="workpage-panel__header">
        <h2>{section.title}</h2>
      </header>
      <div className="workpage-checklist">
        {section.items.map((item) => {
          const value = values[item.item_id] ?? {
            selected: item.selected,
            note: item.note
          };
          return (
            <article
              key={item.item_id}
              className="workpage-checklist__item"
              data-testid={`checklist-item-${item.item_id}`}
            >
              <label className="workpage-checklist__toggle">
                <input
                  type="checkbox"
                  checked={value.selected}
                  disabled={readOnly}
                  onChange={(event) => onToggle(item.item_id, event.currentTarget.checked)}
                />
                <span>{item.title}</span>
              </label>
              <p>{item.detail}</p>
              <div className="workpage-checklist__tags">
                {item.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <label className="workpage-form__field">
                <span>Manager note</span>
                <textarea
                  value={value.note}
                  disabled={readOnly}
                  onChange={(event) => onNoteChange(item.item_id, event.currentTarget.value)}
                  rows={3}
                />
              </label>
            </article>
          );
        })}
      </div>
    </section>
  );
}
