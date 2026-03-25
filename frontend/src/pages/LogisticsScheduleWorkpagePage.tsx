import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { StatePanel } from "@/components/StatePanel";
import {
  WorkpageFrame,
  WorkpageHistorySection,
  WorkpageNotePanelSection,
  WorkpageSummaryCardsSection,
  WorkpageTableSection
} from "@/components/workpages/WorkpageContent";
import { WorkpageFormSection } from "@/components/workpages/WorkpageFormSection";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { workpagesRepository } from "@/lib/repositories";
import type {
  WorkpageFormSection as WorkpageFormSectionModel,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";
import {
  buildEditableSectionResetKey,
  buildFormState,
  type WorkpageFormState
} from "@/lib/workpages/state";

function findTableSection(
  sections: WorkpageTableSectionModel[],
  tableId: string
): WorkpageTableSectionModel | null {
  return sections.find((section) => section.table_id === tableId) ?? null;
}

export function LogisticsScheduleWorkpagePage(): JSX.Element {
  const query = useQuery({
    queryKey: ["workpages", "schedule-v0"],
    queryFn: () => workpagesRepository.schedule(),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const contract = query.data;
  const model = contract?.workpage;
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
  const lastFormResetKeyRef = useRef<string | null>(null);
  const formResetKey = useMemo(() => {
    if (!contract || !formSection) {
      return null;
    }
    return buildEditableSectionResetKey(contract.workpage, contract.freshness.source_version, formSection);
  }, [contract, formSection]);

  useEffect(() => {
    if (!formSection || !formResetKey) {
      lastFormResetKeyRef.current = null;
      setFormState({});
      return;
    }
    if (lastFormResetKeyRef.current === formResetKey) {
      return;
    }
    lastFormResetKeyRef.current = formResetKey;
    setFormState(buildFormState(formSection));
  }, [formResetKey, formSection]);

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading schedule workpage"
        detail="Fetching the backend demo workpage query."
      />
    );
  }

  if (query.isError || !contract || !model) {
    return (
      <StatePanel
        kind="error"
        title="Schedule workpage failed to load"
        detail={errorText(query.error, "Unable to load the schedule workpage demo query.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  return (
    <WorkpageFrame
      eyebrow="Weekly Planning Review"
      description="A backend demo query for weekly schedule review, selected-day preview, and bounded what-if exploration."
      summaryItems={[
        `Week ${model.summary.planning_week_id}`,
        `${model.summary.service_area}`,
        `${model.summary.station_code}`,
        `Week starts ${model.summary.operational_week_start}`
      ]}
      model={model}
      source={contract.source}
      freshness={contract.freshness}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching}
      pollIntervalMs={apiConfig.pollIntervalMs}
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
