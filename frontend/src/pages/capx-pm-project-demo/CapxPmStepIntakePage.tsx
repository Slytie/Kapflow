import type { CapxPmWorkspaceViewModel } from "./capxPmProjectViewModels";
import {
  CapxPmMockActionNotice,
  CapxPmStepCardGrid,
  CapxPmStepMatrix,
  CapxPmStepMetricStrip,
  CapxPmStepRegisterTable,
  CapxPmStepTimeline
} from "./CapxPmStepShared";

export function CapxPmStepIntakePage({ viewModel }: { viewModel: CapxPmWorkspaceViewModel }): JSX.Element {
  const { detail } = viewModel.stepState;

  return (
    <div className="capx-pm-step-body capx-pm-step-body--intake" data-testid="capx-pm-step-intake">
      <CapxPmStepMetricStrip metrics={detail.metrics} />
      <div className="capx-pm-step-layout">
        <CapxPmStepCardGrid title={detail.cardsTitle} cards={detail.cards} />
        <CapxPmStepMatrix
          title={detail.matrixTitle}
          rows={detail.matrixRows}
          columns={{
            label: "Module",
            current: "Activation",
            owner: "Accountable",
            basis: "Routing basis"
          }}
        />
        <CapxPmStepTimeline title={detail.timelineTitle} items={detail.timelineItems} />
        <CapxPmStepRegisterTable stepState={viewModel.stepState} label="Intake setup exceptions" />
        <CapxPmMockActionNotice label={detail.mockActionLabel} />
      </div>
    </div>
  );
}
