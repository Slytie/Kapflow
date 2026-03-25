import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { mutationLog } from "@/test/api/handlers";

function setFrontendOperatorContext(): void {
  const currentContext = getApiRequestContextHeaders();
  setApiRequestContextHeaders({
    ...currentContext,
    actorId: "human:frontend-operator",
    actorType: "human",
    actorRoles: "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  });
}

describe("LogisticsScheduleWorkpagePage", () => {
  it("renders inside the logistics shell and keeps what-if edits local", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics/workpages/schedule-v0");
    render(<App />);

    const page = await screen.findByTestId("schedule-workpage-page");
    expect(within(page).getByRole("heading", { name: "Weekly schedule review" })).toBeInTheDocument();
    expect(screen.getByLabelText("Secondary detail routes")).toBeInTheDocument();
    expect(screen.queryByText(/Server-authoritative view backed by HITL HTTP query contracts/i)).not.toBeInTheDocument();

    const sickCallsFieldset = screen.getByText("Scenario sick calls").closest("fieldset");
    expect(sickCallsFieldset).not.toBeNull();

    await user.click(within(sickCallsFieldset as HTMLElement).getByRole("checkbox", { name: "Parampreet Singh" }));
    await user.clear(screen.getByRole("spinbutton", { name: /Scenario added routes/i }));
    await user.type(screen.getByRole("spinbutton", { name: /Scenario added routes/i }), "2");
    await user.type(screen.getByRole("textbox", { name: /Planner note/i }), "Late-request what-if");

    expect(within(sickCallsFieldset as HTMLElement).getByRole("checkbox", { name: "Parampreet Singh" })).toBeChecked();
    expect(screen.getByRole("spinbutton", { name: /Scenario added routes/i })).toHaveValue(2);
    expect(screen.getByRole("textbox", { name: /Planner note/i })).toHaveValue("Late-request what-if");
    expect(mutationLog()).toEqual([]);
  });
});
