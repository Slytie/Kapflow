import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import { AppShell } from "@/app/AppShell";
import { BoardPage } from "@/pages/BoardPage";
import { CapxCeoCockpitAccessGate } from "@/pages/capx-ceo-cockpit-demo/CapxCeoCockpitAccessGate";
import { CapxCeoCockpitOverviewPage } from "@/pages/capx-ceo-cockpit-demo/CapxCeoCockpitOverviewPage";
import { CapxCeoCockpitProjectPage } from "@/pages/capx-ceo-cockpit-demo/CapxCeoCockpitProjectPage";
import { CapexEpicProgressPage } from "@/pages/CapexEpicProgressPage";
import { CapxPmFeDemoRoot } from "@/pages/capx-pm-fe-demo";
import { CapxPmFeDemoV2Root } from "@/pages/capx-pm-fe-demo-v2";
import { CapxUiOneWorkbenchPage } from "@/pages/capx-ui-one-demo/CapxUiOneWorkbenchPage";
import { CapxDesignAWorkbenchPage } from "@/pages/capx-ui-versions-demo/CapxDesignAWorkbenchPage";
import { CapxK12PmCockpitPage } from "@/pages/capx-ui-versions-demo/CapxK12PmCockpitPage";
import { CapxUiVersionsDemoPage } from "@/pages/capx-ui-versions-demo/CapxUiVersionsDemoPage";
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
            <Route path="/demo/capex/epic-progress" element={<CapexEpicProgressPage />} />
            <Route
              path="/demo/capx/ceo-cockpit"
              element={
                <CapxCeoCockpitAccessGate>
                  <CapxCeoCockpitOverviewPage />
                </CapxCeoCockpitAccessGate>
              }
            />
            <Route
              path="/demo/capx/ceo-cockpit/projects/:projectId"
              element={
                <CapxCeoCockpitAccessGate>
                  <CapxCeoCockpitProjectPage />
                </CapxCeoCockpitAccessGate>
              }
            />
            <Route path="/demo/capx/pm/*" element={<CapxPmFeDemoRoot />} />
            <Route path="/demo/capx/pm-v2/*" element={<CapxPmFeDemoV2Root />} />
            <Route path="/demo/capx/ui-one/*" element={<CapxUiOneWorkbenchPage />} />
            <Route path="/demo/capx/ui-versions" element={<CapxUiVersionsDemoPage />} />
            <Route path="/demo/capx/ui-versions/design-a" element={<CapxDesignAWorkbenchPage />} />
            <Route path="/demo/capx/ui-versions/design-a/:pageId" element={<CapxDesignAWorkbenchPage />} />
            <Route path="/demo/capx/ui-versions/k12-pm-cockpit" element={<CapxK12PmCockpitPage />} />
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
