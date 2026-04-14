"""
Hermes External Adapter: true integration boundary with external Hermes agent.

This adapter represents the real external Hermes engine connection.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from src.review.contracts import FactPacket, FindingItem, ReviewBrief, ReviewPacketMetrics
from src.review.hermes_review_engine import HermesReviewEngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hermes review system prompt (for external agent)
# ---------------------------------------------------------------------------
HERMES_EXTERNAL_PROMPT = """\
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
      "id": "HF-001",
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


class HermesExternalAdapter(HermesReviewEngine):
    """External Hermes agent integration adapter."""

    def __init__(self, endpoint: str | None = None):
        self._endpoint = endpoint

    @property
    def available(self) -> bool:
        """Return True if an external endpoint is configured."""
        return bool(self._endpoint)

    async def health_check(self) -> dict[str, Any]:
        if not self.available:
            return {'available': False, 'mode': 'not_configured', 'detail': 'External endpoint not configured'}
        
        try:
            # P0 assumes standard REST Fastapi endpoint -> GET /health or GET /
            base_url = self._endpoint.rstrip('/')
            health_url = f"{base_url}/health" if not base_url.endswith('/chat') else base_url.replace('/chat', '/health')
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(health_url)
                if resp.status_code < 500:
                    return {'available': True, 'mode': 'available', 'detail': f'HTTP {resp.status_code}'}
                return {'available': False, 'mode': 'reachable_but_invalid', 'detail': f'HTTP Error {resp.status_code}'}
        except httpx.ConnectError as e:
            return {'available': False, 'mode': 'configured_but_unreachable', 'detail': 'Connection failed'}
        except httpx.TimeoutException:
            return {'available': False, 'mode': 'configured_but_unreachable', 'detail': 'Connection timeout'}
        except Exception as e:
            return {'available': False, 'mode': 'reachable_but_invalid', 'detail': f'Unexpected probe error: {e}'}

    async def review(
        self,
        brief: ReviewBrief,
        fact_packet_008: FactPacket | None = None,
        *,
        document_preview: str = '',
        governed_support_packet: dict[str, Any] | None = None,
    ) -> FactPacket:
        """Execute review via external Hermes agent."""
        if not self.available:
            logger.info('[hermes_external] External endpoint not configured.')
            return self._degraded_packet(brief.review_id, 'External endpoint not configured')

        try:
            logger.info('[hermes_external] Calling external agent at %s', self._endpoint)
            prompt_content = self._build_prompt(brief, fact_packet_008, document_preview, governed_support_packet)
            system_instruction = HERMES_EXTERNAL_PROMPT
            
            # Assuming external Hermes expects {"message": ..., "system": ...} mapping
            payload = {
                "message": f"[SYSTEM INSTRUCTION]\\n{system_instruction}\\n\\n[USER PROMPT]\\n{prompt_content}",
                "model": "hermes"
            }
            
            base_url = self._endpoint.rstrip('/')
            url = f"{base_url}/chat" if not base_url.endswith('/chat') else base_url

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # Map whatever Hermes returns: "response", "text", or raw root
            raw_response = data.get("response", data.get("text", str(data)))
            parsed = self._parse_json(raw_response)
            
            packet = self._to_packet(brief.review_id, parsed)
            logger.info('[hermes_external] Successfully mapped external result: %d findings', len(packet.findings))
            return packet

        except httpx.TimeoutException:
            return self._degraded_packet(brief.review_id, 'timeout')
        except httpx.HTTPStatusError as e:
            return self._degraded_packet(brief.review_id, f'invalid response HTTP {e.response.status_code}')
        except Exception as e:
            logger.error('[hermes_external] Error calling external Hermes: %s', e)
            return self._degraded_packet(brief.review_id, f'unexpected error: {e}')

    def _build_prompt(self, brief: ReviewBrief, packet_008: FactPacket | None, document_preview: str, governed_support_packet: dict[str, Any] | None = None) -> str:
        parts: list[str] = []
        parts.append('## 审查任务书')
        parts.append(f'- 审查ID: {brief.review_id}')
        parts.append(f'- 文档类型: {brief.review_object_type}')
        parts.append(f'- 审查指令: {brief.query}')
        parts.append('')

        if document_preview:
            parts.append('## 文档内容预览')
            parts.append(document_preview[:6000])
            parts.append('')

        if packet_008 and packet_008.findings:
            m = packet_008.summary_metrics
            parts.append('## 第一路审查（008引擎）结果')
            parts.append(f'总问题数: {m.total_findings}  高: {m.high_severity}  中: {m.medium_severity}')
            parts.append('')
            for f in packet_008.findings[:20]:
                parts.append(f'- [{f.id}] [{f.severity}] {f.title}')
        if governed_support_packet:
            parts.append('## 治理化审查上下文')
            parts.append(json.dumps(getattr(governed_support_packet, 'basis_summary', []), ensure_ascii=False, indent=2)[:12000])
            basis_fulltext_context = getattr(governed_support_packet, 'basis_fulltext_context', [])
            if basis_fulltext_context:
                parts.append(json.dumps(basis_fulltext_context, ensure_ascii=False, indent=2)[:40000])
            expert_review_points = getattr(governed_support_packet, 'expert_review_points', [])
            if expert_review_points:
                parts.append(json.dumps(expert_review_points, ensure_ascii=False, indent=2)[:12000])
        return '\n'.join(parts)

    def _parse_json(self, content: str | None) -> dict[str, Any]:
        if not content:
            logger.warning('[hermes_external] JSON parse failed: empty content returned')
            return {
                'overall_assessment': 'External Hermes agent returned empty response',
                'grade': 'needs_revision',
                'findings': [],
                'top_risks': [],
            }
        text = str(content).strip()
        if text.startswith('```'):
            parts = text.split('```')
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith('json'):
                    text = text[4:]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            logger.warning('[hermes_external] JSON parse failed, using fallback')
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
                id=item.get('id', f'H-EXT-{len(findings) + 1:03d}'),
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
            overall_assessment=f'External Hermes Review unavailable: {reason}',
            raw_result={},
            produced_at=datetime.now(timezone.utc),
            error=reason,
            degraded=True,
        )
