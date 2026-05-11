import { useMemo, type ReactNode } from "react";

import {
  ScheduleWorkpageSurface,
  type ScheduleVersionRailDefinition
} from "@/components/workpages/ScheduleWorkpageSurface";
import {
  WorkpageFrame,
  WorkpageHistorySection,
  WorkpageNotePanelSection
} from "@/components/workpages/WorkpageContent";
import { apiConfig } from "@/lib/api/config";
import type { WorkpageContract } from "@/lib/types/contracts";
import { buildAcceptedRail, buildDraftRail, useScheduleSections } from "@/lib/workpages/schedulePageModel";

interface LogisticsScheduleWorkpageViewProps {
  contract: WorkpageContract;
  sourceDescription: string;
  summaryLabel: string;
  testId: string;
  backLink?: string;
  backLabel?: string;
  heroTitleActions?: ReactNode;
  heroSupportText?: ReactNode;
  heroActions?: ReactNode;
  stickyTitleBar?: boolean;
  preContent?: ReactNode;
  onRefresh: () => void;
  isRefreshing: boolean;
  versionRails?: ScheduleVersionRailDefinition[];
  routeDemandUnresolvedCountsByServiceDate?: Record<string, number>;
}

export function LogisticsScheduleWorkpageView({
  contract,
  sourceDescription,
  summaryLabel,
  testId,
  backLink,
  backLabel,
  heroTitleActions,
  heroSupportText,
  heroActions,
  stickyTitleBar = false,
  preContent,
  onRefresh,
  isRefreshing,
  versionRails,
  routeDemandUnresolvedCountsByServiceDate = {}
}: LogisticsScheduleWorkpageViewProps): JSX.Element {
  const { summarySection, noteSection, historySection, heatmapSection, assignmentSection, reserveSection } =
    useScheduleSections(contract);
  const resolvedVersionRails = useMemo(
    () => versionRails ?? [buildAcceptedRail(contract), buildDraftRail(contract)],
    [contract, versionRails]
  );

  return (
    <WorkpageFrame
      eyebrow="Weekly Planning Review"
      description="A workflow-backed weekly planning review for bounded draft navigation, live schedule context, and backend-authored metrics."
      summaryItems={[
        `Week ${String(contract.workpage.summary.planning_week_id ?? "unknown")}`,
        String(contract.workpage.summary.operational_week_start ?? "unknown"),
        String(contract.workpage.summary.station_code ?? contract.workpage.summary.source_bundle_id ?? "—"),
        summaryLabel
      ]}
      model={contract.workpage}
      source={contract.source}
      freshness={contract.freshness}
      onRefresh={onRefresh}
      isRefreshing={isRefreshing}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId={testId}
      metadataPresentation="dialog"
      infoDialogTitle="Weekly planning context"
      sourceDescription={sourceDescription}
      heroTitleActions={heroTitleActions}
      heroSupportText={heroSupportText}
      heroActions={heroActions}
      stickyTitleBar={stickyTitleBar}
      infoDialogContent={
        <>
          {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
          {historySection ? <WorkpageHistorySection section={historySection} /> : null}
        </>
      }
      backLink={backLink}
      backLabel={backLabel}
    >
      {preContent}
      <ScheduleWorkpageSurface
        summarySection={summarySection}
        heatmapSection={heatmapSection}
        assignmentRows={assignmentSection?.rows ?? []}
        reserveRows={reserveSection?.rows ?? []}
        calculations={contract.calculations}
        dependencies={contract.dependencies}
        versionRails={resolvedVersionRails}
        readOnly
        routeDemandUnresolvedCountsByServiceDate={routeDemandUnresolvedCountsByServiceDate}
      />
    </WorkpageFrame>
  );
}
