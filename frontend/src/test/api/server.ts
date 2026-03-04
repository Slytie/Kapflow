import { setupServer } from "msw/node";

import { handlers } from "@/test/api/handlers";

export const server = setupServer(...handlers);
