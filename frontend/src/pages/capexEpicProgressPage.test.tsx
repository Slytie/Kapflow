import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { CapexEpicProgressPage } from "@/pages/CapexEpicProgressPage";

function renderCapexProgress(route = "/demo/capex/epic-progress") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/demo/capex/epic-progress" element={<CapexEpicProgressPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("CapexEpicProgressPage", () => {
  it("renders the full CAPEX epic timeline", () => {
    renderCapexProgress();

    const page = screen.getByTestId("capex-epic-progress-page");
    expect(within(page).getByRole("heading", { name: "CAPEX Epic Progress" })).toBeInTheDocument();
    const summary = screen.getByRole("region", { name: "CAPEX progress summary" });
    const metrics = within(summary).getByRole("group", { name: "CAPEX progress metrics" });
    expect(within(metrics).getByText("432")).toBeInTheDocument();
    expect(within(metrics).getByText("26.9%")).toBeInTheDocument();
    expect(within(metrics).getByText("316")).toBeInTheDocument();

    const roadmapProgress = screen.getByRole("region", { name: "CAPEX roadmap progress" });
    const roadmapProgressBar = within(roadmapProgress).getByRole("progressbar", {
      name: "CAPEX roadmap completion"
    });
    expect(roadmapProgressBar).toHaveAttribute("aria-valuenow", "26.9");
    expect(roadmapProgressBar).toHaveAttribute(
      "aria-valuetext",
      "26.9% complete, 316 remaining"
    );
    expect(within(roadmapProgress).getByText("116 completed")).toBeInTheDocument();
    expect(within(roadmapProgress).getByText("316 remaining")).toBeInTheDocument();

    const completionTrend = screen.getByRole("region", { name: "CAPEX completion over time" });
    const trendLine = within(completionTrend).getByRole("img", {
      name: "CAPEX completion trend line"
    });
    expect(trendLine).toHaveAttribute("data-point-count", "8");
    expect(trendLine).toHaveAttribute("data-projection-date", "2026-09-06");
    expect(within(completionTrend).getByText("26.9% current")).toBeInTheDocument();
    expect(within(completionTrend).getByText("84 timestamped completions")).toBeInTheDocument();
    expect(within(completionTrend).getByText("100%")).toBeInTheDocument();
    expect(within(completionTrend).getByText("32 undated baseline")).toBeInTheDocument();
    expect(within(completionTrend).getByText("116 done")).toBeInTheDocument();
    expect(within(completionTrend).getByText("Jun 23 to ETA Sep 06 at 100%")).toBeInTheDocument();

    const timeline = screen.getByTestId("capex-epic-timeline");
    expect(within(timeline).getByRole("button", { name: /EPIC-136/i })).toBeInTheDocument();
    expect(within(timeline).getByRole("button", { name: /EPIC-152/i })).toBeInTheDocument();
    expect(within(timeline).queryAllByText("ETA needs completion timestamp history")).toHaveLength(0);
    expect(
      within(timeline).getByRole("button", { name: /EPIC-139.*Done/i })
    ).toBeInTheDocument();
  }, 15000);

  it("shows EPIC-139 as accepted after final neutral-default validation", () => {
    renderCapexProgress("/demo/capex/epic-progress?epic=EPIC-139");

    expect(screen.getByRole("heading", { name: "CAPEX domain-boundary cleanup" })).toBeInTheDocument();
    const epicEstimate = screen.getByRole("region", { name: "EPIC-139 completion estimate" });
    expect(epicEstimate).toHaveTextContent("Complete");
    expect(epicEstimate).toHaveTextContent("100%");
    expect(epicEstimate).toHaveTextContent("Remaining0");
    expect(epicEstimate).toHaveTextContent("No remaining current-scope tasks.");
  });

  it("drills from an epic into task detail", async () => {
    const user = userEvent.setup();
    renderCapexProgress();

    await user.click(screen.getByRole("button", { name: /EPIC-145/i }));

    expect(
      screen.getByRole("heading", { name: "CAPEX real-project fixture governance" })
    ).toBeInTheDocument();
    expect(screen.getByText("TASK-0470")).toBeInTheDocument();
    const epicEstimate = screen.getByRole("region", { name: "EPIC-145 completion estimate" });
    expect(within(epicEstimate).getByText("0%")).toBeInTheDocument();
    expect(within(epicEstimate).getByText("36")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: /TASK-0470.*Define capex\.sensitivity_manifest\.v1 schema/i
      })
    );

    expect(
      screen.getByRole("heading", { name: "Define capex.sensitivity_manifest.v1 schema" })
    ).toBeInTheDocument();
    expect(screen.getByText("Acceptance Criteria")).toBeInTheDocument();
    expect(screen.getByText("Source Row")).toBeInTheDocument();
    expect(screen.getByText("Not completed yet")).toBeInTheDocument();
    expect(screen.getByText("codex/tasks/TASK-0470-define-capex-sensitivity-manifest-v1-schema.md")).toBeInTheDocument();
  }, 15000);

  it("opens a direct epic and task drilldown from URL state", () => {
    renderCapexProgress("/demo/capex/epic-progress?epic=EPIC-145&task=TASK-0470");

    expect(
      screen.getByRole("heading", { name: "CAPEX real-project fixture governance" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Define capex.sensitivity_manifest.v1 schema" })
    ).toBeInTheDocument();
  });

  it("shows blocked/review caveats and historical missing completion timestamps", () => {
    renderCapexProgress("/demo/capex/epic-progress?epic=EPIC-138&task=TASK-0241");

    expect(screen.getByText("1 blocked or needs-review task(s) remain.")).toBeInTheDocument();
    expect(
      screen.getByText("Completion timestamp missing for historical DONE task")
    ).toBeInTheDocument();
  });

  it("filters the timeline by status and search text", async () => {
    const user = userEvent.setup();
    renderCapexProgress();

    await user.click(screen.getByRole("button", { name: "Needs fresh check" }));
    const filteredTimeline = screen.getByTestId("capex-epic-timeline");
    expect(within(filteredTimeline).getByRole("button", { name: /EPIC-141/i })).toBeInTheDocument();
    expect(within(filteredTimeline).getByRole("button", { name: /EPIC-144/i })).toBeInTheDocument();
    expect(within(filteredTimeline).queryByRole("button", { name: /EPIC-139/i })).not.toBeInTheDocument();
    expect(within(filteredTimeline).queryByRole("button", { name: /EPIC-152/i })).not.toBeInTheDocument();

    await user.clear(screen.getByRole("searchbox"));
    await user.type(screen.getByRole("searchbox"), "TASK-0291");
    expect(within(filteredTimeline).getByRole("button", { name: /EPIC-144/i })).toBeInTheDocument();
    expect(within(filteredTimeline).queryByRole("button", { name: /EPIC-141/i })).not.toBeInTheDocument();
  }, 15000);
});
