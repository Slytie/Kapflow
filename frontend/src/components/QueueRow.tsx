import { ActionCluster } from "@/components/ActionCluster";
import { AttachmentActions } from "@/components/AttachmentActions";
import { StatusBadge } from "@/components/StatusBadge";

interface QueueRowProps {
  title: string;
  subtitle: string;
  status: string;
  onDetails: () => void;
  onClaim?: () => void;
  onComplete?: () => void;
  onUpload?: () => void;
  onDownload?: () => void;
  actionPending?: boolean;
}

export function QueueRow({
  title,
  subtitle,
  status,
  onDetails,
  onClaim,
  onComplete,
  onUpload,
  onDownload,
  actionPending = false
}: QueueRowProps): JSX.Element {
  return (
    <article className="queue-row" data-testid="queue-row">
      <div className="queue-row__main">
        <h4>{title}</h4>
        <p>{subtitle}</p>
      </div>
      <StatusBadge status={status} />
      <AttachmentActions compact onUpload={onUpload} onDownload={onDownload} disabled={actionPending} />
      <ActionCluster
        actions={[
          { key: "claim", label: "Claim", onClick: onClaim, disabled: actionPending },
          {
            key: "complete",
            label: "Complete",
            tone: "positive",
            onClick: onComplete,
            disabled: actionPending
          }
        ]}
      />
      <button type="button" className="link-button" onClick={onDetails}>
        Details
      </button>
    </article>
  );
}
