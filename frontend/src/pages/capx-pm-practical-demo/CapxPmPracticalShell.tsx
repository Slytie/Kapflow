import { useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

import "./capxPmPractical.css";

type CapxPmPracticalTheme = "practical" | "command";

interface CapxPmPracticalShellProps {
  children: ReactNode;
  title?: string;
  updatedAt: string;
}

const THEME_KEY = "capx-pm-practical-demo-theme";

function readTheme(): CapxPmPracticalTheme {
  try {
    return window.sessionStorage.getItem(THEME_KEY) === "command" ? "command" : "practical";
  } catch {
    return "practical";
  }
}

function writeTheme(theme: CapxPmPracticalTheme): void {
  try {
    window.sessionStorage.setItem(THEME_KEY, theme);
  } catch {
    // Session-only preference; ignore storage failures.
  }
}

export function CapxPmPracticalShell({
  children,
  title = "PM Project Workspace",
  updatedAt
}: CapxPmPracticalShellProps): JSX.Element {
  const [theme, setTheme] = useState(readTheme);
  const isCommand = theme === "command";

  function toggleTheme(): void {
    const nextTheme: CapxPmPracticalTheme = isCommand ? "practical" : "command";
    writeTheme(nextTheme);
    setTheme(nextTheme);
  }

  return (
    <div
      className={`capx-pm-practical-demo ${isCommand ? "capx-pm-practical-demo--command" : ""}`}
      data-theme={theme}
      data-testid="capx-pm-practical-shell"
    >
      <aside className="capx-pm-practical-nav" aria-label="CAPX PM demo navigation">
        <Link className="capx-pm-practical-nav__brand" to="/demo/capx/pm/projects" aria-label="CAPX PM project list">
          CAPX PM
        </Link>
        <nav>
          <NavLink to="/demo/capx/pm/projects">Projects</NavLink>
          <span>Tasks</span>
          <span>Files</span>
          <span>Reports</span>
        </nav>
        <p>Mock data only</p>
      </aside>
      <div className="capx-pm-practical-main">
        <header className="capx-pm-practical-header">
          <div>
            <p className="capx-pm-practical-eyebrow">Private PM demo</p>
            <h1>{title}</h1>
          </div>
          <div className="capx-pm-practical-header__meta">
            <span>Updated {updatedAt}</span>
            <span className="capx-pm-practical-live-dot" aria-label="static mock data indicator" />
            <span>Local mock workspace</span>
            <button
              className="capx-pm-practical-theme-toggle"
              type="button"
              aria-pressed={isCommand}
              onClick={toggleTheme}
            >
              {isCommand ? "Practical theme" : "Command theme"}
            </button>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
