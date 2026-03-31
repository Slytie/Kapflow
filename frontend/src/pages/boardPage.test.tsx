import { screen } from "@testing-library/react";

import { BoardPage } from "@/pages/BoardPage";
import { renderRoute } from "@/test/renderRoute";

describe("BoardPage", () => {
  it("loads board data from API contracts and renders lanes", async () => {
    renderRoute(<BoardPage />, {
      route: "/board?run=wr-test-001",
      path: "/board"
    });

    expect(await screen.findByLabelText("Unclaimed")).toBeInTheDocument();
    expect(screen.getByLabelText("Claimed / In Progress")).toBeInTheDocument();
    expect(screen.getByLabelText("Awaiting Approval")).toBeInTheDocument();
    expect(screen.getByLabelText("Needs Information")).toBeInTheDocument();
    expect(screen.getByLabelText("Exception Work")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Stage06 · Information Request" })).toBeInTheDocument();
  });
});
