import { CapxPmStatusChip } from "./CapxPmStatusChip";
import type {
  CapxPmDetailCard,
  CapxPmDetailMatrixRow,
  CapxPmDetailMetric,
  CapxPmDetailTimelineItem,
  CapxPmStepState
} from "./capxPmProjectTypes";

interface MetricStripProps {
  metrics: CapxPmDetailMetric[];
}

interface CardGridProps {
  title: string;
  cards: CapxPmDetailCard[];
}

interface MatrixProps {
  title: string;
  rows: CapxPmDetailMatrixRow[];
  columns?: {
    label: string;
    current: string;
    owner: string;
    basis: string;
  };
}

interface TimelineProps {
  title: string;
  items: CapxPmDetailTimelineItem[];
}

interface RegisterTableProps {
  stepState: CapxPmStepState;
  label?: string;
}

function sectionId(title: string): string {
  return `capx-pm-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "")}`;
}

export function CapxPmStepMetricStrip({ metrics }: MetricStripProps): JSX.Element {
  return (
    <dl className="capx-pm-step-metrics">
      {metrics.map((metric) => (
        <div key={`${metric.label}-${metric.value}`}>
          <dt>{metric.label}</dt>
          <dd>
            <CapxPmStatusChip status={metric.status} />
            <span>{metric.value}</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function CapxPmStepCardGrid({ title, cards }: CardGridProps): JSX.Element {
  const id = sectionId(title);
  return (
    <section className="capx-pm-step-section" aria-labelledby={id}>
      <div className="capx-pm-step-section__header">
        <h3 id={id}>{title}</h3>
        <span>{cards.length} checks</span>
      </div>
      <div className="capx-pm-step-card-grid">
        {cards.map((card) => (
          <article key={card.title} className={`capx-pm-step-card capx-pm-step-card--${card.status}`}>
            <div>
              <strong>{card.title}</strong>
              <CapxPmStatusChip status={card.status} />
            </div>
            <span>{card.value}</span>
            <p>{card.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function CapxPmStepMatrix({
  title,
  rows,
  columns = {
    label: "Item",
    current: "State",
    owner: "Owner",
    basis: "Basis"
  }
}: MatrixProps): JSX.Element {
  const id = sectionId(title);
  return (
    <section className="capx-pm-step-section" aria-labelledby={id}>
      <div className="capx-pm-step-section__header">
        <h3 id={id}>{title}</h3>
        <span>{rows.length} rows</span>
      </div>
      <div className="capx-pm-step-matrix-wrap">
        <table className="capx-pm-step-matrix">
          <thead>
            <tr>
              <th>{columns.label}</th>
              <th>{columns.current}</th>
              <th>{columns.owner}</th>
              <th>{columns.basis}</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className={row.status === "critical" ? "capx-pm-row--critical" : ""}>
                <td>{row.label}</td>
                <td>{row.current}</td>
                <td>{row.owner}</td>
                <td>{row.basis}</td>
                <td>
                  <CapxPmStatusChip status={row.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function CapxPmStepTimeline({ title, items }: TimelineProps): JSX.Element {
  const id = sectionId(title);
  return (
    <section className="capx-pm-step-section" aria-labelledby={id}>
      <div className="capx-pm-step-section__header">
        <h3 id={id}>{title}</h3>
        <span>static strip</span>
      </div>
      <ol className="capx-pm-step-timeline">
        {items.map((item) => (
          <li key={`${item.marker}-${item.label}`}>
            <span>{item.marker}</span>
            <div>
              <strong>{item.label}</strong>
              <p>{item.body}</p>
            </div>
            <CapxPmStatusChip status={item.status} />
          </li>
        ))}
      </ol>
    </section>
  );
}

export function CapxPmStepRegisterTable({ stepState, label = "Projection register" }: RegisterTableProps): JSX.Element {
  const id = sectionId(label);
  return (
    <section className="capx-pm-step-section" aria-labelledby={id}>
      <div className="capx-pm-step-section__header">
        <h3 id={id}>{label}</h3>
        <span>{stepState.registerRows.length} rows</span>
      </div>
      <div className="capx-pm-step-matrix-wrap">
        <table className="capx-pm-step-matrix">
          <thead>
            <tr>
              <th>Register item</th>
              <th>State / issue</th>
              <th>Owner</th>
              <th>Evidence basis</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {stepState.registerRows.map((registerRow) => (
              <tr key={registerRow.id} className={registerRow.status === "critical" ? "capx-pm-row--critical" : ""}>
                <td>{registerRow.primary}</td>
                <td>{registerRow.secondary}</td>
                <td>{registerRow.owner}</td>
                <td>{registerRow.basis}</td>
                <td>
                  <CapxPmStatusChip status={registerRow.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function CapxPmMockActionNotice({ label }: { label: string }): JSX.Element {
  return (
    <div className="capx-pm-mock-action">
      <button type="button" disabled>
        {label}
      </button>
      <p>Mock control only. This route cannot approve, close, promote, publish, or create official CAPX truth.</p>
    </div>
  );
}
