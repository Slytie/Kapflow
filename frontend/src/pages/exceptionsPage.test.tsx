import { screen } from "@testing-library/react";

import { ExceptionsPage } from "@/pages/ExceptionsPage";
import { renderRoute } from "@/test/renderRoute";

describe("ExceptionsPage", () => {
  it("renders severity and flag metadata", async () => {
    renderRoute(<ExceptionsPage />, {
      route: "/exceptions?run=wr-test-001",
      path: "/exceptions"
    });

    expect(await screen.findByText(/Courier C-104 did not report for shift/i)).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();
  });
});
