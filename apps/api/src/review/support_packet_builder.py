from __future__ import annotations

from typing import Any
from pydantic import BaseModel

from src.review.schema import ExtractedFacts, ResolvedReviewProfile
from src.domain.models import TaskRecord
from src.review.basis_pack_resolver import ResolvedBasisProfile

class SupportPacket(BaseModel):
    """
    The support packet provided to the Hermes main review kernel.
    It contains structured facts, visibility metadata, and resolved governance profiles 
    but does NOT contain official verdicts, final grades, or judgment logic.
    """
    task_id: str
    document_type: str
    profile: dict[str, Any]
    facts: dict[str, Any]
    degraded: bool
    warning_signals: list[str]

class SupportPacketBuilder:
    """
    Harness component responsible for building the context boundary for Hermes.
    It packages 008 facts and resolved basis profiles without attempting to issue
    a final decision. 
    """
    def __init__(self) -> None:
        pass

    def build_packet(
        self, 
        review_record: TaskRecord, 
        profile: ResolvedReviewProfile,
        basis_profile: ResolvedBasisProfile,
        facts: ExtractedFacts
    ) -> SupportPacket:
        
        warning_signals = []
        if basis_profile.degraded:
            warning_signals.extend(basis_profile.degradation_reasons)
            
        return SupportPacket(
            task_id=review_record.id,
            document_type=profile.documentType,
            profile=basis_profile.model_dump(mode='json'),
            facts=facts.model_dump(mode='json'),
            degraded=basis_profile.degraded,
            warning_signals=warning_signals
        )
