import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { useIsFetching, useQuery, useQueryClient } from "@tanstack/react-query";

import { DetailDrawer } from "@/components/DetailDrawer";
import { FilterBar } from "@/components/FilterBar";
import { FreshnessBanner } from "@/components/FreshnessBanner";
import { StatePanel } from "@/components/StatePanel";
import { useShellFilters } from "@/app/useShellFilters";
import { errorText } from "@/lib/api/errorText";
import {
  apiConfig,
  getApiRequestContextHeaders,
  getApiViewerSession,
  setApiRequestContextHeaders,
  setApiViewerSession
} from "@/lib/api/config";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { ACTOR_PROFILES } from "@/lib/actors";
import { useDrawer } from "@/lib/state/drawerContext";

const NAV_LINKS = [
  { to: "/demo/logistics", label: "Logistics Demo" },
  { to: "/my-work", label: "My Work" },
  { to: "/approvals", label: "Approvals" },
  { to: "/exceptions", label: "Exceptions" },
  { to: "/official-outputs", label: "Official Outputs" }
];

const SECONDARY_LINKS = [{ to: "/runs", label: "Run Details" }];

export function AppShell(): JSX.Element {
  const location = useLocation();
  const queryClient = useQueryClient();
  const isFetching = useIsFetching();
  const { filters, setFilters } = useShellFilters();
  const { payload, close } = useDrawer();
  const [viewerBootstrapReady, setViewerBootstrapReady] = useState(() => getApiViewerSession() !== null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const isWorkspaceRoute = /^\/runs\/[^/]+\/workspace$/.test(location.pathname);
  const isTimelineRoute = location.pathname === "/timeline";
  const isLogisticsShellRoute =
    location.pathname === "/demo/logistics" || location.pathname.startsWith("/demo/logistics/");
  const viewerQuery = useQuery({
    queryKey: ["viewer-session"],
    queryFn: () => onetruthApi.getViewerSession()
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

  useEffect(() => {
    return queryClient.getQueryCache().subscribe((event) => {
      const query = event?.query;
      if (!query) {
        return;
      }
      const dataUpdatedAt = query.state.dataUpdatedAt;
      if (dataUpdatedAt > 0) {
        setLastRefreshedAt(new Date(dataUpdatedAt).toISOString());
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
    const nextActor = ACTOR_PROFILES.find((profile) => profile.key === actorKey) ?? ACTOR_PROFILES[0];
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
        <div
          className="app-shell__actor-switcher"
          data-testid={viewerSession.actor_switching_allowed ? "actor-switcher" : "viewer-session-panel"}
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
        <nav>
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        {isLogisticsShellRoute ? (
          <div className="app-shell__secondary-nav" aria-label="Secondary detail routes">
            <p>Secondary detail routes</p>
            {SECONDARY_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        ) : null}
      </aside>

      <section className="app-shell__main">
        {isWorkspaceRoute || isTimelineRoute || isLogisticsShellRoute ? null : (
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
