import { NavLink } from "react-router-dom";

import { CapxPmStatusChip } from "./CapxPmStatusChip";
import type { CapxPmStatus } from "./capxPmProjectTypes";
import type { CapxPmWorkspaceViewModel } from "./capxPmProjectViewModels";

interface CapxPmProjectStepRailProps {
  steps: CapxPmWorkspaceViewModel["steps"];
}

function statusRailClass(status: CapxPmStatus): string {
  return `capx-pm-step-rail__link capx-pm-step-rail__link--${status}`;
}

export function CapxPmProjectStepRail({ steps }: CapxPmProjectStepRailProps): JSX.Element {
  return (
    <nav className="capx-pm-step-rail" aria-label="CAPX PM workflow steps">
      {steps.map(({ step, state, href }) => (
        <NavLink key={step.slug} to={href} className={({ isActive }) => `${statusRailClass(state.status)}${isActive ? " is-active" : ""}`}>
          <span className="capx-pm-step-rail__number">{step.number}</span>
          <span>
            <strong>{step.shortTitle}</strong>
            <small>{step.workflowId}</small>
          </span>
          <CapxPmStatusChip status={state.status} />
        </NavLink>
      ))}
    </nav>
  );
}
