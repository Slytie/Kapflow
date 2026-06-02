import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useIsFetching, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import { DetailDrawer } from "@/components/DetailDrawer";
import { FilterBar } from "@/components/FilterBar";
import { FreshnessBanner } from "@/components/FreshnessBanner";
import { InfoDialog } from "@/components/InfoDialog";
import { LogisticsFamilyNav } from "@/components/LogisticsFamilyNav";
import { StatePanel } from "@/components/StatePanel";
import { ScheduleQuickEditModal } from "@/pages/LogisticsScheduleWorkpagePage";
import { DriverPreferencesQuickEditModal } from "@/pages/LogisticsDriverPreferencesWorkpagePage";
import { RouteDemandQuickEditModal } from "@/pages/LogisticsRouteDemandWorkpagePage";
import { DispatchReportCloseoutModal } from "@/pages/DispatchReportWorkpagePage";
import { useShellFilters } from "@/app/useShellFilters";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { errorText } from "@/lib/api/errorText";
import {
  buildBoardItemDrawerPayload,
  DEFAULT_LOGISTICS_PLANNING_WEEK_ID,
  logisticsFamilyGraphEdges,
  logisticsFamilyGraphNodes,
  logisticsTaskStripCards,
  moduleRunRefs,
  runRowsForStory,
  workflowIdToModuleId
} from "@/lib/logistics/familyStory";
import { logisticsStoryRepository, workpagesRepository } from "@/lib/repositories";
import {
  apiConfig,
  getApiRequestContextHeaders,
  getApiViewerSession,
  setApiRequestContextHeaders,
  setApiViewerSession
} from "@/lib/api/config";
import { ACTOR_PROFILES } from "@/lib/actors";
import { useDrawer } from "@/lib/state/drawerContext";
import type { LogisticsStoryBoardWorkItem, WorkpageContract } from "@/lib/types/contracts";
import type {
  WorkpageScheduleAction,
  WorkpageScheduleRouteDemandCoverageContext
} from "@/lib/types/workpages";

const UTILITY_LINKS = [
  { to: "/my-work", label: "My Work" },
  { to: "/approvals", label: "Approvals" },
  { to: "/exceptions", label: "Exceptions" },
  { to: "/official-outputs", label: "Official Outputs" }
];

const SECONDARY_LINKS = [{ to: "/runs", label: "Run Details" }];

type ScheduleQuickEditTarget = {
  workflowRunId: string;
  artifactVersionId: string | null;
  routeDemandCoverageContext: WorkpageScheduleRouteDemandCoverageContext | null;
  comparisonModeHint: "future_week" | null;
};

type ScheduleWeekChoice = {
  key: "current" | "next";
  workflowRunId: string;
  artifactVersionId: string | null;
  label: string;
  dateRangeLabel: string;
  available: boolean;
  disabledReason: string | null;
};

function scheduleRouteDemandCoverageContextFromState(
  value: unknown
): WorkpageScheduleRouteDemandCoverageContext | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const record = value as Record<string, unknown>;
  if (
    typeof record.workflow_run_id !== "string" ||
    typeof record.schedule_artifact_version_id !== "string" ||
    typeof record.route_demand_artifact_version_id !== "string" ||
    typeof record.coverage_candidates_path !== "string" ||
    typeof record.coverage_apply_path !== "string"
  ) {
    return null;
  }
  return {
    workflow_run_id: record.workflow_run_id,
    schedule_artifact_version_id: record.schedule_artifact_version_id,
    route_demand_artifact_version_id: record.route_demand_artifact_version_id,
    coverage_candidates_path: record.coverage_candidates_path,
    coverage_apply_path: record.coverage_apply_path,
    service_dates: Array.isArray(record.service_dates)
      ? record.service_dates.filter((item): item is string => typeof item === "string")
      : [],
    added_route_count:
      typeof record.added_route_count === "number" ? record.added_route_count : 0,
    deltas: Array.isArray(record.deltas)
      ? record.deltas
          .filter(
            (item): item is Record<string, unknown> =>
              Boolean(item) && typeof item === "object" && !Array.isArray(item)
          )
          .map((item) => ({
            service_date: typeof item.service_date === "string" ? item.service_date : "",
            previous_planned_route_count:
              typeof item.previous_planned_route_count === "number"
                ? item.previous_planned_route_count
                : 0,
            planned_route_count:
              typeof item.planned_route_count === "number" ? item.planned_route_count : 0,
            delta: typeof item.delta === "number" ? item.delta : 0
          }))
      : []
  };
}

function buildLogisticsDemoRoute(input: {
  planningWeekId: string;
  serviceDateId?: string;
  moduleId?: string | null;
  workflowRunId?: string | null;
}): string {
  const nextParams = new URLSearchParams();
  nextParams.set("planning_week_id", input.planningWeekId);
  if (input.serviceDateId) {
    nextParams.set("service_date_id", input.serviceDateId);
  }
  if (input.moduleId) {
    nextParams.set("module", input.moduleId);
  }
  if (input.workflowRunId) {
    nextParams.set("workflow_run_id", input.workflowRunId);
  }
  return `/demo/logistics?${nextParams.toString()}`;
}

function activeModuleIdForLocation(input: {
  pathname: string;
  selectedModuleId: string | null;
  runWorkflowById: Map<string, string>;
  fallbackModuleId: string | null;
}): string | null {
  if (input.pathname === "/demo/logistics") {
    return input.selectedModuleId ?? input.fallbackModuleId;
  }
  if (/^\/runs\/[^/]+\/workpages\/schedule-v0(?:\/.*)?$/.test(input.pathname)) {
    return "weekly_schedule_planning";
  }
  if (/^\/runs\/[^/]+\/workpages\/route-demand-v0(?:\/.*)?$/.test(input.pathname)) {
    return "weekly_schedule_planning";
  }
  if (/^\/runs\/[^/]+\/workpages\/driver-preferences-v0(?:\/.*)?$/.test(input.pathname)) {
    return "weekly_schedule_planning";
  }
  if (/^\/runs\/[^/]+\/workpages\/eod-v0(?:\/.*)?$/.test(input.pathname)) {
    return "dispatch_reporting";
  }
  const runMatch = input.pathname.match(/^\/runs\/([^/]+)(?:\/workspace)?$/);
  if (!runMatch) {
    return null;
  }
  const workflowId = input.runWorkflowById.get(runMatch[1] ?? "");
  return workflowId ? workflowIdToModuleId(workflowId) : null;
}

function workflowRunIdForLocation(input: {
  pathname: string;
  searchParams: URLSearchParams;
}): string | null {
  if (input.pathname === "/demo/logistics") {
    return input.searchParams.get("workflow_run_id")?.trim() || null;
  }
  const runMatch = input.pathname.match(/^\/runs\/([^/]+)(?:\/.*)?$/);
  return runMatch?.[1] ?? null;
}

function canonicalRouteForWorkflow(input: {
  workflowId: string;
  workflowRunId: string;
}): string {
  if (input.workflowId === "weekly_schedule_planning.v1") {
    return `/runs/${input.workflowRunId}/workpages/schedule-v0`;
  }
  if (input.workflowId === "dispatch_reporting.v1") {
    return `/runs/${input.workflowRunId}/workpages/eod-v0`;
  }
  return `/runs/${input.workflowRunId}/workspace`;
}

function scheduleOpenLatestDraftAction(
  contract: WorkpageContract | undefined
): WorkpageScheduleAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageScheduleAction =>
        action.workpage_kind === "schedule-v0" &&
        action.kind === "open_latest_draft" &&
        action.state === "available" &&
        Boolean(action.artifact_version_id)
    ) ?? null
  );
}

function routeDemandVisibleWeekDateRange(
  contract: WorkpageContract | undefined
): { startDate: string; endDate: string; label: string } | null {
  const visibleDayCards = (contract?.route_demand_calculations?.day_cards ?? []).slice(0, 7);
  const startDate = visibleDayCards[0]?.service_date ?? "";
  const endDate = visibleDayCards[visibleDayCards.length - 1]?.service_date ?? startDate;
  if (!startDate) {
    return null;
  }
  return {
    startDate,
    endDate,
    label: startDate === endDate ? startDate : `${startDate} to ${endDate}`
  };
}

function actorInitials(label: string): string {
  const normalized = label
    .replace(/^(human|agent|service|system):/i, "")
    .replace(/[-_.]+/g, " ")
    .trim();
  const parts = normalized.split(/\s+/).filter(Boolean);
  const initials = parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
  return initials || "U";
}

export function AppShell(): JSX.Element {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isFetching = useIsFetching();
  const { filters, setFilters } = useShellFilters();
  const { payload, close, open } = useDrawer();
  const [viewerBootstrapReady, setViewerBootstrapReady] = useState(
    () => getApiViewerSession() !== null
  );
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [isUtilityMenuOpen, setIsUtilityMenuOpen] = useState(false);
  const [isActorMenuOpen, setIsActorMenuOpen] = useState(false);
  const [isDriversQuickEditOpen, setIsDriversQuickEditOpen] = useState(false);
  const [scheduleQuickEditTarget, setScheduleQuickEditTarget] =
    useState<ScheduleQuickEditTarget | null>(null);
  const [isScheduleWeekPickerOpen, setIsScheduleWeekPickerOpen] = useState(false);
  const [isRouteDemandQuickEditOpen, setIsRouteDemandQuickEditOpen] = useState(false);
  const [isDispatchCloseoutOpen, setIsDispatchCloseoutOpen] = useState(false);
  const isWorkspaceRoute = /^\/runs\/[^/]+\/workspace$/.test(location.pathname);
  const isTimelineRoute = location.pathname === "/timeline";
  const isDemoLogisticsRoute =
    location.pathname === "/demo/logistics" ||
    location.pathname.startsWith("/demo/logistics/");
  const isRunWorkpageRoute = /^\/runs\/[^/]+\/workpages(?:\/.*)?$/.test(location.pathname);
  const isWeeklyPlanningWorkpageRoute =
    /^\/runs\/[^/]+\/workpages\/(?:schedule-v0|route-demand-v0|driver-preferences-v0)(?:\/.*)?$/.test(
      location.pathname
    );
  const isDispatchReportingWorkpageRoute =
    /^\/runs\/[^/]+\/workpages\/eod-v0(?:\/.*)?$/.test(location.pathname);
  const isWorkpageFullPageRoute = isDemoLogisticsRoute || isRunWorkpageRoute;
  const routeSearchParams = useMemo(
    () => new URLSearchParams(location.search),
    [location.search]
  );
  const planningWeekId =
    routeSearchParams.get("planning_week_id")?.trim() || DEFAULT_LOGISTICS_PLANNING_WEEK_ID;
  const serviceDateId = routeSearchParams.get("service_date_id")?.trim() || undefined;
  const selectedModuleId = routeSearchParams.get("module")?.trim() || null;
  const shouldFetchLogisticsStory =
    isDemoLogisticsRoute ||
    isWorkspaceRoute ||
    isWeeklyPlanningWorkpageRoute ||
    isDispatchReportingWorkpageRoute;

  const viewerQuery = useQuery({
    queryKey: ["viewer-session"],
    queryFn: () => onetruthApi.getViewerSession()
  });
  const logisticsStoryQuery = useQuery({
    queryKey: ["logistics-demo-story", planningWeekId, serviceDateId],
    queryFn: () =>
      logisticsStoryRepository.view({
        planningWeekId,
        serviceDateId
      }),
    enabled: shouldFetchLogisticsStory,
    refetchInterval: isDemoLogisticsRoute ? apiConfig.pollIntervalMs : false
  });
  const viewerSession = viewerQuery.data ?? getApiViewerSession();
  const actorRoles = viewerSession?.actor_roles.join(",") ?? "";
  const activeActor =
    ACTOR_PROFILES.find(
      (profile) =>
        profile.actorId === viewerSession?.actor_id &&
        profile.actorType === viewerSession?.actor_type &&
        profile.actorRoles === actorRoles
    ) ?? null;
  const activeActorKey = activeActor?.key ?? ACTOR_PROFILES[0].key;
  const activeActorLabel = activeActor?.label ?? viewerSession?.actor_id ?? "Unknown user";
  const activeActorInitials = actorInitials(activeActorLabel);
  const activeActorRoleLabel =
    viewerSession?.actor_roles
      .map((role) => role.replace(/_/g, " "))
      .join(", ") || viewerSession?.actor_type || "user";
  const logisticsStory = logisticsStoryQuery.data;

  useEffect(() => {
    setIsUtilityMenuOpen(false);
    setIsActorMenuOpen(false);
  }, [location.pathname, location.search]);

  useEffect(() => {
    return queryClient.getQueryCache().subscribe((event) => {
      const query = event?.query;
      if (!query) {
        return;
      }
      const dataUpdatedAt = query.state.dataUpdatedAt;
      if (dataUpdatedAt > 0) {
        queueMicrotask(() => {
          setLastRefreshedAt(new Date(dataUpdatedAt).toISOString());
        });
      }
    });
  }, [queryClient]);

  useEffect(() => {
    if (!viewerQuery.data) {
      return;
    }
    setApiViewerSession(viewerQuery.data);
    setViewerBootstrapReady(true);
  }, [viewerQuery.data]);

  const refresh = (): void => {
    void queryClient.invalidateQueries();
  };

  const handleActorChange = (actorKey: string): void => {
    if (!viewerSession || !viewerSession.actor_switching_allowed) {
      return;
    }
    const nextActor =
      ACTOR_PROFILES.find((profile) => profile.key === actorKey) ?? ACTOR_PROFILES[0];
    const current = getApiRequestContextHeaders();
    setApiRequestContextHeaders({
      ...current,
      actorId: nextActor.actorId,
      actorType: nextActor.actorType,
      actorRoles: nextActor.actorRoles
    });
    const nextViewerSession = {
      ...viewerSession,
      actor_id: nextActor.actorId,
      actor_type: nextActor.actorType,
      actor_roles: nextActor.actorRoles
        .split(",")
        .map((role) => role.trim())
        .filter(Boolean)
    };
    setApiViewerSession(nextViewerSession);
    queryClient.setQueryData(["viewer-session"], nextViewerSession);
    setIsActorMenuOpen(false);
    void queryClient.invalidateQueries({
      predicate: (query) => query.queryKey[0] !== "viewer-session"
    });
  };

  const runWorkflowById = useMemo(() => {
    if (!logisticsStory) {
      return new Map<string, string>();
    }
    return new Map(
      runRowsForStory(logisticsStory).map((run) => [run.workflow_run_id, run.workflow_id])
    );
  }, [logisticsStory]);

  const familyNavNodes = useMemo(
    () => (logisticsStory ? logisticsFamilyGraphNodes(logisticsStory) : []),
    [logisticsStory]
  );
  const familyNavEdges = useMemo(
    () => (logisticsStory ? logisticsFamilyGraphEdges(logisticsStory) : []),
    [logisticsStory]
  );
  const taskCards = useMemo(
    () => (logisticsStory ? logisticsTaskStripCards(logisticsStory) : []),
    [logisticsStory]
  );
  const fallbackModuleId = logisticsStory?.family_graph.modules[0]?.module_id ?? null;
  const activeModuleId = useMemo(
    () =>
      activeModuleIdForLocation({
        pathname: location.pathname,
        selectedModuleId,
        runWorkflowById,
        fallbackModuleId
      }),
    [fallbackModuleId, location.pathname, runWorkflowById, selectedModuleId]
  );
  const activeWorkflowRunId = useMemo(
    () =>
      workflowRunIdForLocation({
        pathname: location.pathname,
        searchParams: routeSearchParams
      }),
    [location.pathname, routeSearchParams]
  );
  const logisticsDemoRoute = useMemo(
    () =>
      buildLogisticsDemoRoute({
        planningWeekId,
        serviceDateId,
        moduleId: activeModuleId,
        workflowRunId: activeWorkflowRunId
      }),
    [activeModuleId, activeWorkflowRunId, planningWeekId, serviceDateId]
  );
  const activeWorkflowId = activeWorkflowRunId
    ? runWorkflowById.get(activeWorkflowRunId) ?? null
    : null;
  const weeklyModuleRunIds = useMemo(() => {
    const weeklyModule = logisticsStory?.family_graph.modules.find(
      (module) => module.module_id === "weekly_schedule_planning"
    );
    if (!weeklyModule) {
      return [];
    }
    return moduleRunRefs(weeklyModule)
      .map((ref) => ref.workflow_run_id)
      .filter(Boolean);
  }, [logisticsStory]);
  const isDispatchReportingContext = Boolean(
    activeWorkflowRunId &&
      (activeWorkflowId === "dispatch_reporting.v1" ||
        activeModuleId === "dispatch_reporting" ||
        /^\/runs\/[^/]+\/workpages\/eod-v0(?:\/.*)?$/.test(location.pathname))
  );
  const isWeeklyPlanningContext = Boolean(
    activeWorkflowRunId &&
      (activeWorkflowId === "weekly_schedule_planning.v1" ||
        activeModuleId === "weekly_schedule_planning" ||
        isWeeklyPlanningWorkpageRoute)
  );
  const secondaryWeeklyRunId = useMemo(() => {
    if (!activeWorkflowRunId) {
      return null;
    }
    return weeklyModuleRunIds.find((workflowRunId) => workflowRunId !== activeWorkflowRunId) ?? null;
  }, [activeWorkflowRunId, weeklyModuleRunIds]);
  const shouldLoadScheduleWeekChoices = Boolean(
    isScheduleWeekPickerOpen && activeWorkflowRunId && isWeeklyPlanningContext
  );
  const [currentScheduleWeekChoiceQuery, currentRouteDemandWeekChoiceQuery] = useQueries({
    queries: [
      {
        queryKey: ["workpages", "schedule-v0", "landing", activeWorkflowRunId, "week-picker"],
        queryFn: () => workpagesRepository.scheduleForRun(activeWorkflowRunId ?? ""),
        enabled: shouldLoadScheduleWeekChoices,
        refetchInterval: false
      },
      {
        queryKey: ["workpages", "route-demand-v0", "run", activeWorkflowRunId, "week-picker"],
        queryFn: () => workpagesRepository.routeDemandForRun(activeWorkflowRunId ?? ""),
        enabled: shouldLoadScheduleWeekChoices,
        refetchInterval: false
      }
    ]
  });
  const [secondaryScheduleWeekChoiceQuery, secondaryRouteDemandWeekChoiceQuery] = useQueries({
    queries: [
      {
        queryKey: ["workpages", "schedule-v0", "landing", secondaryWeeklyRunId, "week-picker"],
        queryFn: () => workpagesRepository.scheduleForRun(secondaryWeeklyRunId ?? ""),
        enabled: Boolean(shouldLoadScheduleWeekChoices && secondaryWeeklyRunId),
        refetchInterval: false
      },
      {
        queryKey: ["workpages", "route-demand-v0", "run", secondaryWeeklyRunId, "week-picker"],
        queryFn: () => workpagesRepository.routeDemandForRun(secondaryWeeklyRunId ?? ""),
        enabled: Boolean(shouldLoadScheduleWeekChoices && secondaryWeeklyRunId),
        refetchInterval: false
      }
    ]
  });
  const canOpenDriversQuickEdit = Boolean(activeWorkflowRunId && isWeeklyPlanningContext);
  const scheduleWeekChoices = useMemo((): ScheduleWeekChoice[] => {
    const candidates = [
      {
        workflowRunId: activeWorkflowRunId,
        scheduleContract: currentScheduleWeekChoiceQuery.data,
        routeDemandContract: currentRouteDemandWeekChoiceQuery.data,
        scheduleError: currentScheduleWeekChoiceQuery.isError
      },
      {
        workflowRunId: secondaryWeeklyRunId,
        scheduleContract: secondaryScheduleWeekChoiceQuery.data,
        routeDemandContract: secondaryRouteDemandWeekChoiceQuery.data,
        scheduleError: secondaryScheduleWeekChoiceQuery.isError
      }
    ]
      .filter(
        (candidate): candidate is {
          workflowRunId: string;
          scheduleContract: WorkpageContract | undefined;
          routeDemandContract: WorkpageContract | undefined;
          scheduleError: boolean;
        } => Boolean(candidate.workflowRunId)
      )
      .map((candidate) => {
        const openAction = scheduleOpenLatestDraftAction(candidate.scheduleContract);
        const dateRange = routeDemandVisibleWeekDateRange(candidate.routeDemandContract);
        return {
          workflowRunId: candidate.workflowRunId,
          artifactVersionId: openAction?.artifact_version_id ?? null,
          dateRangeLabel: dateRange?.label ?? "Week details unavailable",
          startDate: dateRange?.startDate ?? "9999-12-31",
          available: Boolean(openAction),
          disabledReason: openAction
            ? null
            : candidate.scheduleError
              ? "Weekly schedule could not be loaded."
              : "No draft yet"
        };
      })
      .sort((left, right) => left.startDate.localeCompare(right.startDate));
    return candidates.slice(0, 2).map((candidate, index) => ({
      key: index === 0 ? "current" : "next",
      workflowRunId: candidate.workflowRunId,
      artifactVersionId: candidate.artifactVersionId,
      label: index === 0 ? "Current week" : "Next week",
      dateRangeLabel: candidate.dateRangeLabel,
      available: candidate.available,
      disabledReason: candidate.disabledReason
    }));
  }, [
    activeWorkflowRunId,
    currentRouteDemandWeekChoiceQuery.data,
    currentScheduleWeekChoiceQuery.data,
    currentScheduleWeekChoiceQuery.isError,
    secondaryRouteDemandWeekChoiceQuery.data,
    secondaryScheduleWeekChoiceQuery.data,
    secondaryScheduleWeekChoiceQuery.isError,
    secondaryWeeklyRunId
  ]);
  const hasScheduleWeekPicker = isWeeklyPlanningContext && weeklyModuleRunIds.length > 1;
  const canOpenScheduleQuickEdit = Boolean(
    activeWorkflowRunId &&
      isWeeklyPlanningContext &&
      (!shouldFetchLogisticsStory || Boolean(logisticsStory) || logisticsStoryQuery.isError)
  );
  const canOpenRouteDemandQuickEdit = Boolean(activeWorkflowRunId && isWeeklyPlanningContext);
  const canOpenDispatchCloseout = Boolean(activeWorkflowRunId && isDispatchReportingContext);
  const weeklyActionUnavailableReason = !activeWorkflowRunId
    ? "No active workflow run is selected."
    : !isWeeklyPlanningContext
      ? "This action is available on weekly planning runs."
      : "Open a weekly planning route to use this action.";
  const dispatchCloseoutUnavailableReason = !activeWorkflowRunId
    ? "No active workflow run is selected."
    : !isDispatchReportingContext
      ? "This action is available on dispatch reporting runs."
      : "The dispatch reporting closeout flow is still resolving.";
  const driversQuickEditUnavailableReason = weeklyActionUnavailableReason;
  const scheduleQuickEditUnavailableReason = weeklyActionUnavailableReason;
  const routeDemandQuickEditUnavailableReason = weeklyActionUnavailableReason;

  useEffect(() => {
    setIsDriversQuickEditOpen(false);
    setScheduleQuickEditTarget(null);
    setIsScheduleWeekPickerOpen(false);
    setIsRouteDemandQuickEditOpen(false);
  }, [activeWorkflowRunId]);

  useEffect(() => {
    if (activeWorkflowRunId && isDispatchReportingContext) {
      return;
    }
    setIsDispatchCloseoutOpen(false);
  }, [activeWorkflowRunId, isDispatchReportingContext]);

  useEffect(() => {
    const routeState =
      location.state && typeof location.state === "object"
        ? (location.state as Record<string, unknown>)
        : null;
    if (!routeState?.openScheduleQuickEdit || !activeWorkflowRunId) {
      return;
    }
    if (!/^\/runs\/[^/]+\/workpages\/schedule-v0(?:\/.*)?$/.test(location.pathname)) {
      return;
    }
    setScheduleQuickEditTarget({
      workflowRunId: activeWorkflowRunId,
      artifactVersionId:
        typeof routeState.targetScheduleArtifactVersionId === "string"
          ? routeState.targetScheduleArtifactVersionId
          : null,
      routeDemandCoverageContext: scheduleRouteDemandCoverageContextFromState(
        routeState.routeDemandCoverageContext
      ),
      comparisonModeHint:
        routeState.scheduleComparisonModeHint === "future_week" ? "future_week" : null
    });
    setIsScheduleWeekPickerOpen(false);
    const nextState = { ...routeState };
    delete nextState.openScheduleQuickEdit;
    delete nextState.targetScheduleArtifactVersionId;
    delete nextState.routeDemandCoverageContext;
    delete nextState.scheduleComparisonModeHint;
    navigate(
      {
        pathname: location.pathname,
        search: location.search
      },
      {
        replace: true,
        state: Object.keys(nextState).length > 0 ? nextState : null
      }
    );
  }, [activeWorkflowRunId, location.pathname, location.search, location.state, navigate]);

  const handleTaskSelect = (item: LogisticsStoryBoardWorkItem): void => {
    open(buildBoardItemDrawerPayload(item));
  };

  const handleNodeSelect = (nodeId: string): void => {
    if (!logisticsStory) {
      return;
    }
    const module = logisticsStory.family_graph.modules.find(
      (candidate) => candidate.module_id === nodeId
    );
    if (!module) {
      return;
    }
    const refs = moduleRunRefs(module);
    if (refs.length === 1) {
      navigate(
        canonicalRouteForWorkflow({
          workflowId: refs[0]?.workflow_id ?? module.workflow_id,
          workflowRunId: refs[0]?.workflow_run_id ?? ""
        })
      );
      return;
    }
    navigate(
      buildLogisticsDemoRoute({
        planningWeekId,
        serviceDateId,
        moduleId: module.module_id
      })
    );
  };

  const openScheduleQuickEditForSelection = (selection: ScheduleWeekChoice): void => {
    setIsScheduleWeekPickerOpen(false);
    const targetRoute = `/runs/${selection.workflowRunId}/workpages/schedule-v0`;
    if (
      location.pathname === targetRoute &&
      activeWorkflowRunId === selection.workflowRunId
    ) {
      setScheduleQuickEditTarget({
        workflowRunId: selection.workflowRunId,
        artifactVersionId: selection.artifactVersionId,
        routeDemandCoverageContext: null,
        comparisonModeHint: selection.key === "next" ? "future_week" : null
      });
      return;
    }
    navigate(targetRoute, {
      state: {
        openScheduleQuickEdit: true,
        targetScheduleArtifactVersionId: selection.artifactVersionId,
        routeDemandCoverageContext: null,
        scheduleComparisonModeHint: selection.key === "next" ? "future_week" : null
      }
    });
  };

  if ((!viewerSession && viewerQuery.isLoading) || (viewerQuery.data && !viewerBootstrapReady)) {
    return (
      <StatePanel
        kind="loading"
        title="Loading viewer session"
        detail="Resolving server-derived viewer/bootstrap context."
        testId="viewer-session-loading"
      />
    );
  }

  if (!viewerSession && viewerQuery.isError) {
    return (
      <StatePanel
        kind="error"
        title="Viewer session failed to load"
        detail={errorText(viewerQuery.error, "Unable to load viewer/bootstrap session")}
        onRetry={() => void viewerQuery.refetch()}
        testId="viewer-session-error"
      />
    );
  }

  if (!viewerSession) {
    return (
      <StatePanel
        kind="error"
        title="Viewer session missing"
        detail="Viewer/bootstrap session did not resolve."
        onRetry={() => void viewerQuery.refetch()}
        testId="viewer-session-missing"
      />
    );
  }

  return (
    <div className={`app-shell ${isWorkspaceRoute ? "app-shell--workspace" : ""}`}>
      <aside className="app-shell__nav">
        <div className="app-shell__nav-meta">
          <div
            className="app-shell__identity"
            data-testid={
              viewerSession.actor_switching_allowed
                ? "actor-switcher"
                : "viewer-session-panel"
            }
          >
            {viewerSession.actor_switching_allowed ? (
              <button
                type="button"
                className="app-shell__identity-chip"
                aria-expanded={isActorMenuOpen}
                aria-label={`Current user ${activeActorLabel}. Open actor switcher`}
                onClick={() => {
                  setIsActorMenuOpen((current) => !current);
                }}
              >
                <span className="app-shell__identity-avatar" aria-hidden="true">
                  {activeActorInitials}
                </span>
                <span className="app-shell__identity-copy">
                  <strong>{activeActorLabel}</strong>
                  <span>{activeActorRoleLabel}</span>
                </span>
              </button>
            ) : (
              <div
                className="app-shell__identity-chip app-shell__identity-chip--static"
                aria-label={`Current viewer ${activeActorLabel}`}
              >
                <span className="app-shell__identity-avatar" aria-hidden="true">
                  {activeActorInitials}
                </span>
                <span className="app-shell__identity-copy">
                  <strong>{activeActorLabel}</strong>
                  <span>{activeActorRoleLabel}</span>
                </span>
              </div>
            )}
            {!viewerSession.actor_switching_allowed ? (
              <div className="app-shell__identity-static" data-testid="viewer-session">
                <strong>Viewer session</strong>
                <p>{viewerSession.actor_id}</p>
                <p>{viewerSession.boundary_profile}</p>
              </div>
            ) : null}
            {isActorMenuOpen && viewerSession.actor_switching_allowed ? (
              <div className="app-shell__identity-popover" role="menu">
                {ACTOR_PROFILES.map((profile) => (
                  <button
                    key={profile.key}
                    type="button"
                    role="menuitemradio"
                    aria-checked={profile.key === activeActorKey}
                    className={profile.key === activeActorKey ? "is-active" : ""}
                    onClick={() => handleActorChange(profile.key)}
                  >
                    <span>{profile.label}</span>
                    <small>{profile.actorRoles.replace(/_/g, " ")}</small>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <NavLink className="app-shell__brand" to={logisticsDemoRoute}>
            Logistics Demo
          </NavLink>
        </div>

        <div className="app-shell__nav-primary">
          <div className="app-shell__nav-tools">
            {logisticsStory ? (
              <LogisticsFamilyNav
                nodes={familyNavNodes}
                edges={familyNavEdges}
                activeNodeId={activeModuleId}
                taskCards={taskCards}
                onNodeSelect={handleNodeSelect}
                onTaskSelect={handleTaskSelect}
              />
            ) : (
              <div className="app-shell__nav-loading" data-testid="logistics-family-nav-fallback">
                {!shouldFetchLogisticsStory
                  ? "Logistics family nav unavailable on this route."
                  : logisticsStoryQuery.isError
                  ? "Logistics family nav unavailable."
                  : "Loading logistics family nav..."}
              </div>
            )}

            <div className="app-shell__nav-actions" data-testid="app-shell-nav-actions">
              <button
                type="button"
                className="action-btn app-shell__quick-action"
                disabled={!canOpenDriversQuickEdit}
                title={canOpenDriversQuickEdit ? undefined : driversQuickEditUnavailableReason}
                aria-label={
                  canOpenDriversQuickEdit
                    ? "Drivers"
                    : `Drivers unavailable: ${driversQuickEditUnavailableReason}`
                }
                onClick={() => {
                  setIsDriversQuickEditOpen(true);
                }}
              >
                Drivers
              </button>

              <button
                type="button"
                className="action-btn app-shell__quick-action"
                disabled={!canOpenScheduleQuickEdit}
                title={canOpenScheduleQuickEdit ? undefined : scheduleQuickEditUnavailableReason}
                aria-label={
                  canOpenScheduleQuickEdit
                    ? "Edit weekly schedule"
                    : `Edit weekly schedule unavailable: ${scheduleQuickEditUnavailableReason}`
                }
                onClick={() => {
                  if (hasScheduleWeekPicker) {
                    setIsScheduleWeekPickerOpen(true);
                    return;
                  }
                  if (!activeWorkflowRunId) {
                    return;
                  }
                  setScheduleQuickEditTarget({
                    workflowRunId: activeWorkflowRunId,
                    artifactVersionId: null,
                    routeDemandCoverageContext: null,
                    comparisonModeHint: null
                  });
                }}
              >
                Edit weekly schedule
              </button>

              <button
                type="button"
                className="action-btn app-shell__quick-action app-shell__route-demand-edit"
                disabled={!canOpenRouteDemandQuickEdit}
                title={canOpenRouteDemandQuickEdit ? undefined : routeDemandQuickEditUnavailableReason}
                aria-label={
                  canOpenRouteDemandQuickEdit
                    ? "Edit route demand"
                    : `Edit route demand unavailable: ${routeDemandQuickEditUnavailableReason}`
                }
                onClick={() => {
                  setIsRouteDemandQuickEditOpen(true);
                }}
              >
                Edit route demand
              </button>

              {isDispatchReportingContext ? (
                <button
                  type="button"
                  className="action-btn app-shell__quick-action"
                  disabled={!canOpenDispatchCloseout}
                  title={canOpenDispatchCloseout ? undefined : dispatchCloseoutUnavailableReason}
                  aria-label={
                    canOpenDispatchCloseout
                      ? "Upload route activity"
                      : `Upload route activity unavailable: ${dispatchCloseoutUnavailableReason}`
                  }
                  onClick={() => {
                    setIsDispatchCloseoutOpen(true);
                  }}
                >
                  Upload route activity
                </button>
              ) : null}

              <div className="app-shell__utility-menu">
                <button
                  type="button"
                  className="action-btn"
                  aria-expanded={isUtilityMenuOpen}
                  aria-label="Open utility menu"
                  onClick={() => {
                    setIsUtilityMenuOpen((current) => !current);
                  }}
                >
                  Menu
                </button>
                {isUtilityMenuOpen ? (
                  <div className="app-shell__utility-menu-popover" role="menu">
                    {UTILITY_LINKS.map((link) => (
                      <NavLink
                        key={link.to}
                        to={link.to}
                        role="menuitem"
                        className={({ isActive }) => (isActive ? "active" : "")}
                      >
                        {link.label}
                      </NavLink>
                    ))}
                  </div>
                ) : null}
              </div>

              {isWorkpageFullPageRoute ? (
                <InfoDialog
                  triggerLabel="Open secondary detail routes"
                  dialogTitle="Secondary detail routes"
                  dialogDescription="Open secondary logistics detail destinations without taking extra header space."
                  className="app-shell__secondary-info-button"
                >
                  <div className="app-shell__secondary-links-dialog">
                    {SECONDARY_LINKS.map((link) => (
                      <NavLink
                        key={link.to}
                        to={link.to}
                        className={({ isActive }) => `link-button${isActive ? " active" : ""}`}
                      >
                        {link.label}
                      </NavLink>
                    ))}
                  </div>
                </InfoDialog>
              ) : null}
            </div>
          </div>
        </div>
      </aside>

      <section className="app-shell__main">
        {isWorkspaceRoute || isTimelineRoute || isWorkpageFullPageRoute ? null : (
          <>
            <header className="app-shell__header">
              <div>
                <strong>{location.pathname}</strong>
                <p>Server-authoritative view backed by HITL HTTP query contracts</p>
              </div>
              <FreshnessBanner
                lastRefreshedAt={lastRefreshedAt}
                onRefresh={refresh}
                isRefreshing={isFetching > 0}
                pollIntervalMs={apiConfig.pollIntervalMs}
              />
            </header>

            <FilterBar filters={filters} onChange={setFilters} />
          </>
        )}

        <div className="app-shell__content">
          <Outlet />
        </div>
      </section>

      {isDriversQuickEditOpen && activeWorkflowRunId ? (
        <DriverPreferencesQuickEditModal
          workflowRunId={activeWorkflowRunId}
          onClose={() => {
            setIsDriversQuickEditOpen(false);
          }}
        />
      ) : null}
      {isScheduleWeekPickerOpen ? (
        <div
          className="route-demand-quick-edit-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setIsScheduleWeekPickerOpen(false);
            }
          }}
        >
          <section
            className="route-demand-quick-edit-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Choose weekly schedule"
          >
            <header className="route-demand-quick-edit-modal__header">
              <div>
                <p className="timeline-page__eyebrow">Quick edit</p>
                <h2>Choose weekly schedule</h2>
                <p>Select the current or next week draft to edit.</p>
              </div>
              <button
                type="button"
                className="action-btn"
                onClick={() => {
                  setIsScheduleWeekPickerOpen(false);
                }}
              >
                Close
              </button>
            </header>
            <div className="route-demand-quick-edit-modal__body">
              <section className="workpage-panel">
                <header className="workpage-panel__header">
                  <h2>Editable weeks</h2>
                  <p>The schedule editor supports the current week and immediate next week in this demo flow.</p>
                </header>
                {currentScheduleWeekChoiceQuery.isLoading ||
                currentRouteDemandWeekChoiceQuery.isLoading ||
                secondaryScheduleWeekChoiceQuery.isLoading ||
                secondaryRouteDemandWeekChoiceQuery.isLoading ? (
                  <StatePanel
                    kind="loading"
                    title="Loading editable weeks"
                    detail="Resolving the current and next weekly schedule drafts."
                  />
                ) : currentScheduleWeekChoiceQuery.isError ||
                  currentRouteDemandWeekChoiceQuery.isError ||
                  secondaryScheduleWeekChoiceQuery.isError ||
                  secondaryRouteDemandWeekChoiceQuery.isError ? (
                  <StatePanel
                    kind="error"
                    title="Weekly schedule chooser failed to load"
                    detail="Unable to resolve the current and next weekly schedule drafts."
                    onRetry={() => {
                      void currentScheduleWeekChoiceQuery.refetch();
                      void currentRouteDemandWeekChoiceQuery.refetch();
                      void secondaryScheduleWeekChoiceQuery.refetch();
                      void secondaryRouteDemandWeekChoiceQuery.refetch();
                    }}
                  />
                ) : (
                  <div className="route-demand-history-list">
                    {scheduleWeekChoices.map((choice) => (
                      <button
                        key={choice.workflowRunId}
                        type="button"
                        className="route-demand-history-list__item"
                        disabled={!choice.available}
                        onClick={() => {
                          openScheduleQuickEditForSelection(choice);
                        }}
                      >
                        <strong>{choice.label}</strong>
                        <span>{choice.dateRangeLabel}</span>
                        <span>{choice.available ? "Draft available" : choice.disabledReason ?? "Unavailable"}</span>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </section>
        </div>
      ) : null}
      {scheduleQuickEditTarget ? (
        <ScheduleQuickEditModal
          workflowRunId={scheduleQuickEditTarget.workflowRunId}
          targetArtifactVersionId={scheduleQuickEditTarget.artifactVersionId}
          routeDemandCoverageContext={scheduleQuickEditTarget.routeDemandCoverageContext}
          comparisonModeHint={scheduleQuickEditTarget.comparisonModeHint}
          onClose={() => {
            setScheduleQuickEditTarget(null);
          }}
        />
      ) : null}
      {isRouteDemandQuickEditOpen && activeWorkflowRunId ? (
        <RouteDemandQuickEditModal
          workflowRunId={activeWorkflowRunId}
          onClose={() => {
            setIsRouteDemandQuickEditOpen(false);
          }}
        />
      ) : null}
      {isDispatchCloseoutOpen && activeWorkflowRunId ? (
        <DispatchReportCloseoutModal
          workflowRunId={activeWorkflowRunId}
          onClose={() => {
            setIsDispatchCloseoutOpen(false);
          }}
        />
      ) : null}
      <DetailDrawer payload={payload} onClose={close} />
    </div>
  );
}
