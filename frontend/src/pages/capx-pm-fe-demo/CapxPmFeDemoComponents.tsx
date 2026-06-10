import { Link } from "react-router-dom";
import type { ReactNode } from "react";

import { getCapxPmFeDemoStatusClass, getCapxPmFeDemoStatusLabel } from "./capxPmFeDemoStatus";
import type { CapxPmFeDemoStatus } from "./capxPmFeDemoTypes";

export function CapxPmFeStatusChip({ status }: { status: CapxPmFeDemoStatus }): JSX.Element {
  const label = getCapxPmFeDemoStatusLabel(status);
  return (
    <span
      className={`capx-pm-fe-status ${getCapxPmFeDemoStatusClass(status)}`}
      aria-label={label}
      title={label}
      data-status-chip
    >
      {label}
    </span>
  );
}

export function CapxPmFeMetricCard({
  label,
  value,
  tone = "neutral"
}: {
  label: string;
  value: string | number;
  tone?: "neutral" | "alert" | "ready";
}): JSX.Element {
  return (
    <div className={`capx-pm-fe-metric capx-pm-fe-metric--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function CapxPmFeSection({
  title,
  note,
  children
}: {
  title: string;
  note?: string;
  children: ReactNode;
}): JSX.Element {
  return (
    <section className="capx-pm-fe-section">
      <div className="capx-pm-fe-section__head">
        <h2>{title}</h2>
        {note ? <p>{note}</p> : null}
      </div>
      {children}
    </section>
  );
}

export interface CapxPmFeColumn<T> {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
}

export function CapxPmFeResponsiveTable<T extends { id: string }>({
  columns,
  rows,
  testId
}: {
  columns: Array<CapxPmFeColumn<T>>;
  rows: T[];
  testId: string;
}): JSX.Element {
  return (
    <>
      <div className="capx-pm-fe-table-wrap">
        <table className="capx-pm-fe-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} scope="col">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                {columns.map((column) => (
                  <td key={column.key}>{column.render(row)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="capx-pm-fe-mobile-cards" data-testid={testId}>
        {rows.map((row) => (
          <article className="capx-pm-fe-mobile-card" key={row.id}>
            {columns.map((column) => (
              <div className="capx-pm-fe-mobile-card__row" key={column.key}>
                <span>{column.label}</span>
                <strong>{column.render(row)}</strong>
              </div>
            ))}
          </article>
        ))}
      </div>
    </>
  );
}

export function CapxPmFeNotFound({
  title,
  body,
  linkLabel,
  linkHref,
  testId
}: {
  title: string;
  body: string;
  linkLabel: string;
  linkHref: string;
  testId: string;
}): JSX.Element {
  return (
    <main className="capx-pm-fe-demo capx-pm-fe-demo--standalone">
      <section className="capx-pm-fe-not-found" data-testid={testId}>
        <p className="capx-pm-fe-eyebrow">CAPX PM Demo</p>
        <h1>{title}</h1>
        <p>{body}</p>
        <Link className="capx-pm-fe-button" to={linkHref}>
          {linkLabel}
        </Link>
      </section>
    </main>
  );
}
