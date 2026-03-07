import type { TimelineRowModel } from "@/lib/types/ui";

interface TimelineRowProps {
  row: TimelineRowModel;
  onDetails: () => void;
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

export function TimelineRow({ row, onDetails }: TimelineRowProps): JSX.Element {
  return (
    <article className="timeline-row">
      <div className="timeline-row__marker" aria-hidden="true" />
      <div className="timeline-row__surface">
        <header className="timeline-row__header">
          <span className="timeline-row__sequence">#{row.sequenceNo}</span>
          <h4>{row.eventType}</h4>
          <time dateTime={row.occurredAt}>{formatTimestamp(row.occurredAt)}</time>
        </header>
        <p className="timeline-row__details">{row.details}</p>
        <div className="timeline-row__meta">
          <span>Actor: {row.actorId}</span>
          <span>Subject: {row.subject}</span>
        </div>
        <button type="button" className="link-button" onClick={onDetails}>
          Details
        </button>
      </div>
    </article>
  );
}
