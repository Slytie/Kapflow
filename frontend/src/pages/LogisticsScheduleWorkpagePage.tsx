import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { StatePanel } from "@/components/StatePanel";
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
  WorkpageFormSection as WorkpageFormSectionModel,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";
import { buildFormState, type WorkpageFormState } from "@/lib/workpages/state";

function findTableSection(
  sections: WorkpageTableSectionModel[],
  tableId: string
): WorkpageTableSectionModel | null {
  return sections.find((section) => section.table_id === tableId) ?? null;
}

export function LogisticsScheduleWorkpagePage(): JSX.Element {
  const query = useQuery({
    queryKey: ["workpages", "schedule-v0"],
    queryFn: () => workpagesRepository.scheduleExample()
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
  const [formState, setFormState] = useState<WorkpageFormState>({});

  useEffect(() => {
    setFormState(formSection ? buildFormState(formSection) : {});
  }, [formSection]);

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading schedule workpage"
        detail="Building the example-backed workpage view model."
      />
    );
  }

  if (query.isError || !model) {
    return (
      <StatePanel
        kind="error"
        title="Schedule workpage failed to load"
        detail="Unable to build the schedule workpage example."
      />
    );
  }

  return (
    <WorkpageFrame
      eyebrow="Weekly Planning Review"
      description="A fixture-backed full page for weekly schedule review, selected-day preview, and bounded what-if exploration."
      summaryItems={[
        `Week ${model.summary.planning_week_id}`,
        `${model.summary.service_area}`,
        `${model.summary.station_code}`,
        `Week starts ${model.summary.operational_week_start}`
      ]}
      model={model}
      testId="schedule-workpage-page"
    >
      <div className="workpage-page__grid workpage-page__grid--two-column">
        {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}
        {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
      </div>

      {findTableSection(tableSections, "day_demand") ? (
        <WorkpageTableSection section={findTableSection(tableSections, "day_demand") as WorkpageTableSectionModel} />
      ) : null}

      <div className="workpage-page__grid workpage-page__grid--two-column">
        {findTableSection(tableSections, "selected_day_preview") ? (
          <WorkpageTableSection
            section={findTableSection(tableSections, "selected_day_preview") as WorkpageTableSectionModel}
          />
        ) : null}
        {historySection ? <WorkpageHistorySection section={historySection} /> : null}
      </div>

      {findTableSection(tableSections, "driver_roster") ? (
        <WorkpageTableSection section={findTableSection(tableSections, "driver_roster") as WorkpageTableSectionModel} />
      ) : null}

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
    </WorkpageFrame>
  );
}
