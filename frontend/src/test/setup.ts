import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";

import { resetApiRequestContextHeaders } from "@/lib/api/config";
import { resetApiState } from "@/test/api/handlers";
import { server } from "@/test/api/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  resetApiState();
  resetApiRequestContextHeaders();
});
afterAll(() => server.close());
