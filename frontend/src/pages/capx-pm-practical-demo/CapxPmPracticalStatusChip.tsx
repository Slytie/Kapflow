import { getCapxPmPracticalStatusClass, getCapxPmPracticalStatusLabel } from "./capxPmPracticalStatus";
import type { CapxPmPracticalStatus } from "./capxPmPracticalTypes";

interface CapxPmPracticalStatusChipProps {
  status: CapxPmPracticalStatus;
}

export function CapxPmPracticalStatusChip({ status }: CapxPmPracticalStatusChipProps): JSX.Element {
  const label = getCapxPmPracticalStatusLabel(status);

  return (
    <span
      className={`capx-pm-practical-status-chip ${getCapxPmPracticalStatusClass(status)}`}
      aria-label={label}
      title={label}
      data-status-chip
    >
      <span className="capx-pm-practical-visually-hidden">{label}</span>
    </span>
  );
}
