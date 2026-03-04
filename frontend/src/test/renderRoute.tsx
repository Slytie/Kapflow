import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { DrawerProvider } from "@/lib/state/drawerContext";

interface RenderRouteOptions {
  route: string;
  path: string;
}

export function renderRoute(element: ReactElement, options: RenderRouteOptions) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false }
    }
  });

  const renderWithProviders = (ui: ReactElement): ReactElement => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[options.route]}>
        <DrawerProvider>
          <Routes>
            <Route path={options.path} element={ui} />
          </Routes>
        </DrawerProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );

  const rendered = render(renderWithProviders(element));
  return {
    ...rendered,
    rerender: (nextElement: ReactElement) => rendered.rerender(renderWithProviders(nextElement))
  };
}
