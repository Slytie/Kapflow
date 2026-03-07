import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { mutationLog } from "@/test/api/handlers";

describe("App smoke", () => {
  it("loads board, switches active user, and executes a claim as that user", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/board?run=wr-test-001");

    render(<App />);

    expect(await screen.findByTestId("board-page")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Claim" }).length).toBeGreaterThan(0);
    await user.selectOptions(screen.getByLabelText("Active user"), "dispatch-supervisor");

    const needsInformationLane = screen.getByLabelText("Needs Information");
    await user.click(within(needsInformationLane).getAllByRole("button", { name: "Claim" })[0]);
    await waitFor(() => {
      expect(mutationLog()).toContain("claim:ht-open-001");
    });
    await waitFor(() => {
      expect(screen.queryAllByText(/human:dispatch-supervisor-1/i).length).toBeGreaterThan(0);
    });
  });
});
