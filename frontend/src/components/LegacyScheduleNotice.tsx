import { Link } from "react-router-dom";

interface LegacyScheduleNoticeProps {
  surface: string;
}

export function LegacyScheduleNotice({ surface }: LegacyScheduleNoticeProps): JSX.Element {
  return (
    <p className="legacy-surface-notice">
      {surface} is a legacy schedule-planning regression view. Primary demo entrypoint:
      {" "}
      <Link to="/demo/logistics">/demo/logistics</Link>
    </p>
  );
}
