import type { WorkpageActionSubjectContext } from "@/lib/types/contracts";

export interface WorkpageLocationState {
  workpageSubjectContext?: unknown;
}

function isSubjectKind(value: unknown): value is WorkpageActionSubjectContext["subject_kind"] {
  return value === "human_task" || value === "approval";
}

export function resolveWorkpageSubjectContext(
  state: unknown,
  options: {
    workflowRunId: string | null | undefined;
  }
): WorkpageActionSubjectContext | undefined {
  const locationState = state as WorkpageLocationState | null | undefined;
  const candidate = locationState?.workpageSubjectContext;
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    return undefined;
  }
  const subject = candidate as Record<string, unknown>;
  const subjectKind = subject.subject_kind;
  const subjectId = subject.subject_id;
  const subjectWorkflowRunId = subject.workflow_run_id;
  if (!isSubjectKind(subjectKind) || typeof subjectId !== "string" || typeof subjectWorkflowRunId !== "string") {
    return undefined;
  }
  if (!options.workflowRunId || subjectWorkflowRunId !== options.workflowRunId) {
    return undefined;
  }
  return {
    subject_kind: subjectKind,
    subject_id: subjectId,
    workflow_run_id: subjectWorkflowRunId
  };
}
