import type { CapxPmWorkspaceViewModel } from "./capxPmProjectViewModels";
import {
  CapxPmMockActionNotice,
  CapxPmStepCardGrid,
  CapxPmStepMatrix,
  CapxPmStepMetricStrip,
  CapxPmStepRegisterTable,
  CapxPmStepTimeline
} from "./CapxPmStepShared";

export function CapxPmStepAssumptionsPage({ viewModel }: { viewModel: CapxPmWorkspaceViewModel }): JSX.Element {
  const { detail } = viewModel.stepState;

  return (
    <div className="capx-pm-step-body capx-pm-step-body--assumptions" data-testid="capx-pm-step-assumptions">
      <CapxPmStepMetricStrip metrics={detail.metrics} />
      <div className="capx-pm-step-layout">
        <CapxPmStepCardGrid title={detail.cardsTitle} cards={detail.cards} />
        <CapxPmStepMatrix
          title={detail.matrixTitle}
          rows={detail.matrixRows}
          columns={{
            label: "Assumption",
            current: "Closure mode",
            owner: "Task owner",
            basis: "Evidence basis"
          }}
        />
        <CapxPmStepTimeline title={detail.timelineTitle} items={detail.timelineItems} />
        <CapxPmStepRegisterTable stepState={viewModel.stepState} label="Assumption exception register" />
        <CapxPmMockActionNotice label={detail.mockActionLabel} />
      </div>
    </div>
  );
}
