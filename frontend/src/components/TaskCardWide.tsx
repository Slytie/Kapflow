import { ActionCluster } from "@/components/ActionCluster";
import { AttachmentActions } from "@/components/AttachmentActions";
import { StatusBadge } from "@/components/StatusBadge";
import type { HumanTaskRow } from "@/lib/types/contracts";
import { taskDisplayHeading } from "@/lib/workspace/taskLabels";
import type { ActionItem } from "@/components/ActionCluster";

interface TaskCardWideProps {
  task: HumanTaskRow;
  onDetails: () => void;
  onClaim?: () => void;
  onComplete?: () => void;
  onNeedInfo?: () => void;
  onUpload?: (file: File) => void;
  onDownload?: () => void;
  claimDisabled?: boolean;
  completeDisabled?: boolean;
  needInfoDisabled?: boolean;
  completeHint?: string;
  extraActions?: ActionItem[];
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
  claimDisabled = false,
  completeDisabled = false,
  needInfoDisabled = false,
  completeHint,
  extraActions = [],
  actionPending = false
}: TaskCardWideProps): JSX.Element {
  const actions: ActionItem[] = [
    {
      key: "claim",
      label: "Claim",
      tone: "default" as const,
      onClick: onClaim,
      disabled: actionPending || claimDisabled
    },
    {
      key: "complete",
      label: "Complete",
      tone: "positive" as const,
      onClick: onComplete,
      disabled: actionPending || completeDisabled
    },
    {
      key: "request_info",
      label: "Need Info",
      tone: "negative" as const,
      onClick: onNeedInfo,
      disabled: actionPending || needInfoDisabled
    },
    ...extraActions
  ].filter((action) => Boolean(action.onClick));

  return (
    <article className="task-card-wide" data-testid="task-card-wide">
      <header>
        <h4>{taskDisplayHeading(task)}</h4>
        <StatusBadge status={task.state} />
      </header>
      <p className="task-card-wide__meta">
        Owner: {task.owner_role ?? "n/a"} · Assignee: {task.assignee_actor_id ?? "unassigned"}
      </p>
      <div className="task-card-wide__actions">
        {actions.length > 0 ? <ActionCluster actions={actions} /> : null}
        <AttachmentActions onUpload={onUpload} onDownload={onDownload} disabled={actionPending} />
      </div>
      {completeHint ? <p className="task-card-wide__hint">{completeHint}</p> : null}
      <button type="button" className="link-button" onClick={onDetails}>
        Details
      </button>
    </article>
  );
}
