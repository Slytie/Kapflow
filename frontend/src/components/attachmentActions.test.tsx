import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AttachmentActions } from "@/components/AttachmentActions";
describe("AttachmentActions", () => {
  it("renders upload/download controls when used directly", () => {
    render(<AttachmentActions onUpload={() => undefined} onDownload={() => undefined} />);

    expect(screen.getByRole("button", { name: "Upload" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download" })).toBeInTheDocument();
  });

  it("calls upload and download callbacks from inline controls", async () => {
    const user = userEvent.setup();
    const onUpload = vi.fn();
    const onDownload = vi.fn();
    const { container } = render(
      <AttachmentActions onUpload={onUpload} onDownload={onDownload} />
    );

    const input = container.querySelector('input[type="file"]');
    if (!(input instanceof HTMLInputElement)) {
      throw new Error("file input not found");
    }
    const file = new File(["fixture-content"], "fixture.txt", { type: "text/plain" });
    await user.upload(input, file);
    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(onUpload).toHaveBeenCalledWith(file);

    await user.click(screen.getByRole("button", { name: "Download" }));
    expect(onDownload).toHaveBeenCalledTimes(1);
  });
});
