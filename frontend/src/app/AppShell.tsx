import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useIsFetching, useQuery, useQueryClient } from "@tanstack/react-query";

import { DetailDrawer } from "@/components/DetailDrawer";
import { FilterBar } from "@/components/FilterBar";
import { FreshnessBanner } from "@/components/FreshnessBanner";
import { InfoDialog } from "@/components/InfoDialog";
import { LogisticsFamilyNav } from "@/components/LogisticsFamilyNav";
import { StatePanel } from "@/components/StatePanel";
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
import { logisticsStoryRepository } from "@/lib/repositories";
import {
  apiConfig,
  getApiRequestContextHeaders,
  getApiViewerSession,
  setApiRequestContextHeaders,
  setApiViewerSession
} from "@/lib/api/config";
import { ACTOR_PROFILES } from "@/lib/actors";
import { useDrawer } from "@/lib/state/drawerContext";

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
  const isWorkspaceRoute = /^\/runs\/[^/]+\/workspace$/.test(location.pathname);
  const isTimelineRoute = location.pathname === "/timeline";
  const isDemoLogisticsRoute =
    location.pathname === "/demo/logistics" ||
    location.pathname.startsWith("/demo/logistics/");
  const isRunWorkpageRoute = /^\/runs\/[^/]+\/workpages(?:\/.*)?$/.test(location.pathname);
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
  const logisticsStory = logisticsStoryQuery.data;

  useEffect(() => {
    setIsUtilityMenuOpen(false);
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
          <NavLink className="app-shell__brand" to="/demo/logistics">
            Logistics Demo
          </NavLink>
          <div
            className="app-shell__actor-switcher"
            data-testid={
              viewerSession.actor_switching_allowed
                ? "actor-switcher"
                : "viewer-session-panel"
            }
          >
            {viewerSession.actor_switching_allowed ? (
              <>
                <label htmlFor="actor-switcher">Active user</label>
                <select
                  id="actor-switcher"
                  value={activeActorKey}
                  onChange={(event) => handleActorChange(event.currentTarget.value)}
                >
                  {ACTOR_PROFILES.map((profile) => (
                    <option key={profile.key} value={profile.key}>
                      {profile.label}
                    </option>
                  ))}
                </select>
                <p>{activeActor?.actorId ?? viewerSession.actor_id}</p>
              </>
            ) : (
              <div data-testid="viewer-session">
                <strong>Viewer session</strong>
                <p>{viewerSession.actor_id}</p>
                <p>{viewerSession.boundary_profile}</p>
              </div>
            )}
          </div>
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

      <DetailDrawer payload={payload} onClose={close} />
    </div>
  );
}
