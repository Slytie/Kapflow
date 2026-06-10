import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { getCapxPmFeDemoStatusClass, getCapxPmFeDemoStatusLabel } from "@/pages/capx-pm-fe-demo/capxPmFeDemoStatus";
import type { CapxPmFeDemoProject, CapxPmFeDemoStatus } from "@/pages/capx-pm-fe-demo/capxPmFeDemoTypes";

export interface CapxPmV2Column<Row> {
  key: string;
  header: string;
  render: (row: Row) => ReactNode;
}

export function CapxPmV2StatusPill({ status }: { status: CapxPmFeDemoStatus }): JSX.Element {
  const label = getCapxPmFeDemoStatusLabel(status);
  return (
    <span className={`capx-pm-v2-status ${getCapxPmFeDemoStatusClass(status)}`} aria-label={label} title={label}>
      {label}
    </span>
  );
}

export function CapxPmV2Section({
  eyebrow,
  title,
  note,
  action,
  children,
  className = "",
  testId
}: {
  eyebrow: string;
  title: string;
  note?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  testId?: string;
}): JSX.Element {
  return (
    <section className={`capx-pm-v2-panel ${className}`.trim()} data-testid={testId}>
      <div className="capx-pm-v2-section-head">
        <div>
          <p className="capx-pm-v2-eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          {note ? <p>{note}</p> : null}
        </div>
        {action ? <div className="capx-pm-v2-section-head__action">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function CapxPmV2DataGrid<Row>({
  rows,
  columns,
  getKey,
  ariaLabel,
  mobileTestId
}: {
  rows: Row[];
  columns: CapxPmV2Column<Row>[];
  getKey: (row: Row) => string;
  ariaLabel: string;
  mobileTestId: string;
}): JSX.Element {
  return (
    <>
      <div className="capx-pm-v2-table-wrap">
        <table className="capx-pm-v2-table" aria-label={ariaLabel}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} scope="col">
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={getKey(row)}>
                {columns.map((column) => (
                  <td key={column.key}>{column.render(row)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="capx-pm-v2-mobile-cards" data-testid={mobileTestId}>
        {rows.map((row) => (
          <article className="capx-pm-v2-mobile-card" key={getKey(row)}>
            {columns.map((column) => (
              <div className="capx-pm-v2-mobile-card__row" key={column.key}>
                <span>{column.header}</span>
                <strong>{column.render(row)}</strong>
              </div>
            ))}
          </article>
        ))}
      </div>
    </>
  );
}

export function CapxPmV2InfoGrid({
  items
}: {
  items: Array<{
    label: string;
    value: ReactNode;
  }>;
}): JSX.Element {
  return (
    <dl className="capx-pm-v2-info-grid">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function CapxPmV2Shell({ children }: { children: ReactNode }): JSX.Element {
  return (
    <main className="capx-pm-v2" data-testid="capx-pm-v2-shell">
      <header className="capx-pm-v2-topbar">
        <div>
          <p className="capx-pm-v2-eyebrow">CAPX PM Demo V2</p>
          <h1>Attention cockpit</h1>
        </div>
        <nav aria-label="PM demo version links">
          <Link to="/demo/capx/pm/projects">V1</Link>
          <Link to="/demo/capx/pm-v2/projects">V2</Link>
        </nav>
      </header>
      {children}
    </main>
  );
}

export function CapxPmV2ProjectBadge({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  return (
    <div className="capx-pm-v2-project-badge">
      <span>{project.id}</span>
      <strong>{project.name}</strong>
      <p>
        {project.site} / {project.area}
      </p>
    </div>
  );
}

export function CapxPmV2NotFound({
  title,
  body,
  linkHref,
  linkLabel,
  testId
}: {
  title: string;
  body: string;
  linkHref: string;
  linkLabel: string;
  testId: string;
}): JSX.Element {
  return (
    <CapxPmV2Shell>
      <section className="capx-pm-v2-not-found" data-testid={testId}>
        <h2>{title}</h2>
        <p>{body}</p>
        <Link to={linkHref}>{linkLabel}</Link>
      </section>
    </CapxPmV2Shell>
  );
}
