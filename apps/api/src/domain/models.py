from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TaskType = Literal["knowledge_qa", "deep_research", "document_research", "review_assist"]
CapabilityMode = Literal["auto", "deeptutor", "gpt_researcher", "fast", "llm_only"]
TaskStatus = Literal["created", "planned", "running", "waiting_external", "succeeded", "failed", "partial"]
EventStatus = Literal["started", "completed", "failed", "info"]


class CreateTaskRequest(BaseModel):
    taskType: TaskType
    capabilityMode: CapabilityMode = "auto"
    query: str = Field(min_length=1)
    datasetId: str | None = None
    collectionId: str | None = None
    fixtureId: str | None = None
    useWeb: bool = False
    debug: bool = False
    sourceUrls: list[str] | None = None


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
    status: TaskStatus = "created"
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
