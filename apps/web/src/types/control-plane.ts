export type TaskType = "knowledge_qa" | "deep_research" | "document_research" | "review_assist";
export type CapabilityMode = "auto" | "deeptutor" | "gpt_researcher" | "fast" | "llm_only";
export type TaskStatus = "created" | "planned" | "running" | "waiting_external" | "succeeded" | "failed" | "partial";

export interface CapabilityHealth {
  name: string;
  available: boolean;
  mode: string;
  detail?: string;
  raw?: Record<string, unknown>;
  provider?: string;
  model?: string;
  config?: Record<string, unknown>;
}

export interface FixtureRecord {
  id: string;
  title: string;
  domain: string;
  sourcePath: string;
  copiedPath: string;
  fileType: string;
  notes?: string;
}

export interface TaskEvent {
  timestamp: string;
  stage: string;
  capability: string;
  status: "started" | "completed" | "failed" | "info";
  message: string;
  durationMs?: number | null;
  debug?: Record<string, unknown> | null;
  artifactPath?: string | null;
}

export interface TaskRecord {
  id: string;
  taskType: TaskType;
  capabilityMode: CapabilityMode;
  query: string;
  datasetId?: string | null;
  collectionId?: string | null;
  fixtureId?: string | null;
  useWeb: boolean;
  debug: boolean;
  sourceUrls: string[];
  status: TaskStatus;
  plan?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  error?: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface HealthResponse {
  status: string;
  database: string;
  capabilities: CapabilityHealth[];
  fixtureCount: number;
}

export interface CreateTaskRequest {
  taskType: TaskType;
  capabilityMode: CapabilityMode;
  query: string;
  datasetId?: string;
  collectionId?: string;
  fixtureId?: string;
  useWeb: boolean;
  debug: boolean;
  sourceUrls?: string[];
}
