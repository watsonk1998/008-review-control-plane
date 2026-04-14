export type TaskType = "knowledge_qa" | "deep_research" | "document_research" | "review_assist" | "structured_review";
export type CapabilityMode = "auto" | "deeptutor" | "gpt_researcher" | "fast" | "llm_only";
export type TaskStatus = "created" | "planned" | "running" | "waiting_external" | "succeeded" | "failed" | "partial";
export type ReviewLayer = "L1" | "L2" | "L3";
export type ReviewDocumentType =
  | "construction_org"
  | "construction_scheme"
  | "hazardous_special_scheme"
  | "distribution_network_special_scheme"
  | "supervision_plan"
  | "review_support_material";
export type AttachmentVisibility = "parsed" | "attachment_unparsed" | "referenced_only" | "missing" | "unknown";
export type FindingType = "hard_evidence" | "engineering_inference" | "visibility_gap" | "suggestion_enhancement";
export type ConfidenceLevel = "low" | "medium" | "high";
export type ArtifactCategory = "parse" | "facts" | "rule_hits" | "candidates" | "result" | "matrix" | "matrices" | "report" | "generic";
export type ParseMode = "docx_structured" | "pdf_text_only" | "markdown_text" | "plain_text";
export type IssueKind = "hard_defect" | "visibility_gap" | "evidence_gap" | "enhancement";
export type ApplicabilityState = "applies" | "partial" | "blocked_by_visibility" | "blocked_by_missing_fact";
export type ReviewPreparationDisposition = "eligible" | "deferred" | "rejected";

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
  file_id?: string;
  file_name?: string;
  file_type?: string;
  display_name?: string | null;
  uploaded_at?: string | null;
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
  clauseTitle?: string | null;
  forceLevel?: "must" | "should" | "guidance" | null;
  applicability?: string | null;
  sourceProvenance?: string | null;
  evidenceGapReason?: string | null;
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
  issueKind: IssueKind;
  applicabilityState: ApplicabilityState;
  docEvidence: EvidenceSpan[];
  policyEvidence: EvidenceSpan[];
  recommendation: string[];
  confidence: ConfidenceLevel;
  missingFactKeys?: string[];
  blockingReasons?: string[];
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
  parseMode?: ParseMode | null;
  parserLimited: boolean;
  fileType?: string | null;
  attachmentCount: number;
  counts: Record<string, number>;
  reasonCounts: Record<string, number>;
  duplicateSectionTitles: string[];
  parseWarnings: string[];
  manualReviewNeeded: boolean;
  manualReviewReason?: string | null;
  preflight: VisibilityPreflight;
}

export interface VisibilityPreflightChecklistItem {
  key: string;
  status: "pass" | "manual_review_required" | "info";
  summary: string;
  blocking: boolean;
}

export interface VisibilityPreflight {
  gateDecision: "ready" | "manual_review_required";
  blockingReasons: string[];
  checklist: VisibilityPreflightChecklistItem[];
  parserLimitations: string[];
  attachmentTaxonomySummary: Record<string, unknown>;
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
  applicabilityState: ApplicabilityState;
  layerHint: string;
  severityHint: string;
  matchType: string;
  requiredFactKeys?: string[];
  missingFactKeys?: string[];
  clauseIds?: string[];
  blockingReasons?: string[];
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

export interface StructureCompletenessMatchedSection {
  sectionId?: string | null;
  blockId?: string | null;
  title: string;
  position?: number | null;
  level?: number | null;
}

export interface StructureCompletenessMatrixItem {
  itemKey: string;
  requirementLabel: string;
  basisClause: string;
  basisRequirement: string;
  status: "matched" | "partial" | "missing" | "blocked_by_visibility";
  matchedSections: StructureCompletenessMatchedSection[];
  analysis: string;
  reportExcerpt: string;
  scope?: "special" | "common";
  displayOrder?: number;
  groupLabel?: string | null;
}

export interface StructuredReviewMatrices {
  hazardIdentification: HazardIdentificationMatrix;
  ruleHits: RuleHitMatrixRow[];
  conflicts: ConflictMatrix;
  attachmentVisibility: AttachmentVisibilityMatrixItem[];
  sectionStructure: SectionStructureMatrixItem[];
  structureCompleteness: StructureCompletenessMatrixItem[];
  issueLayerCounts?: Record<string, number>;
}

export interface FinalReportPacket {
  review_id: string;
  final_grade: string;
  executive_summary: string;
  top_risks: ReviewIssue[] | Array<Record<string, unknown>>;
  key_findings: ReviewIssue[] | Array<Record<string, unknown>>;
  supplemental_findings: ReviewIssue[] | Array<Record<string, unknown>>;
  all_findings: ReviewIssue[] | Array<Record<string, unknown>>;
  traceability: Array<Record<string, unknown>>;
  report_markdown: string;
  report_sections?: Array<Record<string, unknown>>;
  engines_used: string[];
  degradation_info?: Record<string, unknown>;
  source_packets?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface StructuredReviewResult {
  summary?: StructuredReviewSummary;
  visibility?: VisibilityAssessment;
  resolvedProfile?: ResolvedReviewProfile;
  issues?: ReviewIssue[];
  matrices?: StructuredReviewMatrices;
  artifactIndex?: TaskArtifact[];
  // Canonical final-report field for external/UI consumption.
  finalReportMarkdown?: string;
  finalReportPacket?: FinalReportPacket | null;
  reportMarkdown?: string;
  traceability?: Array<Record<string, unknown>>;
  
  support_result_008?: any;
  hermesController?: any;
  reportHtml?: string;
  reportPrintCss?: string;
  artifacts?: string[];
  unresolvedFacts: Array<{
    code: string;
    factKey: string;
    summary: string;
    sourceExtractor?: string;
    blockingReason?: string | null;
    visibilityLimited?: boolean;
    blockingRuleIds?: string[];
    blockingIssueIds?: string[];
    blockingIssueTitles?: string[];
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

export interface ReviewPreparationSummary {
  truthTier: "runtime_only" | "internal_reviewed_preparation";
  readyForPromotion: boolean;
  blockingReasons: string[];
  eligibleIssueIds: string[];
  deferredIssueIds: string[];
  rejectedIssueIds: string[];
  eligibleAttachmentIds: string[];
  deferredAttachmentIds: string[];
  rejectedAttachmentIds: string[];
  issueBlockingReasons: Record<string, string[]>;
  attachmentBlockingReasons: Record<string, string[]>;
  provenance: ReviewPreparationProvenance;
  disclaimer?: string | null;
}

export interface ReviewPreparationIssueRecord {
  issueId: string;
  disposition: ReviewPreparationDisposition;
  state: ReviewerIssueDecision["state"];
  note?: string | null;
  issueKind?: IssueKind | null;
  applicabilityState?: ApplicabilityState | null;
  manualReviewNeeded: boolean;
  manualReviewReason?: string | null;
  evidenceMissing: boolean;
  missingFactKeys: string[];
  blockingReasons: string[];
  promotionBlockingReasons: string[];
}

export interface ReviewPreparationAttachmentRecord {
  attachmentId: string;
  disposition: ReviewPreparationDisposition;
  state: ReviewerAttachmentDecision["state"];
  note?: string | null;
  visibility?: AttachmentVisibility | null;
  parseState?: string | null;
  manualReviewNeeded: boolean;
  reason?: string | null;
  promotionBlockingReasons: string[];
}

export interface ReviewPreparationAsset {
  schemaVersion: "v0.1";
  truthTier: "internal_reviewed_preparation";
  taskId: string;
  documentType?: ReviewDocumentType | null;
  sourceDocumentRef?: SourceDocumentRef | null;
  reviewerDecisionUpdatedAt?: string | null;
  readyForPromotion: boolean;
  blockingReasons: string[];
  issueDecisions: ReviewPreparationIssueRecord[];
  attachmentDecisions: ReviewPreparationAttachmentRecord[];
  provenance: ReviewPreparationProvenance;
  disclaimer?: string | null;
}

export interface ReviewPreparationProvenance {
  sourceTier: "runtime_only" | "seed" | "bootstrap_seed" | "ci_stage_gate" | "internal_reviewed" | "expert_golden";
  caseId?: string | null;
  caseVersion?: string | null;
  labelStatus?: string | null;
  truthLevel?: string | null;
  reviewStatus?: string | null;
  inferred: boolean;
  taskId?: string | null;
  taskType?: TaskType | null;
  resultArtifactNames: string[];
  resultArtifactPrimary?: string | null;
  usesRuntimeReviewerDecision: boolean;
  usesRuntimeStructuredReviewResult: boolean;
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
  reviewPreparation?: ReviewPreparationSummary | null;
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

export interface ExternalIntegrationContext {
  agentId?: string | null;
  callBackUrl?: string | null;
  userId?: string | null;
  tenantId?: string | null;
}

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
  reviewIntent?: {
    enabled_modules: ReviewModuleName[];
    disabled_modules: ReviewModuleName[];
    focus_requirements: string[];
  };
  externalContext?: ExternalIntegrationContext | null;
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
    label: string;
    readiness: "official" | "experimental" | "skeleton";
  }>;
  packs: Array<{
    packId: string;
    label: string;
    readiness: "ready" | "placeholder";
    docTypes: string[];
    disciplineTags: string[];
    defaultEnabled: boolean;
    description: string;
    promotionCriteria: Record<string, boolean>;
    entryKey?: string | null;
    familyKey?: string | null;
    role?: string | null;
    tier?: string | null;
  }>;
  capabilityTree: Array<{
    entryKey: string;
    label: string;
    families: Array<{
      familyKey: string;
      documentType: ReviewDocumentType;
      label: string;
      readiness: "official" | "experimental" | "skeleton";
      basePackId: string;
      basePackReadiness: "ready" | "placeholder";
      children: Array<{
        tag: string;
        packId: string;
        label: string;
        readiness: "ready" | "placeholder";
        promotionCriteria: Record<string, boolean>;
      }>;
    }>;
    crossCuttingModules: Array<{
      tag: string;
      packId: string;
      label: string;
      readiness: "ready" | "placeholder";
      docTypes: string[];
      promotionCriteria: Record<string, boolean>;
    }>;
  }>;
  basisMapping?: Record<string, string[]>;
}

export type ReviewModuleName =
  | "structure_completeness"
  | "parameter_consistency"
  | "legality_compliance"
  | "execution_continuity"
  | "evidence_validation";

export type FrozenReviewTaskStatus =
  | "created"
  | "compiling"
  | "running"
  | "assembling"
  | "completed"
  | "failed"
  | "degraded";

export type FrozenReviewTaskProgressStage =
  | "review_brief_compiling"
  | "assets_loading"
  | "agents_running"
  | "modules_running"
  | "report_assembling"
  | "done";

export type ReviewTaskEventType =
  | "task_created"
  | "progress"
  | "artifact_ready"
  | "completed"
  | "failed";

export type ReviewFeedbackType = "helpful" | "inaccurate" | "missing" | "save_as_template";

export interface FrozenUploadResponse {
  file_id: string;
  file_name: string;
  file_type: string;
  display_name?: string | null;
  uploaded_at?: string | null;
  source_ref: SourceDocumentRef;
}

export interface ReviewTaskCreateRequest {
  classification: {
    l1: string;
    l2: ReviewDocumentType;
    l3: string[];
  };
  documents: {
    target_file_ids: string[];
    basis_file_ids: string[];
    project_context_file_ids: string[];
  };
  builtin_asset_selections: {
    standard_ids: string[];
    template_ids: string[];
    rule_pack_ids: string[];
  };
  review_intent: {
    enabled_modules: ReviewModuleName[];
    disabled_modules: ReviewModuleName[];
    focus_requirements: string[];
  };
  metadata: {
    client_request_id?: string;
    source?: string;
    debug: boolean;
  };
}

export interface ReviewTaskCreateResponse {
  task_id: string;
  status: FrozenReviewTaskStatus;
  review_brief_id: string;
  links: {
    status: string;
    events: string;
    result: string;
  };
}

export interface ReviewTaskStatusResponse {
  task_id: string;
  status: FrozenReviewTaskStatus;
  progress_stage: FrozenReviewTaskProgressStage;
  progress_message: string;
  created_at: string;
  updated_at: string;
  report_id?: string | null;
  degraded: boolean;
  error?: {
    code: string;
    message: string;
  } | null;
}

export interface ReviewTaskSseEvent {
  event: ReviewTaskEventType;
  task_id: string;
  stage: FrozenReviewTaskProgressStage;
  message: string;
  timestamp: string;
  status: FrozenReviewTaskStatus;
  artifact?: {
    file_name: string;
    download_url: string;
    category?: string | null;
    stage?: string | null;
  } | null;
  payload?: Record<string, unknown> | null;
}

export interface FrozenReviewModuleResult {
  title: string;
  findings: ReviewIssue[] | Array<Record<string, unknown>>;
  severity_summary: Record<string, number>;
  traceability_summary: Array<Record<string, unknown>>;
  status: "available" | "partial" | "not_applicable";
}

export interface ReviewTaskResultResponse {
  task_id: string;
  status: FrozenReviewTaskStatus;
  report_id: string;
  summary: {
    overall_conclusion: string;
    risk_level: "low" | "medium" | "high" | "unknown";
    key_counts: Record<string, number>;
    key_metrics: Record<string, number>;
  };
  modules: Record<ReviewModuleName, FrozenReviewModuleResult>;
  key_findings: Array<Record<string, unknown>>;
  recommendations: string[];
  export_links: {
    markdown?: string | null;
    pdf?: string | null;
    html?: string | null;
  };
  metadata: {
    report_id: string;
    generated_at: string;
    degraded: boolean;
    traceability_available: boolean;
    assembler: string;
  };
  raw: Record<string, unknown>;
}

export interface ReviewReportFeedbackRequest {
  feedback_type: ReviewFeedbackType;
  comment?: string;
  source?: string;
}

export interface ReviewReportFeedbackResponse {
  accepted: boolean;
  report_id: string;
  feedback_id: string;
}
