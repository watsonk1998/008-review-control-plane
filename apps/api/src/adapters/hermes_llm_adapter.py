"""
Hermes LLM fallback/local shim for Hermes review routing.

Status:
- fallback

Freeze boundary:
- fallback/local shim only
- not the external Hermes canonical path
- do not expand with new controller semantics

Do not extend:
- no template-selection logic
- no final-output ownership
- no claims of being the canonical external Hermes backend

Canonical path:
- HermesRouterAdapter chooses a Hermes backend
- HermesReviewEngine defines the backend contract
- this adapter is only the local/fallback implementation

Architecture note:
- This is NOT the real external Hermes integration.
- This is a local simulation using our LLM infrastructure (LLMGateway) to run an
  independent "Hermes-style" review.
- It serves as a fallback or local alternative to the true external Hermes agent.

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
from src.review.hermes_review_engine import HermesReviewEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hermes review system prompt
# ---------------------------------------------------------------------------
HERMES_SYSTEM_PROMPT = """\
你是 Hermes 审查引擎 — 一个独立的工程文档审查专家。
你的职责是对施工方案/施工组织设计进行独立的第二路审查。

你会收到：
1. 审查任务书（ReviewBrief），包含文档类型、指示要求、“规范标准全文”
2. 依据的源文档全文（必须仔细阅读，因为第一路引擎能力受限且未能提取专门事实）
3. 第一路审查（008引擎）已发现的问题清单

你的【核心任务】：
- 绝不要仅仅复述或洗稿第一路审查的结果！你需要作为高级专家挖出真正的问题。
- 仔细阅读审查指令中的【规范标准】，并独立根据这些标准对【源文档全文】进行极其严苛、深度的挑刺。
- 在审查“章节完整性”、“参数一致性”、“合法合规性”、“工序连贯性”、“证据验证”等维度时仔细找出参数错误、工序颠倒、合规性风险。
- 请务必尽可能详尽、全面地列举你所发现的【所有】深层隐患与违反规范项，不要受限于数量。发现越多越好（如果存在超过20条均必须全量指出）。每一条都要明确指出源文档的哪一部分违反了给定规范的哪一部分。

输出格式（严格 JSON，不要包含额外的 markdown 标记或代码块符）：
{
  "overall_assessment": "总体评价（说明你查阅全文后独立发现了哪些深层问题）",
  "grade": "needs_revision",
  "findings": [
    {
      "id": "H-001",
      "severity": "high",
      "title": "（全新发现）具体违反的条款和现象",
      "category": "chapter_completeness | parameter_consistency | compliance | process_coherence | evidence_verification",
      "summary": "重述或描述发现的具体不符点",
      "suggestion": "指出具体违反哪条规范并给出修正动作",
      "evidence_status": "grounded"
    }
  ],
  "top_risks": ["1", "2"]
}
"""


class HermesLLMAdapter(HermesReviewEngine):
    """Independent second-path review engine using local LLM simulation.

    This adapter is intentionally thin — it owns the prompt, the LLM call,
    and the response parsing.
    """

    def __init__(self, llm_gateway: LLMGateway | None = None):
        self._llm = llm_gateway

    @property
    def available(self) -> bool:
        return self._llm is not None

    async def health_check(self) -> dict[str, Any]:
        if not self.available:
            return {'available': False, 'mode': 'not_configured', 'detail': 'LLM gateway is not configured'}
        try:
            llm_health = await self._llm.health_check()
            return {
                'available': llm_health.get('available', False),
                'mode': 'llm_fallback',
                'detail': llm_health.get('detail', 'OK')
            }
        except Exception as e:
            return {'available': False, 'mode': 'error', 'detail': f'LLM error: {str(e)}'}

    async def review(
        self,
        brief: ReviewBrief,
        fact_packet_008: FactPacket | None = None,
        *,
        document_preview: str = '',
        governed_support_packet: dict[str, Any] | None = None,
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
            user_prompt = self._build_prompt(brief, fact_packet_008, document_preview, governed_support_packet)

            response = await self._llm.chat(
                [
                    {'role': 'system', 'content': HERMES_SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_prompt[:500000]},
                ],
                temperature=0.15,
                max_tokens=20000,
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
        governed_support_packet: dict[str, Any] | None = None,
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
            parts.append(document_preview[:500000])
            parts.append('')

        # 008 results
        if packet_008 and packet_008.findings:
            m = packet_008.summary_metrics
            parts.append('## 第一路审查（008引擎）结果')
            parts.append(f'总问题数: {m.total_findings}  高: {m.high_severity}  中: {m.medium_severity}')
            parts.append('')
            for f in packet_008.findings[:200]:
                parts.append(f'- [{f.id}] [{f.severity}] {f.title}')
                if f.summary:
                    parts.append(f'  {f.summary[:1000]}')
            parts.append('')

        if governed_support_packet:
            parts.append('## 审查治理包 (Governed Support Packet)')
            parts.append(json.dumps(getattr(governed_support_packet, 'basis_summary', []), ensure_ascii=False, indent=2)[:50000])
            parts.append(json.dumps(getattr(governed_support_packet, 'rule_pack_summary', []), ensure_ascii=False, indent=2)[:50000])
            parts.append('')

        parts.append('请根据以上信息进行独立审查，输出结构化 JSON。')
        return '\n'.join(parts)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_json(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if '```json' in text:
            parts = text.split('```json')
            if len(parts) >= 2:
                text = parts[1].split('```')[0].strip()
        elif '```' in text:
            parts = text.split('```')
            if len(parts) >= 3:
                text = parts[1].strip()
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as exc:
            logger.warning('[hermes] JSON parse failed: %s. Content start: %s...', exc, content[:200])
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
