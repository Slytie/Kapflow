import type { TimelineRowModel } from "@/lib/types/ui";

interface TimelineRowProps {
  row: TimelineRowModel;
  onDetails: () => void;
}

export function TimelineRow({ row, onDetails }: TimelineRowProps): JSX.Element {
  return (
    <article className="timeline-row">
      <div>
        <h4>{row.eventType}</h4>
        <p>{row.details}</p>
      </div>
      <p className="timeline-row__meta">
        #{row.sequenceNo} · {new Date(row.occurredAt).toLocaleString()} · {row.actorId}
      </p>
      <button type="button" className="link-button" onClick={onDetails}>
        Details
      </button>
    </article>
  );
}
