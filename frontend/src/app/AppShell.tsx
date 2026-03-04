import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { useIsFetching, useQueryClient } from "@tanstack/react-query";

import { DetailDrawer } from "@/components/DetailDrawer";
import { FilterBar } from "@/components/FilterBar";
import { FreshnessBanner } from "@/components/FreshnessBanner";
import { useShellFilters } from "@/app/useShellFilters";
import { apiConfig } from "@/lib/api/config";
import { useDrawer } from "@/lib/state/drawerContext";

const NAV_LINKS = [
  { to: "/board", label: "Board" },
  { to: "/my-work", label: "My Work" },
  { to: "/approvals", label: "Approvals" },
  { to: "/exceptions", label: "Exceptions" },
  { to: "/runs", label: "Runs" },
  { to: "/official-outputs", label: "Official Outputs" },
  { to: "/timeline", label: "Timeline" }
];

export function AppShell(): JSX.Element {
  const location = useLocation();
  const queryClient = useQueryClient();
  const isFetching = useIsFetching();
  const { filters, setFilters } = useShellFilters();
  const { payload, close } = useDrawer();
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

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

  const refresh = (): void => {
    void queryClient.invalidateQueries();
  };

  return (
    <div className="app-shell">
      <aside className="app-shell__nav">
        <h1>CompanyOS HITL</h1>
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
      </aside>

      <section className="app-shell__main">
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

        <div className="app-shell__content">
          <Outlet />
        </div>
      </section>

      <DetailDrawer payload={payload} onClose={close} />
    </div>
  );
}
