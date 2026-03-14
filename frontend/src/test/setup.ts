import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi } from "vitest";

import { resetApiRequestContextHeaders } from "@/lib/api/config";
import { resetApiState } from "@/test/api/handlers";
import { server } from "@/test/api/server";

const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  resetApiState();
  resetApiRequestContextHeaders();
  (URL.createObjectURL as unknown as { mockClear?: () => void }).mockClear?.();
  (URL.revokeObjectURL as unknown as { mockClear?: () => void }).mockClear?.();
});
beforeAll(() => {
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn(() => "blob:mock-url")
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn()
  });
});
afterAll(() => {
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    writable: true,
    value: originalCreateObjectURL
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    writable: true,
    value: originalRevokeObjectURL
  });
  server.close();
});
