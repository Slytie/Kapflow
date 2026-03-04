interface SeverityChipProps {
  severity: string;
}

function severityToken(severity: string): string {
  const normalized = severity.toLowerCase();
  if (normalized === "high" || normalized === "critical") {
    return "high";
  }
  if (normalized === "medium") {
    return "medium";
  }
  return "low";
}

export function SeverityChip({ severity }: SeverityChipProps): JSX.Element {
  return <span className={`severity-chip severity-chip--${severityToken(severity)}`}>{severity}</span>;
}
