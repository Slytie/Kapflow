import { apiConfig } from "@/lib/api/config";

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
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

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const url = `${apiConfig.baseUrl}${path}${encodeQuery(options.query)}`;

  const headers: HeadersInit = {
    "content-type": "application/json",
    "x-onetruth-tenant-id": apiConfig.tenantId,
    "x-onetruth-domain-id": apiConfig.domainId,
    "x-onetruth-actor-id": apiConfig.actorId,
    "x-onetruth-actor-type": apiConfig.actorType,
    "x-onetruth-actor-roles": apiConfig.actorRoles,
    ...(options.headers ?? {})
  };

  const init: RequestInit = {
    method,
    headers
  };
  if (options.body !== undefined) {
    init.body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new ApiClientError(0, {
      code: "network_error",
      message: "Unable to reach the API endpoint"
    });
  }

  const text = await response.text();
  let payload: unknown = {};
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = {};
    }
  }

  if (!response.ok) {
    throw new ApiClientError(response.status, normalizeErrorPayload(payload, response.status));
  }

  return payload as T;
}
