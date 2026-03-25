import type { ChangeEvent } from "react";

import type { WorkpageFormField, WorkpageFormSection as WorkpageFormSectionModel } from "@/lib/types/workpages";
import type { WorkpageFormState } from "@/lib/workpages/state";

function valuesForField(value: WorkpageFormState[string]): string[] {
  return Array.isArray(value) ? value : [];
}

function fieldTextValue(value: WorkpageFormState[string]): string {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return typeof value === "number" ? String(value) : value;
}

interface WorkpageFormSectionProps {
  section: WorkpageFormSectionModel;
  values: WorkpageFormState;
  onChange: (fieldKey: string, value: WorkpageFormState[string]) => void;
  readOnly?: boolean;
}

function renderRepeaterField(
  field: WorkpageFormField,
  value: WorkpageFormState[string],
  onChange: WorkpageFormSectionProps["onChange"],
  readOnly: boolean
): JSX.Element {
  const entries = valuesForField(value);
  return (
    <div className="workpage-form__repeater">
      {entries.length === 0 ? <p className="workpage-form__empty">No entries yet.</p> : null}
      {entries.map((entry, index) => (
        <div key={`${field.key}-${index}`} className="workpage-form__repeater-row">
          <input
            type="text"
            value={entry}
            disabled={readOnly}
            onChange={(event) => {
              const nextEntries = [...entries];
              nextEntries[index] = event.currentTarget.value;
              onChange(field.key, nextEntries);
            }}
            aria-label={`${field.label} ${index + 1}`}
          />
          <button
            type="button"
            className="action-btn"
            disabled={readOnly}
            onClick={() => onChange(field.key, entries.filter((_, currentIndex) => currentIndex !== index))}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        className="action-btn"
        disabled={readOnly}
        onClick={() => onChange(field.key, [...entries, ""])}
      >
        Add entry
      </button>
    </div>
  );
}

export function WorkpageFormSection({
  section,
  values,
  onChange,
  readOnly = false
}: WorkpageFormSectionProps): JSX.Element {
  return (
    <section className="workpage-panel">
      <header className="workpage-panel__header">
        <h2>{section.title}</h2>
      </header>
      <div className="workpage-form">
        {section.fields.map((field) => {
          const value = values[field.key] ?? field.value;
          if (field.input === "multi_select") {
            const selectedValues = valuesForField(value);
            return (
              <fieldset key={field.key} className="workpage-form__field">
                <legend>{field.label}</legend>
                <div className="workpage-form__options">
                  {(field.options ?? []).map((option) => {
                    const isSelected = selectedValues.includes(option);
                    return (
                      <label key={option} className="workpage-form__option">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          disabled={readOnly}
                          onChange={() => {
                            const nextValues = isSelected
                              ? selectedValues.filter((current) => current !== option)
                              : [...selectedValues, option];
                            onChange(field.key, nextValues);
                          }}
                        />
                        <span>{option}</span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            );
          }

          if (field.input === "textarea") {
            return (
              <label key={field.key} className="workpage-form__field">
                <span>{field.label}</span>
                <textarea
                  value={fieldTextValue(value)}
                  disabled={readOnly}
                  onChange={(event) => onChange(field.key, event.currentTarget.value)}
                  rows={4}
                />
              </label>
            );
          }

          if (field.input === "integer") {
            return (
              <label key={field.key} className="workpage-form__field">
                <span>{field.label}</span>
                <input
                  type="number"
                  disabled={readOnly}
                  value={typeof value === "number" ? value : Number.parseInt(fieldTextValue(value), 10) || 0}
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    onChange(field.key, Number.parseInt(event.currentTarget.value || "0", 10))
                  }
                />
              </label>
            );
          }

          if (field.input === "repeater") {
            return (
              <div key={field.key} className="workpage-form__field">
                <span>{field.label}</span>
                {renderRepeaterField(field, value, onChange, readOnly)}
              </div>
            );
          }

          return (
            <label key={field.key} className="workpage-form__field">
              <span>{field.label}</span>
              <input
                type={field.input === "time" ? "time" : "text"}
                value={fieldTextValue(value)}
                disabled={readOnly}
                onChange={(event) => onChange(field.key, event.currentTarget.value)}
              />
            </label>
          );
        })}
      </div>
    </section>
  );
}
