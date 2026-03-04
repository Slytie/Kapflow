import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { mutationLog } from "@/test/api/handlers";

describe("App smoke", () => {
  it("loads board, opens drawer, and executes a safe inline action", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/board?run=wr-test-001");

    render(<App />);

    expect(await screen.findByTestId("board-page")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Claim" }).length).toBeGreaterThan(0);

    await user.click(screen.getAllByRole("button", { name: "Details" })[0]);
    expect(await screen.findByLabelText("Details drawer")).toBeInTheDocument();

    const needsInformationLane = screen.getByLabelText("Needs Information");
    await user.click(within(needsInformationLane).getAllByRole("button", { name: "Claim" })[0]);
    await waitFor(() => {
      expect(mutationLog()).toContain("claim:ht-open-001");
    });
  });
});
