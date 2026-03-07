import { useEffect, useState } from "react";

import { onetruthApi } from "@/lib/api/onetruthApi";
import { errorText } from "@/lib/api/errorText";
import { downloadBase64ToFile } from "@/lib/repositories/artifactAttachments";
import type { DrawerArtifact, DrawerPayload } from "@/lib/types/ui";

interface DetailDrawerProps {
  payload: DrawerPayload | null;
  onClose: () => void;
}

export function DetailDrawer({ payload, onClose }: DetailDrawerProps): JSX.Element {
  const [downloadError, setDownloadError] = useState<unknown>(null);
  const [downloadingArtifactVersionId, setDownloadingArtifactVersionId] = useState<string | null>(null);
  const [artifacts, setArtifacts] = useState<DrawerArtifact[]>([]);
  const [artifactLoadError, setArtifactLoadError] = useState<unknown>(null);
  const [artifactsLoading, setArtifactsLoading] = useState(false);

  useEffect(() => {
    setDownloadError(null);
    setDownloadingArtifactVersionId(null);
  }, [payload]);

  useEffect(() => {
    if (!payload) {
      setArtifacts([]);
      setArtifactLoadError(null);
      setArtifactsLoading(false);
      return;
    }
    if (payload.artifacts && payload.artifacts.length > 0) {
      setArtifacts(payload.artifacts);
      setArtifactLoadError(null);
      setArtifactsLoading(false);
      return;
    }
    if (!payload.artifact_sources || payload.artifact_sources.length === 0) {
      setArtifacts([]);
      setArtifactLoadError(null);
      setArtifactsLoading(false);
      return;
    }

    let cancelled = false;
    setArtifactsLoading(true);
    setArtifactLoadError(null);

    const loadArtifacts = async (): Promise<void> => {
      try {
        const byArtifactVersionId = new Map<string, DrawerArtifact>();
        for (const source of payload.artifact_sources ?? []) {
          const rows = await onetruthApi.listArtifactsForSubject({
            workflow_run_id: source.workflow_run_id,
            subject_kind: source.subject_kind,
            subject_id: source.subject_id
          });
          for (const row of rows) {
            if (byArtifactVersionId.has(row.artifact_version_id)) {
              continue;
            }
            const fileName = row.metadata_json?.file_name;
            byArtifactVersionId.set(row.artifact_version_id, {
              artifact_version_id: row.artifact_version_id,
              artifact_kind: row.artifact_kind,
              artifact_role: row.artifact_role ?? null,
              media_type: row.media_type,
              created_at: row.created_at,
              file_name: typeof fileName === "string" && fileName.length > 0 ? fileName : null,
              source_label: source.source_label
            });
          }
        }
        const loaded = Array.from(byArtifactVersionId.values()).sort((left, right) =>
          right.created_at.localeCompare(left.created_at)
        );
        if (!cancelled) {
          setArtifacts(loaded);
          setArtifactLoadError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setArtifacts([]);
          setArtifactLoadError(error);
        }
      } finally {
        if (!cancelled) {
          setArtifactsLoading(false);
        }
      }
    };

    void loadArtifacts();
    return () => {
      cancelled = true;
    };
  }, [payload]);

  if (!payload) {
    return <aside className="detail-drawer" aria-hidden="true" />;
  }

  const handleDownloadArtifact = async (artifact: DrawerArtifact): Promise<void> => {
    setDownloadError(null);
    setDownloadingArtifactVersionId(artifact.artifact_version_id);
    try {
      const downloaded = await onetruthApi.downloadArtifact(artifact.artifact_version_id);
      const metadataName = downloaded.artifact_version.metadata_json?.file_name;
      const fileName =
        artifact.file_name ??
        (typeof metadataName === "string" && metadataName.length > 0
          ? metadataName
          : downloaded.artifact_version.artifact_version_id);
      downloadBase64ToFile(
        downloaded.content_base64,
        fileName,
        downloaded.artifact_version.media_type
      );
    } catch (error) {
      setDownloadError(error);
    } finally {
      setDownloadingArtifactVersionId(null);
    }
  };

  return (
    <aside className="detail-drawer detail-drawer--open" aria-label="Details drawer">
      <header>
        <h2>{payload.title}</h2>
        {payload.subtitle ? <p>{payload.subtitle}</p> : null}
        <button type="button" className="link-button" onClick={onClose} aria-label="Close drawer">
          Close
        </button>
      </header>
      {payload.description ? <p className="detail-drawer__description">{payload.description}</p> : null}
      <dl>
        {payload.fields.map((field) => (
          <div key={field.label} className="detail-drawer__field">
            <dt>{field.label}</dt>
            <dd>{field.value}</dd>
          </div>
        ))}
      </dl>

      {artifacts.length > 0 ? (
        <section className="detail-drawer__artifacts" aria-label="Task artifacts">
          <h3>Task Artifacts ({artifacts.length})</h3>
          <ul className="detail-drawer__artifact-list">
            {artifacts.map((artifact) => (
              <li key={artifact.artifact_version_id} className="detail-drawer__artifact-row">
                <div className="detail-drawer__artifact-meta">
                  <p className="detail-drawer__artifact-name">
                    {artifact.file_name ?? artifact.artifact_kind}
                  </p>
                  <p className="detail-drawer__artifact-details">
                    {artifact.artifact_kind}
                    {artifact.artifact_role ? ` · ${artifact.artifact_role}` : ""}
                    {artifact.source_label ? ` · ${artifact.source_label}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  className="action-btn"
                  onClick={() => void handleDownloadArtifact(artifact)}
                  disabled={downloadingArtifactVersionId === artifact.artifact_version_id}
                >
                  Download
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {artifactsLoading ? (
        <p className="detail-drawer__hint">Loading task artifacts...</p>
      ) : null}

      {!artifactsLoading &&
      artifacts.length === 0 &&
      payload.artifact_sources &&
      payload.artifact_sources.length > 0 ? (
        <p className="detail-drawer__hint">No task artifacts are currently linked.</p>
      ) : null}

      {downloadError ? (
        <p className="detail-drawer__error">
          {errorText(downloadError, "Artifact download failed")}
        </p>
      ) : null}

      {artifactLoadError ? (
        <p className="detail-drawer__error">
          {errorText(artifactLoadError, "Task artifacts failed to load")}
        </p>
      ) : null}
    </aside>
  );
}
