import type { CapxPmWorkspaceViewModel } from "./capxPmProjectViewModels";
import {
  CapxPmMockActionNotice,
  CapxPmStepCardGrid,
  CapxPmStepMatrix,
  CapxPmStepMetricStrip,
  CapxPmStepRegisterTable,
  CapxPmStepTimeline
} from "./CapxPmStepShared";

export function CapxPmStepInterfacesPage({ viewModel }: { viewModel: CapxPmWorkspaceViewModel }): JSX.Element {
  const { detail } = viewModel.stepState;

  return (
    <div className="capx-pm-step-body capx-pm-step-body--interfaces" data-testid="capx-pm-step-interfaces">
      <CapxPmStepMetricStrip metrics={detail.metrics} />
      <div className="capx-pm-step-layout">
        <CapxPmStepCardGrid title={detail.cardsTitle} cards={detail.cards} />
        <CapxPmStepMatrix
          title={detail.matrixTitle}
          rows={detail.matrixRows}
          columns={{
            label: "Interface",
            current: "Responsibility state",
            owner: "Provider / owner",
            basis: "Required proof"
          }}
        />
        <CapxPmStepTimeline title={detail.timelineTitle} items={detail.timelineItems} />
        <CapxPmStepRegisterTable stepState={viewModel.stepState} label="Required vs provided evidence" />
        <CapxPmMockActionNotice label={detail.mockActionLabel} />
      </div>
    </div>
  );
}
