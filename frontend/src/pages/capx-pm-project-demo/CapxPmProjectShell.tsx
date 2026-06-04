import { Link, NavLink } from "react-router-dom";
import { useState } from "react";
import type { ReactNode } from "react";

import "./capxPmProjectWorkflow.css";

type CapxPmTheme = "terminal" | "light";

const THEME_KEY = "capx-pm-project-demo-theme";

interface CapxPmProjectShellProps {
  children: ReactNode;
  title?: string;
  updatedAt: string;
}

function readTheme(): CapxPmTheme {
  try {
    return window.sessionStorage.getItem(THEME_KEY) === "light" ? "light" : "terminal";
  } catch {
    return "terminal";
  }
}

function writeTheme(theme: CapxPmTheme): void {
  try {
    window.sessionStorage.setItem(THEME_KEY, theme);
  } catch {
    // Session storage can be unavailable in private or restricted browser modes.
  }
}

export function CapxPmProjectShell({
  children,
  title = "PM Project Workflow",
  updatedAt
}: CapxPmProjectShellProps): JSX.Element {
  const [theme, setTheme] = useState(readTheme);
  const isLight = theme === "light";

  function toggleTheme(): void {
    const nextTheme: CapxPmTheme = isLight ? "terminal" : "light";
    writeTheme(nextTheme);
    setTheme(nextTheme);
  }

  return (
    <div
      className={`capx-pm-project-demo ${isLight ? "capx-pm-project-demo--light" : ""}`}
      data-testid="capx-pm-project-shell"
      data-theme={theme}
    >
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
            <button type="button" className="capx-pm-theme-toggle" aria-pressed={isLight} onClick={toggleTheme}>
              {isLight ? "Terminal theme" : "Light theme"}
            </button>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
