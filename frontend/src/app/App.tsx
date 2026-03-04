import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { AppShell } from "@/app/AppShell";
import { BoardPage } from "@/pages/BoardPage";
import { ApprovalsPage } from "@/pages/ApprovalsPage";
import { ExceptionsPage } from "@/pages/ExceptionsPage";
import { MyWorkPage } from "@/pages/MyWorkPage";
import { OfficialOutputsPage } from "@/pages/OfficialOutputsPage";
import { RunDetailPage } from "@/pages/RunDetailPage";
import { RunsPage } from "@/pages/RunsPage";
import { TimelinePage } from "@/pages/TimelinePage";
import { DrawerProvider } from "@/lib/state/drawerContext";
import "@/app/app.css";

export function App(): JSX.Element {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false
          }
        }
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <DrawerProvider>
          <Routes>
            <Route path="/" element={<Navigate to="/board" replace />} />
            <Route element={<AppShell />}>
              <Route path="/board" element={<BoardPage />} />
              <Route path="/my-work" element={<MyWorkPage />} />
              <Route path="/approvals" element={<ApprovalsPage />} />
              <Route path="/exceptions" element={<ExceptionsPage />} />
              <Route path="/runs" element={<RunsPage />} />
              <Route path="/runs/:workflowRunId" element={<RunDetailPage />} />
              <Route path="/official-outputs" element={<OfficialOutputsPage />} />
              <Route path="/timeline" element={<TimelinePage />} />
            </Route>
          </Routes>
        </DrawerProvider>
      </Router>
    </QueryClientProvider>
  );
}
