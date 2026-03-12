import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { useIsFetching, useQueryClient } from "@tanstack/react-query";

import { DetailDrawer } from "@/components/DetailDrawer";
import { FilterBar } from "@/components/FilterBar";
import { FreshnessBanner } from "@/components/FreshnessBanner";
import { useShellFilters } from "@/app/useShellFilters";
import { apiConfig, getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
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
  const [activeActorKey, setActiveActorKey] = useState(() => {
    const current = getApiRequestContextHeaders();
    return (
      ACTOR_PROFILES.find(
        (profile) =>
          profile.actorId === current.actorId &&
          profile.actorType === current.actorType &&
          profile.actorRoles === current.actorRoles
      )?.key ?? ACTOR_PROFILES[0].key
    );
  });
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const isWorkspaceRoute = /^\/runs\/[^/]+\/workspace$/.test(location.pathname);
  const isTimelineRoute = location.pathname === "/timeline";
  const isLogisticsDemoRoute = location.pathname === "/demo/logistics";
  const activeActor = ACTOR_PROFILES.find((profile) => profile.key === activeActorKey) ?? ACTOR_PROFILES[0];

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
    const current = getApiRequestContextHeaders();
    setApiRequestContextHeaders({
      ...current,
      actorId: activeActor.actorId,
      actorType: activeActor.actorType,
      actorRoles: activeActor.actorRoles
    });
    void queryClient.invalidateQueries();
  }, [activeActor, queryClient]);

  const refresh = (): void => {
    void queryClient.invalidateQueries();
  };

  return (
    <div className={`app-shell ${isWorkspaceRoute ? "app-shell--workspace" : ""}`}>
      <aside className="app-shell__nav">
        <div className="app-shell__actor-switcher" data-testid="actor-switcher">
          <label htmlFor="actor-switcher">Active user</label>
          <select
            id="actor-switcher"
            value={activeActorKey}
            onChange={(event) => setActiveActorKey(event.currentTarget.value)}
          >
            {ACTOR_PROFILES.map((profile) => (
              <option key={profile.key} value={profile.key}>
                {profile.label}
              </option>
            ))}
          </select>
          <p>{activeActor.actorId}</p>
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
        {isLogisticsDemoRoute ? (
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
        {isWorkspaceRoute || isTimelineRoute || isLogisticsDemoRoute ? null : (
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
