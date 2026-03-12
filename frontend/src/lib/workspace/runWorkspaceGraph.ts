import { actorLabelForActorId, candidateActorLabelsForRoles } from "@/lib/actors";
import type {
  HumanTaskRow,
  WorkflowRunDetailContract,
  WorkflowWorkspaceGraphNode
} from "@/lib/types/contracts";
import type { DrawerArtifact, DrawerArtifactSource, DrawerPayload } from "@/lib/types/ui";

function titleCaseWords(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function compactLabels(labels: string[], maxItems = 2): string {
  if (labels.length <= maxItems) {
    return labels.join(", ");
  }
  const shown = labels.slice(0, maxItems).join(", ");
  return `${shown} +${labels.length - maxItems}`;
}

function chooseLatestStageTask(tasks: HumanTaskRow[]): HumanTaskRow | null {
  if (tasks.length === 0) {
    return null;
  }
  const active = tasks.filter((task) => task.state === "OPEN" || task.state === "CLAIMED");
  const pool = active.length > 0 ? active : tasks;
  return [...pool].sort((left, right) => {
    const leftTime = Date.parse(left.updated_at);
    const rightTime = Date.parse(right.updated_at);
    if (Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime !== rightTime) {
      return rightTime - leftTime;
    }
    return right.human_task_id.localeCompare(left.human_task_id);
  })[0];
}

function preferredTaskKindForNode(node: WorkflowWorkspaceGraphNode): string | null {
  const label = node.label.toLowerCase();
  if (label.includes("information")) {
    return "information_request";
  }
  if (label.includes("approval")) {
    return "final_review";
  }
  return null;
}

function artifactFileName(
  artifact: WorkflowRunDetailContract["artifact_versions"][number]
): string | null {
  const fileName = artifact.metadata_json?.file_name;
  if (typeof fileName === "string" && fileName.length > 0) {
    return fileName;
  }
  return null;
}

export function workspaceTab(workflowId: string): string {
  if (workflowId === "weekly_schedule_planning.v1") {
    return "Weekly Schedule Planning";
  }
  if (workflowId === "live_dispatch.v1") {
    return "Live Dispatch";
  }
  if (workflowId === "dispatch_reporting.v1") {
    return "Dispatch Reporting";
  }
  if (workflowId === "schedule_planning.v1") {
    return "Schedule Planning";
  }
  return "Workflow Workspace";
}

export function graphNodesWithResponsibility(
  nodes: WorkflowWorkspaceGraphNode[],
  tasks: HumanTaskRow[]
): WorkflowWorkspaceGraphNode[] {
  return nodes.map((node) => {
    const stageTasks = tasks.filter((task) => task.stage_id === node.stage_id);
    const preferredTaskKind = preferredTaskKindForNode(node);
    const preferredStageTasks =
      preferredTaskKind === null
        ? stageTasks
        : stageTasks.filter((task) => task.task_kind === preferredTaskKind);
    const latestTask =
      chooseLatestStageTask(preferredStageTasks) ?? chooseLatestStageTask(stageTasks);
    if (!latestTask) {
      return {
        ...node,
        responsibility_summary: null,
        responsibility_detail: null
      };
    }

    const detail = `Latest task: ${titleCaseWords(latestTask.task_kind)}`;
    if (latestTask.assignee_actor_id) {
      return {
        ...node,
        responsibility_summary: `Claimed by ${actorLabelForActorId(latestTask.assignee_actor_id)}`,
        responsibility_detail: detail
      };
    }

    if (latestTask.state === "OPEN") {
      const candidates = candidateActorLabelsForRoles(latestTask.candidate_roles ?? []);
      const summary =
        candidates.length > 0
          ? `Can claim: ${compactLabels(candidates)}`
          : `Can claim: ${compactLabels((latestTask.candidate_roles ?? []).map(titleCaseWords))}`;
      return {
        ...node,
        responsibility_summary: summary,
        responsibility_detail: detail
      };
    }

    return {
      ...node,
      responsibility_summary: "No active claimant",
      responsibility_detail: detail
    };
  });
}

export function stageArtifactSources(
  node: WorkflowWorkspaceGraphNode,
  runDetail: WorkflowRunDetailContract
): DrawerArtifactSource[] {
  const byKey = new Map<string, DrawerArtifactSource>();

  const addSource = (source: DrawerArtifactSource): void => {
    const key = `${source.subject_kind}:${source.subject_id}`;
    if (!byKey.has(key)) {
      byKey.set(key, source);
    }
  };

  for (const task of runDetail.human_tasks) {
    if (task.stage_id !== node.stage_id) {
      continue;
    }
    addSource({
      workflow_run_id: task.workflow_run_id,
      subject_kind: "human_task",
      subject_id: task.human_task_id,
      source_label: "Stage task attachment"
    });
    addSource({
      workflow_run_id: task.workflow_run_id,
      subject_kind: "task_run",
      subject_id: task.task_run_id,
      source_label: "Stage step output"
    });
  }

  for (const approval of runDetail.approvals) {
    if (approval.scope_ref !== node.stage_id) {
      continue;
    }
    addSource({
      workflow_run_id: approval.workflow_run_id,
      subject_kind: "approval",
      subject_id: approval.approval_id,
      source_label: "Stage approval evidence"
    });
  }

  if (node.stage_id === "Stage07") {
    for (const flag of runDetail.flags) {
      addSource({
        workflow_run_id: flag.workflow_run_id,
        subject_kind: "flag",
        subject_id: flag.flag_id,
        source_label: "Stage flag evidence"
      });
    }
  }

  return Array.from(byKey.values());
}

export function stageArtifacts(
  node: WorkflowWorkspaceGraphNode,
  runDetail: WorkflowRunDetailContract
): DrawerArtifact[] {
  const stageTaskIds = new Set<string>();
  const stageTaskRunIds = new Set<string>();
  for (const task of runDetail.human_tasks) {
    if (task.stage_id === node.stage_id) {
      stageTaskIds.add(task.human_task_id);
      stageTaskRunIds.add(task.task_run_id);
    }
  }

  const stageApprovalIds = new Set<string>();
  const stageApprovalTaskRunIds = new Set<string>();
  for (const approval of runDetail.approvals) {
    if (approval.scope_ref === node.stage_id) {
      stageApprovalIds.add(approval.approval_id);
      stageApprovalTaskRunIds.add(approval.task_run_id);
    }
  }

  const stagePointerArtifactIds = new Set<string>();
  for (const pointer of runDetail.pointers) {
    if (pointer.scope_kind === "stage" && pointer.scope_ref === node.stage_id) {
      stagePointerArtifactIds.add(pointer.artifact_version_id);
    }
  }

  const stageFlagIds = new Set<string>();
  if (node.stage_id === "Stage07") {
    for (const flag of runDetail.flags) {
      stageFlagIds.add(flag.flag_id);
    }
  }

  const byArtifactVersionId = new Map<string, DrawerArtifact>();

  for (const artifact of runDetail.artifact_versions) {
    const links = artifact.links ?? [];

    const linkedToStageTask = links.some(
      (link) => link.subject_kind === "human_task" && stageTaskIds.has(link.subject_id)
    );
    const linkedToStageTaskRun = links.some(
      (link) => link.subject_kind === "task_run" && stageTaskRunIds.has(link.subject_id)
    );
    const linkedToStageApproval = links.some(
      (link) => link.subject_kind === "approval" && stageApprovalIds.has(link.subject_id)
    );
    const linkedToStageFlag = links.some(
      (link) => link.subject_kind === "flag" && stageFlagIds.has(link.subject_id)
    );
    const createdByStageTaskRun = artifact.task_run_id ? stageTaskRunIds.has(artifact.task_run_id) : false;
    const createdByStageApprovalTaskRun = artifact.task_run_id
      ? stageApprovalTaskRunIds.has(artifact.task_run_id)
      : false;
    const pointerMatchesStage = stagePointerArtifactIds.has(artifact.artifact_version_id);
    const metadataStageId =
      typeof artifact.metadata_json?.stage_id === "string" ? artifact.metadata_json.stage_id : null;
    const metadataMatchesStage = metadataStageId === node.stage_id;

    if (
      !linkedToStageTask &&
      !linkedToStageTaskRun &&
      !linkedToStageApproval &&
      !linkedToStageFlag &&
      !createdByStageTaskRun &&
      !createdByStageApprovalTaskRun &&
      !pointerMatchesStage &&
      !metadataMatchesStage
    ) {
      continue;
    }

    let sourceLabel = "Stage evidence";
    if (linkedToStageTask) {
      sourceLabel = "Stage task attachment";
    } else if (linkedToStageTaskRun || createdByStageTaskRun || createdByStageApprovalTaskRun) {
      sourceLabel = "Stage step output";
    } else if (linkedToStageApproval) {
      sourceLabel = "Stage approval evidence";
    } else if (linkedToStageFlag) {
      sourceLabel = "Stage flag evidence";
    } else if (pointerMatchesStage) {
      sourceLabel = "Stage official output";
    }

    byArtifactVersionId.set(artifact.artifact_version_id, {
      artifact_version_id: artifact.artifact_version_id,
      artifact_kind: artifact.artifact_kind,
      artifact_role: artifact.artifact_role ?? null,
      media_type: artifact.media_type,
      created_at: artifact.created_at,
      file_name: artifactFileName(artifact),
      source_label: sourceLabel
    });
  }

  return Array.from(byArtifactVersionId.values()).sort((left, right) =>
    right.created_at.localeCompare(left.created_at)
  );
}

export function buildStageNodeDrawerPayload(
  node: WorkflowWorkspaceGraphNode,
  runDetail: WorkflowRunDetailContract
): DrawerPayload {
  const stageTasks = runDetail.human_tasks.filter((task) => task.stage_id === node.stage_id);
  const stageCompletedTasks = stageTasks.filter((task) => task.state === "COMPLETED").length;
  return {
    title: `${node.stage_id} ${node.label}`,
    subtitle: node.node_id,
    description: "Graph node status is projected by the server workspace endpoint.",
    fields: [
      { label: "Status", value: node.status },
      { label: "Row", value: String(node.row) },
      { label: "Column", value: String(node.column) },
      { label: "Blocking", value: node.is_blocking ? "yes" : "no" },
      { label: "Stage tasks", value: String(stageTasks.length) },
      { label: "Completed tasks", value: String(stageCompletedTasks) }
    ],
    artifacts: stageArtifacts(node, runDetail),
    artifact_sources: stageArtifactSources(node, runDetail)
  };
}
