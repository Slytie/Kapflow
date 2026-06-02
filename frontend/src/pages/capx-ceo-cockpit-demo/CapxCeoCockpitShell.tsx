import { Link, NavLink } from "react-router-dom";
import type { ReactNode } from "react";

import "./capxCeoCockpit.css";

interface CapxCeoCockpitShellProps {
  children: ReactNode;
  title?: string;
  updatedAt: string;
}

export function CapxCeoCockpitShell({
  children,
  title = "CEO Cockpit",
  updatedAt
}: CapxCeoCockpitShellProps): JSX.Element {
  return (
    <div className="capx-ceo-cockpit-demo" data-testid="capx-ceo-cockpit-shell">
      <aside className="capx-shell-nav" aria-label="CAPX demo navigation">
        <Link className="capx-shell-nav__brand" to="/demo/capx/ceo-cockpit" aria-label="CAPX cockpit home">
          CAPX
        </Link>
        <nav>
          <NavLink to="/demo/capx/ceo-cockpit">Cockpit</NavLink>
          <span aria-disabled="true">Projects</span>
          <span aria-disabled="true">Risks</span>
          <span aria-disabled="true">Approvals</span>
          <span aria-disabled="true">Evidence</span>
        </nav>
        <p className="capx-shell-nav__mode">Mock data only</p>
      </aside>
      <div className="capx-shell-main">
        <header className="capx-shell-header">
          <div>
            <p className="capx-shell-header__label">Private demo</p>
            <h1>{title}</h1>
          </div>
          <div className="capx-shell-header__meta">
            <span>Updated {updatedAt}</span>
            <span className="capx-live-dot" aria-label="static mock data indicator" />
            <span>CEO A. Morgan</span>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
