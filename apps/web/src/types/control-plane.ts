export type TaskType = "knowledge_qa" | "deep_research" | "document_research" | "review_assist" | "structured_review";
export type CapabilityMode = "auto" | "deeptutor" | "gpt_researcher" | "fast" | "llm_only";
export type TaskStatus = "created" | "planned" | "running" | "waiting_external" | "succeeded" | "failed" | "partial";
export type ReviewLayer = "L1" | "L2" | "L3";
export type ReviewDocumentType = "construction_org" | "construction_scheme" | "hazardous_special_scheme" | "supervision_plan" | "review_support_material";
export type AttachmentVisibility = "parsed" | "attachment_unparsed" | "referenced_only" | "missing" | "unknown";
export type FindingType = "hard_evidence" | "engineering_inference" | "visibility_gap" | "suggestion_enhancement";
export type ConfidenceLevel = "low" | "medium" | "high";

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

export interface EvidenceSpan {
  sourceType: "document" | "policy" | "artifact";
  sourceId: string;
  locator: Record<string, unknown>;
  excerpt: string;
  visibility?: AttachmentVisibility | null;
  confidence: ConfidenceLevel;
}

export interface ReviewIssue {
  id: string;
  title: string;
  layer: ReviewLayer;
  severity: "high" | "medium" | "low" | "info";
  findingType: FindingType;
  summary: string;
  manualReviewNeeded: boolean;
  docEvidence: EvidenceSpan[];
  policyEvidence: EvidenceSpan[];
  recommendation: string[];
  confidence: ConfidenceLevel;
  whetherManualReviewNeeded: boolean;
}

export interface StructuredReviewSummary {
  overallConclusion: string;
  documentType: ReviewDocumentType;
  selectedPacks: string[];
  manualReviewNeeded: boolean;
  issueCount: number;
  layerCounts: Record<string, number>;
  stats: Record<string, unknown>;
}

export interface ResolvedReviewProfile {
  requestedDocumentType?: ReviewDocumentType | null;
  requestedDisciplineTags: string[];
  requestedPolicyPackIds: string[];
  documentType: ReviewDocumentType;
  disciplineTags: string[];
  policyPackIds: string[];
  strictMode: boolean;
}

export interface TaskArtifact {
  name: string;
  fileName: string;
  mediaType: string;
  sizeBytes: number;
  downloadUrl: string;
}

export interface HazardIdentificationMatrix {
  values: Record<string, unknown>;
}

export interface RuleHitMatrixRow {
  ruleId: string;
  packId: string;
  status: string;
  layerHint: string;
  severityHint: string;
  matchType: string;
}

export interface ConflictMatrix {
  values: Record<string, unknown>;
}

export interface AttachmentVisibilityMatrixItem {
  id: string;
  attachmentNumber: string;
  title: string;
  visibility: AttachmentVisibility;
  parseState: string;
  referenceBlockIds: string[];
  titleBlockId?: string | null;
}

export interface SectionStructureMatrixItem {
  id: string;
  title: string;
  level: number;
  parentId?: string | null;
  duplicate: boolean;
}

export interface StructuredReviewMatrices {
  hazardIdentification: HazardIdentificationMatrix;
  ruleHits: RuleHitMatrixRow[];
  conflicts: ConflictMatrix;
  attachmentVisibility: AttachmentVisibilityMatrixItem[];
  sectionStructure: SectionStructureMatrixItem[];
  issueLayerCounts?: Record<string, number>;
}

export interface StructuredReviewResult {
  summary: StructuredReviewSummary;
  resolvedProfile: ResolvedReviewProfile;
  issues: ReviewIssue[];
  matrices: StructuredReviewMatrices;
  artifactIndex: TaskArtifact[];
  reportMarkdown: string;
  artifacts: string[];
  plan?: Record<string, unknown> | null;
  capabilitiesUsed: string[];
  finalAnswer: string;
  notice?: string | null;
  fixture?: FixtureRecord;
  steps?: TaskEvent[];
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
  documentType?: ReviewDocumentType | null;
  disciplineTags: string[];
  strictMode?: boolean | null;
  policyPackIds: string[];
  status: TaskStatus;
  plan?: Record<string, unknown> | null;
  result?: Record<string, unknown> | StructuredReviewResult | null;
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

export interface HeartbeatResponse {
  status: string;
  serverTime: string;
  database: string;
  runningTaskCount: number;
  latestTaskUpdatedAt?: string | null;
}

export interface RecentTaskSummary {
  id: string;
  taskType: TaskType;
  capabilityMode: CapabilityMode;
  status: TaskStatus;
  query: string;
  fixtureId?: string | null;
  documentType?: ReviewDocumentType | null;
  createdAt: string;
  updatedAt: string;
}

export interface TaskStreamSnapshotEvent {
  type: "snapshot";
  payload: {
    task: TaskRecord | null;
    events: TaskEvent[];
    artifacts: TaskArtifact[];
  };
}

export interface TaskStreamTaskEvent {
  type: "task";
  payload: TaskRecord;
}

export interface TaskStreamEventEvent {
  type: "event";
  payload: TaskEvent;
}

export interface TaskStreamArtifactsEvent {
  type: "artifacts";
  payload: TaskArtifact[];
}

export interface TaskStreamHeartbeatEvent {
  type: "heartbeat";
  payload: {
    taskId: string;
    serverTime: string;
  };
}

export type TaskStreamEnvelope =
  | TaskStreamSnapshotEvent
  | TaskStreamTaskEvent
  | TaskStreamEventEvent
  | TaskStreamArtifactsEvent
  | TaskStreamHeartbeatEvent;

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
  documentType?: ReviewDocumentType;
  disciplineTags?: string[];
  strictMode?: boolean;
  policyPackIds?: string[];
}
