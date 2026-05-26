import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { AppShell } from "@/app/AppShell";
import { BoardPage } from "@/pages/BoardPage";
import { ApprovalsPage } from "@/pages/ApprovalsPage";
import {
  DispatchReportArtifactWorkpagePage,
  DispatchReportWorkpagePage
} from "@/pages/DispatchReportWorkpagePage";
import { ExceptionsPage } from "@/pages/ExceptionsPage";
import { MyWorkPage } from "@/pages/MyWorkPage";
import { OfficialOutputsPage } from "@/pages/OfficialOutputsPage";
import { RunDetailPage } from "@/pages/RunDetailPage";
import { RunWorkspacePage } from "@/pages/RunWorkspacePage";
import { RunsPage } from "@/pages/RunsPage";
import { TimelinePage } from "@/pages/TimelinePage";
import { LogisticsDemoPage } from "@/pages/LogisticsDemoPage";
import {
  LogisticsDriverPreferencesArtifactWorkpagePage,
  LogisticsDriverPreferencesWorkpagePage
} from "@/pages/LogisticsDriverPreferencesWorkpagePage";
import {
  LogisticsRouteDemandArtifactWorkpagePage,
  LogisticsRouteDemandWorkpagePage
} from "@/pages/LogisticsRouteDemandWorkpagePage";
import {
  LogisticsScheduleArtifactWorkpagePage,
  LogisticsSchedulePreviousWeekRealityPage,
  LogisticsScheduleWorkpagePage
} from "@/pages/LogisticsScheduleWorkpagePage";
import { WorkspaceHomePage } from "@/pages/WorkspaceHomePage";
import { DrawerProvider } from "@/lib/state/drawerContext";
import "@/app/app.css";
import "../styles/workspace.css";

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
            <Route path="/" element={<Navigate to="/demo/logistics" replace />} />
            <Route element={<AppShell />}>
              <Route path="/demo/logistics" element={<LogisticsDemoPage />} />
              <Route
                path="/runs/:workflowRunId/workpages/schedule-v0"
                element={<LogisticsScheduleWorkpagePage />}
              />
              <Route
                path="/runs/:workflowRunId/workpages/route-demand-v0"
                element={<LogisticsRouteDemandWorkpagePage />}
              />
              <Route
                path="/runs/:workflowRunId/workpages/driver-preferences-v0"
                element={<LogisticsDriverPreferencesWorkpagePage />}
              />
              <Route
                path="/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId"
                element={<LogisticsScheduleArtifactWorkpagePage />}
              />
              <Route
                path="/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId/reality/previous-week"
                element={<LogisticsSchedulePreviousWeekRealityPage />}
              />
              <Route
                path="/runs/:workflowRunId/workpages/route-demand-v0/artifacts/:artifactVersionId"
                element={<LogisticsRouteDemandArtifactWorkpagePage />}
              />
              <Route
                path="/runs/:workflowRunId/workpages/driver-preferences-v0/artifacts/:artifactVersionId"
                element={<LogisticsDriverPreferencesArtifactWorkpagePage />}
              />
              <Route path="/runs/:workflowRunId/workpages/eod-v0" element={<DispatchReportWorkpagePage />} />
              <Route
                path="/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId"
                element={<DispatchReportArtifactWorkpagePage />}
              />
              <Route path="/workspace" element={<WorkspaceHomePage />} />
              <Route path="/board" element={<BoardPage />} />
              <Route path="/my-work" element={<MyWorkPage />} />
              <Route path="/approvals" element={<ApprovalsPage />} />
              <Route path="/exceptions" element={<ExceptionsPage />} />
              <Route path="/runs" element={<RunsPage />} />
              <Route path="/runs/:workflowRunId" element={<RunDetailPage />} />
              <Route path="/runs/:workflowRunId/workspace" element={<RunWorkspacePage />} />
              <Route path="/official-outputs" element={<OfficialOutputsPage />} />
              <Route path="/timeline" element={<TimelinePage />} />
            </Route>
          </Routes>
        </DrawerProvider>
      </Router>
    </QueryClientProvider>
  );
}
