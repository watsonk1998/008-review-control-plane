from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class GovernanceEntityType(str, Enum):
    basis = 'basis'
    pack = 'pack'
    rule_pack = 'rule_pack'
    profile_mapping = 'profile_mapping'

class DraftStatus(str, Enum):
    draft = 'draft'
    pending_approval = 'pending_approval'
    approved = 'approved'
    published = 'published'
    rejected = 'rejected'
    archived = 'archived'

class CandidateStatus(str, Enum):
    draft = 'draft'
    pending_review = 'pending_review'
    approved_for_transcription = 'approved_for_transcription'
    transcribed = 'transcribed'
    published = 'published'
    rejected = 'rejected'
    archived = 'archived'

class CandidateType(str, Enum):
    rule_note = 'rule_note'
    template_hint = 'template_hint'
    evidence_heuristic = 'evidence_heuristic'
    disambiguation_hint = 'disambiguation_hint'
    candidate_skill_note = 'candidate_skill_note'

class AuditAction(str, Enum):
    create = 'create'
    update = 'update'
    delete = 'delete'
    publish = 'publish'
    reject = 'reject'

class DraftRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str
    target_entity_type: GovernanceEntityType
    target_entity_id: str
    proposed_changes: dict[str, Any] = Field(default_factory=dict)
    status: DraftStatus = DraftStatus.draft
    created_by: str = 'system'
    reviewer_notes: str | None = None
    created_at: datetime
    updated_at: datetime

class CandidateArtifact(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str
    profile_id: str
    candidate_type: CandidateType
    content: str
    source: str = 'manual'
    status: CandidateStatus = CandidateStatus.draft
    created_by: str = 'system'
    reviewer_notes: str | None = None
    created_at: datetime
    updated_at: datetime

class AuditLogRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str
    entity_type: GovernanceEntityType
    entity_id: str
    action: AuditAction
    changes: dict[str, Any] = Field(default_factory=dict)
    created_by: str = 'system'
    created_at: datetime

# ---------------------------------------------------------------------------
# Frontend DTOs
# ---------------------------------------------------------------------------

class BasisDTO(BaseModel):
    basis_id: str
    title: str
    source_type: str
    version: str
    effective_status: str
    jurisdiction: str
    file_refs: list[str] = Field(default_factory=list)
    applicability_tags: list[str] = Field(default_factory=list)
    owner: str
    freshness_rule: str

class PackDTO(BaseModel):
    pack_id: str
    display_name: str
    basis_ids: list[str] = Field(default_factory=list)
    status: str
    default_profiles: list[str] = Field(default_factory=list)
    priority: str
    promotion_state: str
    role: str
    family: str

class RulePackDTO(BaseModel):
    rule_pack_id: str
    display_name: str
    description: str | None = None
    trigger_conditions: list[dict[str, Any]] = Field(default_factory=list)
    checks: list[dict[str, Any]] = Field(default_factory=list)
    status: str

class ProfileMappingDTO(BaseModel):
    mappings: dict[str, Any] = Field(default_factory=dict)

class CandidateArtifactDTO(BaseModel):
    id: str
    profile_id: str
    candidate_type: str
    content: str
    source: str
    status: str
    created_by: str
    reviewer_notes: str | None = None
    created_at: datetime
    updated_at: datetime

class CreateCandidateRequest(BaseModel):
    profile_id: str
    candidate_type: str
    content: str
    source: str = 'manual'

class UpdateCandidateRequest(BaseModel):
    status: str | None = None
    reviewer_notes: str | None = None

class PublishStateDTO(BaseModel):
    has_pending_draft: bool
    draft_id: str | None = None
    last_published_at: datetime | None = None

class SimulationRunRequest(BaseModel):
    document_type: str
    target_file_id: str
    pack_ids: list[str] = Field(default_factory=list)
    rule_pack_ids: list[str] = Field(default_factory=list)
    simulation_mode: bool = True
    learning_mode: bool = False

class SimulationRunResponse(BaseModel):
    result_class: str
    user_visible_title: str
    user_visible_notice: str
    support_packet: dict[str, Any] | None = None
    hermes_review_packets: list[dict[str, Any]] = Field(default_factory=list)
    generated_candidates: list[dict[str, Any]] | None = None
