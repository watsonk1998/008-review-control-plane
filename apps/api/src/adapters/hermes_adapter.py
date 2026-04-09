"""
Hermes Review Adapter: independent second-path review via LLM.

Architecture note:
- The upstream hermes-agent (NousResearch/hermes-agent) is a CLI agent, NOT a REST API
- Our integration uses the same LLM infrastructure (LLMGateway) to run an
  independent "Hermes-style" review — no subprocess, no CLI dependency
- This keeps the integration lightweight, async-safe, and decoupled from
  hermes-agent releases

Boundary contract:
    Input:  ReviewBrief + optional 008 FactPacket
    Output: FactPacket (engine='hermes')
    Degradation: returns degraded packet with error info on any failure
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from src.adapters.llm_gateway import LLMGateway
from src.review.contracts import FactPacket, FindingItem, ReviewBrief, ReviewPacketMetrics

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hermes review system prompt
# ---------------------------------------------------------------------------
HERMES_SYSTEM_PROMPT = """\
你是 Hermes 审查引擎 — 一个独立的工程文档审查专家。
你的职责是对施工方案/施工组织设计进行独立的第二路审查。

你会收到：
1. 审查任务书（ReviewBrief），包含文档类型、关注领域等
2. 第一路审查（008引擎）已发现的问题清单

你的任务：
- 独立评估文档的整体质量和合规性
- 发现第一路审查可能遗漏的问题
- 对第一路审查已有的重要问题给出你的独立判断
- 关注宏观层面的风险和系统性问题

输出格式（严格 JSON，不要包裹 markdown 代码块）：
{
  "overall_assessment": "总体评价（一段话）",
  "grade": "conditional_pass | needs_revision | fail",
  "findings": [
    {
      "id": "H-001",
      "title": "问题标题",
      "severity": "high | medium | low | info",
      "category": "structure | compliance | safety | completeness | consistency",
      "summary": "问题概述",
      "suggestion": "改进建议",
      "confidence": "high | medium | low",
      "corroborates_008_finding": "如与008问题相关填008问题ID，否则null"
    }
  ],
  "top_risks": ["风险1", "风险2"],
  "supplemental_observations": "补充观察（可选）"
}

规则：
- 不要简单重复第一路审查的内容，要有独立视角
- 重点关注系统性风险、逻辑一致性、关键遗漏
- severity 要保守，没有充分依据时用 info
- 返回纯 JSON"""


class HermesAdapter:
    """Independent second-path review engine using LLM.

    This adapter is intentionally thin — it owns the prompt, the LLM call,
    and the response parsing. All orchestration logic lives in
    DualReviewOrchestrator.
    """

    def __init__(self, llm_gateway: LLMGateway | None = None):
        self._llm = llm_gateway

    @property
    def available(self) -> bool:
        return self._llm is not None

    async def review(
        self,
        brief: ReviewBrief,
        fact_packet_008: FactPacket | None = None,
        *,
        document_preview: str = '',
    ) -> FactPacket:
        """Execute Hermes second-path review.

        Returns FactPacket with engine='hermes'.
        On any failure, returns a degraded packet (degraded=True, error set).
        """
        if not self.available:
            logger.warning('[hermes] LLM gateway not configured — returning degraded packet')
            return self._degraded_packet(brief.review_id, 'LLM gateway not configured')

        try:
            logger.info('[hermes] Starting review for %s', brief.review_id)
            user_prompt = self._build_prompt(brief, fact_packet_008, document_preview)

            response = await self._llm.chat(
                [
                    {'role': 'system', 'content': HERMES_SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_prompt[:15000]},
                ],
                temperature=0.15,
                max_tokens=3000,
            )

            parsed = self._parse_json(response.get('content', ''))
            packet = self._to_packet(brief.review_id, parsed)
            logger.info(
                '[hermes] Review complete: %d findings, grade=%s',
                len(packet.findings), parsed.get('grade', '?'),
            )
            return packet

        except Exception as exc:
            logger.error('[hermes] Review failed: %s', exc, exc_info=True)
            return self._degraded_packet(brief.review_id, str(exc))

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        brief: ReviewBrief,
        packet_008: FactPacket | None,
        document_preview: str,
    ) -> str:
        parts: list[str] = []

        # Brief
        parts.append('## 审查任务书')
        parts.append(f'- 审查ID: {brief.review_id}')
        parts.append(f'- 文档类型: {brief.review_object_type}')
        parts.append(f'- 审查指令: {brief.query}')
        if brief.focus_pack.get('discipline_tags'):
            parts.append(f"- 关注领域: {', '.join(brief.focus_pack['discipline_tags'])}")
        parts.append('')

        # Document preview
        if document_preview:
            parts.append('## 文档内容预览')
            parts.append(document_preview[:6000])
            parts.append('')

        # 008 results
        if packet_008 and packet_008.findings:
            m = packet_008.summary_metrics
            parts.append('## 第一路审查（008引擎）结果')
            parts.append(f'总问题数: {m.total_findings}  高: {m.high_severity}  中: {m.medium_severity}')
            parts.append('')
            for f in packet_008.findings[:20]:
                parts.append(f'- [{f.id}] [{f.severity}] {f.title}')
                if f.summary:
                    parts.append(f'  {f.summary[:200]}')
            parts.append('')

        parts.append('请根据以上信息进行独立审查，输出结构化 JSON。')
        return '\n'.join(parts)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_json(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith('```'):
            parts = text.split('```')
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith('json'):
                    text = text[4:]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            logger.warning('[hermes] JSON parse failed, using fallback')
            return {
                'overall_assessment': content[:500],
                'grade': 'needs_revision',
                'findings': [],
                'top_risks': [],
            }

    def _to_packet(self, review_id: str, parsed: dict[str, Any]) -> FactPacket:
        findings: list[FindingItem] = []
        for item in parsed.get('findings', []):
            findings.append(FindingItem(
                id=item.get('id', f'H-{len(findings) + 1:03d}'),
                title=item.get('title', ''),
                severity=item.get('severity', 'info'),
                category=item.get('category', 'general'),
                summary=item.get('summary', ''),
                suggestion=item.get('suggestion', ''),
                confidence=item.get('confidence', 'medium'),
                evidence_status='inferred',
                source_engine='hermes',
                finding_type='engineering_inference',
                raw_data={'corroborates_008_finding': item.get('corroborates_008_finding')},
            ))

        metrics = ReviewPacketMetrics(
            total_findings=len(findings),
            high_severity=sum(1 for f in findings if f.severity == 'high'),
            medium_severity=sum(1 for f in findings if f.severity == 'medium'),
            low_severity=sum(1 for f in findings if f.severity == 'low'),
            info_findings=sum(1 for f in findings if f.severity == 'info'),
        )

        return FactPacket(
            review_id=review_id,
            engine='hermes',
            summary_metrics=metrics,
            findings=findings,
            overall_assessment=parsed.get('overall_assessment', ''),
            raw_result=parsed,
            produced_at=datetime.now(timezone.utc),
        )

    def _degraded_packet(self, review_id: str, reason: str) -> FactPacket:
        return FactPacket(
            review_id=review_id,
            engine='hermes',
            summary_metrics=ReviewPacketMetrics(),
            findings=[],
            overall_assessment=f'Hermes 审查未能完成: {reason}',
            raw_result={},
            produced_at=datetime.now(timezone.utc),
            error=reason,
            degraded=True,
        )
