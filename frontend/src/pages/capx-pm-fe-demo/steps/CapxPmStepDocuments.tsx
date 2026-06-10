import { useState } from "react";

import { CapxPmFeResponsiveTable, CapxPmFeSection, CapxPmFeStatusChip, type CapxPmFeColumn } from "../CapxPmFeDemoComponents";
import type { CapxPmFeDemoDocument, CapxPmFeDemoProject } from "../capxPmFeDemoTypes";

export function CapxPmStepDocuments({ project }: { project: CapxPmFeDemoProject }): JSX.Element {
  const [selectedDocumentId, setSelectedDocumentId] = useState(project.documents[0]?.id);
  const selectedDocument = project.documents.find((document) => document.id === selectedDocumentId) ?? project.documents[0];
  const columns: Array<CapxPmFeColumn<CapxPmFeDemoDocument>> = [
    { key: "document", label: "Document", render: (document) => document.name },
    { key: "type", label: "Type", render: (document) => document.type },
    { key: "version", label: "Version/date", render: (document) => document.versionDate },
    { key: "used", label: "Used for", render: (document) => document.usedFor },
    { key: "status", label: "Status", render: (document) => <CapxPmFeStatusChip status={document.status} /> },
    { key: "owner", label: "Owner", render: (document) => document.owner },
    {
      key: "action",
      label: "Action",
      render: (document) => (
        <button className="capx-pm-fe-inline-button" type="button" onClick={() => setSelectedDocumentId(document.id)}>
          {document.action}
        </button>
      )
    }
  ];

  return (
    <div data-testid="capx-pm-fe-step-documents">
      <CapxPmFeSection title="Document checklist" note="Wrong versions, missing files, and proof gaps">
        <CapxPmFeResponsiveTable
          columns={columns}
          rows={project.documents}
          testId="capx-pm-fe-documents-mobile-cards"
        />
      </CapxPmFeSection>

      {selectedDocument ? (
        <CapxPmFeSection title="Proof detail" note="Local UI state only">
          <article className="capx-pm-fe-proof-panel" aria-label="Document proof detail">
            <div>
              <span>Selected document</span>
              <strong>{selectedDocument.name}</strong>
            </div>
            <div>
              <span>Why PM cares</span>
              <strong>{selectedDocument.detail}</strong>
            </div>
            <div>
              <span>Owner</span>
              <strong>{selectedDocument.owner}</strong>
            </div>
            <div>
              <span>Status</span>
              <CapxPmFeStatusChip status={selectedDocument.status} />
            </div>
          </article>
        </CapxPmFeSection>
      ) : null}
    </div>
  );
}
