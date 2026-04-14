from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

TaskType = Literal['knowledge_qa', 'deep_research', 'document_research', 'review_assist', 'structured_review']
CapabilityMode = Literal['auto', 'deeptutor', 'gpt_researcher', 'fast', 'llm_only']
TaskStatus = Literal['created', 'planned', 'running', 'waiting_external', 'succeeded', 'failed', 'partial']
EventStatus = Literal['started', 'completed', 'failed', 'info']
ReviewTaskStatus = Literal['created', 'compiling', 'running', 'assembling', 'completed', 'failed', 'degraded']
ReviewTaskProgressStage = Literal[
    'review_brief_compiling',
    'assets_loading',
    'agents_running',
    'modules_running',
    'report_assembling',
    'done',
]
ReviewTaskEventType = Literal['task_created', 'progress', 'artifact_ready', 'completed', 'failed']
ReviewFeedbackType = Literal['helpful', 'inaccurate', 'missing', 'save_as_template']
ReviewerTaskState = Literal['pending', 'accepted', 'rejected', 'needs_attachment']
ReviewerItemState = Literal['pending', 'confirmed', 'dismissed', 'needs_attachment']
ReviewPreparationDisposition = Literal['eligible', 'deferred', 'rejected']
IssueKind = Literal['hard_defect', 'visibility_gap', 'evidence_gap', 'enhancement']
ApplicabilityState = Literal['applies', 'partial', 'blocked_by_visibility', 'blocked_by_missing_fact']
ReviewPreparationSourceTier = Literal[
    'runtime_only',
    'seed',
    'bootstrap_seed',
    'ci_stage_gate',
    'internal_reviewed',
    'expert_golden',
]
ReviewDocumentType = Literal[
    'construction_org',
    'construction_scheme',
    'hazardous_special_scheme',
    'distribution_network_special_scheme',
    'supervision_plan',
    'review_support_material',
]


class AttachmentVisibility(str, Enum):
    parsed = 'parsed'
    attachment_unparsed = 'attachment_unparsed'
    referenced_only = 'referenced_only'
    missing = 'missing'
    unknown = 'unknown'


class ReviewLayer(str, Enum):
    L1 = 'L1'
    L2 = 'L2'
    L3 = 'L3'


class FindingType(str, Enum):
    hard_evidence = 'hard_evidence'
    engineering_inference = 'engineering_inference'
    visibility_gap = 'visibility_gap'
    suggestion_enhancement = 'suggestion_enhancement'


class ConfidenceLevel(str, Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'


ArtifactCategory = Literal['parse', 'facts', 'rule_hits', 'candidates', 'result', 'matrix', 'matrices', 'report', 'generic']
SourceDocumentType = Literal['fixture', 'upload']


class BlockLocator(BaseModel):
    blockId: str
    sectionId: str | None = None


class TableLocator(BaseModel):
    tableId: str
    sectionId: str | None = None


class AttachmentLocator(BaseModel):
    attachmentId: str


class ClauseLocator(BaseModel):
    clauseId: str


class SectionLocator(BaseModel):
    sectionId: str


EvidenceLocator = Union[BlockLocator, TableLocator, AttachmentLocator, ClauseLocator, SectionLocator]


class SourceDocumentRef(BaseModel):
    model_config = ConfigDict(extra='ignore')

    refId: str
    sourceType: SourceDocumentType
    fileName: str
    fileType: str
    storagePath: str
    displayName: str | None = None
    mediaType: str | None = None
    fixtureId: str | None = None
    uploadedAt: datetime | None = None


class ExternalIntegrationContext(BaseModel):
    agentId: str | None = None
    callBackUrl: str | None = None
    userId: str | None = None
    tenantId: str | None = None


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    taskType: TaskType
    capabilityMode: CapabilityMode = 'auto'
    query: str = Field(min_length=1)
    datasetId: str | None = None
    collectionId: str | None = None
    fixtureId: str | None = None
    sourceDocumentRef: SourceDocumentRef | None = None
    useWeb: bool = False
    debug: bool = False
    sourceUrls: list[str] | None = None
    documentType: ReviewDocumentType | None = None
    disciplineTags: list[str] | None = None
    strictMode: bool | None = None
    policyPackIds: list[str] | None = None
    rulePackIds: list[str] | None = None
    externalContext: ExternalIntegrationContext | None = None

    @model_validator(mode='after')
    def _validate_structured_review_source(self):
        if self.taskType != 'structured_review':
            return self
        if bool(self.fixtureId) == bool(self.sourceDocumentRef):
            raise ValueError('structured_review requires exactly one of fixtureId or sourceDocumentRef')
        return self


class EvidenceSpan(BaseModel):
    sourceType: Literal['document', 'policy', 'artifact']
    sourceId: str
    locator: EvidenceLocator
    excerpt: str
    visibility: AttachmentVisibility | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    clauseTitle: str | None = None
    forceLevel: Literal['must', 'should', 'guidance'] | None = None
    applicability: str | None = None
    sourceProvenance: str | None = None
    evidenceGapReason: str | None = None


class ReviewIssue(BaseModel):
    id: str
    title: str
    layer: ReviewLayer
    severity: Literal['high', 'medium', 'low', 'info']
    findingType: FindingType
    summary: str
    manualReviewNeeded: bool = False
    evidenceMissing: bool = False
    manualReviewReason: str | None = None
    issueKind: IssueKind = 'hard_defect'
    applicabilityState: ApplicabilityState = 'applies'


class TaskArtifact(BaseModel):
    name: str
    fileName: str
    mediaType: str
    sizeBytes: int
    downloadUrl: str
    category: ArtifactCategory | None = None
    stage: str | None = None
    primary: bool = False


class TaskEvent(BaseModel):
    timestamp: datetime
    stage: str
    capability: str
    status: EventStatus
    message: str
    durationMs: int | None = None
    debug: dict[str, Any] | None = None
    artifactPath: str | None = None


class ReviewerIssueDecision(BaseModel):
    issueId: str
    state: ReviewerItemState = 'pending'
    note: str | None = None


class ReviewerAttachmentDecision(BaseModel):
    attachmentId: str
    state: ReviewerItemState = 'pending'
    note: str | None = None


class ReviewerDecision(BaseModel):
    taskState: ReviewerTaskState = 'pending'
    note: str | None = None
    issues: list[ReviewerIssueDecision] = Field(default_factory=list)
    attachments: list[ReviewerAttachmentDecision] = Field(default_factory=list)
    updatedAt: datetime | None = None


class ReviewerDecisionUpdateRequest(BaseModel):
    taskState: ReviewerTaskState = 'pending'
    note: str | None = None
    issues: list[ReviewerIssueDecision] = Field(default_factory=list)
    attachments: list[ReviewerAttachmentDecision] = Field(default_factory=list)


class ReviewPreparationProvenance(BaseModel):
    sourceTier: ReviewPreparationSourceTier = 'runtime_only'
    caseId: str | None = None
    caseVersion: str | None = None
    labelStatus: str | None = None
    truthLevel: str | None = None
    reviewStatus: str | None = None
    inferred: bool = False
    taskId: str | None = None
    taskType: TaskType | None = None
    resultArtifactNames: list[str] = Field(default_factory=list)
    resultArtifactPrimary: str | None = None
    usesRuntimeReviewerDecision: bool = True
    usesRuntimeStructuredReviewResult: bool = True


class ReviewPreparationSummary(BaseModel):
    truthTier: Literal['runtime_only', 'internal_reviewed_preparation'] = 'internal_reviewed_preparation'
    readyForPromotion: bool = False
    blockingReasons: list[str] = Field(default_factory=list)
    eligibleIssueIds: list[str] = Field(default_factory=list)
    deferredIssueIds: list[str] = Field(default_factory=list)
    rejectedIssueIds: list[str] = Field(default_factory=list)
    eligibleAttachmentIds: list[str] = Field(default_factory=list)
    deferredAttachmentIds: list[str] = Field(default_factory=list)
    rejectedAttachmentIds: list[str] = Field(default_factory=list)
    issueBlockingReasons: dict[str, list[str]] = Field(default_factory=dict)
    attachmentBlockingReasons: dict[str, list[str]] = Field(default_factory=dict)
    provenance: ReviewPreparationProvenance = Field(default_factory=ReviewPreparationProvenance)
    disclaimer: str | None = None


class ReviewPreparationIssueRecord(BaseModel):
    issueId: str
    disposition: ReviewPreparationDisposition = 'deferred'
    state: ReviewerItemState = 'pending'
    note: str | None = None
    issueKind: IssueKind | None = None
    applicabilityState: ApplicabilityState | None = None
    manualReviewNeeded: bool = False
    manualReviewReason: str | None = None
    evidenceMissing: bool = False
    missingFactKeys: list[str] = Field(default_factory=list)
    blockingReasons: list[str] = Field(default_factory=list)
    promotionBlockingReasons: list[str] = Field(default_factory=list)


class ReviewPreparationAttachmentRecord(BaseModel):
    attachmentId: str
    disposition: ReviewPreparationDisposition = 'deferred'
    state: ReviewerItemState = 'pending'
    note: str | None = None
    visibility: AttachmentVisibility | None = None
    parseState: str | None = None
    manualReviewNeeded: bool = False
    reason: str | None = None
    promotionBlockingReasons: list[str] = Field(default_factory=list)


class ReviewPreparationAsset(BaseModel):
    schemaVersion: Literal['v0.1'] = 'v0.1'
    truthTier: Literal['internal_reviewed_preparation'] = 'internal_reviewed_preparation'
    taskId: str
    documentType: ReviewDocumentType | None = None
    sourceDocumentRef: SourceDocumentRef | None = None
    reviewerDecisionUpdatedAt: datetime | None = None
    readyForPromotion: bool = False
    blockingReasons: list[str] = Field(default_factory=list)
    issueDecisions: list[ReviewPreparationIssueRecord] = Field(default_factory=list)
    attachmentDecisions: list[ReviewPreparationAttachmentRecord] = Field(default_factory=list)
    provenance: ReviewPreparationProvenance = Field(default_factory=ReviewPreparationProvenance)
    disclaimer: str | None = None


class TaskRecord(BaseModel):
    id: str
    taskType: TaskType
    capabilityMode: CapabilityMode
    query: str
    datasetId: str | None = None
    collectionId: str | None = None
    fixtureId: str | None = None
    sourceDocumentRef: SourceDocumentRef | None = None
    useWeb: bool = False
    debug: bool = False
    sourceUrls: list[str] = Field(default_factory=list)
    documentType: ReviewDocumentType | None = None
    disciplineTags: list[str] = Field(default_factory=list)
    strictMode: bool | None = None  # compatibility field still persisted and propagated into profile/result shaping; not an independent runtime branch switch
    policyPackIds: list[str] = Field(default_factory=list)
    rulePackIds: list[str] = Field(default_factory=list)
    externalContext: ExternalIntegrationContext | None = None
    status: TaskStatus = 'created'
    plan: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    reviewerDecision: ReviewerDecision | None = None
    error: dict[str, Any] | None = None
    createdAt: datetime
    updatedAt: datetime


class FixtureRecord(BaseModel):
    id: str
    title: str
    domain: str
    sourcePath: str
    copiedPath: str
    fileType: str
    notes: str | None = None


class CapabilityHealth(BaseModel):
    name: str
    available: bool
    mode: str
    detail: str | None = None
    raw: dict[str, Any] | None = None


class ReviewTaskClassification(BaseModel):
    model_config = ConfigDict(extra='forbid')

    l1: str = Field(min_length=1)
    l2: ReviewDocumentType
    l3: list[str] = Field(default_factory=list)


class ReviewTaskDocuments(BaseModel):
    model_config = ConfigDict(extra='forbid')

    target_file_ids: list[str] = Field(default_factory=list)
    basis_file_ids: list[str] = Field(default_factory=list)
    project_context_file_ids: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def _validate_target_files(self):
        if len(self.target_file_ids) != 1:
            raise ValueError('review-tasks currently require exactly one target_file_id')
        return self


class ReviewTaskBuiltinAssetSelections(BaseModel):
    model_config = ConfigDict(extra='forbid')

    standard_ids: list[str] = Field(default_factory=list)
    template_ids: list[str] = Field(default_factory=list)
    policy_pack_ids: list[str] = Field(default_factory=list)
    rule_pack_ids: list[str] = Field(default_factory=list)


class ReviewTaskIntent(BaseModel):
    model_config = ConfigDict(extra='forbid')

    enabled_modules: list[str] = Field(default_factory=list)
    disabled_modules: list[str] = Field(default_factory=list)
    focus_requirements: list[str] = Field(default_factory=list)


class ReviewTaskMetadata(BaseModel):
    model_config = ConfigDict(extra='forbid')

    client_request_id: str | None = None
    source: str | None = None
    debug: bool = False


class CreateReviewTaskRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    classification: ReviewTaskClassification
    documents: ReviewTaskDocuments
    builtin_asset_selections: ReviewTaskBuiltinAssetSelections = Field(default_factory=ReviewTaskBuiltinAssetSelections)
    review_intent: ReviewTaskIntent = Field(default_factory=ReviewTaskIntent)
    metadata: ReviewTaskMetadata = Field(default_factory=ReviewTaskMetadata)


class ReviewTaskLinks(BaseModel):
    status: str
    events: str
    result: str


class CreateReviewTaskResponse(BaseModel):
    task_id: str
    status: ReviewTaskStatus
    review_brief_id: str
    links: ReviewTaskLinks


class ReviewTaskError(BaseModel):
    code: str
    message: str


class ReviewTaskStatusResponse(BaseModel):
    task_id: str
    status: ReviewTaskStatus
    progress_stage: ReviewTaskProgressStage
    progress_message: str
    created_at: datetime
    updated_at: datetime
    report_id: str | None = None
    error: ReviewTaskError | None = None
    degraded: bool = False


class ReviewTaskSseArtifact(BaseModel):
    file_name: str
    download_url: str
    category: str | None = None
    stage: str | None = None


class ReviewTaskSseEvent(BaseModel):
    event: ReviewTaskEventType
    task_id: str
    stage: ReviewTaskProgressStage
    message: str
    timestamp: datetime
    status: ReviewTaskStatus
    artifact: ReviewTaskSseArtifact | None = None
    payload: dict[str, Any] | None = None


class ReviewTaskModuleResult(BaseModel):
    title: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    severity_summary: dict[str, int] = Field(default_factory=dict)
    traceability_summary: list[dict[str, Any]] = Field(default_factory=list)
    status: Literal['available', 'partial', 'not_applicable'] = 'available'


class ReviewTaskResultSummary(BaseModel):
    overall_conclusion: str
    risk_level: Literal['low', 'medium', 'high', 'unknown']
    key_counts: dict[str, int] = Field(default_factory=dict)
    key_metrics: dict[str, int] = Field(default_factory=dict)


class ReviewTaskExportLinks(BaseModel):
    markdown: str | None = None
    pdf: str | None = None
    html: str | None = None


class ReviewTaskResultMetadata(BaseModel):
    report_id: str
    generated_at: datetime
    degraded: bool = False
    traceability_available: bool = False
    assembler: str = 'HermesReviewAssembler'
    decision_owner: str = 'hermes'
    support_owner: str = 'structured_review_capability_facade'
    final_output_entrypoint: str = 'hermes_review_assembler'
    result_ownership: str = 'hermes_decision_layer'
    module_bucketing: str = 'execution_metadata_first'
    support_material_present: bool = False


class ReviewTaskResultResponse(BaseModel):
    task_id: str
    status: ReviewTaskStatus
    report_id: str
    summary: ReviewTaskResultSummary
    modules: dict[str, ReviewTaskModuleResult]
    key_findings: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    export_links: ReviewTaskExportLinks = Field(default_factory=ReviewTaskExportLinks)
    metadata: ReviewTaskResultMetadata
    raw: dict[str, Any] = Field(default_factory=dict)


class ReviewReportFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    feedback_type: ReviewFeedbackType
    comment: str | None = None
    source: str | None = None


class ReviewReportFeedbackResponse(BaseModel):
    accepted: bool = True
    report_id: str
    feedback_id: str
