import { NavLink } from "react-router-dom";

import { CapxPmPracticalStatusChip } from "./CapxPmPracticalStatusChip";
import { capxPmPracticalSteps } from "./capxPmPracticalMockData";
import type { CapxPmPracticalProject, CapxPmPracticalStepSlug } from "./capxPmPracticalTypes";
import { buildCapxPmPracticalStepHref } from "./capxPmPracticalViewModels";

interface CapxPmStepRailProps {
  project: CapxPmPracticalProject;
  selectedStepSlug: CapxPmPracticalStepSlug;
}

export function CapxPmStepRail({ project, selectedStepSlug }: CapxPmStepRailProps): JSX.Element {
  return (
    <nav className="capx-pm-practical-step-rail" aria-label="Project steps">
      {project.steps.map((stepState, index) => {
        const step = capxPmPracticalSteps[index];
        return (
          <NavLink
            aria-current={stepState.slug === selectedStepSlug ? "page" : undefined}
            key={stepState.slug}
            to={buildCapxPmPracticalStepHref(project, stepState.slug)}
          >
            <span>{step.number}</span>
            <strong>
              {step.number} {step.label}
            </strong>
            <CapxPmPracticalStatusChip status={stepState.status} />
          </NavLink>
        );
      })}
    </nav>
  );
}
