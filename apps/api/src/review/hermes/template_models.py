from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentTemplate(BaseModel):
    id: str
    agent_name: str
    agent_purpose: str
    agent_scope: str
    execution_mode: Literal['module_only', 'hermes_router'] = 'module_only'
    module_bindings: list[str] = Field(default_factory=list)
    supported_document_types: list[str] = Field(default_factory=list)
    focus_keywords: list[str] = Field(default_factory=list)
    required_context_types: list[str] = Field(default_factory=list)
    input_contract: dict[str, Any] = Field(default_factory=dict)
    output_contract: dict[str, Any] = Field(default_factory=lambda: {'type': 'fact_packet'})
    instructions: str = ''
    prompt: str = ''
    default_enabled: bool = True
    save_policy: dict[str, Any] = Field(default_factory=dict)
    template_version: str = '1.0.0'
    compatibility: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentTemplateMatch(BaseModel):
    template: AgentTemplate
    score: int = 0
    reasons: list[str] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    agent_id: str
    template_id: str
    worker_id: str
    packet: dict[str, Any] | None = None
    module_outputs: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
