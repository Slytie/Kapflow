import { getCapxPmStatusClass, getCapxPmStatusLabel } from "./capxPmProjectStatus";
import type { CapxPmStatus } from "./capxPmProjectTypes";

interface CapxPmStatusChipProps {
  status: CapxPmStatus;
}

export function CapxPmStatusChip({ status }: CapxPmStatusChipProps): JSX.Element {
  const label = getCapxPmStatusLabel(status);
  return (
    <span
      className={`capx-pm-status-chip ${getCapxPmStatusClass(status)}`}
      aria-label={label}
      title={label}
      data-status-chip
    >
      <span className="capx-pm-visually-hidden">{label}</span>
    </span>
  );
}
