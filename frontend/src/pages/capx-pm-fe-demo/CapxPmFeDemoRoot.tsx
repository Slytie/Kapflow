import { Navigate, Route, Routes } from "react-router-dom";

import { CapxPmFeDemoAccessGate } from "./CapxPmFeDemoAccessGate";
import { CapxPmFeDemoShell } from "./CapxPmFeDemoShell";
import { CapxPmFeNotFound } from "./CapxPmFeDemoComponents";
import { CapxPmProjectGanttPage } from "./CapxPmProjectGanttPage";
import { CapxPmProjectWorkspacePage } from "./CapxPmProjectWorkspacePage";
import { CapxPmProjectsPage } from "./CapxPmProjectsPage";

export function CapxPmFeDemoRoot(): JSX.Element {
  return (
    <CapxPmFeDemoAccessGate>
      <Routes>
        <Route element={<CapxPmFeDemoShell />}>
          <Route index element={<Navigate to="projects" replace />} />
          <Route path="projects" element={<CapxPmProjectsPage />} />
          <Route path="projects/:projectId" element={<CapxPmProjectWorkspacePage />} />
          <Route path="projects/:projectId/steps/:stepId" element={<CapxPmProjectWorkspacePage />} />
          <Route path="projects/:projectId/gantt" element={<CapxPmProjectGanttPage />} />
          <Route
            path="*"
            element={
              <CapxPmFeNotFound
                title="Demo route not found"
                body="This route is outside the approved CAPX PM demo route family."
                linkLabel="Back to My CAPX Projects"
                linkHref="/demo/capx/pm/projects"
                testId="capx-pm-fe-route-not-found"
              />
            }
          />
        </Route>
      </Routes>
    </CapxPmFeDemoAccessGate>
  );
}
