import type {
  ArtifactVersionRow,
  HumanTaskRow,
  WorkflowRunWorkspaceContract,
  WorkflowWorkspaceTaskWorkItem
} from "@/lib/types/contracts";
import type { DrawerArtifact, DrawerPayload, DrawerLink } from "@/lib/types/ui";
import { taskDisplayHeading } from "@/lib/workspace/taskLabels";

function artifactFileName(artifact: ArtifactVersionRow): string | null {
  const fileName = artifact.metadata_json?.file_name;
  if (typeof fileName === "string" && fileName.length > 0) {
    return fileName;
  }
  return null;
}

export function buildTaskArtifacts(
  task: HumanTaskRow,
  artifactVersions: ArtifactVersionRow[]
): DrawerArtifact[] {
  const byArtifactVersionId = new Map<string, DrawerArtifact>();

  for (const artifact of artifactVersions) {
    const links = artifact.links ?? [];
    const linkedToHumanTask = links.some(
      (link) => link.subject_kind === "human_task" && link.subject_id === task.human_task_id
    );
    const linkedToTaskRun = links.some(
      (link) => link.subject_kind === "task_run" && link.subject_id === task.task_run_id
    );
    const createdByTaskRun = artifact.task_run_id === task.task_run_id;
    if (!linkedToHumanTask && !linkedToTaskRun && !createdByTaskRun) {
      continue;
    }

    const sourceLabel = linkedToHumanTask ? "Task attachment" : "Step output";
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

export function buildTaskDetailPayload({
  task,
  item = null,
  artifactVersions = [],
  description = "Task details open in the centered task modal so cards can stay dense and synchronized with the graph.",
  links = []
}: {
  task: HumanTaskRow;
  item?: WorkflowWorkspaceTaskWorkItem | null;
  artifactVersions?: ArtifactVersionRow[];
  description?: string;
  links?: DrawerLink[];
}): DrawerPayload {
  const artifacts = buildTaskArtifacts(task, artifactVersions);
  return {
    title: taskDisplayHeading(task),
    subtitle: task.human_task_id,
    description,
    fields: [
      { label: "State", value: task.state },
      { label: "Owner role", value: task.owner_role ?? "n/a" },
      { label: "Assignee", value: task.assignee_actor_id ?? "unassigned" },
      { label: "Available actions", value: item?.available_actions.join(", ") || "none" },
      {
        label: "Missing required inputs",
        value: item?.missing_required_inputs.join(", ") || "none"
      },
      { label: "Artifacts", value: String(artifacts.length) }
    ],
    links,
    task: {
      human_task_id: task.human_task_id,
      workflow_run_id: task.workflow_run_id,
      task_run_id: task.task_run_id,
      stage_id: task.stage_id,
      task_kind: task.task_kind,
      state: task.state,
      created_at: task.created_at,
      updated_at: task.updated_at,
      assignee_actor_id: task.assignee_actor_id,
      assignee_actor_type: task.assignee_actor_type,
      owner_role: task.owner_role,
      candidate_roles: task.candidate_roles ?? [],
      linked_approval_id: task.linked_approval_id,
      blocked_on_kind: task.blocked_on_kind,
      blocked_on_ref: task.blocked_on_ref,
      available_actions: item?.available_actions ?? task.available_actions ?? [],
      blocking_reason_codes: item?.blocking_reason_codes ?? task.blocking_reason_codes ?? [],
      missing_required_inputs: item?.missing_required_inputs ?? task.missing_required_inputs ?? [],
      required_uploads: item?.required_uploads ?? task.required_uploads ?? [],
      required_reviews: item?.required_reviews ?? task.required_reviews ?? [],
      workpage_actions: item?.workpage_actions ?? task.workpage_actions ?? [],
      is_composite: task.is_composite ?? false,
      expansion_kind: task.expansion_kind ?? "none",
      subgraph_ref: task.subgraph_ref ?? null
    },
    artifacts,
    artifact_sources: [
      {
        workflow_run_id: task.workflow_run_id,
        subject_kind: "human_task",
        subject_id: task.human_task_id,
        source_label: "Task attachment"
      },
      {
        workflow_run_id: task.workflow_run_id,
        subject_kind: "task_run",
        subject_id: task.task_run_id,
        source_label: "Step output"
      }
    ]
  };
}

function workspaceTaskItems(
  workspace: WorkflowRunWorkspaceContract
): WorkflowWorkspaceTaskWorkItem[] {
  return [...workspace.user_work, ...workspace.blocking_work].filter(
    (item): item is WorkflowWorkspaceTaskWorkItem => item.item_kind === "human_task"
  );
}

export function findWorkspaceTaskItemByHumanTaskId(
  workspace: WorkflowRunWorkspaceContract,
  humanTaskId: string
): WorkflowWorkspaceTaskWorkItem | null {
  return (
    workspaceTaskItems(workspace).find((item) => item.human_task.human_task_id === humanTaskId) ??
    null
  );
}

export function findWorkspaceTaskItemByLinkedApprovalId(
  workspace: WorkflowRunWorkspaceContract,
  approvalId: string
): WorkflowWorkspaceTaskWorkItem | null {
  return (
    workspaceTaskItems(workspace).find((item) => item.human_task.linked_approval_id === approvalId) ??
    null
  );
}
