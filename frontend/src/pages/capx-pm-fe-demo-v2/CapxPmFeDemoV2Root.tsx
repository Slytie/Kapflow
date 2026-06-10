import { Navigate, Route, Routes } from "react-router-dom";

import { CapxPmFeDemoV2AccessGate } from "./CapxPmFeDemoV2AccessGate";
import { CapxPmV2GanttPage } from "./CapxPmV2GanttPage";
import { CapxPmV2NotFound } from "./CapxPmV2Shared";
import { CapxPmV2ProjectPage } from "./CapxPmV2ProjectPage";
import { CapxPmV2ProjectsPage } from "./CapxPmV2ProjectsPage";

export function CapxPmFeDemoV2Root(): JSX.Element {
  return (
    <CapxPmFeDemoV2AccessGate>
      <Routes>
        <Route index element={<Navigate to="projects" replace />} />
        <Route path="projects" element={<CapxPmV2ProjectsPage />} />
        <Route path="projects/:projectId" element={<CapxPmV2ProjectPage />} />
        <Route path="projects/:projectId/steps/:stepId" element={<CapxPmV2ProjectPage />} />
        <Route path="projects/:projectId/gantt" element={<CapxPmV2GanttPage />} />
        <Route
          path="*"
          element={
            <CapxPmV2NotFound
              body="This route is outside the isolated PM V2 prototype."
              linkHref="/demo/capx/pm-v2/projects"
              linkLabel="Back to PM V2"
              testId="capx-pm-v2-route-not-found"
              title="V2 route not found"
            />
          }
        />
      </Routes>
    </CapxPmFeDemoV2AccessGate>
  );
}
