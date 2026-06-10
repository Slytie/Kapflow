import { Link, NavLink, Outlet } from "react-router-dom";

import { capxPmFeDemoState } from "./capxPmFeDemoMockData";
import "./capxPmFeDemo.css";

export function CapxPmFeDemoShell(): JSX.Element {
  return (
    <div className="capx-pm-fe-demo" data-testid="capx-pm-fe-shell">
      <aside className="capx-pm-fe-nav" aria-label="CAPX PM demo navigation">
        <Link className="capx-pm-fe-nav__brand" to="/demo/capx/pm/projects">
          CAPX PM
        </Link>
        <nav>
          <NavLink to="/demo/capx/pm/projects">My CAPX Projects</NavLink>
          <NavLink to="/demo/capx/pm/projects/P-104">Workspace</NavLink>
          <NavLink to="/demo/capx/pm/projects/P-104/gantt">Project Gantt</NavLink>
        </nav>
        <p>Fake local data only</p>
      </aside>
      <div className="capx-pm-fe-main">
        <header className="capx-pm-fe-topbar">
          <div>
            <p className="capx-pm-fe-eyebrow">Private PM design demo</p>
            <h1>CAPX PM Frontend Demo</h1>
          </div>
          <div className="capx-pm-fe-topbar__meta">
            <span>Updated {capxPmFeDemoState.generatedAt}</span>
            <span>Loopback review</span>
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  );
}
