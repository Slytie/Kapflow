import { ActionCluster } from "@/components/ActionCluster";
import { AttachmentActions } from "@/components/AttachmentActions";
import { StatusBadge } from "@/components/StatusBadge";
import type { ApprovalRow } from "@/lib/types/contracts";

interface ApprovalCardProps {
  approval: ApprovalRow;
  onDetails: () => void;
  onApprove?: () => void;
  onReject?: () => void;
  onRequestInfo?: () => void;
  onUpload?: (file: File) => void;
  onDownload?: () => void;
  actionPending?: boolean;
}

export function ApprovalCard({
  approval,
  onDetails,
  onApprove,
  onReject,
  onRequestInfo,
  onUpload,
  onDownload,
  actionPending = false
}: ApprovalCardProps): JSX.Element {
  return (
    <article className="approval-card">
      <header>
        <h4>{approval.scope_ref}</h4>
        <StatusBadge status={approval.state} />
      </header>
      <p>{approval.approval_kind} · Required: {approval.required_role}</p>
      <ActionCluster
        actions={[
          { key: "approve", label: "Approve", tone: "positive", onClick: onApprove, disabled: actionPending },
          { key: "reject", label: "Reject", tone: "negative", onClick: onReject, disabled: actionPending },
          {
            key: "request_more",
            label: "Request Info",
            onClick: onRequestInfo,
            disabled: actionPending
          }
        ]}
      />
      <AttachmentActions onUpload={onUpload} onDownload={onDownload} disabled={actionPending} />
      <button type="button" className="link-button" onClick={onDetails}>
        Details
      </button>
    </article>
  );
}
