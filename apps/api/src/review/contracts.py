"""
Unified review contracts for 008 + Hermes dual-path architecture.

Design intent:
- ReviewBrief: compiled task input, single source of truth for both engines
- FactPacket: structured output from any review engine, aligned schema
- FinalReportPacket: fused output from dual-path orchestration

These contracts sit BETWEEN the task entry layer and engine implementations,
providing a clean boundary for dual-path orchestration. They do NOT replace
008's internal schemas (review/schema.py) — they wrap them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.domain.models import ReviewDocumentType


# ---------------------------------------------------------------------------
# ReviewBrief — compiled task specification
# ---------------------------------------------------------------------------

class ReviewBrief(BaseModel):
    """Compiled task specification — single input contract for all review engines.

    Created by TaskCompiler from raw task inputs.
    Both 008 and Hermes receive the same brief.
    """

    review_id: str
    review_object_type: ReviewDocumentType
    target_files: list[dict[str, Any]] = Field(default_factory=list)
    basis_files: list[dict[str, Any]] = Field(default_factory=list)
    project_context_files: list[dict[str, Any]] = Field(default_factory=list)
    focus_pack: dict[str, Any] = Field(default_factory=dict)
    review_policy: dict[str, Any] = Field(default_factory=dict)
    report_type: str = 'structured_review'
    query: str = ''
    compiled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# FindingItem — single finding, aligned across engines
# ---------------------------------------------------------------------------

class FindingItem(BaseModel):
    """Single finding in a review packet — aligned across engines."""

    id: str
    title: str
    severity: Literal['high', 'medium', 'low', 'info']
    category: str = ''
    layer: str = ''
    evidence_status: Literal[
        'grounded', 'inferred', 'evidence_gap', 'visibility_gap'
    ] = 'grounded'
    evidence_refs: list[str] = Field(default_factory=list)
    basis_refs: list[str] = Field(default_factory=list)
    suggestion: str = ''
    summary: str = ''
    finding_type: str = ''
    manual_review_needed: bool = False
    confidence: Literal['high', 'medium', 'low'] = 'medium'
    source_engine: str = ''
    raw_data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# ReviewPacketMetrics — summary counts
# ---------------------------------------------------------------------------

class ReviewPacketMetrics(BaseModel):
    """Summary metrics for a review packet."""

    total_findings: int = 0
    high_severity: int = 0
    medium_severity: int = 0
    low_severity: int = 0
    info_findings: int = 0
    grounded_findings: int = 0
    evidence_gap_findings: int = 0
    manual_review_needed: int = 0


# ---------------------------------------------------------------------------
# FactPacket — structured engine output (008 or Hermes)
# ---------------------------------------------------------------------------

class FactPacket(BaseModel):
    """Structured output from a review engine.

    Used for both 008 and Hermes results.
    The ``engine`` field discriminates origin.
    """

    review_id: str
    engine: Literal['008', 'hermes']
    summary_metrics: ReviewPacketMetrics = Field(default_factory=ReviewPacketMetrics)
    findings: list[FindingItem] = Field(default_factory=list)
    overall_assessment: str = ''
    raw_result: dict[str, Any] = Field(default_factory=dict)
    produced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    degraded: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# FinalReportPacket — fused dual-path output
# ---------------------------------------------------------------------------

class FinalReportPacket(BaseModel):
    """Fused output from dual-path review."""

    review_id: str
    final_grade: str = ''
    executive_summary: str = ''
    top_risks: list[FindingItem] = Field(default_factory=list)
    key_findings: list[FindingItem] = Field(default_factory=list)
    supplemental_findings: list[FindingItem] = Field(default_factory=list)
    all_findings: list[FindingItem] = Field(default_factory=list)
    traceability: list[dict[str, Any]] = Field(default_factory=list)
    report_markdown: str = ''
    report_sections: list[dict[str, Any]] = Field(default_factory=list)
    engines_used: list[str] = Field(default_factory=list)
    degradation_info: dict[str, Any] = Field(default_factory=dict)
    produced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_packets: dict[str, dict[str, Any]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
