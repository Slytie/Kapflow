import { Link, NavLink } from "react-router-dom";
import type { ReactNode } from "react";

import "./capxPmProjectWorkflow.css";

interface CapxPmProjectShellProps {
  children: ReactNode;
  title?: string;
  updatedAt: string;
}

export function CapxPmProjectShell({
  children,
  title = "PM Project Workflow",
  updatedAt
}: CapxPmProjectShellProps): JSX.Element {
  return (
    <div className="capx-pm-project-demo" data-testid="capx-pm-project-shell">
      <aside className="capx-pm-shell-nav" aria-label="CAPX PM demo navigation">
        <Link className="capx-pm-shell-nav__brand" to="/demo/capx/pm/projects" aria-label="CAPX PM project index">
          CAPX PM
        </Link>
        <nav>
          <NavLink to="/demo/capx/pm/projects">Projects</NavLink>
          <span aria-disabled="true">Steps</span>
          <span aria-disabled="true">Evidence</span>
          <span aria-disabled="true">Tasks</span>
          <span aria-disabled="true">Handoffs</span>
        </nav>
        <p className="capx-pm-shell-nav__mode">Mock data only</p>
      </aside>
      <div className="capx-pm-shell-main">
        <header className="capx-pm-shell-header">
          <div>
            <p className="capx-pm-eyebrow">Private demo</p>
            <h1>{title}</h1>
          </div>
          <div className="capx-pm-shell-header__meta">
            <span>Updated {updatedAt}</span>
            <span className="capx-pm-live-dot" aria-label="static mock data indicator" />
            <span>PM review workspace</span>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
