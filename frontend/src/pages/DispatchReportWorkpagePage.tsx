import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { StatePanel } from "@/components/StatePanel";
import { WorkpageChecklistSection } from "@/components/workpages/WorkpageChecklistSection";
import {
  WorkpageFrame,
  WorkpageHistorySection,
  WorkpageNotePanelSection,
  WorkpageSummaryCardsSection,
  WorkpageTableSection
} from "@/components/workpages/WorkpageContent";
import { WorkpageFormSection } from "@/components/workpages/WorkpageFormSection";
import { workpagesRepository } from "@/lib/repositories";
import type {
  WorkpageChecklistSection as WorkpageChecklistSectionModel,
  WorkpageFormSection as WorkpageFormSectionModel,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";
import {
  buildChecklistState,
  buildFormState,
  type WorkpageChecklistState,
  type WorkpageFormState
} from "@/lib/workpages/state";

function findTableSection(
  sections: WorkpageTableSectionModel[],
  tableId: string
): WorkpageTableSectionModel | null {
  return sections.find((section) => section.table_id === tableId) ?? null;
}

export function DispatchReportWorkpagePage(): JSX.Element {
  const query = useQuery({
    queryKey: ["workpages", "eod-v0"],
    queryFn: () => workpagesRepository.eodExample()
  });

  const model = query.data;
  const summarySection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageSummaryCardsSectionModel => section.kind === "summary_cards"
      ) ?? null,
    [model]
  );
  const noteSection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageNotePanelSectionModel => section.kind === "note_panel"
      ) ?? null,
    [model]
  );
  const historySection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageHistorySectionModel => section.kind === "history_stub"
      ) ?? null,
    [model]
  );
  const tableSections = useMemo(
    () =>
      model?.sections.filter(
        (section): section is WorkpageTableSectionModel => section.kind === "table"
      ) ?? [],
    [model]
  );
  const formSection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageFormSectionModel => section.kind === "form"
      ) ?? null,
    [model]
  );
  const checklistSection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageChecklistSectionModel => section.kind === "checklist"
      ) ?? null,
    [model]
  );
  const [formState, setFormState] = useState<WorkpageFormState>({});
  const [checklistState, setChecklistState] = useState<WorkpageChecklistState>({});

  useEffect(() => {
    setFormState(formSection ? buildFormState(formSection) : {});
  }, [formSection]);

  useEffect(() => {
    setChecklistState(checklistSection ? buildChecklistState(checklistSection) : {});
  }, [checklistSection]);

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading end-of-day workpage"
        detail="Building the example-backed dispatch-reporting workpage."
      />
    );
  }

  if (query.isError || !model) {
    return (
      <StatePanel
        kind="error"
        title="End-of-day workpage failed to load"
        detail="Unable to build the dispatch-reporting workpage example."
      />
    );
  }

  return (
    <WorkpageFrame
      eyebrow="Dispatch Reporting Draft"
      description="A fixture-backed full page for route actual review, closeout capture, and UPD draft posture."
      summaryItems={[
        `Service date ${model.summary.service_date}`,
        `${model.summary.station_code}`,
        `${model.summary.dsp_name}`,
        "UPD draft anchor"
      ]}
      model={model}
      testId="dispatch-report-workpage-page"
    >
      <div className="workpage-page__grid workpage-page__grid--two-column">
        {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}
        {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
      </div>

      {findTableSection(tableSections, "route_actuals") ? (
        <WorkpageTableSection section={findTableSection(tableSections, "route_actuals") as WorkpageTableSectionModel} />
      ) : null}

      <div className="workpage-page__grid workpage-page__grid--two-column">
        {formSection ? (
          <WorkpageFormSection
            section={formSection}
            values={formState}
            onChange={(fieldKey, value) => {
              setFormState((current) => ({
                ...current,
                [fieldKey]: value
              }));
            }}
          />
        ) : null}
        {checklistSection ? (
          <WorkpageChecklistSection
            section={checklistSection}
            values={checklistState}
            onToggle={(itemId, checked) => {
              setChecklistState((current) => ({
                ...current,
                [itemId]: {
                  ...(current[itemId] ?? { selected: false, note: "" }),
                  selected: checked
                }
              }));
            }}
            onNoteChange={(itemId, note) => {
              setChecklistState((current) => ({
                ...current,
                [itemId]: {
                  ...(current[itemId] ?? { selected: false, note: "" }),
                  note
                }
              }));
            }}
          />
        ) : null}
      </div>

      {historySection ? <WorkpageHistorySection section={historySection} /> : null}
    </WorkpageFrame>
  );
}
