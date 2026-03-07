import { onetruthApi } from "@/lib/api/onetruthApi";
import type { TemplateRecord } from "@/lib/types/contracts";
import { downloadBase64ToFile } from "@/lib/repositories/artifactAttachments";

export interface TemplateQuery {
  workflowId?: string;
  stageId?: string;
  datasetKey?: string;
  variant?: string;
}

export const templatesRepository = {
  async list(query: TemplateQuery = {}): Promise<TemplateRecord[]> {
    const result = await onetruthApi.listTemplates({
      workflow_id: query.workflowId,
      stage_id: query.stageId,
      dataset_key: query.datasetKey,
      variant: query.variant,
      limit: 300,
      offset: 0
    });
    return result.templates;
  },

  async download(templateId: string): Promise<void> {
    const downloaded = await onetruthApi.downloadTemplate(templateId);
    downloadBase64ToFile(
      downloaded.content_base64,
      downloaded.template.file_name,
      downloaded.template.media_type
    );
  }
};
