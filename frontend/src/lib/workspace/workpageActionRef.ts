import type { WorkpageActionRef } from "@/lib/types/workpages";

export interface WorkpageLocationState {
  workpageActionRef?: unknown;
}

function isSubjectKind(value: unknown): value is NonNullable<WorkpageActionRef["subject"]>["subject_kind"] {
  return value === "human_task" || value === "approval";
}

export function resolveWorkpageActionRef(
  state: unknown,
  options: {
    workflowRunId: string | null | undefined;
    workpageKind?: string | null | undefined;
    artifactVersionId?: string | null | undefined;
  }
): WorkpageActionRef | undefined {
  const locationState = state as WorkpageLocationState | null | undefined;
  const candidate = locationState?.workpageActionRef;
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    return undefined;
  }
  const actionRef = candidate as Record<string, unknown>;
  const actionId = actionRef.action_id;
  const workpageKind = actionRef.workpage_kind;
  const subjectWorkflowRunId = actionRef.workflow_run_id;
  const subjectArtifactVersionId = actionRef.artifact_version_id;
  const rawSubject = actionRef.subject;
  const subjectRecord =
    rawSubject && typeof rawSubject === "object" && !Array.isArray(rawSubject)
      ? (rawSubject as Record<string, unknown>)
      : null;
  const subjectKind = subjectRecord?.subject_kind;
  const subjectId = subjectRecord?.subject_id;
  if (
    typeof actionId !== "string" ||
    typeof workpageKind !== "string" ||
    typeof subjectWorkflowRunId !== "string"
  ) {
    return undefined;
  }
  if (!options.workflowRunId || subjectWorkflowRunId !== options.workflowRunId) {
    return undefined;
  }
  if (options.workpageKind && workpageKind !== options.workpageKind) {
    return undefined;
  }
  if (
    options.artifactVersionId &&
    typeof subjectArtifactVersionId === "string" &&
    subjectArtifactVersionId !== options.artifactVersionId
  ) {
    return undefined;
  }
  return {
    action_id: actionId,
    workpage_kind: workpageKind,
    workflow_run_id: subjectWorkflowRunId,
    artifact_version_id: typeof subjectArtifactVersionId === "string" ? subjectArtifactVersionId : null,
    subject:
      isSubjectKind(subjectKind) && typeof subjectId === "string"
        ? {
            subject_kind: subjectKind,
            subject_id: subjectId
          }
        : null
  };
}

export function mergeWorkpageActionRef(
  actionRef: WorkpageActionRef | null | undefined,
  carriedActionRef: WorkpageActionRef | null | undefined
): WorkpageActionRef | undefined {
  if (!actionRef && !carriedActionRef) {
    return undefined;
  }
  if (!actionRef) {
    return carriedActionRef ?? undefined;
  }
  if (!carriedActionRef?.subject) {
    return actionRef;
  }
  if (
    actionRef.workflow_run_id !== carriedActionRef.workflow_run_id ||
    actionRef.workpage_kind !== carriedActionRef.workpage_kind
  ) {
    return actionRef;
  }
  return {
    ...actionRef,
    subject: carriedActionRef.subject
  };
}

export function replaceWorkpageActionRefArtifactVersionId(
  actionRef: WorkpageActionRef | null | undefined,
  artifactVersionId: string
): WorkpageActionRef | undefined {
  if (!actionRef) {
    return undefined;
  }
  return {
    ...actionRef,
    artifact_version_id: artifactVersionId
  };
}
