from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

TaskType = Literal['knowledge_qa', 'deep_research', 'document_research', 'review_assist', 'structured_review']
CapabilityMode = Literal['auto', 'deeptutor', 'gpt_researcher', 'fast', 'llm_only']
TaskStatus = Literal['created', 'planned', 'running', 'waiting_external', 'succeeded', 'failed', 'partial']
EventStatus = Literal['started', 'completed', 'failed', 'info']
ReviewDocumentType = Literal[
    'construction_org',
    'construction_scheme',
    'hazardous_special_scheme',
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


class CreateTaskRequest(BaseModel):
    taskType: TaskType
    capabilityMode: CapabilityMode = 'auto'
    query: str = Field(min_length=1)
    datasetId: str | None = None
    collectionId: str | None = None
    fixtureId: str | None = None
    useWeb: bool = False
    debug: bool = False
    sourceUrls: list[str] | None = None
    documentType: ReviewDocumentType | None = None
    disciplineTags: list[str] | None = None
    strictMode: bool | None = None
    policyPackIds: list[str] | None = None


class EvidenceSpan(BaseModel):
    sourceType: Literal['document', 'policy', 'artifact']
    sourceId: str
    locator: dict[str, Any]
    excerpt: str
    visibility: AttachmentVisibility | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.medium


class ReviewIssue(BaseModel):
    id: str
    title: str
    layer: ReviewLayer
    severity: Literal['high', 'medium', 'low', 'info']
    findingType: FindingType
    summary: str
    manualReviewNeeded: bool = False


class TaskArtifact(BaseModel):
    name: str
    fileName: str
    mediaType: str
    sizeBytes: int
    downloadUrl: str


class TaskEvent(BaseModel):
    timestamp: datetime
    stage: str
    capability: str
    status: EventStatus
    message: str
    durationMs: int | None = None
    debug: dict[str, Any] | None = None
    artifactPath: str | None = None


class TaskRecord(BaseModel):
    id: str
    taskType: TaskType
    capabilityMode: CapabilityMode
    query: str
    datasetId: str | None = None
    collectionId: str | None = None
    fixtureId: str | None = None
    useWeb: bool = False
    debug: bool = False
    sourceUrls: list[str] = Field(default_factory=list)
    documentType: ReviewDocumentType | None = None
    disciplineTags: list[str] = Field(default_factory=list)
    strictMode: bool | None = None
    policyPackIds: list[str] = Field(default_factory=list)
    status: TaskStatus = 'created'
    plan: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
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
