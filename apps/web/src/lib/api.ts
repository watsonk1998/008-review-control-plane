import type {
  CreateTaskRequest,
  FixtureRecord,
  HealthResponse,
  HeartbeatResponse,
  RecentTaskSummary,
  TaskArtifact,
  TaskEvent,
  TaskRecord,
} from "@/types/control-plane";

const DEFAULT_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8018";

export function getApiBaseUrl() {
  return DEFAULT_API_BASE_URL.replace(/\/$/, "");
}

export function resolveApiUrl(path: string) {
  if (/^https?:\/\//.test(path)) return path;
  return `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(resolveApiUrl(path), {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
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

export function createTask(payload: CreateTaskRequest) {
  return fetchJson<TaskRecord>("/api/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchTask(taskId: string) {
  return fetchJson<TaskRecord>(`/api/tasks/${taskId}`);
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
