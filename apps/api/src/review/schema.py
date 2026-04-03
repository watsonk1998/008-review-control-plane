from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.models import (
    AttachmentVisibility,
    AttachmentLocator,
    BlockLocator,
    ClauseLocator,
    ConfidenceLevel,
    EvidenceSpan,
    EvidenceLocator,
    FindingType,
    ReviewDocumentType,
    ReviewIssue,
    ReviewLayer,
    SectionLocator,
    SourceDocumentRef,
    TaskArtifact,
    TableLocator,
)


class StructuredReviewTask(BaseModel):
    taskId: str
    requestId: str
    documentType: ReviewDocumentType
    disciplineTags: list[str] = Field(default_factory=list)
    policyPackIds: list[str] = Field(default_factory=list)
    strictMode: bool = True
    sourceDocumentRef: SourceDocumentRef
    sourceDocumentPath: str
    sourceFixtureId: str | None = None
    useAssistArtifacts: bool = False


class ResolvedReviewProfile(BaseModel):
    requestedDocumentType: ReviewDocumentType | None = None
    requestedDisciplineTags: list[str] = Field(default_factory=list)
    requestedPolicyPackIds: list[str] = Field(default_factory=list)
    documentType: ReviewDocumentType
    disciplineTags: list[str] = Field(default_factory=list)
    policyPackIds: list[str] = Field(default_factory=list)
    strictMode: bool = True


class PolicyClause(BaseModel):
    id: str
    sourceId: str
    title: str
    excerpt: str
    forceLevel: Literal['must', 'should', 'guidance']
    applicability: str


class PolicyPack(BaseModel):
    id: str
    version: str
    docTypes: list[str]
    disciplineTags: list[str] = Field(default_factory=list)
    extractorIds: list[str] = Field(default_factory=list)
    ruleIds: list[str] = Field(default_factory=list)
    evidencePackIds: list[str] = Field(default_factory=list)
    defaultEnabled: bool = True
    description: str = ''
    readiness: Literal['ready', 'placeholder'] = 'ready'


class EvidencePack(BaseModel):
    id: str
    version: str
    clauses: list[PolicyClause] = Field(default_factory=list)
    forceLevel: Literal['must', 'should', 'guidance'] = 'guidance'
    applicability: str = ''
    severityMapping: dict[str, str] = Field(default_factory=dict)
    ruleIds: list[str] = Field(default_factory=list)
    docTypes: list[str] = Field(default_factory=list)


class RuleHit(BaseModel):
    ruleId: str
    packId: str
    packReadiness: Literal['ready', 'placeholder'] = 'ready'
    matchType: Literal['direct_hit', 'inferred_risk', 'visibility_gap']
    status: Literal['hit', 'pass', 'not_applicable', 'manual_review_needed']
    layerHint: ReviewLayer
    severityHint: str
    factRefs: list[str] = Field(default_factory=list)
    evidenceRefs: list[str] = Field(default_factory=list)
    rationale: str | None = None


class IssueCandidate(BaseModel):
    candidateId: str
    title: str
    ruleHits: list[RuleHit] = Field(default_factory=list)
    layerHint: ReviewLayer
    severityHint: str
    findingType: FindingType
    docEvidence: list[EvidenceSpan] = Field(default_factory=list)
    policyEvidence: list[EvidenceSpan] = Field(default_factory=list)
    evidenceMissing: bool = False
    manualReviewNeeded: bool = False
    manualReviewReason: str | None = None


class FinalIssue(ReviewIssue):
    model_config = ConfigDict(extra='ignore')

    docEvidence: list[EvidenceSpan] = Field(default_factory=list)
    policyEvidence: list[EvidenceSpan] = Field(default_factory=list)
    recommendation: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.medium


class HazardIdentificationMatrix(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class RuleHitMatrixRow(BaseModel):
    ruleId: str
    packId: str
    status: str
    layerHint: str
    severityHint: str
    matchType: str


class ConflictMatrix(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class AttachmentVisibilityMatrixItem(BaseModel):
    id: str
    attachmentNumber: str
    title: str
    visibility: AttachmentVisibility
    parseState: str
    manualReviewNeeded: bool = False
    reason: str | None = None
    referenceBlockIds: list[str] = Field(default_factory=list)
    titleBlockId: str | None = None


class VisibilityAssessment(BaseModel):
    parserLimited: bool = False
    fileType: str | None = None
    attachmentCount: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    reasonCounts: dict[str, int] = Field(default_factory=dict)
    duplicateSectionTitles: list[str] = Field(default_factory=list)
    manualReviewNeeded: bool = False


class DocumentParseResult(BaseModel):
    documentId: str
    filePath: str
    fileType: str
    parseMode: Literal['docx_structured', 'pdf_text_only', 'markdown_text', 'plain_text']
    parserLimited: bool = False
    sections: list[dict[str, Any]] = Field(default_factory=list)
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[AttachmentVisibilityMatrixItem] = Field(default_factory=list)
    figures: list[dict[str, Any]] = Field(default_factory=list)
    normalizedText: str = ''
    preview: str = ''
    visibility: VisibilityAssessment = Field(default_factory=VisibilityAssessment)
    visibilityReport: dict[str, Any] = Field(default_factory=dict)
    parseWarnings: list[str] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def _load_visibility(cls, data: Any):
        if not isinstance(data, dict):
            return data
        visibility = data.get('visibility')
        visibility_report = data.get('visibilityReport') or {}
        if visibility is None:
            visibility = {
                **visibility_report,
                'parserLimited': data.get('parserLimited', visibility_report.get('parserLimited', False)),
                'fileType': data.get('fileType', visibility_report.get('fileType')),
            }
        data['visibility'] = visibility
        if 'parserLimited' not in data:
            data['parserLimited'] = visibility.get('parserLimited', False)
        return data

    @model_validator(mode='after')
    def _sync_visibility_report(self):
        self.parserLimited = self.visibility.parserLimited
        self.visibilityReport = self.visibility.model_dump(mode='json')
        return self


class UnresolvedFact(BaseModel):
    code: str
    factKey: str
    summary: str


class ExtractedFacts(BaseModel):
    projectFacts: dict[str, Any] = Field(default_factory=dict)
    hazardFacts: dict[str, Any] = Field(default_factory=dict)
    scheduleFacts: dict[str, Any] = Field(default_factory=dict)
    resourceFacts: dict[str, Any] = Field(default_factory=dict)
    attachmentFacts: dict[str, Any] = Field(default_factory=dict)
    emergencyFacts: dict[str, Any] = Field(default_factory=dict)
    factEvidence: dict[str, list[EvidenceSpan]] = Field(default_factory=dict)
    unresolvedFacts: list[UnresolvedFact] = Field(default_factory=list)


class SectionStructureMatrixItem(BaseModel):
    id: str
    title: str
    level: int
    parentId: str | None = None
    duplicate: bool = False


class StructuredReviewMatrices(BaseModel):
    hazardIdentification: HazardIdentificationMatrix
    ruleHits: list[RuleHitMatrixRow] = Field(default_factory=list)
    conflicts: ConflictMatrix
    attachmentVisibility: list[AttachmentVisibilityMatrixItem] = Field(default_factory=list)
    sectionStructure: list[SectionStructureMatrixItem] = Field(default_factory=list)
    issueLayerCounts: dict[str, int] = Field(default_factory=dict)


class StructuredReviewVisibilitySummary(BaseModel):
    attachmentCount: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    duplicateSectionTitles: list[str] = Field(default_factory=list)
    parseWarnings: list[str] = Field(default_factory=list)
    reasonCounts: dict[str, int] = Field(default_factory=dict)
    manualReviewNeeded: bool = False


class StructuredReviewSummary(BaseModel):
    overallConclusion: str
    documentType: ReviewDocumentType
    selectedPacks: list[str] = Field(default_factory=list)
    manualReviewNeeded: bool = False
    issueCount: int = 0
    layerCounts: dict[str, int] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)
    visibilitySummary: StructuredReviewVisibilitySummary = Field(default_factory=StructuredReviewVisibilitySummary)


class StructuredReviewResult(BaseModel):
    summary: StructuredReviewSummary
    resolvedProfile: ResolvedReviewProfile
    issues: list[FinalIssue] = Field(default_factory=list)
    matrices: StructuredReviewMatrices
    artifactIndex: list[TaskArtifact] = Field(default_factory=list)
    reportMarkdown: str = ''
    artifacts: list[str] = Field(default_factory=list)
    unresolvedFacts: list[UnresolvedFact] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    capabilitiesUsed: list[str] = Field(default_factory=list)
    finalAnswer: str = ''
    notice: str | None = None
