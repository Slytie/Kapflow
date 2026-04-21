import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useIsFetching, useQuery, useQueryClient } from "@tanstack/react-query";

import { DetailDrawer } from "@/components/DetailDrawer";
import { FilterBar } from "@/components/FilterBar";
import { FreshnessBanner } from "@/components/FreshnessBanner";
import { InfoDialog } from "@/components/InfoDialog";
import { LogisticsFamilyNav } from "@/components/LogisticsFamilyNav";
import { StatePanel } from "@/components/StatePanel";
import { ScheduleQuickEditModal } from "@/pages/LogisticsScheduleWorkpagePage";
import { DriverPreferencesQuickEditModal } from "@/pages/LogisticsDriverPreferencesWorkpagePage";
import { RouteDemandQuickEditModal } from "@/pages/LogisticsRouteDemandWorkpagePage";
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
import type { WorkpageContract } from "@/lib/types/contracts";
import type {
  WorkpageDriverPreferencesAction,
  WorkpageRouteDemandAction,
  WorkpageScheduleAction
} from "@/lib/types/workpages";

const UTILITY_LINKS = [
  { to: "/my-work", label: "My Work" },
  { to: "/approvals", label: "Approvals" },
  { to: "/exceptions", label: "Exceptions" },
  { to: "/official-outputs", label: "Official Outputs" }
];

const SECONDARY_LINKS = [{ to: "/runs", label: "Run Details" }];

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

function routeDemandOpenLatestAction(
  contract: WorkpageContract | undefined
): WorkpageRouteDemandAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageRouteDemandAction =>
        action.workpage_kind === "route-demand-v0" &&
        action.kind === "open_latest" &&
        action.state === "available" &&
        Boolean(action.artifact_version_id)
    ) ?? null
  );
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

function driverPreferencesAction(
  contract: WorkpageContract | undefined,
  matcher: (action: WorkpageDriverPreferencesAction) => boolean
): WorkpageDriverPreferencesAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageDriverPreferencesAction =>
        action.workpage_kind === "driver-preferences-v0" &&
        matcher(action as WorkpageDriverPreferencesAction)
    ) ?? null
  );
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
  const [isScheduleQuickEditOpen, setIsScheduleQuickEditOpen] = useState(false);
  const [isRouteDemandQuickEditOpen, setIsRouteDemandQuickEditOpen] = useState(false);
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
  const isWorkpageFullPageRoute = isDemoLogisticsRoute || isRunWorkpageRoute;
  const routeSearchParams = useMemo(
    () => new URLSearchParams(location.search),
    [location.search]
  );
  const planningWeekId =
    routeSearchParams.get("planning_week_id")?.trim() || DEFAULT_LOGISTICS_PLANNING_WEEK_ID;
  const serviceDateId = routeSearchParams.get("service_date_id")?.trim() || undefined;
  const selectedModuleId = routeSearchParams.get("module")?.trim() || null;

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
    refetchInterval: apiConfig.pollIntervalMs
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
  const isWeeklyPlanningContext = Boolean(
    activeWorkflowRunId &&
      (activeWorkflowId === "weekly_schedule_planning.v1" ||
        activeModuleId === "weekly_schedule_planning" ||
        isWeeklyPlanningWorkpageRoute)
  );
  const scheduleQuickEditQuery = useQuery({
    queryKey: ["workpages", "schedule-v0", "landing", activeWorkflowRunId],
    queryFn: () => workpagesRepository.scheduleForRun(activeWorkflowRunId ?? ""),
    enabled: Boolean(activeWorkflowRunId && isWeeklyPlanningContext),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const driverPreferencesQuickEditQuery = useQuery({
    queryKey: ["workpages", "driver-preferences-v0", "run", activeWorkflowRunId],
    queryFn: () => workpagesRepository.driverPreferencesForRun(activeWorkflowRunId ?? ""),
    enabled: Boolean(activeWorkflowRunId && isWeeklyPlanningContext),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const routeDemandQuickEditQuery = useQuery({
    queryKey: ["workpages", "route-demand-v0", "run", activeWorkflowRunId],
    queryFn: () => workpagesRepository.routeDemandForRun(activeWorkflowRunId ?? ""),
    enabled: Boolean(activeWorkflowRunId && isWeeklyPlanningContext),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const scheduleQuickEditAction = scheduleOpenLatestDraftAction(scheduleQuickEditQuery.data);
  const driverPreferencesOpenAction = driverPreferencesAction(
    driverPreferencesQuickEditQuery.data,
    (action) =>
      action.kind === "open_latest" &&
      action.state === "available" &&
      Boolean(action.artifact_version_id)
  );
  const driverPreferencesCreateAction = driverPreferencesAction(
    driverPreferencesQuickEditQuery.data,
    (action) =>
      action.kind === "create_snapshot" &&
      action.state === "available" &&
      Boolean(action.create_path)
  );
  const routeDemandQuickEditAction = routeDemandOpenLatestAction(routeDemandQuickEditQuery.data);
  const canOpenDriversQuickEdit = Boolean(
    activeWorkflowRunId && (driverPreferencesOpenAction || driverPreferencesCreateAction)
  );
  const canOpenScheduleQuickEdit = Boolean(activeWorkflowRunId && scheduleQuickEditAction);
  const canOpenRouteDemandQuickEdit = Boolean(activeWorkflowRunId && routeDemandQuickEditAction);
  const weeklyActionUnavailableReason = !activeWorkflowRunId
    ? "No active workflow run is selected."
    : !isWeeklyPlanningContext
      ? "This action is available on weekly planning runs."
      : "The latest editable artifact is still resolving or unavailable.";
  const driversQuickEditUnavailableReason =
    activeWorkflowRunId && isWeeklyPlanningContext && driverPreferencesQuickEditQuery.isError
      ? "Driver preferences could not be loaded."
      : activeWorkflowRunId &&
          isWeeklyPlanningContext &&
          driverPreferencesQuickEditQuery.isSuccess &&
          !driverPreferencesOpenAction &&
          !driverPreferencesCreateAction
        ? "No editable driver preferences snapshot is available."
        : weeklyActionUnavailableReason;
  const scheduleQuickEditUnavailableReason =
    activeWorkflowRunId && isWeeklyPlanningContext && scheduleQuickEditQuery.isError
      ? "Weekly schedule could not be loaded."
      : activeWorkflowRunId &&
          isWeeklyPlanningContext &&
          scheduleQuickEditQuery.isSuccess &&
          !scheduleQuickEditAction
        ? "No editable weekly schedule draft is available."
        : weeklyActionUnavailableReason;
  const routeDemandQuickEditUnavailableReason =
    activeWorkflowRunId && isWeeklyPlanningContext && routeDemandQuickEditQuery.isError
      ? "Route demand could not be loaded."
      : activeWorkflowRunId &&
          isWeeklyPlanningContext &&
          routeDemandQuickEditQuery.isSuccess &&
          !routeDemandQuickEditAction
        ? "No latest route demand artifact is available."
        : weeklyActionUnavailableReason;

  useEffect(() => {
    setIsDriversQuickEditOpen(false);
    setIsScheduleQuickEditOpen(false);
    setIsRouteDemandQuickEditOpen(false);
  }, [activeWorkflowRunId]);

  const handleTaskSelect = (laneId: (typeof taskCards)[number]["lane_id"]): void => {
    const targetCard = taskCards.find((card) => card.lane_id === laneId);
    if (!targetCard?.top_item) {
      return;
    }
    open(buildBoardItemDrawerPayload(targetCard.top_item));
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
                {logisticsStoryQuery.isError
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
                  setIsScheduleQuickEditOpen(true);
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
      {isScheduleQuickEditOpen && activeWorkflowRunId ? (
        <ScheduleQuickEditModal
          workflowRunId={activeWorkflowRunId}
          onClose={() => {
            setIsScheduleQuickEditOpen(false);
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
      <DetailDrawer payload={payload} onClose={close} />
    </div>
  );
}
