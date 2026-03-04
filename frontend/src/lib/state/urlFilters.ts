import type { URLSearchParamsInit } from "react-router-dom";

import type { ShellFilters } from "@/lib/types/ui";

export const DEFAULT_FILTERS: ShellFilters = {
  workflowRunId: "all",
  state: "all",
  assignee: "all",
  severity: "all",
  query: ""
};

export function parseFilters(params: URLSearchParams): ShellFilters {
  return {
    workflowRunId: params.get("run")?.trim() || DEFAULT_FILTERS.workflowRunId,
    state: params.get("state") ?? DEFAULT_FILTERS.state,
    assignee: params.get("assignee") ?? DEFAULT_FILTERS.assignee,
    severity: params.get("severity") ?? DEFAULT_FILTERS.severity,
    query: params.get("q") ?? DEFAULT_FILTERS.query
  };
}

export function toSearchParams(filters: ShellFilters): URLSearchParamsInit {
  const payload: Record<string, string> = {
    run: filters.workflowRunId,
    state: filters.state,
    assignee: filters.assignee,
    severity: filters.severity,
    q: filters.query
  };

  return payload;
}
