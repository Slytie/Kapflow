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
  approveDisabled?: boolean;
  rejectDisabled?: boolean;
  requestInfoDisabled?: boolean;
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
  approveDisabled = false,
  rejectDisabled = false,
  requestInfoDisabled = false,
  actionPending = false
}: ApprovalCardProps): JSX.Element {
  const autoApproveHint =
    approval.scope_ref === "Stage04"
      ? "Approving finalizes the daily packet and sends planning feedback automatically."
      : null;

  return (
    <article className="approval-card">
      <header>
        <h4>{approval.scope_ref}</h4>
        <StatusBadge status={approval.state} />
      </header>
      <p>{approval.approval_kind} · Required: {approval.required_role}</p>
      {autoApproveHint ? <p>{autoApproveHint}</p> : null}
      <ActionCluster
        actions={[
          {
            key: "approve",
            label: "Approve",
            tone: "positive",
            onClick: onApprove,
            disabled: actionPending || approveDisabled
          },
          {
            key: "reject",
            label: "Reject",
            tone: "negative",
            onClick: onReject,
            disabled: actionPending || rejectDisabled
          },
          {
            key: "request_more",
            label: "Request Info",
            onClick: onRequestInfo,
            disabled: actionPending || requestInfoDisabled
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
