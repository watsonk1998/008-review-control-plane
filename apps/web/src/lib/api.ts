import type {
  CreateTaskRequest,
  FrozenUploadResponse,
  FixtureRecord,
  HealthResponse,
  HeartbeatResponse,
  RecentTaskSummary,
  ReviewReportFeedbackRequest,
  ReviewReportFeedbackResponse,
  ReviewTaskCreateRequest,
  ReviewTaskCreateResponse,
  ReviewTaskResultResponse,
  ReviewTaskStatusResponse,
  ReviewerDecisionUpdateRequest,
  SourceDocumentRef,
  SupportScopeResponse,
  TaskArtifact,
  TaskEvent,
  TaskRecord,
} from "@/types/control-plane";

const isServer = typeof window === "undefined";
const DEFAULT_API_BASE_URL = isServer
  ? (process.env.BACKEND_API_BASE || "http://127.0.0.1:8018")
  : "";

export function getApiBaseUrl() {
  return DEFAULT_API_BASE_URL.replace(/\/$/, "");
}

export function resolveApiUrl(path: string) {
  if (/^https?:\/\//.test(path)) return path;
  return `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(resolveApiUrl(path), {
    ...init,
    cache: "no-store",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers || {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text) as { detail?: string | { message?: string } };
      const detail = parsed?.detail;
      if (typeof detail === "string") {
        throw new Error(detail);
      }
      if (detail && typeof detail === "object" && typeof detail.message === "string") {
        throw new Error(detail.message);
      }
    } catch (parseError) {
      if (parseError instanceof Error && !(parseError instanceof SyntaxError)) {
        throw parseError;
      }
    }
    throw new Error(text || `${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export function fetchHealth() {
  return fetchJson<HealthResponse>("/api/health");
}

export function fetchHeartbeat() {
  return fetchJson<HeartbeatResponse>("/api/heartbeat");
}

export function fetchFixtures() {
  return fetchJson<FixtureRecord[]>("/api/fixtures");
}

export function fetchRecentTasks(limit = 8) {
  return fetchJson<RecentTaskSummary[]>(`/api/tasks?limit=${encodeURIComponent(String(limit))}`);
}

export function fetchSupportScope() {
  return fetchJson<SupportScopeResponse>("/api/tasks/support-scope");
}

export function createTask(payload: CreateTaskRequest) {
  return fetchJson<TaskRecord>("/api/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return fetchJson<SourceDocumentRef>("/api/uploads/documents", {
    method: "POST",
    body: formData,
  });
}

export async function uploadReviewDocument(file: File): Promise<FrozenUploadResponse> {
  const payload = await uploadDocument(file);
  return {
    file_id: payload.file_id || payload.refId,
    file_name: payload.file_name || payload.fileName,
    file_type: payload.file_type || payload.fileType,
    display_name: payload.display_name || payload.displayName,
    uploaded_at: payload.uploaded_at || payload.uploadedAt,
    source_ref: payload,
  };
}

export function fetchTask(taskId: string) {
  return fetchJson<TaskRecord>(`/api/tasks/${taskId}`);
}

export function updateReviewerDecision(taskId: string, payload: ReviewerDecisionUpdateRequest) {
  return fetchJson<TaskRecord>(`/api/tasks/${taskId}/reviewer-decision`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function fetchTaskEvents(taskId: string) {
  return fetchJson<TaskEvent[]>(`/api/tasks/${taskId}/events`);
}

export function fetchTaskArtifacts(taskId: string) {
  return fetchJson<TaskArtifact[]>(`/api/tasks/${taskId}/artifacts`);
}

export function getTaskStreamUrl(taskId: string) {
  return resolveApiUrl(`/api/tasks/${taskId}/stream`);
}

export function getTaskArtifactUrl(taskId: string, fileName: string) {
  return resolveApiUrl(`/api/tasks/${taskId}/artifacts/${encodeURIComponent(fileName)}`);
}

export function createReviewTask(payload: ReviewTaskCreateRequest) {
  return fetchJson<ReviewTaskCreateResponse>("/api/review-tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchReviewTask(taskId: string) {
  return fetchJson<ReviewTaskStatusResponse>(`/api/review-tasks/${taskId}`);
}

export function getReviewTaskEventsUrl(taskId: string) {
  return resolveApiUrl(`/api/review-tasks/${taskId}/events`);
}

export function fetchReviewTaskResult(taskId: string) {
  return fetchJson<ReviewTaskResultResponse>(`/api/review-tasks/${taskId}/result`);
}

export function submitReviewReportFeedback(reportId: string, payload: ReviewReportFeedbackRequest) {
  return fetchJson<ReviewReportFeedbackResponse>(`/api/review-reports/${reportId}/feedback`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
