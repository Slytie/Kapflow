import { useQuery } from "@tanstack/react-query";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { LegacyScheduleNotice } from "@/components/LegacyScheduleNotice";
import { StatePanel } from "@/components/StatePanel";
import { TimelineRow } from "@/components/TimelineRow";
import { useShellFilters } from "@/app/useShellFilters";
import { timelineRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";

export function TimelinePage(): JSX.Element {
  const { filters } = useShellFilters();
  const { open } = useDrawer();

  const query = useQuery({
    queryKey: ["timeline", filters.workflowRunId, filters.query],
    queryFn: () =>
      timelineRepository.list({
        workflowRunId: filters.workflowRunId,
        query: filters.query
      }),
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (query.isLoading) {
    return <StatePanel kind="loading" title="Loading timeline" detail="Fetching timeline events." />;
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="Timeline failed to load"
        detail={errorText(query.error, "Unable to load timeline")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const rows = query.data ?? [];
  if (rows.length === 0) {
    return <StatePanel kind="empty" title="No timeline events in scope" detail="Try widening run filters." />;
  }

  const newest = rows[0];
  const oldest = rows[rows.length - 1];

  return (
    <section className="timeline-page" data-testid="timeline-page">
      <LegacyScheduleNotice surface="Timeline" />
      <header className="timeline-page__header">
        <div>
          <p className="timeline-page__eyebrow">Canonical Event Stream</p>
          <h2>Timeline (Legacy View)</h2>
        </div>
        <div className="timeline-page__summary">
          <span>{rows.length} events</span>
          <span>Latest #{newest.sequenceNo}</span>
          <span>Earliest #{oldest.sequenceNo}</span>
        </div>
      </header>

      <div className="timeline-page__rail">
        {rows.map((row) => (
          <TimelineRow
            key={row.eventId}
            row={row}
            onDetails={() =>
              open({
                title: row.eventType,
                subtitle: row.eventId,
                description: "Detailed event payload.",
                fields: [
                  { label: "Sequence", value: String(row.sequenceNo) },
                  { label: "Actor", value: row.actorId },
                  { label: "Subject", value: row.subject }
                ]
              })
            }
          />
        ))}
      </div>
    </section>
  );
}
