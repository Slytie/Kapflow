import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { mutationLog } from "@/test/api/handlers";

describe("DispatchReportWorkpagePage", () => {
  it("renders the draft/review page and keeps closeout edits local", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/logistics/workpages/eod-v0");
    render(<App />);

    const page = await screen.findByTestId("dispatch-report-workpage-page");
    expect(within(page).getByRole("heading", { name: "End-of-day report" })).toBeInTheDocument();
    expect(within(page).getByText(/Formula-integrity warning/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Secondary detail routes")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i }), "36 online");
    await user.click(screen.getAllByRole("button", { name: "Add entry" })[0]);
    await user.type(screen.getByRole("textbox", { name: "Rescues 1" }), "Route CX100 assist");
    await user.click(screen.getByRole("checkbox", { name: /Brahamvir Singh · CX100/i }));
    await user.type(screen.getAllByRole("textbox", { name: /Manager note/i })[0], "Review candidate tomorrow");

    expect(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i })).toHaveValue("36 online");
    expect(screen.getByRole("textbox", { name: "Rescues 1" })).toHaveValue("Route CX100 assist");
    expect(screen.getByRole("checkbox", { name: /Brahamvir Singh · CX100/i })).toBeChecked();
    expect(screen.getAllByRole("textbox", { name: /Manager note/i })[0]).toHaveValue("Review candidate tomorrow");
    expect(mutationLog()).toEqual([]);
  });
});
