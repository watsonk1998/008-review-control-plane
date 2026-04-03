from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.domain.models import (
    AttachmentVisibility,
    ConfidenceLevel,
    EvidenceSpan,
    FindingType,
    ReviewDocumentType,
    ReviewIssue,
    ReviewLayer,
    TaskArtifact,
)


class StructuredReviewTask(BaseModel):
    taskId: str
    requestId: str
    documentType: ReviewDocumentType
    disciplineTags: list[str] = Field(default_factory=list)
    policyPackIds: list[str] = Field(default_factory=list)
    strictMode: bool = True
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


class EvidencePack(BaseModel):
    id: str
    version: str
    clauses: list[PolicyClause] = Field(default_factory=list)
    forceLevel: Literal['must', 'should', 'guidance'] = 'guidance'
    applicability: str = ''
    severityMapping: dict[str, str] = Field(default_factory=dict)
    ruleIds: list[str] = Field(default_factory=list)
    docTypes: list[str] = Field(default_factory=list)


class DocumentParseResult(BaseModel):
    documentId: str
    filePath: str
    fileType: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    figures: list[dict[str, Any]] = Field(default_factory=list)
    normalizedText: str = ''
    preview: str = ''
    visibilityReport: dict[str, Any] = Field(default_factory=dict)
    parseWarnings: list[str] = Field(default_factory=list)


class ExtractedFacts(BaseModel):
    projectFacts: dict[str, Any] = Field(default_factory=dict)
    hazardFacts: dict[str, Any] = Field(default_factory=dict)
    scheduleFacts: dict[str, Any] = Field(default_factory=dict)
    resourceFacts: dict[str, Any] = Field(default_factory=dict)
    attachmentFacts: dict[str, Any] = Field(default_factory=dict)
    emergencyFacts: dict[str, Any] = Field(default_factory=dict)
    factEvidence: dict[str, list[EvidenceSpan]] = Field(default_factory=dict)
    unresolvedFacts: list[str] = Field(default_factory=list)


class RuleHit(BaseModel):
    ruleId: str
    packId: str
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
    docEvidence: list[EvidenceSpan] = Field(default_factory=list)
    policyEvidence: list[EvidenceSpan] = Field(default_factory=list)
    recommendation: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    whetherManualReviewNeeded: bool = False


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
    referenceBlockIds: list[str] = Field(default_factory=list)
    titleBlockId: str | None = None


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


class StructuredReviewSummary(BaseModel):
    overallConclusion: str
    documentType: ReviewDocumentType
    selectedPacks: list[str] = Field(default_factory=list)
    manualReviewNeeded: bool = False
    issueCount: int = 0
    layerCounts: dict[str, int] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)


class StructuredReviewResult(BaseModel):
    summary: StructuredReviewSummary
    resolvedProfile: ResolvedReviewProfile
    issues: list[FinalIssue] = Field(default_factory=list)
    matrices: StructuredReviewMatrices
    artifactIndex: list[TaskArtifact] = Field(default_factory=list)
    reportMarkdown: str = ''
    artifacts: list[str] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    capabilitiesUsed: list[str] = Field(default_factory=list)
    finalAnswer: str = ''
    notice: str | None = None
