"""
SupportPacketBuilder: Builds the context boundary for Hermes main review.

It packages 008 facts, resolved basis profiles, and warning signals
without attempting to issue a final decision.

HARD CONSTRAINT: The SupportPacket MUST NOT contain official verdicts,
final grades, or judgment logic. It is purely support material.
"""

from __future__ import annotations

from pathlib import Path
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
    basis_fulltext_context: list[dict[str, Any]] = Field(default_factory=list)
    expert_review_points: list[str] = Field(default_factory=list)
    priority_focus_axes: list[str] = Field(default_factory=list)
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
        basis_fulltext_context = self._load_basis_fulltext_context(basis_profile)
        expert_review_points = self._collect_expert_review_points(basis_fulltext_context)
        priority_focus_axes = self._collect_priority_focus_axes(profile, basis_profile)

        return SupportPacket(
            task_id=getattr(review_record, 'id', getattr(review_record, 'taskId', '')),
            document_type=profile.documentType,
            profile=basis_profile.model_dump(mode='json'),
            facts=facts.model_dump(mode='json'),
            basis_summary=basis_summary,
            rule_pack_summary=rule_pack_summary,
            basis_fulltext_context=basis_fulltext_context,
            expert_review_points=expert_review_points,
            priority_focus_axes=priority_focus_axes,
            degraded=basis_profile.degraded,
            warning_signals=warning_signals,
        )

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[4]

    def _load_basis_fulltext_context(self, basis_profile: ResolvedBasisProfile) -> list[dict[str, Any]]:
        root = self._repo_root()
        contexts: list[dict[str, Any]] = []
        for basis in basis_profile.basis_documents:
            chunks: list[str] = []
            for ref in basis.file_refs[:2]:
                path = root / ref
                if not path.exists() or not path.is_file():
                    continue
                try:
                    content = path.read_text(encoding='utf-8')
                except Exception:
                    continue
                if not content.strip():
                    continue
                chunks.append(content[:6000])
            if chunks:
                contexts.append({
                    'basis_id': basis.basis_id,
                    'title': basis.title,
                    'excerpt': '\n\n'.join(chunks)[:12000],
                })
        return contexts

    def _collect_expert_review_points(self, contexts: list[dict[str, Any]]) -> list[str]:
        for item in contexts:
            basis_id = str(item.get('basis_id') or '')
            title = str(item.get('title') or '')
            if '监理工程师对停电施工方案的审核规则及要点' not in basis_id and '监理工程师对停电施工方案的审核规则及要点' not in title:
                continue
            excerpt = str(item.get('excerpt') or '')
            points = []
            for line in excerpt.splitlines():
                normalized = line.strip().lstrip('-*•0123456789.、（）() ')
                if len(normalized) < 6:
                    continue
                if any(keyword in normalized for keyword in ('停电', '验电', '接地', '挂牌', '遮栏', '工作票', '操作票', '勘察', '审批', '用户告知', '送电', '归档', '整改', '监护', '交底')):
                    points.append(normalized)
                if len(points) >= 16:
                    break
            return points
        return []

    def _collect_priority_focus_axes(self, profile: ResolvedReviewProfile, basis_profile: ResolvedBasisProfile) -> list[str]:
        axes = [
            '停电范围与停复电关键信息',
            '停电申请审批与用户告知',
            '停电五步法安全动作闭环',
            '工作票/操作票/现场勘察证据链',
            '防反送电与双电源风险控制',
            '完工送电、资料归档与整改闭环',
        ]
        if profile.documentType != 'distribution_network_special_scheme':
            return []
        rule_pack_ids = {item.rule_pack_id for item in basis_profile.rule_packs}
        if 'distribution_network.restoration_closure.v1' not in rule_pack_ids:
            axes = axes[:-1]
        return axes
