import type { ShellFilters } from "@/lib/types/ui";

interface FilterBarProps {
  filters: ShellFilters;
  onChange: (next: ShellFilters) => void;
}

export function FilterBar({ filters, onChange }: FilterBarProps): JSX.Element {
  return (
    <div className="filter-bar">
      <label>
        Workflow Run
        <input
          value={filters.workflowRunId === "all" ? "" : filters.workflowRunId}
          placeholder="all or wr-..."
          onChange={(event) => onChange({ ...filters, workflowRunId: event.target.value || "all" })}
        />
      </label>
      <label>
        State
        <select value={filters.state} onChange={(event) => onChange({ ...filters, state: event.target.value })}>
          <option value="all">All</option>
          <option value="OPEN">Open</option>
          <option value="CLAIMED">Claimed</option>
          <option value="COMPLETED">Completed</option>
          <option value="PENDING">Pending</option>
          <option value="RESPONDED">Responded</option>
          <option value="open">flag: open</option>
          <option value="triage">flag: triage</option>
          <option value="blocked">flag: blocked</option>
          <option value="resolved">flag: resolved</option>
          <option value="closed">flag: closed</option>
          <option value="waived">flag: waived</option>
        </select>
      </label>
      <label>
        Assignee
        <input
          value={filters.assignee === "all" ? "" : filters.assignee}
          placeholder="actor id"
          onChange={(event) => onChange({ ...filters, assignee: event.target.value || "all" })}
        />
      </label>
      <label>
        Severity
        <select value={filters.severity} onChange={(event) => onChange({ ...filters, severity: event.target.value })}>
          <option value="all">All</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="info">Info</option>
        </select>
      </label>
      <label>
        Search
        <input
          value={filters.query}
          placeholder="task kind, stage, role"
          onChange={(event) => onChange({ ...filters, query: event.target.value })}
        />
      </label>
    </div>
  );
}
