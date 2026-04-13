"""
SupportPacketBuilder: Builds the context boundary for Hermes main review.

It packages 008 facts, resolved basis profiles, and warning signals
without attempting to issue a final decision.

HARD CONSTRAINT: The SupportPacket MUST NOT contain official verdicts,
final grades, or judgment logic. It is purely support material.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

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
    basis_summary: list[dict[str, Any]] = Field(default_factory=list)
    rule_pack_summary: list[dict[str, Any]] = Field(default_factory=list)
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

        # Build basis summary for Hermes consumption
        basis_summary = [
            {
                "basis_id": b.basis_id,
                "title": b.title,
                "source_type": b.source_type,
                "effective_status": b.effective_status,
                "file_refs": b.file_refs,
                "degraded": b.degraded,
            }
            for b in basis_profile.basis_documents
        ]

        # Build rule pack summary
        rule_pack_summary = [
            {
                "rule_pack_id": rp.rule_pack_id,
                "scope": rp.scope,
                "evidence_requirements": rp.evidence_requirements,
                "degraded": rp.degraded,
            }
            for rp in basis_profile.rule_packs
        ]

        return SupportPacket(
            task_id=getattr(review_record, 'id', getattr(review_record, 'taskId', '')),
            document_type=profile.documentType,
            profile=basis_profile.model_dump(mode='json'),
            facts=facts.model_dump(mode='json'),
            basis_summary=basis_summary,
            rule_pack_summary=rule_pack_summary,
            degraded=basis_profile.degraded,
            warning_signals=warning_signals,
        )
