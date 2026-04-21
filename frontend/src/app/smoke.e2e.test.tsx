import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { mutationLog } from "@/test/api/handlers";

describe("App smoke", () => {
  it("loads board, switches active user, and executes a claim from the task drawer", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/board?run=wr-test-001");

    render(<App />);

    expect(await screen.findByTestId("board-page")).toBeInTheDocument();
    await user.click(
      await screen.findByRole("button", {
        name: /Current user Frontend Operator\. Open actor switcher/i
      })
    );
    const actorMenu = within(await screen.findByTestId("actor-switcher")).getByRole("menu");
    const dispatchSupervisorOption = within(actorMenu)
      .getAllByRole("menuitemradio")
      .find((option) => within(option).queryByText("Dispatch Supervisor"));
    expect(dispatchSupervisorOption).toBeDefined();
    await user.click(dispatchSupervisorOption as HTMLElement);

    const needsInformationLane = screen.getByLabelText("Needs Information");
    await user.click(within(needsInformationLane).getAllByRole("button", { name: "Details" })[0]);
    await user.click(await screen.findByRole("button", { name: "Claim" }));
    await waitFor(() => {
      expect(mutationLog()).toContain("claim:ht-open-001");
    });
    await waitFor(() => {
      expect(screen.queryAllByText(/human:dispatch-supervisor-1/i).length).toBeGreaterThan(0);
    });
  });
});
