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
    expect(within(summary).getByText("374")).toBeInTheDocument();
    expect(within(summary).getByText("6.1%")).toBeInTheDocument();
    expect(within(summary).getByText("351")).toBeInTheDocument();

    const timeline = screen.getByTestId("capex-epic-timeline");
    expect(within(timeline).getByRole("button", { name: /EPIC-136/i })).toBeInTheDocument();
    expect(within(timeline).getByRole("button", { name: /EPIC-152/i })).toBeInTheDocument();
    expect(
      within(timeline).getAllByText("ETA needs completion timestamp history")
    ).toHaveLength(17);
  });

  it("drills from an epic into task detail", async () => {
    const user = userEvent.setup();
    renderCapexProgress();

    await user.click(screen.getByRole("button", { name: /EPIC-145/i }));

    expect(
      screen.getByRole("heading", { name: "CAPEX K12/K3 fixture governance" })
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
      screen.getByRole("heading", { name: "CAPEX K12/K3 fixture governance" })
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
