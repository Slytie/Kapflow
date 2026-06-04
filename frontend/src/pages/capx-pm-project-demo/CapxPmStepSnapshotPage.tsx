import type { CapxPmWorkspaceViewModel } from "./capxPmProjectViewModels";
import {
  CapxPmMockActionNotice,
  CapxPmStepCardGrid,
  CapxPmStepMatrix,
  CapxPmStepMetricStrip,
  CapxPmStepRegisterTable,
  CapxPmStepTimeline
} from "./CapxPmStepShared";

export function CapxPmStepSnapshotPage({ viewModel }: { viewModel: CapxPmWorkspaceViewModel }): JSX.Element {
  const { detail } = viewModel.stepState;

  return (
    <div className="capx-pm-step-body capx-pm-step-body--snapshot" data-testid="capx-pm-step-snapshot">
      <CapxPmStepMetricStrip metrics={detail.metrics} />
      <div className="capx-pm-step-layout">
        <CapxPmStepCardGrid title={detail.cardsTitle} cards={detail.cards} />
        <CapxPmStepMatrix
          title={detail.matrixTitle}
          rows={detail.matrixRows}
          columns={{
            label: "Input",
            current: "Validation state",
            owner: "Reviewer",
            basis: "Snapshot basis"
          }}
        />
        <CapxPmStepTimeline title={detail.timelineTitle} items={detail.timelineItems} />
        <CapxPmStepRegisterTable stepState={viewModel.stepState} label="Snapshot blocker register" />
        <CapxPmMockActionNotice label={detail.mockActionLabel} />
      </div>
    </div>
  );
}
