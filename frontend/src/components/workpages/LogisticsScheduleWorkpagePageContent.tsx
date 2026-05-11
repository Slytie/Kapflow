import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState
} from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { StatePanel } from "@/components/StatePanel";
import {
  DraftVersionTimeline,
  DraftVersionTimelineEntry,
  draftVersionPrimaryLabel
} from "@/components/workpages/DraftVersionTimeline";
import { ScheduleArtifactAdvancedInfo } from "@/components/workpages/ScheduleArtifactAdvancedInfo";
import type {
  ScheduleRouteDemandPendingCell,
  ScheduleSickNoShowTarget
} from "@/components/workpages/ScheduleHeatmapEditor";
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
import { errorText } from "@/lib/api/errorText";
import { isApiClientError } from "@/lib/api/httpClient";
import { workpagesRepository } from "@/lib/repositories";
import type {
  WorkpageContract,
  WorkpagePreviewResponse,
  WorkpageScheduleRouteDemandCoverageRecommendationsResponse
} from "@/lib/types/contracts";
import { invalidateWorkspaceViews } from "@/lib/workspace/queryInvalidation";
import {
  mergeWorkpageActionRef,
  replaceWorkpageActionRefArtifactVersionId,
  resolveWorkpageActionRef
} from "@/lib/workspace/workpageActionRef";
import type {
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageDriverPreferencesAction,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageRouteDemandAction,
  WorkpageScheduleAction,
  WorkpageScheduleHeatmapSection as WorkpageScheduleHeatmapSectionModel,
  WorkpageScheduleRouteDemandCoverageCandidate,
  WorkpageScheduleRouteDemandCoverageCandidateGroup,
  WorkpageScheduleRouteDemandCoverageContext,
  WorkpageScheduleRouteDemandCoverageRecommendations,
  WorkpageScheduleRouteDemandCoverageSelection,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableRow,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";

function findTableSection(
  sections: WorkpageTableSectionModel[],
  tableId: string
): WorkpageTableSectionModel | null {
  return sections.find((section) => section.table_id === tableId) ?? null;
}

function findHeatmapSection(
  sections: WorkpageContract["workpage"]["sections"]
): WorkpageScheduleHeatmapSectionModel | null {
  return (
    sections.find(
      (section): section is WorkpageScheduleHeatmapSectionModel => section.kind === "schedule_heatmap"
    ) ?? null
  );
}

function buildTableSectionResetKey(
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

function scheduleLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/schedule-v0`;
}

function workpageBackRoute(workflowRunId: string): { href: string; label: string } {
  return { href: `/runs/${workflowRunId}`, label: "Back to run detail" };
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function rowsSignature(rows: WorkpageTableRow[]): string {
  return JSON.stringify(rows);
}

function routeDemandCoverageSelectionMap(
  selections: WorkpageScheduleRouteDemandCoverageSelection[]
): Record<string, WorkpageScheduleRouteDemandCoverageSelection> {
  return selections.reduce<Record<string, WorkpageScheduleRouteDemandCoverageSelection>>(
    (accumulator, selection) => {
      accumulator[selection.target_id] = selection;
      return accumulator;
    },
    {}
  );
}

type RouteDemandCoverageDayRow = {
  target: WorkpageScheduleRouteDemandCoverageCandidateGroup["target"];
  candidate: WorkpageScheduleRouteDemandCoverageCandidate;
};

type RouteDemandCoverageDayGroupViewModel = {
  serviceDate: string;
  targetGroups: WorkpageScheduleRouteDemandCoverageCandidateGroup[];
  inlineRows: RouteDemandCoverageDayRow[];
  overflowRows: RouteDemandCoverageDayRow[];
};

type RouteDemandCoverageTargetById = Record<
  string,
  WorkpageScheduleRouteDemandCoverageCandidateGroup["target"]
>;

function coverageCandidateSelectable(
  candidate: WorkpageScheduleRouteDemandCoverageCandidate
): boolean {
  return candidate.selection_state === "selectable" && candidate.hard_filter_status === "pass";
}

function coverageRecommendationReason(
  candidate: WorkpageScheduleRouteDemandCoverageCandidate
): string {
  const reasons: string[] = [];
  if (candidate.assignment_action === "promote_reserve" || candidate.clear_same_day_on_call_reserve) {
    reasons.push("promotes same-day reserve");
  }
  if (candidate.evaluation_kind) {
    reasons.push(candidate.evaluation_kind.replace(/_/g, " "));
  }
  if (candidate.availability_state) {
    reasons.push(`availability ${candidate.availability_state.toLowerCase()}`);
  }
  if (candidate.score_bucket) {
    reasons.push(`score ${candidate.score_bucket.replace(/_/g, " ")}`);
  }
  if (candidate.template_state_preservation_fit > 0) {
    reasons.push(`template fit ${candidate.template_state_preservation_fit.toFixed(2)}`);
  }
  return reasons.length > 0 ? reasons.join(" · ") : "backend-ranked coverage option";
}

function coverageCandidateMatchesSelection(
  candidate: WorkpageScheduleRouteDemandCoverageCandidate,
  selection: WorkpageScheduleRouteDemandCoverageSelection
): boolean {
  return (
    candidate.route_slot_id === selection.route_slot_id && candidate.driver_id === selection.driver_id
  );
}

function buildRouteDemandCoverageTargetById(
  recommendations: WorkpageScheduleRouteDemandCoverageRecommendations | null
): RouteDemandCoverageTargetById {
  if (!recommendations) {
    return {};
  }
  return recommendations.candidate_groups.reduce<RouteDemandCoverageTargetById>((accumulator, group) => {
    accumulator[group.target.target_id] = group.target;
    return accumulator;
  }, {});
}

function routeDemandCoverageGroupHasSelectableSelection(
  group: WorkpageScheduleRouteDemandCoverageCandidateGroup,
  selection: WorkpageScheduleRouteDemandCoverageSelection
): boolean {
  return group.candidates.some(
    (candidate) =>
      coverageCandidateMatchesSelection(candidate, selection) &&
      coverageCandidateSelectable(candidate)
  );
}

function normalizeRouteDemandCoverageSelections(
  recommendations: WorkpageScheduleRouteDemandCoverageRecommendations | null,
  currentSelections: Record<string, WorkpageScheduleRouteDemandCoverageSelection>,
  options: { applyDefaults?: boolean } = {}
): Record<string, WorkpageScheduleRouteDemandCoverageSelection> {
  if (!recommendations) {
    return {};
  }

  const applyDefaults = options.applyDefaults ?? true;
  const defaultsByTarget = routeDemandCoverageSelectionMap(recommendations.selected_defaults);
  const nextSelections: Record<string, WorkpageScheduleRouteDemandCoverageSelection> = {};
  const usedDriverIdsByServiceDate = new Map<string, Set<string>>();

  const tryAssignSelection = (
    group: WorkpageScheduleRouteDemandCoverageCandidateGroup,
    selection: WorkpageScheduleRouteDemandCoverageSelection | null | undefined
  ): boolean => {
    if (!selection || !routeDemandCoverageGroupHasSelectableSelection(group, selection)) {
      return false;
    }
    const serviceDate = group.target.service_date;
    const usedDriverIds = usedDriverIdsByServiceDate.get(serviceDate) ?? new Set<string>();
    if (usedDriverIds.has(selection.driver_id)) {
      return false;
    }
    usedDriverIds.add(selection.driver_id);
    usedDriverIdsByServiceDate.set(serviceDate, usedDriverIds);
    nextSelections[group.target.target_id] = selection;
    return true;
  };

  recommendations.candidate_groups.forEach((group) => {
    tryAssignSelection(group, currentSelections[group.target.target_id]);
  });

  if (!applyDefaults) {
    return nextSelections;
  }

  recommendations.candidate_groups.forEach((group) => {
    if (nextSelections[group.target.target_id]) {
      return;
    }
    tryAssignSelection(group, defaultsByTarget[group.target.target_id]);
  });

  recommendations.candidate_groups.forEach((group) => {
    if (nextSelections[group.target.target_id]) {
      return;
    }
    const fallbackCandidate = group.candidates.find(
      (candidate) =>
        coverageCandidateSelectable(candidate) &&
        !(usedDriverIdsByServiceDate.get(group.target.service_date) ?? new Set<string>()).has(
          candidate.driver_id
        )
    );
    if (!fallbackCandidate) {
      return;
    }
    tryAssignSelection(group, {
      target_id: group.target.target_id,
      route_slot_id: fallbackCandidate.route_slot_id,
      driver_id: fallbackCandidate.driver_id,
      row_kind: "assignment"
    });
  });

  return nextSelections;
}

function routeDemandCoverageSelectionsComplete(
  recommendations: WorkpageScheduleRouteDemandCoverageRecommendations | null,
  selections: Record<string, WorkpageScheduleRouteDemandCoverageSelection>
): boolean {
  if (!recommendations) {
    return false;
  }
  const usedDriverIdsByServiceDate = new Map<string, Set<string>>();
  for (const group of recommendations.candidate_groups) {
    const selection = selections[group.target.target_id];
    if (!selection || !routeDemandCoverageGroupHasSelectableSelection(group, selection)) {
      return false;
    }
    const serviceDate = group.target.service_date;
    const usedDriverIds = usedDriverIdsByServiceDate.get(serviceDate) ?? new Set<string>();
    if (usedDriverIds.has(selection.driver_id)) {
      return false;
    }
    usedDriverIds.add(selection.driver_id);
    usedDriverIdsByServiceDate.set(serviceDate, usedDriverIds);
  }
  return true;
}

function buildRouteDemandCoverageUnresolvedCountsByServiceDate(
  recommendations: WorkpageScheduleRouteDemandCoverageRecommendations | null,
  selections: Record<string, WorkpageScheduleRouteDemandCoverageSelection>
): Record<string, number> {
  if (!recommendations) {
    return {};
  }
  const normalizedSelections = normalizeRouteDemandCoverageSelections(
    recommendations,
    selections,
    { applyDefaults: false }
  );
  return recommendations.candidate_groups.reduce<Record<string, number>>((accumulator, group) => {
    if (normalizedSelections[group.target.target_id]) {
      return accumulator;
    }
    accumulator[group.target.service_date] =
      (accumulator[group.target.service_date] ?? 0) + 1;
    return accumulator;
  }, {});
}

function buildRouteDemandCoverageFallbackCountsByServiceDate(
  context: WorkpageScheduleRouteDemandCoverageContext | null | undefined
): Record<string, number> {
  if (!context) {
    return {};
  }
  if (context.deltas.length > 0) {
    return context.deltas.reduce<Record<string, number>>((accumulator, delta) => {
      if (delta.delta > 0) {
        accumulator[delta.service_date] = delta.delta;
      }
      return accumulator;
    }, {});
  }
  if (context.service_dates.length === 1 && context.added_route_count > 0) {
    return {
      [context.service_dates[0]]: context.added_route_count
    };
  }
  return {};
}

function buildRouteDemandCoveragePendingCells(
  recommendations: WorkpageScheduleRouteDemandCoverageRecommendations | null,
  selections: Record<string, WorkpageScheduleRouteDemandCoverageSelection>
): Record<string, ScheduleRouteDemandPendingCell> {
  if (!recommendations) {
    return {};
  }
  const normalizedSelections = normalizeRouteDemandCoverageSelections(
    recommendations,
    selections,
    { applyDefaults: false }
  );
  const pendingCells: Record<string, ScheduleRouteDemandPendingCell> = {};
  recommendations.candidate_groups.forEach((group) => {
    const selection = normalizedSelections[group.target.target_id];
    if (!selection) {
      return;
    }
    const candidate = group.candidates.find((item) =>
      coverageCandidateMatchesSelection(item, selection)
    );
    if (!candidate) {
      return;
    }
    pendingCells[`${group.target.service_date}:${candidate.driver_id}`] = {
      targetId: group.target.target_id,
      routeId: group.target.route_id,
      driverId: candidate.driver_id,
      driverName: candidate.driver_name,
      serviceDate: group.target.service_date,
      projectedMinutes: candidate.projected_minutes ?? null
    };
  });
  return pendingCells;
}

function selectRouteDemandCoverageHeatmapCell(
  recommendations: WorkpageScheduleRouteDemandCoverageRecommendations | null,
  currentSelections: Record<string, WorkpageScheduleRouteDemandCoverageSelection>,
  targetById: RouteDemandCoverageTargetById,
  options: {
    serviceDate: string;
    driverId: string;
  }
): {
  nextSelections: Record<string, WorkpageScheduleRouteDemandCoverageSelection>;
  message: string;
} {
  const { serviceDate, driverId } = options;
  if (!recommendations) {
    return {
      nextSelections: {},
      message: "Route-demand recovery is unavailable for this draft."
    };
  }
  const normalizedSelections = normalizeRouteDemandCoverageSelections(
    recommendations,
    currentSelections,
    { applyDefaults: false }
  );
  const pendingCells = buildRouteDemandCoveragePendingCells(recommendations, normalizedSelections);
  const activePendingCell = pendingCells[`${serviceDate}:${driverId}`];
  if (activePendingCell) {
    const nextSelections = { ...normalizedSelections };
    delete nextSelections[activePendingCell.targetId];
    return {
      nextSelections,
      message: `Pending route add cleared for ${activePendingCell.routeId}.`
    };
  }
  for (const group of recommendations.candidate_groups) {
    if (group.target.service_date !== serviceDate) {
      continue;
    }
    if (normalizedSelections[group.target.target_id]) {
      continue;
    }
    const candidate = group.candidates.find(
      (item) =>
        item.driver_id === driverId &&
        coverageCandidateSelectable(item) &&
        !coverageCandidateLocalConflictReason(
          item,
          group.target,
          normalizedSelections,
          targetById
        )
    );
    if (!candidate) {
      continue;
    }
    return {
      nextSelections: {
        ...normalizedSelections,
        [group.target.target_id]: {
          target_id: group.target.target_id,
          route_slot_id: candidate.route_slot_id,
          driver_id: candidate.driver_id,
          row_kind: "assignment"
        }
      },
      message: `Pending route add selected for ${group.target.route_id}.`
    };
  }
  return {
    nextSelections: normalizedSelections,
    message: `No uncovered added route is available for that driver on ${serviceDate}.`
  };
}

function coverageCandidateLocalConflictReason(
  candidate: WorkpageScheduleRouteDemandCoverageCandidate,
  target: WorkpageScheduleRouteDemandCoverageCandidateGroup["target"],
  selections: Record<string, WorkpageScheduleRouteDemandCoverageSelection>,
  targetById: RouteDemandCoverageTargetById
): string | null {
  for (const [otherTargetId, selection] of Object.entries(selections)) {
    if (otherTargetId === target.target_id) {
      continue;
    }
    const otherTarget = targetById[otherTargetId];
    if (!otherTarget || otherTarget.service_date !== target.service_date) {
      continue;
    }
    if (selection.driver_id !== candidate.driver_id) {
      continue;
    }
    return `Already selected for ${otherTarget.route_id}`;
  }
  return null;
}

function resolveRouteDemandCoverageInlineCandidate(
  group: WorkpageScheduleRouteDemandCoverageCandidateGroup,
  selections: Record<string, WorkpageScheduleRouteDemandCoverageSelection>
): WorkpageScheduleRouteDemandCoverageCandidate | null {
  const currentSelection = selections[group.target.target_id];
  if (currentSelection) {
    const selectedCandidate = group.candidates.find((candidate) =>
      coverageCandidateMatchesSelection(candidate, currentSelection)
    );
    if (selectedCandidate) {
      return selectedCandidate;
    }
  }

  return group.candidates[0] ?? null;
}

function buildRouteDemandCoverageDayGroups(
  recommendations: WorkpageScheduleRouteDemandCoverageRecommendations | null,
  selections: Record<string, WorkpageScheduleRouteDemandCoverageSelection>
): RouteDemandCoverageDayGroupViewModel[] {
  if (!recommendations) {
    return [];
  }
  const groupsByServiceDate = new Map<string, RouteDemandCoverageDayGroupViewModel>();

  recommendations.candidate_groups.forEach((group) => {
    const serviceDate = group.target.service_date;
    let dayGroup = groupsByServiceDate.get(serviceDate);
    if (!dayGroup) {
      dayGroup = {
        serviceDate,
        targetGroups: [],
        inlineRows: [],
        overflowRows: []
      };
      groupsByServiceDate.set(serviceDate, dayGroup);
    }

    dayGroup.targetGroups.push(group);
    const inlineCandidate = resolveRouteDemandCoverageInlineCandidate(group, selections);
    if (inlineCandidate) {
      dayGroup.inlineRows.push({
        target: group.target,
        candidate: inlineCandidate
      });
    }

    group.candidates.forEach((candidate) => {
      if (
        inlineCandidate &&
        coverageCandidateMatchesSelection(candidate, {
          target_id: group.target.target_id,
          route_slot_id: inlineCandidate.route_slot_id,
          driver_id: inlineCandidate.driver_id,
          row_kind: "assignment"
        })
      ) {
        return;
      }
      dayGroup.overflowRows.push({
        target: group.target,
        candidate
      });
    });
  });

  return Array.from(groupsByServiceDate.values());
}

function coverageCandidateStateSummary(
  candidate: WorkpageScheduleRouteDemandCoverageCandidate,
  localConflictReason: string | null = null
): string {
  if (localConflictReason) {
    return `${candidate.availability_state || "UNKNOWN"} · taken`;
  }
  return `${candidate.availability_state || "UNKNOWN"} · ${
    candidate.hard_filter_status === "pass" ? "pass" : "blocked"
  }`;
}

function coverageCandidateLoadSummary(
  candidate: WorkpageScheduleRouteDemandCoverageCandidate
): string {
  return `${candidate.current_week_shift_count} wk · ${candidate.projected_rolling7_minutes} r7 · ${candidate.remaining_rolling7_minutes} rem`;
}

function coverageCandidateReserveSummary(
  candidate: WorkpageScheduleRouteDemandCoverageCandidate
): string {
  return candidate.clear_same_day_on_call_reserve ? "Consumes reserve" : "—";
}

function coverageCandidateScoreSummary(
  candidate: WorkpageScheduleRouteDemandCoverageCandidate,
  localConflictReason: string | null = null
): string {
  if (localConflictReason) {
    return localConflictReason;
  }
  if (coverageCandidateSelectable(candidate)) {
    return candidate.soft_score_total.toFixed(2);
  }
  return candidate.hard_filter_reasons.join(", ") || candidate.hard_filter_status;
}

function coverageOverflowSummaryLabel(
  rows: RouteDemandCoverageDayRow[]
): string {
  const blockedCount = rows.filter((row) => !coverageCandidateSelectable(row.candidate)).length;
  const routeCount = new Set(rows.map((row) => row.target.target_id)).size;
  const routeLabel = routeCount === 1 ? "route" : "routes";
  if (blockedCount > 0) {
    return `Show ${rows.length} more options across ${routeCount} ${routeLabel} (${blockedCount} blocked)`;
  }
  return `Show ${rows.length} more options across ${routeCount} ${routeLabel}`;
}

function coverageDayDeltaSummary(
  serviceDate: string,
  context: WorkpageScheduleRouteDemandCoverageContext | null
): string | null {
  const delta = context?.deltas?.find((candidate) => candidate.service_date === serviceDate);
  if (!delta) {
    return null;
  }
  return `${delta.previous_planned_route_count} -> ${delta.planned_route_count} (${
    delta.delta >= 0 ? "+" : ""
  }${delta.delta})`;
}

function findScheduleAction(
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

function findRouteDemandAction(
  contract: WorkpageContract | undefined
): WorkpageRouteDemandAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageRouteDemandAction =>
        action.workpage_kind === "route-demand-v0"
    ) ?? null
  );
}

function findDriverPreferencesAction(
  contract: WorkpageContract | undefined
): WorkpageDriverPreferencesAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageDriverPreferencesAction =>
        action.workpage_kind === "driver-preferences-v0"
    ) ?? null
  );
}

function workpageConflictDetails(error: unknown): {
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

function useEditableScheduleArtifactRows(
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

function buildAcceptedRail(contract: WorkpageContract): ScheduleVersionRailDefinition {
  const acceptedSeries = contract.accepted_series;
  const acceptedEntries = acceptedSeries?.entries ?? [];
  const acceptedEntryById = new Map(acceptedEntries.map((entry) => [entry.artifact_version_id, entry]));
  const latestLogicalDate = acceptedSeries?.entries.reduce<string | null>((current, entry) => {
    if (!current || entry.logical_date > current) {
      return entry.logical_date;
    }
    return current;
  }, null);
  const entries: DraftVersionTimelineEntry[] = (acceptedSeries?.entries ?? []).map((entry) => ({
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

function buildDraftRail(contract: WorkpageContract): ScheduleVersionRailDefinition {
  const artifactHistory = contract.artifact_history;
  const historyEntries = artifactHistory?.entries ?? [];
  const historyEntryById = new Map(historyEntries.map((entry) => [entry.artifact_version_id, entry]));
  const currentDraftArtifactVersionId = artifactHistory?.current_artifact_version_id ?? "";
  const entries: DraftVersionTimelineEntry[] = historyEntries.map((entry) => {
    return {
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
    };
  });

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

function ScheduleDraftHistoryDialog({
  rail,
  onClose
}: {
  rail: ScheduleVersionRailDefinition;
  onClose: () => void;
}): JSX.Element {
  const titleId = useId();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div
      className="schedule-draft-history-dialog-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className="schedule-draft-history-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="schedule-draft-history-dialog__header">
          <div>
            <p className="timeline-page__eyebrow">{rail.eyebrow}</p>
            <h2 id={titleId}>{rail.title}</h2>
          </div>
          <button type="button" className="action-btn" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="schedule-draft-history-dialog__body">
          <p className="schedule-draft-history-dialog__description">{rail.description}</p>
          <div className="schedule-version-rail__controls">
            {rail.previousRoute ? (
              <Link className="link-button" to={rail.previousRoute}>
                {rail.previousLabel ?? "Previous"}
              </Link>
            ) : (
              <span className="schedule-version-rail__hint" aria-disabled="true">
                {rail.previousLabel ?? "Previous unavailable"}
              </span>
            )}
            {rail.nextRoute ? (
              <Link className="link-button" to={rail.nextRoute}>
                {rail.nextLabel ?? "Next"}
              </Link>
            ) : (
              <span className="schedule-version-rail__hint" aria-disabled="true">
                {rail.nextLabel ?? "Next unavailable"}
              </span>
            )}
          </div>
          {rail.entries.length > 0 ? (
            <DraftVersionTimeline ariaLabel={rail.title} entries={rail.entries} />
          ) : (
            <p className="workpage-history__empty">{rail.emptyText}</p>
          )}
        </div>
      </section>
    </div>
  );
}

const EMPTY_WORKPAGE_MODEL = {
  sections: []
} as unknown as WorkpageContract["workpage"];

function useScheduleSections(contract?: WorkpageContract | null) {
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
  showHero?: boolean;
  stickyTitleBar?: boolean;
  preContent?: ReactNode;
  onRefresh: () => void;
  isRefreshing: boolean;
  routeDemandUnresolvedCountsByServiceDate?: Record<string, number>;
}

function LogisticsScheduleWorkpageView({
  contract,
  sourceDescription,
  summaryLabel,
  testId,
  backLink,
  backLabel,
  heroTitleActions,
  heroSupportText,
  heroActions,
  showHero = true,
  stickyTitleBar = false,
  preContent,
  onRefresh,
  isRefreshing,
  routeDemandUnresolvedCountsByServiceDate = {}
}: LogisticsScheduleWorkpageViewProps): JSX.Element {
  const { summarySection, noteSection, historySection, heatmapSection, assignmentSection, reserveSection } =
    useScheduleSections(contract);
  const versionRails = useMemo(
    () => [buildAcceptedRail(contract), buildDraftRail(contract)],
    [contract]
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
      showHero={showHero}
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
        versionRails={versionRails}
        readOnly
        routeDemandUnresolvedCountsByServiceDate={routeDemandUnresolvedCountsByServiceDate}
      />
    </WorkpageFrame>
  );
}

export function ScheduleQuickEditModal({
  workflowRunId,
  targetArtifactVersionId = null,
  routeDemandCoverageContext = null,
  onClose
}: {
  workflowRunId: string;
  targetArtifactVersionId?: string | null;
  routeDemandCoverageContext?: WorkpageScheduleRouteDemandCoverageContext | null;
  onClose: () => void;
}): JSX.Element {
  const titleId = useId();
  const descriptionId = useId();
  const query = useQuery({
    queryKey: ["workpages", "schedule-v0", "landing", workflowRunId],
    queryFn: () => workpagesRepository.scheduleForRun(workflowRunId),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const openLatestDraftAction = findScheduleAction(
    query.data,
    (action) =>
      action.kind === "open_latest_draft" &&
      action.state === "available" &&
      Boolean(action.artifact_version_id)
  );
  const artifactVersionId = openLatestDraftAction?.artifact_version_id ?? null;
  const [activeArtifactVersionId, setActiveArtifactVersionId] = useState<string | null>(null);
  useEffect(() => {
    if (targetArtifactVersionId) {
      return;
    }
    if (artifactVersionId && !activeArtifactVersionId) {
      setActiveArtifactVersionId(artifactVersionId);
    }
  }, [activeArtifactVersionId, artifactVersionId, targetArtifactVersionId]);
  useEffect(() => {
    setActiveArtifactVersionId(targetArtifactVersionId ?? null);
  }, [workflowRunId, targetArtifactVersionId]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        if (document.querySelector(".schedule-draft-history-dialog")) {
          return;
        }
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div
      className="quick-edit-backdrop route-demand-quick-edit-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className="quick-edit-modal route-demand-quick-edit-modal schedule-quick-edit-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <header className="quick-edit-modal__header route-demand-quick-edit-modal__header">
          <div>
            <p className="timeline-page__eyebrow">Quick edit</p>
            <h2 id={titleId}>Edit Weekly Schedule</h2>
            <p id={descriptionId}>
              Fine-tune route assignments and on-call coverage without leaving the weekly planning view.
            </p>
          </div>
          <button type="button" className="action-btn" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="quick-edit-modal__body route-demand-quick-edit-modal__body">
          {activeArtifactVersionId ? (
            <ScheduleArtifactEditor
              workflowRunId={workflowRunId}
              artifactVersionId={activeArtifactVersionId}
              layout="embedded"
              afterSave="close"
              onClose={onClose}
              enableSickNoShow
              onArtifactVersionChange={setActiveArtifactVersionId}
              routeDemandCoverageContext={routeDemandCoverageContext}
            />
          ) : query.isLoading ? (
            <StatePanel
              kind="loading"
              title="Loading weekly schedule editor"
              detail="Resolving the latest editable schedule draft for this weekly run."
            />
          ) : query.isError ? (
            <StatePanel
              kind="error"
              title="Weekly schedule editor failed to load"
              detail={errorText(query.error, "Unable to resolve the latest schedule draft.")}
              onRetry={() => {
                void query.refetch();
              }}
            />
          ) : (
            <StatePanel
              kind="error"
              title="Weekly schedule editor is unavailable"
              detail="No editable schedule draft is available for this weekly run yet."
            />
          )}
        </div>
      </section>
    </div>
  );
}

export function LogisticsScheduleArtifactWorkpagePage(): JSX.Element {
  const { artifactVersionId, workflowRunId } = useParams<{
    artifactVersionId: string;
    workflowRunId: string;
  }>();

  if (!workflowRunId) {
    return (
      <StatePanel
        kind="error"
        title="Schedule draft route is unavailable"
        detail="Open schedule drafts from a canonical workflow-run route."
      />
    );
  }

  if (!artifactVersionId) {
    return (
      <StatePanel
        kind="error"
        title="Schedule draft route is incomplete"
        detail="An artifact version id is required for schedule draft workpages."
      />
    );
  }

  return (
    <ScheduleArtifactEditor
      workflowRunId={workflowRunId}
      artifactVersionId={artifactVersionId}
    />
  );
}

export function LogisticsScheduleWorkpagePage(): JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { workflowRunId } = useParams<{ workflowRunId: string }>();
  if (!workflowRunId) {
    return (
      <StatePanel
        kind="error"
        title="Schedule workpage route is unavailable"
        detail="Open schedule workpages from a canonical workflow-run route."
      />
    );
  }
  const query = useQuery({
    queryKey: ["workpages", "schedule-v0", "landing", workflowRunId],
    queryFn: () => workpagesRepository.scheduleForRun(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const { assignmentSection, reserveSection } = useScheduleSections(query.data);
  const runCoverageContext = query.data?.route_demand_coverage_context ?? null;
  const runCoverageRecommendationsQuery = useQuery({
    queryKey: [
      "workpages",
      "schedule-v0",
      "landing",
      workflowRunId,
      "route-demand-coverage",
      runCoverageContext?.schedule_artifact_version_id ?? null,
      runCoverageContext?.route_demand_artifact_version_id ?? null,
      rowsSignature(assignmentSection?.rows ?? []),
      rowsSignature(reserveSection?.rows ?? [])
    ],
    enabled: Boolean(runCoverageContext),
    queryFn: () =>
      workpagesRepository.getScheduleRouteDemandCoverageCandidatesAtPath(
        runCoverageContext?.coverage_candidates_path ?? "",
        {
          routeDemandArtifactVersionId:
            runCoverageContext?.route_demand_artifact_version_id ?? "",
          serviceDates: runCoverageContext?.service_dates ?? [],
          rows: assignmentSection?.rows ?? [],
          reserveRows: reserveSection?.rows ?? [],
          maxCandidates: 8
        }
      )
  });
  const createDriverPreferencesMutation = useMutation({
    mutationFn: (payload: { createPath: string; actionRef: WorkpageDriverPreferencesAction["action_ref"] }) =>
      workpagesRepository.createWorkpage(payload.createPath, payload.actionRef ?? undefined),
    onSuccess: (created, payload) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void invalidateWorkspaceViews(queryClient, created.workflow_run_id);
      navigate(created.route, {
        state: {
          workpageActionRef: replaceWorkpageActionRefArtifactVersionId(
            payload.actionRef ?? null,
            created.artifact_version_id
          )
        }
      });
    }
  });

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading schedule workpage"
        detail="Fetching the workflow-run-backed schedule workpage."
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <StatePanel
        kind="error"
        title="Schedule workpage failed to load"
        detail={errorText(query.error, "Unable to load the workflow-run-backed schedule workpage.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const openLatestDraftAction = findScheduleAction(
    query.data,
    (action) => action.kind === "open_latest_draft"
  );
  const routeDemandAction = findRouteDemandAction(query.data);
  const driverPreferencesAction = findDriverPreferencesAction(query.data);
  const backRoute = workpageBackRoute(workflowRunId);
  const editableDraftRoute =
    openLatestDraftAction?.state === "available" ? openLatestDraftAction.route : null;
  const runCoverageRecommendations =
    runCoverageRecommendationsQuery.data?.route_demand_coverage_recommendations ?? null;
  const runCoverageUnresolvedCountsByServiceDate =
    runCoverageRecommendations
      ? buildRouteDemandCoverageUnresolvedCountsByServiceDate(runCoverageRecommendations, {})
      : buildRouteDemandCoverageFallbackCountsByServiceDate(runCoverageContext);
  const runCoverageUnresolvedCount = Object.values(runCoverageUnresolvedCountsByServiceDate).reduce(
    (total, count) => total + count,
    0
  );
  const runCoverageCallout = runCoverageContext ? (
    runCoverageRecommendationsQuery.isError ? (
      <StatePanel
        kind="error"
        title="Uncovered route recovery failed"
        detail={errorText(
          runCoverageRecommendationsQuery.error,
          "Unable to load uncovered route additions for the latest draft."
        )}
      />
    ) : runCoverageRecommendationsQuery.isLoading && !runCoverageRecommendations ? (
      <StatePanel
        kind="loading"
        title="Loading uncovered route recovery"
        detail="Checking whether the latest route-demand changes still need driver coverage in the current draft."
      />
    ) : runCoverageUnresolvedCount > 0 ? (
      <section
        className="workpage-panel workpage-panel--callout"
        data-testid="schedule-route-demand-recovery-callout"
      >
        <header className="workpage-panel__header">
          <h2>Uncovered route additions</h2>
          <p>
            {runCoverageUnresolvedCount} added{" "}
            {runCoverageUnresolvedCount === 1 ? "route is" : "routes are"} still
            uncovered in the latest schedule draft for{" "}
            {(runCoverageContext.service_dates ?? []).join(", ")}.
          </p>
        </header>
        {editableDraftRoute ? (
          <div className="action-cluster">
            <Link className="link-button" to={editableDraftRoute}>
              Open editable draft
            </Link>
          </div>
        ) : null}
      </section>
    ) : null
  ) : null;

  return (
    <LogisticsScheduleWorkpageView
      contract={query.data}
      testId="schedule-workpage-page"
      sourceDescription="Workflow-run-backed schedule projection served from canonical weekly Stage04 source artifacts."
      summaryLabel="Run-backed review"
      backLink={backRoute.href}
      backLabel={backRoute.label}
      preContent={runCoverageCallout}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching}
      routeDemandUnresolvedCountsByServiceDate={runCoverageUnresolvedCountsByServiceDate}
      showHero={false}
      heroTitleActions={
        editableDraftRoute || routeDemandAction?.route || driverPreferencesAction?.route || driverPreferencesAction?.create_path ? (
          <>
            {editableDraftRoute ? (
              <Link className="action-btn action-btn--hero" to={editableDraftRoute}>
                Open editable draft
              </Link>
            ) : null}
            {routeDemandAction?.route ? (
              <Link className="action-btn action-btn--ghost" to={routeDemandAction.route}>
                Open route demand
              </Link>
            ) : null}
            {driverPreferencesAction?.route ? (
              <Link className="action-btn action-btn--ghost" to={driverPreferencesAction.route}>
                Open driver preferences
              </Link>
            ) : driverPreferencesAction?.create_path ? (
              <button
                type="button"
                className="action-btn action-btn--ghost"
                disabled={createDriverPreferencesMutation.isPending}
                onClick={() =>
                  createDriverPreferencesMutation.mutate({
                    createPath: driverPreferencesAction.create_path ?? "",
                    actionRef: driverPreferencesAction.action_ref
                  })
                }
              >
                {createDriverPreferencesMutation.isPending
                  ? "Creating preferences snapshot..."
                  : "Create preferences snapshot"}
              </button>
            ) : null}
          </>
        ) : undefined
      }
      heroSupportText={
        editableDraftRoute
          ? "This landing page stays read-only. Open the backend-selected latest draft when you need live preview and save controls."
          : "This landing page stays read-only. The Stage04 draft weekly schedule artifact is not available for this run yet."
      }
    />
  );
}

interface ScheduleArtifactEditorProps {
  workflowRunId: string;
  artifactVersionId: string;
  layout?: "page" | "embedded";
  afterSave?: "navigate" | "close";
  onClose?: () => void;
  enableSickNoShow?: boolean;
  onArtifactVersionChange?: (artifactVersionId: string) => void;
  routeDemandCoverageContext?: WorkpageScheduleRouteDemandCoverageContext | null;
}

interface PendingRouteDemandCoverageIntent {
  driverId: string;
  serviceDate: string;
}

function ScheduleArtifactEditor({
  workflowRunId,
  artifactVersionId,
  layout = "page",
  afterSave = "navigate",
  onClose,
  enableSickNoShow = false,
  onArtifactVersionChange,
  routeDemandCoverageContext = null
}: ScheduleArtifactEditorProps): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const previewRequestSequenceRef = useRef(0);
  const sickNoShowTitleId = useId();
  const sickNoShowDescriptionId = useId();
  const [previewResponse, setPreviewResponse] =
    useState<WorkpagePreviewResponse["preview"] | null>(null);
  const [previewErrorMessage, setPreviewErrorMessage] = useState<string | null>(null);
  const [isPreviewPending, setIsPreviewPending] = useState(false);
  const [isDraftHistoryOpen, setIsDraftHistoryOpen] = useState(false);
  const [sickNoShowTarget, setSickNoShowTarget] =
    useState<ScheduleSickNoShowTarget | null>(null);
  const [sickNoShowReasonNote, setSickNoShowReasonNote] = useState("");
  const routeDemandCoverageRequestSequenceRef = useRef(0);
  const [
    routeDemandCoverageRecommendations,
    setRouteDemandCoverageRecommendations
  ] = useState<WorkpageScheduleRouteDemandCoverageRecommendations | null>(null);
  const [routeDemandCoverageErrorMessage, setRouteDemandCoverageErrorMessage] =
    useState<string | null>(null);
  const [isRouteDemandCoveragePending, setIsRouteDemandCoveragePending] = useState(false);
  const [routeDemandCoverageSelections, setRouteDemandCoverageSelections] = useState<
    Record<string, WorkpageScheduleRouteDemandCoverageSelection>
  >({});
  const [routeDemandCoveragePendingIntent, setRouteDemandCoveragePendingIntent] =
    useState<PendingRouteDemandCoverageIntent | null>(null);
  const [routeDemandCoverageOverflowOpen, setRouteDemandCoverageOverflowOpen] = useState<
    Record<string, boolean>
  >({});
  const query = useQuery({
    queryKey: ["workpages", "schedule-v0", "artifacts", workflowRunId, artifactVersionId],
    queryFn: () => workpagesRepository.scheduleArtifact(workflowRunId, artifactVersionId),
    enabled: Boolean(artifactVersionId && workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const contract = query.data;
  const artifactWorkflowRunId = workflowRunId;

  const {
    summarySection,
    noteSection,
    historySection,
    heatmapSection,
    assignmentSection,
    reserveSection,
    iterationSection
  } = useScheduleSections(contract);

  const { assignmentRows, setAssignmentRows, reserveRows, setReserveRows } =
    useEditableScheduleArtifactRows(contract, assignmentSection, reserveSection);
  const previewAction = findScheduleAction(
    contract,
    (action) => action.kind === "preview_recalc" || action.action_id === "workpage.schedule-v0.preview_recalc"
  );
  const saveAction = findScheduleAction(
    contract,
    (action) => action.kind === "submit_artifact" || action.action_id === "workpage.schedule-v0.save_draft"
  );
  const sickNoShowAction = findScheduleAction(
    contract,
    (action) =>
      action.kind === "mark_sick_no_show" ||
      action.action_id === "workpage.schedule-v0.mark_sick_no_show"
  );
  const routeDemandAction = findRouteDemandAction(contract);
  const driverPreferencesAction = findDriverPreferencesAction(contract);
  const baseAssignmentSignature = useMemo(
    () => rowsSignature(assignmentSection?.rows ?? []),
    [assignmentSection]
  );
  const baseReserveSignature = useMemo(
    () => rowsSignature(reserveSection?.rows ?? []),
    [reserveSection]
  );
  const assignmentSignature = useMemo(() => rowsSignature(assignmentRows), [assignmentRows]);
  const reserveSignature = useMemo(() => rowsSignature(reserveRows), [reserveRows]);
  const hasUnsavedEdits =
    assignmentSignature !== baseAssignmentSignature || reserveSignature !== baseReserveSignature;
  const explicitRouteDemandCoverageContext =
    routeDemandCoverageContext &&
    routeDemandCoverageContext.schedule_artifact_version_id === artifactVersionId
      ? routeDemandCoverageContext
      : null;
  const contractRouteDemandCoverageContext =
    contract?.route_demand_coverage_context &&
    contract.route_demand_coverage_context.schedule_artifact_version_id === artifactVersionId
      ? contract.route_demand_coverage_context
      : null;
  const activeRouteDemandCoverageContext =
    explicitRouteDemandCoverageContext ?? contractRouteDemandCoverageContext;
  const routeDemandCoverageMode =
    explicitRouteDemandCoverageContext
      ? "explicit"
      : contractRouteDemandCoverageContext
        ? "recovery"
        : null;
  const routeDemandCoverageTargetById = useMemo(
    () => buildRouteDemandCoverageTargetById(routeDemandCoverageRecommendations),
    [routeDemandCoverageRecommendations]
  );
  const routeDemandCoverageDayGroups = useMemo(
    () =>
      buildRouteDemandCoverageDayGroups(
        routeDemandCoverageRecommendations,
        routeDemandCoverageSelections
      ),
    [routeDemandCoverageRecommendations, routeDemandCoverageSelections]
  );
  const routeDemandCoverageUnresolvedCountsByServiceDate = useMemo(
    () =>
      routeDemandCoverageRecommendations
        ? buildRouteDemandCoverageUnresolvedCountsByServiceDate(
            routeDemandCoverageRecommendations,
            routeDemandCoverageSelections
          )
        : buildRouteDemandCoverageFallbackCountsByServiceDate(activeRouteDemandCoverageContext),
    [
      activeRouteDemandCoverageContext,
      routeDemandCoverageRecommendations,
      routeDemandCoverageSelections
    ]
  );
  const routeDemandCoveragePendingCells = useMemo(
    () =>
      buildRouteDemandCoveragePendingCells(
        routeDemandCoverageRecommendations,
        routeDemandCoverageSelections
      ),
    [routeDemandCoverageRecommendations, routeDemandCoverageSelections]
  );
  const submitMutation = useMutation({
    mutationFn: () => {
      const carriedActionRef = resolveWorkpageActionRef(location.state, {
        workflowRunId: artifactWorkflowRunId,
        workpageKind: "schedule-v0",
        artifactVersionId
      });
      const actionRef = mergeWorkpageActionRef(
        saveAction?.action_ref ?? null,
        carriedActionRef ?? null
      );
      if (saveAction?.submit_path) {
        return workpagesRepository.submitScheduleArtifactAtPath(
          saveAction.submit_path,
          artifactVersionId,
          {
            rows: assignmentRows,
            reserveRows
          },
          actionRef
        );
      }
      return workpagesRepository.submitScheduleArtifact(
        artifactWorkflowRunId,
        artifactVersionId,
        {
          rows: assignmentRows,
          reserveRows
        },
        actionRef
      );
    },
    onSuccess: (submitted) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void queryClient.invalidateQueries({ queryKey: ["logistics-demo-story"] });
      void invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
      if (afterSave === "close") {
        onClose?.();
        return;
      }
      const carriedActionRef = resolveWorkpageActionRef(location.state, {
        workflowRunId: artifactWorkflowRunId,
        workpageKind: "schedule-v0",
        artifactVersionId
      });
      navigate(submitted.route, {
        state: {
          workpageActionRef: replaceWorkpageActionRefArtifactVersionId(
            mergeWorkpageActionRef(saveAction?.action_ref ?? null, carriedActionRef ?? null),
            submitted.artifact_version_id
          )
        }
      });
    }
  });
  const routeDemandCoverageApplyMutation = useMutation({
    mutationFn: () => {
      if (!activeRouteDemandCoverageContext) {
        throw new Error("Route-demand coverage context is unavailable for this draft.");
      }
      return workpagesRepository.applyScheduleRouteDemandCoverageAtPath(
        activeRouteDemandCoverageContext.coverage_apply_path,
        artifactVersionId,
        {
          routeDemandArtifactVersionId:
            activeRouteDemandCoverageContext.route_demand_artifact_version_id,
          serviceDates: activeRouteDemandCoverageContext.service_dates,
          rows: assignmentRows,
          reserveRows,
          selections: Object.values(routeDemandCoverageSelections).map((selection) => ({
            target_id: selection.target_id,
            route_slot_id: selection.route_slot_id,
            driver_id: selection.driver_id,
            row_kind: selection.row_kind
          })),
          maxCandidates: routeDemandCoverageRecommendations?.max_candidates ?? 8
        }
      );
    },
    onSuccess: (submitted) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void queryClient.invalidateQueries({ queryKey: ["logistics-demo-story"] });
      void invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
      setRouteDemandCoverageRecommendations(null);
      setRouteDemandCoverageErrorMessage(null);
      setRouteDemandCoverageSelections({});
      setRouteDemandCoverageOverflowOpen({});
      onArtifactVersionChange?.(submitted.artifact_version_id);
      if (!onArtifactVersionChange && layout === "page") {
        navigate(submitted.route);
      }
    }
  });
  const sickNoShowMutation = useMutation({
    mutationFn: (target: ScheduleSickNoShowTarget) => {
      if (!sickNoShowAction?.sick_no_show_path || sickNoShowAction.state !== "available") {
        throw new Error(
          sickNoShowAction?.disabled_reason || "Sick / No Show is unavailable for this draft."
        );
      }
      return workpagesRepository.markScheduleSickNoShowAtPath(
        sickNoShowAction.sick_no_show_path,
        artifactVersionId,
        {
          driverId: target.driverId,
          serviceDate: target.serviceDate,
          reasonNote: sickNoShowReasonNote,
          rows: assignmentRows,
          reserveRows
        },
        sickNoShowAction.action_ref ?? undefined
      );
    },
    onSuccess: (submitted) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void queryClient.invalidateQueries({ queryKey: ["logistics-demo-story"] });
      void invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
      setSickNoShowTarget(null);
      setSickNoShowReasonNote("");
      onArtifactVersionChange?.(submitted.artifact_version_id);
      if (!onArtifactVersionChange && layout === "page") {
        navigate(submitted.route);
      }
    }
  });
  const downloadMutation = useMutation({
    mutationFn: (currentArtifactVersionId: string) =>
      workpagesRepository.downloadScheduleArtifactJson(currentArtifactVersionId)
  });
  const createDriverPreferencesMutation = useMutation({
    mutationFn: (payload: { createPath: string; actionRef: WorkpageDriverPreferencesAction["action_ref"] }) =>
      workpagesRepository.createWorkpage(payload.createPath, payload.actionRef ?? undefined),
    onSuccess: (created, payload) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void invalidateWorkspaceViews(queryClient, created.workflow_run_id);
      navigate(created.route, {
        state: {
          workpageActionRef: replaceWorkpageActionRefArtifactVersionId(
            payload.actionRef ?? null,
            created.artifact_version_id
          )
        }
      });
    }
  });

  useEffect(() => {
    setPreviewResponse(null);
    setPreviewErrorMessage(null);
    setIsPreviewPending(false);
    setSickNoShowTarget(null);
    setSickNoShowReasonNote("");
    previewRequestSequenceRef.current += 1;
    routeDemandCoverageRequestSequenceRef.current += 1;
    setRouteDemandCoverageRecommendations(null);
    setRouteDemandCoverageErrorMessage(null);
    setIsRouteDemandCoveragePending(false);
    setRouteDemandCoverageSelections({});
    setRouteDemandCoveragePendingIntent(null);
    setRouteDemandCoverageOverflowOpen({});
  }, [artifactVersionId]);

  useEffect(() => {
    if (!activeRouteDemandCoverageContext) {
      routeDemandCoverageRequestSequenceRef.current += 1;
      setRouteDemandCoverageRecommendations(null);
      setRouteDemandCoverageErrorMessage(null);
      setIsRouteDemandCoveragePending(false);
      setRouteDemandCoverageSelections({});
      setRouteDemandCoveragePendingIntent(null);
      setRouteDemandCoverageOverflowOpen({});
    }
  }, [activeRouteDemandCoverageContext]);

  useEffect(() => {
    if (!routeDemandCoverageDayGroups.length) {
      setRouteDemandCoverageOverflowOpen({});
      return;
    }
    setRouteDemandCoverageOverflowOpen((current) => {
      const next = { ...current };
      const validServiceDates = new Set(
        routeDemandCoverageDayGroups
          .filter((group) => group.overflowRows.length > 0)
          .map((group) => group.serviceDate)
      );

      Object.keys(next).forEach((serviceDate) => {
        if (!validServiceDates.has(serviceDate)) {
          delete next[serviceDate];
        }
      });

      const currentKeys = Object.keys(current);
      const nextKeys = Object.keys(next);
      const changed =
        currentKeys.length !== nextKeys.length ||
        nextKeys.some((key) => current[key] !== next[key]);
      return changed ? next : current;
    });
  }, [routeDemandCoverageDayGroups]);

  useEffect(() => {
    if (!activeRouteDemandCoverageContext) {
      return;
    }
    routeDemandCoverageRequestSequenceRef.current += 1;
    const requestToken = routeDemandCoverageRequestSequenceRef.current;
    const timer = window.setTimeout(() => {
      setIsRouteDemandCoveragePending(true);
      void workpagesRepository
        .getScheduleRouteDemandCoverageCandidatesAtPath(
          activeRouteDemandCoverageContext.coverage_candidates_path,
          {
            routeDemandArtifactVersionId:
              activeRouteDemandCoverageContext.route_demand_artifact_version_id,
            serviceDates: activeRouteDemandCoverageContext.service_dates,
            rows: assignmentRows,
            reserveRows,
            maxCandidates: 8
          }
        )
        .then((response: WorkpageScheduleRouteDemandCoverageRecommendationsResponse) => {
          if (routeDemandCoverageRequestSequenceRef.current !== requestToken) {
            return;
          }
          const recommendations = response.route_demand_coverage_recommendations;
          setRouteDemandCoverageRecommendations(recommendations);
          setRouteDemandCoverageErrorMessage(null);
          setRouteDemandCoverageSelections((currentSelections) =>
            normalizeRouteDemandCoverageSelections(recommendations, currentSelections, {
              applyDefaults: routeDemandCoverageMode === "explicit"
            })
          );
        })
        .catch((error) => {
          if (routeDemandCoverageRequestSequenceRef.current !== requestToken) {
            return;
          }
          setRouteDemandCoverageRecommendations(null);
          setRouteDemandCoverageSelections({});
          setRouteDemandCoveragePendingIntent(null);
          setRouteDemandCoverageErrorMessage(
            errorText(error, "Unable to load route-demand coverage recommendations.")
          );
        })
        .finally(() => {
          if (routeDemandCoverageRequestSequenceRef.current === requestToken) {
            setIsRouteDemandCoveragePending(false);
          }
        });
    }, 300);

    return () => {
      window.clearTimeout(timer);
    };
  }, [
    activeRouteDemandCoverageContext,
    assignmentRows,
    assignmentSignature,
    routeDemandCoverageMode,
    reserveRows,
    reserveSignature
  ]);

  useEffect(() => {
    if (!routeDemandCoveragePendingIntent || !routeDemandCoverageRecommendations) {
      return;
    }
    const result = selectRouteDemandCoverageHeatmapCell(
      routeDemandCoverageRecommendations,
      routeDemandCoverageSelections,
      routeDemandCoverageTargetById,
      routeDemandCoveragePendingIntent
    );
    setRouteDemandCoverageSelections(result.nextSelections);
    setRouteDemandCoveragePendingIntent(null);
  }, [
    routeDemandCoveragePendingIntent,
    routeDemandCoverageRecommendations,
    routeDemandCoverageSelections,
    routeDemandCoverageTargetById
  ]);

  useEffect(() => {
    previewRequestSequenceRef.current += 1;
    const requestToken = previewRequestSequenceRef.current;

    if (!hasUnsavedEdits) {
      setPreviewResponse(null);
      setPreviewErrorMessage(null);
      setIsPreviewPending(false);
      return;
    }

    if (!previewAction?.preview_path || previewAction.state !== "available") {
      setIsPreviewPending(false);
      return;
    }

    const timer = window.setTimeout(() => {
      setIsPreviewPending(true);
      void workpagesRepository
        .previewScheduleArtifact(previewAction.preview_path ?? "", {
          rows: assignmentRows,
          reserveRows
        })
        .then((response) => {
          if (previewRequestSequenceRef.current !== requestToken) {
            return;
          }
          setPreviewResponse(response.preview);
          setPreviewErrorMessage(null);
        })
        .catch((error) => {
          if (previewRequestSequenceRef.current !== requestToken) {
            return;
          }
          setPreviewErrorMessage(
            errorText(error, "Unable to recalculate the backend-authored schedule preview.")
          );
        })
        .finally(() => {
          if (previewRequestSequenceRef.current === requestToken) {
            setIsPreviewPending(false);
          }
        });
    }, 500);

    return () => {
      window.clearTimeout(timer);
    };
  }, [
    assignmentRows,
    assignmentSignature,
    hasUnsavedEdits,
    previewAction?.preview_path,
    previewAction?.state,
    reserveRows,
    reserveSignature
  ]);

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading schedule draft artifact"
        detail="Fetching the immutable Stage04 draft weekly schedule artifact projection."
      />
    );
  }

  if (
    query.isError ||
    !contract ||
    !artifactVersionId ||
    !heatmapSection ||
    !assignmentSection ||
    !reserveSection ||
    !iterationSection
  ) {
    return (
      <StatePanel
        kind="error"
        title="Schedule draft artifact failed to load"
        detail={errorText(query.error, "Unable to load the artifact-backed schedule draft.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const artifactContext = contract.artifact_context;
  const latestArtifactVersionId =
    artifactContext?.latest_in_chain_artifact_version_id ?? artifactVersionId;
  const latestRoute =
    contract.artifact_history?.entries.find(
      (entry) => entry.artifact_version_id === latestArtifactVersionId
    )?.route ?? null;
  const currentCalculations = previewResponse?.calculations ?? contract.calculations;
  const currentDependencies = previewResponse?.dependencies ?? contract.dependencies;
  const isStaleArtifact = latestArtifactVersionId !== artifactVersionId;
  const submitConflict = workpageConflictDetails(submitMutation.error);
  const staleOrConflictRoute = submitConflict?.route ?? (isStaleArtifact ? latestRoute : null);
  const backRoute = workpageBackRoute(workflowRunId);
  const draftRail = buildDraftRail(contract);
  const versionRails = [buildAcceptedRail(contract), draftRail];
  const isEmbedded = layout === "embedded";
  const previewBlockedReason =
    hasUnsavedEdits && previewAction?.state !== "available"
      ? previewAction?.disabled_reason ?? "Preview recalculation is unavailable for this draft."
      : null;
  const saveDisabled =
    submitMutation.isPending ||
    isStaleArtifact ||
    saveAction?.state !== "available" ||
    !artifactVersionId;
  const showRouteDemandCoveragePanel = Boolean(
    activeRouteDemandCoverageContext && !submitConflict && !isStaleArtifact
  );
  const selectedRouteDemandCoverageCount = Object.keys(routeDemandCoverageSelections).length;
  const routeDemandCoverageApplyDisabled =
    routeDemandCoverageApplyMutation.isPending ||
    !routeDemandCoverageSelectionsComplete(
      routeDemandCoverageRecommendations,
      routeDemandCoverageSelections
    );
  const routeDemandCoverageApplyLabel =
    routeDemandCoverageMode === "recovery"
      ? `Apply ${selectedRouteDemandCoverageCount} route ${
          selectedRouteDemandCoverageCount === 1 ? "addition" : "additions"
        }`
      : `Apply ${selectedRouteDemandCoverageCount} coverage ${
          selectedRouteDemandCoverageCount === 1 ? "selection" : "selections"
        }`;
  const renderRouteDemandCoverageCandidateRow = (
    candidate: WorkpageScheduleRouteDemandCoverageCandidate,
    target: WorkpageScheduleRouteDemandCoverageCandidateGroup["target"]
  ): JSX.Element => {
    const targetId = target.target_id;
    const selection = routeDemandCoverageSelections[targetId];
    const checked =
      selection?.driver_id === candidate.driver_id &&
      selection?.route_slot_id === candidate.route_slot_id;
    const localConflictReason = coverageCandidateLocalConflictReason(
      candidate,
      target,
      routeDemandCoverageSelections,
      routeDemandCoverageTargetById
    );
    const selectable = coverageCandidateSelectable(candidate) && !localConflictReason;
    const reason = coverageRecommendationReason(candidate);

    return (
      <tr
        key={`${candidate.route_slot_id}:${candidate.driver_id}`}
        className={`route-demand-coverage-panel__candidate-row${
          checked ? " route-demand-coverage-panel__candidate-row--selected" : ""
        }${selectable ? "" : " route-demand-coverage-panel__candidate-row--blocked"}`}
      >
        <td className="route-demand-coverage-panel__cell route-demand-coverage-panel__cell--route">
          <strong>{target.route_id}</strong>
          <span className="route-demand-coverage-panel__route-slot">{target.route_slot_id}</span>
        </td>
        <td className="route-demand-coverage-panel__cell route-demand-coverage-panel__cell--pick">
          <input
            type="radio"
            className="route-demand-coverage-panel__radio"
            name={`route-demand-coverage-${targetId}`}
            aria-label={`Select ${candidate.driver_name} for ${target.route_id} on ${candidate.service_date}`}
            checked={checked}
            disabled={!selectable}
            onChange={() => {
              setRouteDemandCoverageSelections((current) => ({
                ...current,
                [targetId]: {
                  target_id: targetId,
                  route_slot_id: candidate.route_slot_id,
                  driver_id: candidate.driver_id,
                  row_kind: "assignment"
                }
              }));
            }}
          />
        </td>
        <td className="route-demand-coverage-panel__cell route-demand-coverage-panel__cell--driver">
          <strong>{candidate.driver_name}</strong>
        </td>
        <td className="route-demand-coverage-panel__cell">
          {coverageCandidateStateSummary(candidate, localConflictReason)}
        </td>
        <td className="route-demand-coverage-panel__cell">
          {coverageCandidateLoadSummary(candidate)}
        </td>
        <td className="route-demand-coverage-panel__cell">
          {coverageCandidateReserveSummary(candidate)}
        </td>
        <td className="route-demand-coverage-panel__cell route-demand-coverage-panel__cell--why">
          <span className="route-demand-coverage-panel__truncate" title={reason}>
            {reason}
          </span>
        </td>
        <td className="route-demand-coverage-panel__cell route-demand-coverage-panel__cell--score">
          <span
            className="route-demand-coverage-panel__truncate"
            title={coverageCandidateScoreSummary(candidate, localConflictReason)}
          >
            {coverageCandidateScoreSummary(candidate, localConflictReason)}
          </span>
        </td>
      </tr>
    );
  };

  return (
    <WorkpageFrame
      eyebrow="Weekly Schedule Draft Artifact"
      description="A bounded Stage04 draft workbook edit lane with live backend preview and explicit save into a new immutable draft version."
      summaryItems={[
        `Week ${String(contract.workpage.summary.planning_week_id ?? "unknown")}`,
        `Artifact ${artifactVersionId}`,
        `${String(contract.workpage.summary.route_assignment_count ?? 0)} assignments`,
        String(contract.workpage.summary.source_bundle_id ?? "—")
      ]}
      model={contract.workpage}
      source={contract.source}
      freshness={contract.freshness}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching || submitMutation.isPending || downloadMutation.isPending}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId={layout === "embedded" ? "schedule-quick-edit-editor" : "schedule-artifact-workpage-page"}
      metadataPresentation="dialog"
      infoDialogTitle="Schedule draft context"
      sourceDescription="Artifact-backed projection of an immutable Stage04 draft weekly schedule workbook. Save creates a new superseding draft artifact version without publishing."
      heroTitle={isEmbedded ? "Weekly Schedule Draft" : undefined}
      heroTitleActions={
        <>
          {isEmbedded ? (
            <button
              type="button"
              className="action-btn"
              onClick={() => {
                setIsDraftHistoryOpen(true);
              }}
            >
              History
            </button>
          ) : null}
          <button
            type="button"
            className="action-btn action-btn--positive"
            disabled={saveDisabled}
            onClick={() => submitMutation.mutate()}
          >
            {submitMutation.isPending ? "Saving draft..." : "Save draft"}
          </button>
          <button
            type="button"
            className="action-btn"
            disabled={downloadMutation.isPending}
            onClick={() => downloadMutation.mutate(artifactVersionId)}
          >
            {downloadMutation.isPending ? "Downloading draft JSON..." : "Download draft JSON"}
          </button>
        </>
      }
      heroSupportText="Live preview recalculates in place. Save creates the next immutable draft in this weekly lineage."
      heroPresentation={isEmbedded ? "title_only" : "default"}
      heroActions={
        layout === "page" ? (
          <>
            <Link className="link-button" to={scheduleLandingRoute(workflowRunId)}>
              Back to query landing
            </Link>
            {routeDemandAction?.route ? (
              <Link className="link-button" to={routeDemandAction.route}>
                Open route demand
              </Link>
            ) : null}
            {driverPreferencesAction?.route ? (
              <Link className="link-button" to={driverPreferencesAction.route}>
                Open driver preferences
              </Link>
            ) : driverPreferencesAction?.create_path ? (
              <button
                type="button"
                className="action-btn"
                disabled={createDriverPreferencesMutation.isPending}
                onClick={() =>
                  createDriverPreferencesMutation.mutate({
                    createPath: driverPreferencesAction.create_path ?? "",
                    actionRef: driverPreferencesAction.action_ref
                  })
                }
              >
                {createDriverPreferencesMutation.isPending
                  ? "Creating preferences snapshot..."
                  : "Create preferences snapshot"}
              </button>
            ) : null}
          </>
        ) : undefined
      }
      stickyTitleBar
      infoDialogContent={
        <ScheduleArtifactAdvancedInfo
          noteSection={noteSection}
          historySection={historySection}
          assignmentSection={assignmentSection}
          reserveSection={reserveSection}
          iterationSection={iterationSection}
          artifactContext={artifactContext}
        />
      }
      backLink={backRoute.href}
      backLabel={backRoute.label}
      layout={layout}
    >
      {isEmbedded && isDraftHistoryOpen ? (
        <ScheduleDraftHistoryDialog rail={draftRail} onClose={() => setIsDraftHistoryOpen(false)} />
      ) : null}

      {submitConflict ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Latest draft already exists</h2>
            <p>
              This base schedule artifact has already been superseded. Keep your local edits for
              now, then reopen the latest draft artifact before saving again.
            </p>
          </header>
          <div className="action-cluster">
            <Link className="link-button" to={submitConflict.route}>
              Open latest draft
            </Link>
          </div>
        </section>
      ) : null}

      {!submitConflict && isStaleArtifact && staleOrConflictRoute ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Latest draft available</h2>
            <p>
              This artifact version is no longer the latest draft in the chain. Reopen the latest
              version before saving more changes.
            </p>
          </header>
          <div className="action-cluster">
            <Link className="link-button" to={staleOrConflictRoute}>
              Open latest draft
            </Link>
          </div>
        </section>
      ) : null}

      {submitMutation.isError && !submitConflict ? (
        <StatePanel
          kind="error"
          title="Draft save failed"
          detail={errorText(submitMutation.error, "Unable to save the artifact-backed schedule draft.")}
        />
      ) : null}

      {downloadMutation.isError ? (
        <StatePanel
          kind="error"
          title="Draft JSON download failed"
          detail={errorText(downloadMutation.error, "Unable to download the schedule draft artifact.")}
        />
      ) : null}

      {sickNoShowTarget ? (
        <div className="schedule-sick-no-show-dialog-backdrop">
          <section
            className="schedule-sick-no-show-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={sickNoShowTitleId}
            aria-describedby={sickNoShowDescriptionId}
          >
            <header>
              <p className="timeline-page__eyebrow">Driver status</p>
              <h2 id={sickNoShowTitleId}>Mark Sick / No Show</h2>
              <p id={sickNoShowDescriptionId}>
                {`${sickNoShowTarget.driverName} will be marked unavailable on ${sickNoShowTarget.serviceDateLabel}. Any route or on-call assignment for that day will be cleared from this draft.`}
              </p>
            </header>
            <label>
              <span>Optional note</span>
              <textarea
                rows={3}
                value={sickNoShowReasonNote}
                onChange={(event) => setSickNoShowReasonNote(event.target.value)}
                placeholder="Add context for the operations log."
              />
            </label>
            {sickNoShowMutation.isError ? (
              <StatePanel
                kind="error"
                title="Sick / No Show failed"
                detail={errorText(
                  sickNoShowMutation.error,
                  "Unable to mark the driver Sick / No Show."
                )}
              />
            ) : null}
            <div className="action-cluster">
              <button
                type="button"
                className="action-btn"
                disabled={sickNoShowMutation.isPending}
                onClick={() => {
                  setSickNoShowTarget(null);
                  setSickNoShowReasonNote("");
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="action-btn action-btn--danger"
                disabled={sickNoShowMutation.isPending}
                onClick={() => sickNoShowMutation.mutate(sickNoShowTarget)}
              >
                {sickNoShowMutation.isPending ? "Marking..." : "Confirm Sick / No Show"}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {showRouteDemandCoveragePanel ? (
        <section
          className="workpage-panel workpage-panel--callout"
          data-testid="route-demand-coverage-panel"
        >
          <header className="workpage-panel__header">
            <h2>Route-demand coverage recommendations</h2>
            <p>
              The added route demand was saved separately. Use empty heatmap cells or choose a
              backend-ranked driver option for each new target route slot, then apply to create
              the next schedule draft.
            </p>
          </header>
          <div className="route-demand-coverage-panel__summary">
            <p>
              {routeDemandCoverageRecommendations?.added_route_count ??
                activeRouteDemandCoverageContext?.added_route_count ??
                0}{" "}
              added routes across {(activeRouteDemandCoverageContext?.service_dates ?? []).join(", ")}
            </p>
            {activeRouteDemandCoverageContext?.deltas?.length ? (
              <p>
                {activeRouteDemandCoverageContext.deltas
                  .map(
                    (delta) =>
                      `${delta.service_date}: ${delta.previous_planned_route_count} -> ${delta.planned_route_count} (${delta.delta >= 0 ? "+" : ""}${delta.delta})`
                  )
                  .join(" · ")}
              </p>
            ) : null}
          </div>
          {routeDemandCoverageErrorMessage ? (
            <StatePanel
              kind="error"
              title="Coverage recommendations failed"
              detail={routeDemandCoverageErrorMessage}
            />
          ) : isRouteDemandCoveragePending && !routeDemandCoverageRecommendations ? (
            <StatePanel
              kind="loading"
              title="Loading coverage recommendations"
              detail="Evaluating backend-ranked driver options for the added route demand."
            />
          ) : routeDemandCoverageRecommendations ? (
            <>
              {routeDemandCoverageDayGroups.map((dayGroup) => {
                const isOverflowOpen = Boolean(
                  routeDemandCoverageOverflowOpen[dayGroup.serviceDate]
                );
                const dayDeltaSummary = coverageDayDeltaSummary(
                  dayGroup.serviceDate,
                  activeRouteDemandCoverageContext
                );

                return (
                  <section
                    key={dayGroup.serviceDate}
                    className="route-demand-coverage-panel__day"
                    data-testid={`route-demand-coverage-day-${dayGroup.serviceDate}`}
                  >
                    <header className="route-demand-coverage-panel__day-header">
                      <div className="route-demand-coverage-panel__day-heading">
                        <h3>{dayGroup.serviceDate}</h3>
                      </div>
                      <div className="route-demand-coverage-panel__meta">
                        <span>
                          {dayGroup.targetGroups.length} added{" "}
                          {dayGroup.targetGroups.length === 1 ? "route" : "routes"}
                        </span>
                        {dayDeltaSummary ? <span>{dayDeltaSummary}</span> : null}
                      </div>
                    </header>

                    <div
                      className="route-demand-coverage-panel__table-wrap"
                      data-testid={`route-demand-coverage-day-table-${dayGroup.serviceDate}`}
                    >
                      <table className="route-demand-coverage-panel__table">
                        <thead>
                          <tr>
                            <th>Route</th>
                            <th>Pick</th>
                            <th>Driver</th>
                            <th>State</th>
                            <th>Load</th>
                            <th>Reserve</th>
                            <th>Why</th>
                            <th>Score</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dayGroup.inlineRows.length > 0 ? (
                            dayGroup.inlineRows.map((row) =>
                              renderRouteDemandCoverageCandidateRow(row.candidate, row.target)
                            )
                          ) : (
                            <tr className="route-demand-coverage-panel__empty-row">
                              <td colSpan={8}>
                                No route-level inline recommendations are available for this day.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>

                    {dayGroup.overflowRows.length > 0 ? (
                      <details
                        className="route-demand-coverage-panel__overflow"
                        data-testid={`route-demand-coverage-day-overflow-${dayGroup.serviceDate}`}
                        open={isOverflowOpen}
                        onToggle={(event) => {
                          const isOpen = (event.currentTarget as HTMLDetailsElement).open;
                          setRouteDemandCoverageOverflowOpen((current) => {
                            const next = { ...current };
                            if (isOpen) {
                              next[dayGroup.serviceDate] = true;
                            } else {
                              delete next[dayGroup.serviceDate];
                            }
                            return next;
                          });
                        }}
                      >
                        <summary>{coverageOverflowSummaryLabel(dayGroup.overflowRows)}</summary>
                        <div className="route-demand-coverage-panel__table-wrap">
                          <table className="route-demand-coverage-panel__table">
                            <thead>
                              <tr>
                                <th>Route</th>
                                <th>Pick</th>
                                <th>Driver</th>
                                <th>State</th>
                                <th>Load</th>
                                <th>Reserve</th>
                                <th>Why</th>
                                <th>Score</th>
                              </tr>
                            </thead>
                            <tbody>
                              {dayGroup.overflowRows.map((row) =>
                                renderRouteDemandCoverageCandidateRow(row.candidate, row.target)
                              )}
                            </tbody>
                          </table>
                        </div>
                      </details>
                    ) : null}
                  </section>
                );
              })}
              {routeDemandCoverageApplyMutation.isError ? (
                <StatePanel
                  kind="error"
                  title="Coverage apply failed"
                  detail={errorText(
                    routeDemandCoverageApplyMutation.error,
                    "Unable to apply the selected route-demand coverage options."
                  )}
                />
              ) : null}
              <div className="action-cluster route-demand-coverage-panel__footer">
                <button
                  type="button"
                  className="action-btn action-btn--positive"
                  disabled={routeDemandCoverageApplyDisabled}
                  onClick={() => routeDemandCoverageApplyMutation.mutate()}
                >
                  {routeDemandCoverageApplyMutation.isPending
                    ? routeDemandCoverageMode === "recovery"
                      ? "Applying route additions..."
                      : "Applying coverage..."
                    : routeDemandCoverageApplyLabel}
                </button>
              </div>
            </>
          ) : (
            <StatePanel
              kind="empty"
              title="No coverage recommendations yet"
              detail="The backend did not return any added route-demand targets for this draft."
            />
          )}
        </section>
      ) : null}

      <ScheduleWorkpageSurface
        summarySection={summarySection}
        heatmapSection={heatmapSection}
        assignmentRows={assignmentRows}
        reserveRows={reserveRows}
        onRowsChange={({ assignmentRows: nextAssignmentRows, reserveRows: nextReserveRows }) => {
          setAssignmentRows(nextAssignmentRows);
          setReserveRows(nextReserveRows);
        }}
        calculations={currentCalculations}
        dependencies={currentDependencies}
        versionRails={versionRails}
        readOnly={false}
        previewStatus={{
          isDirty: hasUnsavedEdits,
          isPending: isPreviewPending,
          error: previewErrorMessage,
          blockedReason: previewBlockedReason
        }}
        saveAction={saveAction}
        presentation={isEmbedded ? "quick_edit" : "default"}
        routeDemandUnresolvedCountsByServiceDate={routeDemandCoverageUnresolvedCountsByServiceDate}
        routeDemandPendingCells={routeDemandCoveragePendingCells}
        onRouteDemandCellToggle={
          showRouteDemandCoveragePanel
            ? ({ driverId, serviceDate }) => {
                if (!routeDemandCoverageRecommendations) {
                  setRouteDemandCoveragePendingIntent({
                    driverId,
                    serviceDate
                  });
                  return "Loading uncovered route options for that driver.";
                }
                const result = selectRouteDemandCoverageHeatmapCell(
                  routeDemandCoverageRecommendations,
                  routeDemandCoverageSelections,
                  routeDemandCoverageTargetById,
                  {
                    driverId,
                    serviceDate
                  }
                );
                setRouteDemandCoverageSelections(result.nextSelections);
                return result.message;
              }
            : undefined
        }
        onMarkSickNoShow={
          enableSickNoShow && sickNoShowAction?.state === "available"
            ? (target) => {
                setSickNoShowTarget(target);
                setSickNoShowReasonNote("");
              }
            : undefined
        }
        sickNoShowDisabled={sickNoShowMutation.isPending}
        sickNoShowPendingKey={
          sickNoShowMutation.isPending && sickNoShowTarget
            ? `${sickNoShowTarget.serviceDate}:${sickNoShowTarget.driverId}`
            : null
        }
      />
    </WorkpageFrame>
  );
}
