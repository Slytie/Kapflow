import { createIdempotencyKey } from "@/lib/api/idempotency";
import type { ArtifactDownloadResult, ArtifactUploadPayload } from "@/lib/api/onetruthApi";
import { onetruthApi } from "@/lib/api/onetruthApi";
import type { ArtifactVersionRow } from "@/lib/types/contracts";

const MEDIA_TYPE_FALLBACK: Record<string, string> = {
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ".json": "application/json",
  ".txt": "text/plain"
};

function fileExtension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot).toLowerCase() : "";
}

function inferMediaType(file: File): string {
  if (file.type) {
    return file.type;
  }
  return MEDIA_TYPE_FALLBACK[fileExtension(file.name)] ?? "application/octet-stream";
}

export async function fileToBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function downloadBase64ToFile(
  base64Payload: string,
  fileName: string,
  mediaType: string
): void {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return;
  }
  if (typeof URL === "undefined" || typeof URL.createObjectURL !== "function") {
    return;
  }
  const binary = atob(base64Payload);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: mediaType || "application/octet-stream" });
  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(downloadUrl);
}

function downloadName(artifact: ArtifactVersionRow): string {
  const metadataName = artifact.metadata_json?.file_name;
  if (typeof metadataName === "string" && metadataName.length > 0) {
    return metadataName;
  }
  const extension = fileExtension(artifact.artifact_kind) || fileExtension(artifact.storage_uri);
  return `${artifact.artifact_version_id}${extension}`;
}

export async function uploadAttachmentForSubject(
  *,
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string,
  file: File,
  artifactKind: string,
  artifactRole: string,
): Promise<ArtifactVersionRow> {
  const payload: ArtifactUploadPayload = {
    artifact_kind: artifactKind,
    artifact_role: artifactRole,
    file_name: file.name,
    media_type: inferMediaType(file),
    content_base64: await fileToBase64(file),
    metadata_json: {
      original_file_name: file.name,
      uploaded_via: "frontend_inline_attachment",
      subject_kind: subjectKind,
      subject_id: subjectId
    },
    idempotency_key: createIdempotencyKey(`${subjectKind}-upload`, `${subjectId}:${file.name}`),
  };

  if (subjectKind === "human_task") {
    return onetruthApi.uploadHumanTaskArtifact(subjectId, payload);
  }
  if (subjectKind === "approval") {
    return onetruthApi.uploadApprovalArtifact(subjectId, payload);
  }
  if (subjectKind === "flag") {
    return onetruthApi.uploadFlagArtifact(subjectId, payload);
  }
  return onetruthApi.uploadWorkflowRunArtifact(subjectId, payload);
}

export async function listAttachmentsForSubject(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string
): Promise<ArtifactVersionRow[]> {
  if (subjectKind === "human_task") {
    return onetruthApi.listHumanTaskArtifacts(subjectId);
  }
  if (subjectKind === "approval") {
    return onetruthApi.listApprovalArtifacts(subjectId);
  }
  if (subjectKind === "flag") {
    return onetruthApi.listFlagArtifacts(subjectId);
  }
  return onetruthApi.listWorkflowRunArtifacts(subjectId);
}

async function downloadArtifact(artifactVersionId: string): Promise<ArtifactDownloadResult> {
  return onetruthApi.downloadArtifact(artifactVersionId);
}

export async function downloadLatestAttachmentForSubject(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string
): Promise<ArtifactVersionRow | null> {
  const attachments = await listAttachmentsForSubject(subjectKind, subjectId);
  if (attachments.length === 0) {
    return null;
  }

  const latest = attachments[0];
  const downloaded = await downloadArtifact(latest.artifact_version_id);
  downloadBase64ToFile(
    downloaded.content_base64,
    downloadName(downloaded.artifact_version),
    downloaded.artifact_version.media_type
  );
  return latest;
}
