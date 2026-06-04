import type { CapxPmWorkspaceViewModel } from "./capxPmProjectViewModels";
import {
  CapxPmMockActionNotice,
  CapxPmStepCardGrid,
  CapxPmStepMatrix,
  CapxPmStepMetricStrip,
  CapxPmStepRegisterTable,
  CapxPmStepTimeline
} from "./CapxPmStepShared";

export function CapxPmStepCorpusPage({ viewModel }: { viewModel: CapxPmWorkspaceViewModel }): JSX.Element {
  const { detail } = viewModel.stepState;

  return (
    <div className="capx-pm-step-body capx-pm-step-body--corpus" data-testid="capx-pm-step-corpus">
      <CapxPmStepMetricStrip metrics={detail.metrics} />
      <div className="capx-pm-step-layout">
        <CapxPmStepCardGrid title={detail.cardsTitle} cards={detail.cards} />
        <CapxPmStepMatrix
          title={detail.matrixTitle}
          rows={detail.matrixRows}
          columns={{
            label: "Packet",
            current: "Completeness",
            owner: "Resolver",
            basis: "Evidence basis"
          }}
        />
        <CapxPmStepTimeline title={detail.timelineTitle} items={detail.timelineItems} />
        <CapxPmStepRegisterTable stepState={viewModel.stepState} label="Source occurrence register" />
        <CapxPmMockActionNotice label={detail.mockActionLabel} />
      </div>
    </div>
  );
}
