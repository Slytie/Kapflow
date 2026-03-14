import { apiConfig } from "@/lib/api/config";

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface BinaryResponsePayload {
  body: Blob;
  fileName: string | null;
  mediaType: string;
  contentLength: number | null;
  requestId: string | null;
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, unknown>;

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = payload.code;
    this.details = payload.details;
  }
}

function encodeQuery(query?: Record<string, string | number | null | undefined>): string {
  if (!query) {
    return "";
  }

  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    params.set(key, String(value));
  });

  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

function normalizeErrorPayload(payload: unknown, status: number): ApiErrorPayload {
  if (
    payload &&
    typeof payload === "object" &&
    "error" in payload &&
    payload.error &&
    typeof payload.error === "object"
  ) {
    const error = payload.error as Record<string, unknown>;
    const code = typeof error.code === "string" ? error.code : "unknown_error";
    const message =
      typeof error.message === "string" ? error.message : `Request failed with status ${status}`;
    const details =
      error.details && typeof error.details === "object"
        ? (error.details as Record<string, unknown>)
        : undefined;
    return { code, message, details };
  }

  return {
    code: "http_error",
    message: `Request failed with status ${status}`
  };
}

export function isApiClientError(error: unknown): error is ApiClientError {
  return error instanceof ApiClientError;
}

interface RequestOptions {
  method?: "GET" | "POST";
  query?: Record<string, string | number | null | undefined>;
  body?: unknown;
  headers?: Record<string, string>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

function buildHeaders(options: RequestOptions, contentType?: string): HeadersInit {
  return {
    ...(contentType ? { "content-type": contentType } : {}),
    "x-onetruth-tenant-id": apiConfig.tenantId,
    "x-onetruth-domain-id": apiConfig.domainId,
    "x-onetruth-actor-id": apiConfig.actorId,
    "x-onetruth-actor-type": apiConfig.actorType,
    "x-onetruth-actor-roles": apiConfig.actorRoles,
    ...(options.headers ?? {})
  };
}

async function performRequest(path: string, options: RequestOptions, contentType?: string): Promise<Response> {
  const method = options.method ?? "GET";
  const url = `${apiConfig.baseUrl}${path}${encodeQuery(options.query)}`;
  const init: RequestInit = {
    method,
    headers: buildHeaders(options, contentType)
  };

  if (options.body !== undefined) {
    init.body = JSON.stringify(options.body);
  }

  try {
    return await fetch(url, init);
  } catch {
    throw new ApiClientError(0, {
      code: "network_error",
      message: "Unable to reach the API endpoint"
    });
  }
}

function invalidJsonPayload(path: string, contentType: string): ApiErrorPayload {
  const maybeHtml =
    contentType.toLowerCase().includes("text/html") || contentType.toLowerCase().includes("<!doctype html>");
  return {
    code: "invalid_json_response",
    message: maybeHtml
      ? "API returned HTML instead of JSON. Check VITE_ONETRUTH_API_BASE_URL or Vite dev proxy."
      : "API returned a non-JSON response.",
    details: { path, content_type: contentType }
  };
}

function parseJsonText(text: string, status: number, path: string, contentType: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    throw new ApiClientError(status, invalidJsonPayload(path, contentType));
  }
}

function normalizeErrorResponse(
  text: string,
  status: number,
  path: string,
  contentType: string
): ApiErrorPayload {
  if (!text) {
    return {
      code: "http_error",
      message: `Request failed with status ${status}`
    };
  }

  try {
    return normalizeErrorPayload(JSON.parse(text) as unknown, status);
  } catch {
    return invalidJsonPayload(path, contentType);
  }
}

function parseContentDispositionFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) {
    return null;
  }

  const utf8Match = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(contentDisposition);
  if (utf8Match) {
    const encoded = utf8Match[1]?.trim();
    if (!encoded) {
      return null;
    }
    try {
      return decodeURIComponent(encoded);
    } catch {
      return encoded;
    }
  }

  const quotedMatch = /filename\s*=\s*"([^"]+)"/i.exec(contentDisposition);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  const bareMatch = /filename\s*=\s*([^;]+)/i.exec(contentDisposition);
  return bareMatch?.[1]?.trim() || null;
}

function parseContentLength(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await performRequest(path, options, "application/json");

  const text = await response.text();
  const contentType = response.headers.get("content-type") ?? "";
  let payload: unknown = {};
  if (text) {
    payload = parseJsonText(text, response.status, path, contentType);
  }

  if (!response.ok) {
    throw new ApiClientError(response.status, normalizeErrorPayload(payload, response.status));
  }

  if (!isRecord(payload)) {
    throw new ApiClientError(response.status, {
      code: "invalid_api_envelope",
      message: "API response was not a JSON object envelope.",
      details: { path }
    });
  }

  const status = payload.status;
  if (status === "error") {
    throw new ApiClientError(response.status, normalizeErrorPayload(payload, response.status));
  }
  if (status !== "ok") {
    throw new ApiClientError(response.status, {
      code: "invalid_api_envelope",
      message: "API response missing status='ok' envelope.",
      details: { path, observed_status: status ?? null }
    });
  }

  return payload as T;
}

export async function requestBinary(
  path: string,
  options: RequestOptions = {}
): Promise<BinaryResponsePayload> {
  const response = await performRequest(path, options);

  if (!response.ok) {
    const text = await response.text();
    const contentType = response.headers.get("content-type") ?? "";
    throw new ApiClientError(response.status, normalizeErrorResponse(text, response.status, path, contentType));
  }

  const mediaType = response.headers.get("content-type") ?? "application/octet-stream";
  return {
    body: await response.blob(),
    fileName: parseContentDispositionFilename(response.headers.get("content-disposition")),
    mediaType,
    contentLength: parseContentLength(response.headers.get("content-length")),
    requestId: response.headers.get("x-request-id")
  };
}
