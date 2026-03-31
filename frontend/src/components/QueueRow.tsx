import { ActionCluster } from "@/components/ActionCluster";
import { TaskDocumentCues } from "@/components/TaskDocumentCues";
import { StatusBadge } from "@/components/StatusBadge";
import type { TaskDocumentPreviewCue } from "@/lib/workspace/taskDocumentUi";

interface QueueRowProps {
  title: string;
  subtitle: string;
  status: string;
  hint?: string;
  documentCues?: TaskDocumentPreviewCue[];
  onDetails: () => void;
  onClaim?: () => void;
  onComplete?: () => void;
  actionPending?: boolean;
}

export function QueueRow({
  title,
  subtitle,
  status,
  hint,
  documentCues = [],
  onDetails,
  onClaim,
  onComplete,
  actionPending = false
}: QueueRowProps): JSX.Element {
  const actions = [
    { key: "claim", label: "Claim", onClick: onClaim, disabled: actionPending },
    {
      key: "complete",
      label: "Complete",
      tone: "positive" as const,
      onClick: onComplete,
      disabled: actionPending
    }
  ].filter((action) => Boolean(action.onClick));

  return (
    <article className="queue-row" data-testid="queue-row">
      <div className="queue-row__main">
        <div className="queue-row__headline">
          <h4>{title}</h4>
          <StatusBadge status={status} />
        </div>
        <p>{subtitle}</p>
        <TaskDocumentCues cues={documentCues} compact />
        {hint ? <p className="queue-row__hint">{hint}</p> : null}
      </div>
      <div className="queue-row__controls">
        {actions.length > 0 ? <ActionCluster actions={actions} /> : null}
        <button type="button" className="link-button" onClick={onDetails}>
          Details
        </button>
      </div>
    </article>
  );
}
