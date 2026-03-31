import { ActionCluster } from "@/components/ActionCluster";
import { TaskDocumentCues } from "@/components/TaskDocumentCues";
import { StatusBadge } from "@/components/StatusBadge";
import type { HumanTaskRow } from "@/lib/types/contracts";
import type { TaskDocumentPreviewCue } from "@/lib/workspace/taskDocumentUi";
import { taskDisplayHeading } from "@/lib/workspace/taskLabels";
import type { ActionItem } from "@/components/ActionCluster";

interface TaskCardWideProps {
  task: HumanTaskRow;
  onDetails: () => void;
  onClaim?: () => void;
  onComplete?: () => void;
  onNeedInfo?: () => void;
  claimDisabled?: boolean;
  completeDisabled?: boolean;
  needInfoDisabled?: boolean;
  completeHint?: string;
  documentCues?: TaskDocumentPreviewCue[];
  extraActions?: ActionItem[];
  actionPending?: boolean;
}

export function TaskCardWide({
  task,
  onDetails,
  onClaim,
  onComplete,
  onNeedInfo,
  claimDisabled = false,
  completeDisabled = false,
  needInfoDisabled = false,
  completeHint,
  documentCues = [],
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
      <header className="task-card-wide__header">
        <div className="task-card-wide__title-block">
          <p className="task-card-wide__eyebrow">{task.stage_id}</p>
          <h4>{taskDisplayHeading(task)}</h4>
        </div>
        <StatusBadge status={task.state} />
      </header>
      <dl className="task-card-wide__facts">
        <div>
          <dt>Owner</dt>
          <dd>{task.owner_role ?? "n/a"}</dd>
        </div>
        <div>
          <dt>Assignee</dt>
          <dd>{task.assignee_actor_id ?? "unassigned"}</dd>
        </div>
      </dl>
      <TaskDocumentCues cues={documentCues} compact />
      <div className="task-card-wide__actions">
        {actions.length > 0 ? <ActionCluster actions={actions} /> : null}
      </div>
      {completeHint ? <p className="task-card-wide__hint">{completeHint}</p> : null}
      <button type="button" className="link-button" onClick={onDetails}>
        Details
      </button>
    </article>
  );
}
