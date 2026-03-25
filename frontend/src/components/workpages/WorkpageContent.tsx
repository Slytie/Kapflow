import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { FreshnessBanner } from "@/components/FreshnessBanner";
import type { WorkpageFreshness, WorkpageSourceMetadata } from "@/lib/types/contracts";
import type {
  WorkpageHistorySection,
  WorkpageNotePanelSection,
  WorkpageScalar,
  WorkpageSummaryCardsSection,
  WorkpageTableSection,
  WorkpageViewModel
} from "@/lib/types/workpages";

function formatWorkpageValue(value: WorkpageScalar): string {
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (value === null) {
    return "—";
  }
  return String(value);
}

interface WorkpageFrameProps {
  eyebrow: string;
  description: string;
  summaryItems: string[];
  model: WorkpageViewModel;
  testId: string;
  source: WorkpageSourceMetadata;
  freshness: WorkpageFreshness;
  onRefresh: () => void;
  isRefreshing?: boolean;
  pollIntervalMs?: number | false;
  children: ReactNode;
}

export function WorkpageFrame({
  eyebrow,
  description,
  summaryItems,
  model,
  testId,
  source,
  freshness,
  onRefresh,
  isRefreshing = false,
  pollIntervalMs,
  children
}: WorkpageFrameProps): JSX.Element {
  const sourceDatasetLabel = source.primary_dataset_key ?? "Composite source bundle";

  return (
    <section className="workpage-page" data-testid={testId}>
      <header className="workpage-page__hero">
        <div>
          <p className="timeline-page__eyebrow">{eyebrow}</p>
          <h1>{model.title}</h1>
          <p>{description}</p>
          <div className="timeline-page__summary">
            {summaryItems.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </div>
        <div className="workpage-page__hero-links">
          <Link className="link-button" to="/demo/logistics">
            Back to logistics demo
          </Link>
          <p>{model.workflow_id}</p>
          <p>{model.dataset_key}</p>
          <p>Mode: {model.mode}</p>
        </div>
      </header>

      <section className="workpage-panel">
        <header className="workpage-panel__header">
          <h2>Source grounding</h2>
          <p>Backend demo query served from repo-native workflow example bundles.</p>
        </header>
        <FreshnessBanner
          lastRefreshedAt={freshness.generated_at}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
          pollIntervalMs={pollIntervalMs}
        />
        <div className="workpage-page__source-grid workpage-page__source-grid--metadata">
          <article className="workpage-page__source-item">
            <strong>Source mode</strong>
            <p>{source.mode}</p>
          </article>
          <article className="workpage-page__source-item">
            <strong>Primary dataset</strong>
            <p>{sourceDatasetLabel}</p>
          </article>
          <article className="workpage-page__source-item">
            <strong>Source version</strong>
            <p>{freshness.source_version}</p>
          </article>
        </div>
        <div className="workpage-page__source-grid">
          {Object.entries(model.source_examples).map(([key, value]) => (
            <article key={key} className="workpage-page__source-item">
              <strong>{key}</strong>
              <p>{value}</p>
            </article>
          ))}
        </div>
        {model.validation.warnings.length > 0 ? (
          <ul className="workpage-page__warning-list">
            {model.validation.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : null}
      </section>

      {children}
    </section>
  );
}

export function WorkpageSummaryCardsSection({
  section,
  className
}: {
  section: WorkpageSummaryCardsSection;
  className?: string;
}): JSX.Element {
  return (
    <section className={`workpage-panel${className ? ` ${className}` : ""}`}>
      <header className="workpage-panel__header">
        <h2>{section.title}</h2>
      </header>
      <div className="workpage-summary-cards">
        {section.cards.map((card) => (
          <article key={card.key} className="workpage-summary-card">
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}

export function WorkpageTableSection({
  section,
  className
}: {
  section: WorkpageTableSection;
  className?: string;
}): JSX.Element {
  return (
    <section className={`workpage-panel${className ? ` ${className}` : ""}`}>
      <header className="workpage-panel__header">
        <h2>{section.title}</h2>
      </header>
      <div className="workpage-table__wrap">
        <table className="workpage-table" data-testid={section.table_id}>
          <thead>
            <tr>
              {section.columns.map((column) => (
                <th key={column.key} scope="col">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {section.rows.map((row, index) => (
              <tr key={`${section.table_id}-${index}`}>
                {section.columns.map((column) => (
                  <td key={column.key}>{formatWorkpageValue(row[column.key] ?? null)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function WorkpageNotePanelSection({
  section,
  className
}: {
  section: WorkpageNotePanelSection;
  className?: string;
}): JSX.Element {
  return (
    <section className={`workpage-panel workpage-panel--note${className ? ` ${className}` : ""}`}>
      <header className="workpage-panel__header">
        <h2>{section.title}</h2>
      </header>
      <p>{section.body}</p>
    </section>
  );
}

export function WorkpageHistorySection({
  section,
  className
}: {
  section: WorkpageHistorySection;
  className?: string;
}): JSX.Element {
  return (
    <section className={`workpage-panel${className ? ` ${className}` : ""}`}>
      <header className="workpage-panel__header">
        <h2>{section.title}</h2>
      </header>
      <div className="workpage-history">
        {section.entries.map((entry) => (
          <article key={entry.label} className="workpage-history__item">
            <strong>{entry.label}</strong>
            <p>{entry.value}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
