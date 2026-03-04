import { onetruthApi } from "@/lib/api/onetruthApi";
import type { TimelineEvent } from "@/lib/types/contracts";
import type { TimelineRowModel } from "@/lib/types/ui";

function summarizeEvent(event: TimelineEvent): string {
  const payload = event.payload;
  if (payload.human_task_id && payload.state) {
    return `Task ${String(payload.human_task_id)} -> ${String(payload.state)}`;
  }
  if (payload.approval_id && payload.response_kind) {
    return `Approval ${String(payload.approval_id)}: ${String(payload.response_kind)}`;
  }
  if (payload.flag_id && payload.state) {
    return `Flag ${String(payload.flag_id)} -> ${String(payload.state)}`;
  }
  return JSON.stringify(payload);
}

function subjectFromLinks(event: TimelineEvent): string {
  const subject = event.links.find((link) => link.rel === "subject");
  return subject ? `${subject.type}:${subject.id}` : "n/a";
}

export interface TimelineQuery {
  workflowRunId?: string;
  query?: string;
}

export const timelineRepository = {
  async list(query: TimelineQuery): Promise<TimelineRowModel[]> {
    const events = await onetruthApi.listTimelineEvents({
      workflow_run_id:
        query.workflowRunId && query.workflowRunId !== "all" ? query.workflowRunId : undefined,
      limit: 300,
      offset: 0
    });

    const rows = events
      .slice()
      .sort((a, b) => b.sequence_no - a.sequence_no)
      .map((event) => ({
        eventId: event.event_id,
        sequenceNo: event.sequence_no,
        eventType: event.event_type,
        occurredAt: event.occurred_at,
        actorId: event.actor.id,
        subject: subjectFromLinks(event),
        details: summarizeEvent(event),
        raw: event
      }));

    if (!query.query) {
      return rows;
    }

    const normalized = query.query.toLowerCase();
    return rows.filter(
      (row) =>
        row.eventType.toLowerCase().includes(normalized) ||
        row.details.toLowerCase().includes(normalized) ||
        row.subject.toLowerCase().includes(normalized)
    );
  }
};
