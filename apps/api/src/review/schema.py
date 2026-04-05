from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.models import (
    ApplicabilityState,
    AttachmentVisibility,
    AttachmentLocator,
    BlockLocator,
    ClauseLocator,
    ConfidenceLevel,
    EvidenceSpan,
    EvidenceLocator,
    FindingType,
    IssueKind,
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
    promotionCriteria: dict[str, bool] = Field(default_factory=dict)


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
    applicabilityState: ApplicabilityState = 'applies'
    layerHint: ReviewLayer
    severityHint: str
    factRefs: list[str] = Field(default_factory=list)
    evidenceRefs: list[str] = Field(default_factory=list)
    requiredFactKeys: list[str] = Field(default_factory=list)
    missingFactKeys: list[str] = Field(default_factory=list)
    clauseIds: list[str] = Field(default_factory=list)
    blockingReasons: list[str] = Field(default_factory=list)
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
    missingFactKeys: list[str] = Field(default_factory=list)
    blockingReasons: list[str] = Field(default_factory=list)


class FinalIssue(ReviewIssue):
    model_config = ConfigDict(extra='ignore')

    docEvidence: list[EvidenceSpan] = Field(default_factory=list)
    policyEvidence: list[EvidenceSpan] = Field(default_factory=list)
    recommendation: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.medium
    missingFactKeys: list[str] = Field(default_factory=list)
    blockingReasons: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def _derive_review_semantics(self):
        effective_evidence_missing = bool(
            self.evidenceMissing or _has_explicit_evidence_gap(self.missingFactKeys, self.blockingReasons)
        )
        self.issueKind = _derive_issue_kind(
            finding_type=self.findingType,
            evidence_missing=effective_evidence_missing,
            missing_fact_keys=self.missingFactKeys,
            blocking_reasons=self.blockingReasons,
        )
        self.applicabilityState = _derive_applicability_state(
            issue_kind=self.issueKind,
            manual_review_needed=self.manualReviewNeeded,
            manual_review_reason=self.manualReviewReason,
            evidence_missing=effective_evidence_missing,
            missing_fact_keys=self.missingFactKeys,
            blocking_reasons=self.blockingReasons,
        )
        self.evidenceMissing = self.issueKind == 'evidence_gap'
        return self


class HazardIdentificationMatrix(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class RuleHitMatrixRow(BaseModel):
    ruleId: str
    packId: str
    packReadiness: Literal['ready', 'placeholder'] = 'ready'
    status: str
    applicabilityState: ApplicabilityState = 'applies'
    layerHint: str
    severityHint: str
    matchType: str
    requiredFactKeys: list[str] = Field(default_factory=list)
    missingFactKeys: list[str] = Field(default_factory=list)
    clauseIds: list[str] = Field(default_factory=list)
    blockingReasons: list[str] = Field(default_factory=list)


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


class VisibilityPreflightChecklistItem(BaseModel):
    key: str
    status: Literal['pass', 'manual_review_required', 'info'] = 'info'
    summary: str
    blocking: bool = False


class VisibilityPreflight(BaseModel):
    gateDecision: Literal['ready', 'manual_review_required'] = 'ready'
    blockingReasons: list[str] = Field(default_factory=list)
    checklist: list[VisibilityPreflightChecklistItem] = Field(default_factory=list)
    parserLimitations: list[str] = Field(default_factory=list)
    attachmentTaxonomySummary: dict[str, Any] = Field(default_factory=dict)


class VisibilityAssessment(BaseModel):
    parseMode: Literal['docx_structured', 'pdf_text_only', 'markdown_text', 'plain_text'] | None = None
    parserLimited: bool = False
    fileType: str | None = None
    attachmentCount: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    reasonCounts: dict[str, int] = Field(default_factory=dict)
    duplicateSectionTitles: list[str] = Field(default_factory=list)
    parseWarnings: list[str] = Field(default_factory=list)
    manualReviewNeeded: bool = False
    manualReviewReason: str | None = None
    preflight: VisibilityPreflight = Field(default_factory=VisibilityPreflight)


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
                'parseMode': data.get('parseMode', visibility_report.get('parseMode')),
                'parserLimited': data.get('parserLimited', visibility_report.get('parserLimited', False)),
                'fileType': data.get('fileType', visibility_report.get('fileType')),
                'parseWarnings': data.get('parseWarnings', visibility_report.get('parseWarnings', [])),
                'manualReviewReason': data.get('manualReviewReason', visibility_report.get('manualReviewReason')),
            }
        data['visibility'] = visibility
        if 'parserLimited' not in data:
            data['parserLimited'] = visibility.get('parserLimited', False)
        return data

    @model_validator(mode='after')
    def _sync_visibility_report(self):
        self.visibility.parseMode = self.parseMode
        self.parserLimited = self.visibility.parserLimited
        self.visibility.parseWarnings = list(dict.fromkeys(self.parseWarnings or self.visibility.parseWarnings))
        attachment_requires_manual_review = any(
            (self.visibility.counts or {}).get(state, 0) > 0
            for state in ['attachment_unparsed', 'referenced_only', 'missing', 'unknown']
        )
        parser_requires_manual_review = self.parseMode == 'pdf_text_only' and self.visibility.parserLimited
        self.visibility.manualReviewNeeded = bool(
            self.visibility.manualReviewNeeded or attachment_requires_manual_review or parser_requires_manual_review
        )
        if not self.visibility.manualReviewReason:
            self.visibility.manualReviewReason = _default_manual_review_reason_from_visibility(
                self.visibility,
                parser_requires_manual_review=parser_requires_manual_review,
            )
        if not self.visibility.manualReviewNeeded:
            self.visibility.manualReviewReason = None
        self.visibility.preflight = _derive_visibility_preflight(self.visibility)
        self.parseWarnings = list(self.visibility.parseWarnings)
        self.visibilityReport = self.visibility.model_dump(mode='json')
        return self


class UnresolvedFact(BaseModel):
    code: str
    factKey: str
    summary: str
    sourceExtractor: str | None = None
    blockingReason: str | None = None
    visibilityLimited: bool = False
    blockingRuleIds: list[str] = Field(default_factory=list)
    blockingIssueIds: list[str] = Field(default_factory=list)
    blockingIssueTitles: list[str] = Field(default_factory=list)


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
    visibility: VisibilityAssessment
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


_VISIBILITY_BLOCKING_REASONS = {
    'visibility_gap',
    'attachment_unparsed',
    'referenced_only',
    'visibility_unknown',
    'parser_limited_pdf_requires_manual_review',
}

_EVIDENCE_GAP_BLOCKING_REASONS = {
    'missing_fact',
    'parser_limited_source',
    'document_evidence_unavailable',
    'policy_evidence_unavailable',
}

_VISIBILITY_REASON_PRIORITY = [
    'explicit_missing_marker',
    'title_detected_but_body_not_reliably_parsed',
    'title_detected_without_attachment_body',
    'reference_detected_in_limited_parser',
    'reference_detected_without_attachment_body',
]


def _default_manual_review_reason_from_visibility(
    visibility: VisibilityAssessment,
    *,
    parser_requires_manual_review: bool,
) -> str | None:
    reason_counts = visibility.reasonCounts or {}
    for reason in _VISIBILITY_REASON_PRIORITY:
        if reason_counts.get(reason, 0) > 0:
            return reason
    counts = visibility.counts or {}
    if counts.get('attachment_unparsed', 0) > 0:
        return 'attachment_unparsed'
    if counts.get('referenced_only', 0) > 0:
        return 'referenced_only'
    if counts.get('unknown', 0) > 0:
        return 'visibility_unknown'
    if parser_requires_manual_review:
        return 'parser_limited_pdf_requires_manual_review'
    return None


def _derive_visibility_preflight(visibility: VisibilityAssessment) -> VisibilityPreflight:
    counts = visibility.counts or {}
    parser_limitations = [
        warning
        for warning in (visibility.parseWarnings or [])
        if warning.startswith('pdf_') or warning.startswith('text_')
    ]
    blocking_reasons: list[str] = []
    if visibility.parserLimited:
        blocking_reasons.append('parser_limited_pdf')
    if counts.get('attachment_unparsed', 0) > 0:
        blocking_reasons.append('attachment_unparsed')
    if counts.get('referenced_only', 0) > 0:
        blocking_reasons.append('referenced_only')
    if counts.get('unknown', 0) > 0:
        blocking_reasons.append('attachment_unknown')
    if counts.get('missing', 0) > 0:
        blocking_reasons.append('attachment_missing_confirmed')
    blocking_reasons = list(dict.fromkeys(blocking_reasons))

    attachment_gap_count = sum(
        counts.get(state, 0)
        for state in ['attachment_unparsed', 'referenced_only', 'missing', 'unknown']
    )
    checklist = [
        VisibilityPreflightChecklistItem(
            key='parse_source_readiness',
            status='manual_review_required' if visibility.parserLimited else 'pass',
            summary='当前解析路径为 parser-limited，应按保守口径进入人工复核。'
            if visibility.parserLimited
            else '当前解析路径未触发 parser-limited gate。',
            blocking=visibility.parserLimited,
        ),
        VisibilityPreflightChecklistItem(
            key='attachment_visibility',
            status='manual_review_required' if attachment_gap_count else 'pass',
            summary=f'存在 {attachment_gap_count} 个附件/附图条目未完全进入当前可视域。'
            if attachment_gap_count
            else '附件可视域未触发额外前置阻断。',
            blocking=attachment_gap_count > 0,
        ),
        VisibilityPreflightChecklistItem(
            key='section_structure_signal',
            status='info' if visibility.duplicateSectionTitles else 'pass',
            summary='检测到重复章节标题，需在正式审查中谨慎解释定位结果。'
            if visibility.duplicateSectionTitles
            else '章节结构未检测到重复标题信号。',
            blocking=False,
        ),
        VisibilityPreflightChecklistItem(
            key='manual_review_gate',
            status='manual_review_required' if visibility.manualReviewNeeded else 'pass',
            summary='当前任务已满足人工复核前置条件。'
            if visibility.manualReviewNeeded
            else '当前任务未触发额外人工复核 gate。',
            blocking=visibility.manualReviewNeeded,
        ),
    ]
    gate_decision: Literal['ready', 'manual_review_required'] = (
        'manual_review_required' if visibility.manualReviewNeeded or blocking_reasons else 'ready'
    )
    return VisibilityPreflight(
        gateDecision=gate_decision,
        blockingReasons=blocking_reasons,
        checklist=checklist,
        parserLimitations=parser_limitations,
        attachmentTaxonomySummary={
            'attachmentCount': visibility.attachmentCount,
            'counts': dict(counts),
            'reasonCounts': dict(visibility.reasonCounts or {}),
            'manualReviewReason': visibility.manualReviewReason,
        },
    )


def _has_explicit_evidence_gap(missing_fact_keys: list[str], blocking_reasons: list[str]) -> bool:
    return bool(missing_fact_keys or (_EVIDENCE_GAP_BLOCKING_REASONS & set(blocking_reasons or [])))


def _derive_issue_kind(
    *,
    finding_type: FindingType,
    evidence_missing: bool,
    missing_fact_keys: list[str],
    blocking_reasons: list[str],
) -> IssueKind:
    if finding_type == FindingType.visibility_gap:
        return 'visibility_gap'
    if finding_type == FindingType.suggestion_enhancement:
        return 'enhancement'
    if evidence_missing and _has_explicit_evidence_gap(missing_fact_keys, blocking_reasons):
        return 'evidence_gap'
    return 'hard_defect'


def _derive_applicability_state(
    *,
    issue_kind: IssueKind,
    manual_review_needed: bool,
    manual_review_reason: str | None,
    evidence_missing: bool,
    missing_fact_keys: list[str],
    blocking_reasons: list[str],
) -> ApplicabilityState:
    if manual_review_reason in _VISIBILITY_BLOCKING_REASONS or issue_kind == 'visibility_gap':
        return 'blocked_by_visibility'
    if issue_kind == 'evidence_gap' or (evidence_missing and _has_explicit_evidence_gap(missing_fact_keys, blocking_reasons)):
        return 'blocked_by_missing_fact'
    if manual_review_needed:
        return 'partial'
    return 'applies'
