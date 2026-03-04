import { ActionCluster } from "@/components/ActionCluster";
import { AttachmentActions } from "@/components/AttachmentActions";
import { StatusBadge } from "@/components/StatusBadge";
import type { HumanTaskRow } from "@/lib/types/contracts";

interface TaskCardWideProps {
  task: HumanTaskRow;
  onDetails: () => void;
  onClaim?: () => void;
  onComplete?: () => void;
  onNeedInfo?: () => void;
  onUpload?: (file: File) => void;
  onDownload?: () => void;
  actionPending?: boolean;
}

export function TaskCardWide({
  task,
  onDetails,
  onClaim,
  onComplete,
  onNeedInfo,
  onUpload,
  onDownload,
  actionPending = false
}: TaskCardWideProps): JSX.Element {
  const actions = [
    { key: "claim", label: "Claim", tone: "default" as const, onClick: onClaim, disabled: actionPending },
    {
      key: "complete",
      label: "Complete",
      tone: "positive" as const,
      onClick: onComplete,
      disabled: actionPending
    },
    {
      key: "request_info",
      label: "Need Info",
      tone: "negative" as const,
      onClick: onNeedInfo,
      disabled: actionPending
    }
  ];

  return (
    <article className="task-card-wide" data-testid="task-card-wide">
      <header>
        <h4>{task.stage_id} · {task.task_kind}</h4>
        <StatusBadge status={task.state} />
      </header>
      <p className="task-card-wide__meta">
        Owner: {task.owner_role ?? "n/a"} · Assignee: {task.assignee_actor_id ?? "unassigned"}
      </p>
      <div className="task-card-wide__actions">
        <ActionCluster actions={actions} />
        <AttachmentActions onUpload={onUpload} onDownload={onDownload} disabled={actionPending} />
      </div>
      <button type="button" className="link-button" onClick={onDetails}>
        Details
      </button>
    </article>
  );
}
