import { StatusBadge } from "@/components/StatusBadge";
import type { PointerRow } from "@/lib/types/contracts";

interface PointerCardProps {
  pointer: PointerRow;
  onDetails: () => void;
}

export function PointerCard({ pointer, onDetails }: PointerCardProps): JSX.Element {
  return (
    <article className="pointer-card">
      <h4>{pointer.pointer_key}</h4>
      <p>{pointer.artifact_kind}</p>
      <p>{pointer.artifact_version_id}</p>
      <StatusBadge status={pointer.promotion_reason} />
      <button type="button" className="link-button" onClick={onDetails}>
        Details
      </button>
    </article>
  );
}
