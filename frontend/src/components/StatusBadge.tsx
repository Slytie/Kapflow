interface StatusBadgeProps {
  status: string;
}

function token(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized.includes("open") || normalized.includes("pending")) {
    return "warning";
  }
  if (normalized.includes("claimed") || normalized.includes("in_progress")) {
    return "active";
  }
  if (normalized.includes("completed") || normalized.includes("responded") || normalized.includes("resolved")) {
    return "success";
  }
  return "default";
}

export function StatusBadge({ status }: StatusBadgeProps): JSX.Element {
  return <span className={`status-badge status-badge--${token(status)}`}>{status}</span>;
}
