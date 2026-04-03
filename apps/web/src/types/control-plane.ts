export type TaskType = "knowledge_qa" | "deep_research" | "document_research" | "review_assist" | "structured_review";
export type CapabilityMode = "auto" | "deeptutor" | "gpt_researcher" | "fast" | "llm_only";
export type TaskStatus = "created" | "planned" | "running" | "waiting_external" | "succeeded" | "failed" | "partial";
export type ReviewLayer = "L1" | "L2" | "L3";
export type ReviewDocumentType = "construction_org" | "construction_scheme" | "hazardous_special_scheme" | "supervision_plan" | "review_support_material";
export type AttachmentVisibility = "parsed" | "attachment_unparsed" | "referenced_only" | "missing" | "unknown";
export type FindingType = "hard_evidence" | "engineering_inference" | "visibility_gap" | "suggestion_enhancement";
export type ConfidenceLevel = "low" | "medium" | "high";
export type ArtifactCategory = "parse" | "facts" | "rule_hits" | "candidates" | "result" | "matrix" | "report" | "generic";
export type ParseMode = "docx_structured" | "pdf_text_only" | "markdown_text" | "plain_text";

export interface SourceDocumentRef {
  refId: string;
  sourceType: "fixture" | "upload";
  fileName: string;
  fileType: string;
  storagePath: string;
  displayName?: string | null;
  mediaType?: string | null;
  fixtureId?: string | null;
  uploadedAt?: string | null;
}

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
  locator:
    | { blockId: string; sectionId?: string | null }
    | { tableId: string; sectionId?: string | null }
    | { attachmentId: string }
    | { clauseId: string }
    | { sectionId: string };
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
  evidenceMissing: boolean;
  manualReviewReason?: string | null;
  docEvidence: EvidenceSpan[];
  policyEvidence: EvidenceSpan[];
  recommendation: string[];
  confidence: ConfidenceLevel;
  whetherManualReviewNeeded?: boolean | null;
}

export interface StructuredReviewVisibilitySummary {
  attachmentCount: number;
  counts: Record<string, number>;
  duplicateSectionTitles: string[];
  parseWarnings: string[];
  reasonCounts: Record<string, number>;
  manualReviewNeeded: boolean;
}

export interface VisibilityAssessment {
  parserLimited: boolean;
  fileType?: string | null;
  attachmentCount: number;
  counts: Record<string, number>;
  reasonCounts: Record<string, number>;
  duplicateSectionTitles: string[];
  manualReviewNeeded: boolean;
}

export interface StructuredReviewSummary {
  overallConclusion: string;
  documentType: ReviewDocumentType;
  selectedPacks: string[];
  manualReviewNeeded: boolean;
  issueCount: number;
  layerCounts: Record<string, number>;
  stats: Record<string, unknown>;
  visibilitySummary: StructuredReviewVisibilitySummary;
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
  category?: ArtifactCategory | null;
  stage?: string | null;
  primary?: boolean;
}

export interface HazardIdentificationMatrix {
  values: Record<string, unknown>;
}

export interface RuleHitMatrixRow {
  ruleId: string;
  packId: string;
  packReadiness: "ready" | "placeholder";
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
  manualReviewNeeded: boolean;
  reason?: string | null;
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
  visibility: VisibilityAssessment;
  resolvedProfile: ResolvedReviewProfile;
  issues: ReviewIssue[];
  matrices: StructuredReviewMatrices;
  artifactIndex: TaskArtifact[];
  reportMarkdown: string;
  artifacts: string[];
  unresolvedFacts: Array<{
    code: string;
    factKey: string;
    summary: string;
  }>;
  plan?: Record<string, unknown> | null;
  capabilitiesUsed: string[];
  finalAnswer: string;
  notice?: string | null;
  fixture?: FixtureRecord;
  steps?: TaskEvent[];
}

export interface ReviewerIssueDecision {
  issueId: string;
  state: "pending" | "confirmed" | "dismissed" | "needs_attachment";
  note?: string | null;
}

export interface ReviewerAttachmentDecision {
  attachmentId: string;
  state: "pending" | "confirmed" | "dismissed" | "needs_attachment";
  note?: string | null;
}

export interface ReviewerDecision {
  taskState: "pending" | "accepted" | "rejected" | "needs_attachment";
  note?: string | null;
  issues: ReviewerIssueDecision[];
  attachments: ReviewerAttachmentDecision[];
  updatedAt?: string | null;
}

export interface TaskRecord {
  id: string;
  taskType: TaskType;
  capabilityMode: CapabilityMode;
  query: string;
  datasetId?: string | null;
  collectionId?: string | null;
  fixtureId?: string | null;
  sourceDocumentRef?: SourceDocumentRef | null;
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
  reviewerDecision?: ReviewerDecision | null;
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
  sourceDocumentRef?: SourceDocumentRef | null;
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
  sourceDocumentRef?: SourceDocumentRef;
  useWeb: boolean;
  debug: boolean;
  sourceUrls?: string[];
  documentType?: ReviewDocumentType;
  disciplineTags?: string[];
  strictMode?: boolean;
  policyPackIds?: string[];
}

export interface ReviewerDecisionUpdateRequest {
  taskState: "pending" | "accepted" | "rejected" | "needs_attachment";
  note?: string | null;
  issues: ReviewerIssueDecision[];
  attachments: ReviewerAttachmentDecision[];
}

export interface SupportScopeResponse {
  documentTypes: Array<{
    documentType: ReviewDocumentType;
    readiness: "official" | "skeleton";
  }>;
  packs: Array<{
    packId: string;
    readiness: "ready" | "placeholder";
    docTypes: string[];
    disciplineTags: string[];
    defaultEnabled: boolean;
    description: string;
  }>;
}
