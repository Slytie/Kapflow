import { AttachmentActions } from "@/components/AttachmentActions";
import { SeverityChip } from "@/components/SeverityChip";
import { StatusBadge } from "@/components/StatusBadge";
import type { FlagRow } from "@/lib/types/contracts";

interface FlagCardProps {
  flag: FlagRow;
  onDetails: () => void;
  onUpload?: (file: File) => void;
  onDownload?: () => void;
  actionPending?: boolean;
}

export function FlagCard({
  flag,
  onDetails,
  onUpload,
  onDownload,
  actionPending = false
}: FlagCardProps): JSX.Element {
  return (
    <article className="flag-card">
      <header>
        <h4>{flag.kind}</h4>
        <div className="flag-card__chips">
          <SeverityChip severity={flag.severity} />
          <StatusBadge status={flag.state} />
        </div>
      </header>
      <p>{flag.summary}</p>
      <AttachmentActions onUpload={onUpload} onDownload={onDownload} disabled={actionPending} />
      <button type="button" className="link-button" onClick={onDetails}>
        Details
      </button>
    </article>
  );
}
