import {
  type Dispatch,
  type SetStateAction,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import {
  type DraftVersionTimelineEntry,
  draftVersionPrimaryLabel
} from "@/components/workpages/DraftVersionTimeline";
import type { ScheduleVersionRailDefinition } from "@/components/workpages/ScheduleWorkpageSurface";
import { isApiClientError } from "@/lib/api/httpClient";
import type { WorkpageContract } from "@/lib/types/contracts";
import type {
  WorkpageDriverPreferencesAction,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageRouteDemandAction,
  WorkpageScheduleAction,
  WorkpageScheduleHeatmapSection as WorkpageScheduleHeatmapSectionModel,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableRow,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";

export function findTableSection(
  sections: WorkpageTableSectionModel[],
  tableId: string
): WorkpageTableSectionModel | null {
  return sections.find((section) => section.table_id === tableId) ?? null;
}

export function findHeatmapSection(
  sections: WorkpageContract["workpage"]["sections"]
): WorkpageScheduleHeatmapSectionModel | null {
  return (
    sections.find(
      (section): section is WorkpageScheduleHeatmapSectionModel => section.kind === "schedule_heatmap"
    ) ?? null
  );
}

export function buildTableSectionResetKey(
  contract: WorkpageContract,
  section: WorkpageTableSectionModel
): string {
  return [
    contract.workpage.workpage_id,
    contract.workpage.version,
    contract.freshness.source_version,
    section.table_id,
    section.columns.map((column) => column.key).join(","),
    section.rows.length
  ].join("|");
}

export function scheduleLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/schedule-v0`;
}

export function workpageBackRoute(workflowRunId: string): { href: string; label: string } {
  return { href: `/runs/${workflowRunId}`, label: "Back to run detail" };
}

export function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

export function rowsSignature(rows: WorkpageTableRow[]): string {
  return JSON.stringify(rows);
}

export function findScheduleAction(
  contract: WorkpageContract | undefined,
  matcher: (action: WorkpageScheduleAction) => boolean
): WorkpageScheduleAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageScheduleAction => {
        if (action.workpage_kind !== "schedule-v0") {
          return false;
        }
        return matcher(action as WorkpageScheduleAction);
      }
    ) ?? null
  );
}

export function findRouteDemandAction(
  contract: WorkpageContract | undefined
): WorkpageRouteDemandAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageRouteDemandAction =>
        action.workpage_kind === "route-demand-v0"
    ) ?? null
  );
}

export function findDriverPreferencesAction(
  contract: WorkpageContract | undefined
): WorkpageDriverPreferencesAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageDriverPreferencesAction =>
        action.workpage_kind === "driver-preferences-v0"
    ) ?? null
  );
}

export function workpageConflictDetails(error: unknown): {
  artifactVersionId: string;
  latestArtifactVersionId: string;
  workflowRunId: string;
  route: string;
} | null {
  if (!isApiClientError(error) || error.code !== "workpage_artifact_conflict" || !error.details) {
    return null;
  }
  const artifactVersionId = asString(error.details.artifact_version_id);
  const latestArtifactVersionId = asString(error.details.latest_artifact_version_id);
  const workflowRunId = asString(error.details.workflow_run_id);
  const route = asString(error.details.route);
  if (!artifactVersionId || !latestArtifactVersionId || !workflowRunId || !route) {
    return null;
  }
  return {
    artifactVersionId,
    latestArtifactVersionId,
    workflowRunId,
    route
  };
}

export function useEditableScheduleArtifactRows(
  contract: WorkpageContract | undefined,
  assignmentSection: WorkpageTableSectionModel | null,
  reserveSection: WorkpageTableSectionModel | null
): {
  assignmentRows: WorkpageTableRow[];
  setAssignmentRows: Dispatch<SetStateAction<WorkpageTableRow[]>>;
  reserveRows: WorkpageTableRow[];
  setReserveRows: Dispatch<SetStateAction<WorkpageTableRow[]>>;
} {
  const [assignmentRows, setAssignmentRows] = useState<WorkpageTableRow[]>([]);
  const [reserveRows, setReserveRows] = useState<WorkpageTableRow[]>([]);
  const lastResetKeyRef = useRef<string | null>(null);
  const resetKey = useMemo(() => {
    if (!contract || !assignmentSection || !reserveSection) {
      return null;
    }
    return [
      contract.freshness.source_version,
      contract.artifact_context?.artifact_version_id ?? "",
      buildTableSectionResetKey(contract, assignmentSection),
      buildTableSectionResetKey(contract, reserveSection)
    ].join(":");
  }, [contract, assignmentSection, reserveSection]);

  useEffect(() => {
    if (!assignmentSection || !reserveSection || !resetKey) {
      lastResetKeyRef.current = null;
      setAssignmentRows([]);
      setReserveRows([]);
      return;
    }
    if (lastResetKeyRef.current === resetKey) {
      return;
    }
    lastResetKeyRef.current = resetKey;
    setAssignmentRows(assignmentSection.rows.map((row) => ({ ...row })));
    setReserveRows(reserveSection.rows.map((row) => ({ ...row })));
  }, [assignmentSection, reserveSection, resetKey]);

  return {
    assignmentRows,
    setAssignmentRows,
    reserveRows,
    setReserveRows
  };
}

export function buildAcceptedRail(contract: WorkpageContract): ScheduleVersionRailDefinition {
  const acceptedSeries = contract.accepted_series;
  const acceptedEntries = acceptedSeries?.entries ?? [];
  const acceptedEntryById = new Map(acceptedEntries.map((entry) => [entry.artifact_version_id, entry]));
  const latestLogicalDate = acceptedSeries?.entries.reduce<string | null>((current, entry) => {
    if (!current || entry.logical_date > current) {
      return entry.logical_date;
    }
    return current;
  }, null);
  const entries: DraftVersionTimelineEntry[] = acceptedEntries.map((entry) => ({
    artifactVersionId: entry.artifact_version_id,
    createdAt: entry.logical_date,
    label:
      entry.artifact_version_id === acceptedSeries?.current_artifact_version_id
        ? "Current accepted"
        : entry.logical_date,
    isCurrent: entry.artifact_version_id === acceptedSeries?.current_artifact_version_id,
    isLatest: entry.logical_date === latestLogicalDate,
    note: `${entry.partition_key} · ${entry.artifact_kind}`,
    testId: `schedule-accepted-history-${entry.artifact_version_id}`,
    to: entry.route
  }));

  return {
    testId: "schedule-accepted-history-rail",
    title: "Accepted history",
    eyebrow: "Accepted series",
    description: "Accepted navigation stays on accepted weekly history only and never traverses draft lineage.",
    emptyText: "No accepted schedule history is available for this surface yet.",
    entries,
    previousRoute:
      acceptedSeries?.previous_artifact_version_id
        ? acceptedEntryById.get(acceptedSeries.previous_artifact_version_id)?.route ?? null
        : null,
    nextRoute:
      acceptedSeries?.next_artifact_version_id
        ? acceptedEntryById.get(acceptedSeries.next_artifact_version_id)?.route ?? null
        : null,
    previousLabel: "Previous accepted",
    nextLabel: "Next accepted"
  };
}

export function buildDraftRail(contract: WorkpageContract): ScheduleVersionRailDefinition {
  const artifactHistory = contract.artifact_history;
  const historyEntries = artifactHistory?.entries ?? [];
  const historyEntryById = new Map(historyEntries.map((entry) => [entry.artifact_version_id, entry]));
  const currentDraftArtifactVersionId = artifactHistory?.current_artifact_version_id ?? "";
  const entries: DraftVersionTimelineEntry[] = historyEntries.map((entry) => ({
    artifactVersionId: entry.artifact_version_id,
    createdAt: entry.created_at,
    label: draftVersionPrimaryLabel(entry.artifact_version_id, {
      currentArtifactVersionId: currentDraftArtifactVersionId,
      previousArtifactVersionId: artifactHistory?.previous_artifact_version_id ?? null
    }),
    isCurrent: entry.artifact_version_id === currentDraftArtifactVersionId,
    isLatest: entry.artifact_version_id === artifactHistory?.latest_artifact_version_id,
    note:
      entry.lineage_note ??
      (entry.supersedes_artifact_version_id
        ? `Supersedes ${entry.supersedes_artifact_version_id}`
        : "Initial schedule draft in this lineage."),
    testId: `schedule-draft-history-${entry.artifact_version_id}`,
    to: entry.route
  }));

  return {
    testId: "schedule-draft-history-rail",
    title: "Draft lineage",
    eyebrow: "Draft rail",
    description: "Draft navigation stays within backend-authored draft lineage for this immutable schedule surface.",
    emptyText: "No draft lineage is available on this surface yet.",
    entries,
    previousRoute:
      artifactHistory?.previous_artifact_version_id
        ? historyEntryById.get(artifactHistory.previous_artifact_version_id)?.route ?? null
        : null,
    nextRoute:
      artifactHistory?.next_artifact_version_id
        ? historyEntryById.get(artifactHistory.next_artifact_version_id)?.route ?? null
        : null,
    previousLabel: "Previous draft",
    nextLabel: artifactHistory?.next_artifact_version_id ? "Next draft" : "Latest draft unavailable"
  };
}

const EMPTY_WORKPAGE_MODEL = {
  sections: []
} as unknown as WorkpageContract["workpage"];

export function useScheduleSections(contract?: WorkpageContract | null) {
  const model = contract?.workpage ?? EMPTY_WORKPAGE_MODEL;
  const summarySection = useMemo(
    () =>
      model.sections.find(
        (section): section is WorkpageSummaryCardsSectionModel => section.kind === "summary_cards"
      ) ?? null,
    [model]
  );
  const noteSection = useMemo(
    () =>
      model.sections.find(
        (section): section is WorkpageNotePanelSectionModel => section.kind === "note_panel"
      ) ?? null,
    [model]
  );
  const historySection = useMemo(
    () =>
      model.sections.find(
        (section): section is WorkpageHistorySectionModel => section.kind === "history_stub"
      ) ?? null,
    [model]
  );
  const heatmapSection = useMemo(() => findHeatmapSection(model.sections), [model]);
  const tableSections = useMemo(
    () =>
      model.sections.filter(
        (section): section is WorkpageTableSectionModel => section.kind === "table"
      ) ?? [],
    [model]
  );
  return {
    summarySection,
    noteSection,
    historySection,
    heatmapSection,
    assignmentSection: findTableSection(tableSections, "assignment_rows"),
    reserveSection: findTableSection(tableSections, "reserve_rows"),
    iterationSection: findTableSection(tableSections, "iteration_deltas")
  };
}
