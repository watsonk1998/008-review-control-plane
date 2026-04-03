from __future__ import annotations

import json
from typing import Any

import httpx

from src.config.llm import LLMConfig, resolve_llm_config


class LLMGateway:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or resolve_llm_config()

    async def health_check(self) -> dict[str, Any]:
        response = await self.chat([
            {'role': 'system', 'content': 'You are a health check assistant.'},
            {'role': 'user', 'content': 'Reply with exactly: pong'},
        ], temperature=0)
        return {
            'available': True,
            'provider': self.config.provider,
            'model': self.config.model,
            'reply': response.get('content', ''),
            'config': self.config.sanitized(),
        }

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.2, max_tokens: int = 1200) -> dict[str, Any]:
        url = self.config.base_url.rstrip('/') + '/chat/completions'
        payload = {
            'model': self.config.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.config.api_key}',
                },
            )
            response.raise_for_status()
            body = response.json()
        return {
            'content': body['choices'][0]['message']['content'],
            'raw': body,
            'usage': body.get('usage'),
        }

    async def summarize_chunks(self, query: str, chunks: list[dict[str, Any]], extra_instruction: str = '') -> dict[str, Any]:
        context = '\n\n'.join(
            f"[{index + 1}] {chunk.get('sourceLabel') or chunk.get('mode')}: {chunk.get('text', '')}"
            for index, chunk in enumerate(chunks[:8])
        )
        prompt = (
            '请严格基于提供的 chunks 回答。若 chunks 不足，请明确写出“不足以得出结论”。'
            + ('\n' + extra_instruction if extra_instruction else '')
            + f'\n\n问题：{query}\n\n可用上下文：\n{context}'
        )
        return await self.chat([
            {'role': 'system', 'content': '你是一个谨慎的工程知识整理助手。'},
            {'role': 'user', 'content': prompt},
        ])

    def explain_issue_candidates(self, candidates) -> list[dict[str, Any]]:
        return self._fallback_issue_payloads(candidates)

    async def aexplain_issue_candidates(self, candidates) -> list[dict[str, Any]]:
        fallback = self._fallback_issue_payloads(candidates)
        if not candidates:
            return fallback
        prompt = json.dumps(
            [
                {
                    'id': candidate.candidateId,
                    'title': candidate.title,
                    'layer': candidate.layerHint.value,
                    'severity': candidate.severityHint,
                    'findingType': candidate.findingType.value,
                    'manualReviewNeeded': candidate.manualReviewNeeded,
                    'evidenceMissing': candidate.evidenceMissing,
                    'manualReviewReason': candidate.manualReviewReason,
                    'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                    'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                }
                for candidate in candidates
            ],
            ensure_ascii=False,
        )
        try:
            response = await self.chat(
                [
                    {
                        'role': 'system',
                        'content': '你是正式审查结果整理器。只能基于候选问题 JSON 整理 title/summary/recommendation，不得新增事实或法规依据。返回 JSON 数组。',
                    },
                    {'role': 'user', 'content': prompt[:12000]},
                ],
                temperature=0.1,
                max_tokens=1800,
            )
            parsed = self._load_json_array(response.get('content', ''))
            if not parsed:
                return fallback
            merged: list[dict[str, Any]] = []
            for base, generated in zip(fallback, parsed):
                merged.append(
                    {
                        **base,
                        'title': generated.get('title') or base['title'],
                        'summary': generated.get('summary') or base['summary'],
                        'recommendation': generated.get('recommendation') or base['recommendation'],
                        'confidence': generated.get('confidence') or base['confidence'],
                    }
                )
            return merged
        except Exception:
            return fallback

    def merge_issue_candidates(self, candidates) -> list[dict[str, Any]]:
        return self._fallback_issue_payloads(candidates)

    def render_recommendations(self, candidate) -> list[str]:
        return self._fallback_issue_payloads([candidate])[0]['recommendation']

    def _fallback_issue_payloads(self, candidates) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates, start=1):
            payloads.append(
                {
                    'id': f'ISSUE-{index:03d}',
                    'title': candidate.title,
                    'layer': candidate.layerHint.value,
                    'severity': candidate.severityHint,
                    'findingType': candidate.findingType.value,
                    'summary': self._fallback_summary(candidate),
                    'manualReviewNeeded': candidate.manualReviewNeeded,
                    'evidenceMissing': candidate.evidenceMissing,
                    'manualReviewReason': candidate.manualReviewReason,
                    'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                    'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                    'recommendation': self._fallback_recommendations(candidate),
                    'confidence': 'low' if candidate.manualReviewNeeded else 'medium',
                    'whetherManualReviewNeeded': candidate.manualReviewNeeded,
                }
            )
        return payloads

    def _fallback_summary(self, candidate) -> str:
        if candidate.candidateId == 'construction_org_structure_completeness':
            return '施工组织设计缺少核心章节，会削弱部署、资源、安全与应急链路的完整性。'
        if candidate.candidateId == 'construction_org_duplicate_sections':
            return '解析结果中出现重复章节标题，会降低问题定位、矩阵对齐和人工复核稳定性。'
        if candidate.candidateId == 'construction_org_attachment_visibility':
            return '正文已引用附件，但当前解析仅能看到附件标题或引用位置，需人工复核附件原件。'
        if candidate.candidateId == 'construction_org_special_scheme_gap':
            return '文档已识别起重吊装、动火或施工用电等高风险作业，但未看到明确的专项方案挂接位置。'
        if candidate.candidateId == 'construction_org_emergency_plan_targeted':
            return '应急预案数量或类型与主要危险源不完全匹配，针对性不足。'
        if candidate.candidateId == 'construction_org_shutdown_resource_conflict':
            return '停机窗口紧、作业并行度高且投入人力较大，存在组织与交叉作业压力。'
        if candidate.candidateId == 'hazardous_special_scheme_core_sections':
            return '危大专项方案缺少核心章节，难以支撑工艺、控制措施与人工复核。'
        if candidate.candidateId == 'hazardous_special_scheme_attachment_visibility':
            return '专项方案存在附件或图纸可视域缺口，当前只能标记人工复核。'
        if candidate.candidateId == 'hazardous_special_scheme_calculation_evidence':
            return '专项方案识别到吊装/稳定性场景，但未看到可追溯的验算或计算依据。'
        if candidate.candidateId == 'hazardous_special_scheme_emergency_targeted':
            return '专项方案的应急处置安排与主要危险源匹配不足。'
        if candidate.candidateId == 'hazardous_special_scheme_measure_linkage':
            return '危险源、控制措施与监测监控未形成完整闭环，现场执行风险较高。'
        return candidate.title

    def _fallback_recommendations(self, candidate) -> list[str]:
        mapping = {
            'construction_org_structure_completeness': ['补齐工程概况、部署、进度、资源、安全、应急和平面布置等核心章节。'],
            'construction_org_duplicate_sections': ['统一章节编号与标题命名，消除重复“防火安全”等结构冲突。'],
            'construction_org_attachment_visibility': ['补充上传附件原件或补录附件正文内容，并在正式报告中标记人工复核结果。'],
            'construction_org_special_scheme_gap': ['针对识别出的起重吊装/动火/施工用电等高风险作业，明确专项方案或专项技术措施的正文挂接位置。'],
            'construction_org_emergency_plan_targeted': ['按主要危险源补齐对应事故类型、联络链路和现场处置动作。'],
            'construction_org_shutdown_resource_conflict': ['复核停机窗口、班组组织与交叉作业顺序，必要时拆分作业面或增加错峰安排。'],
            'hazardous_special_scheme_core_sections': ['补齐专项方案的工程概况、编制依据、施工工艺、安全措施、应急处置与验算章节。'],
            'hazardous_special_scheme_attachment_visibility': ['补充专项方案附件原件或图纸正文，并将人工复核结论写回正式报告。'],
            'hazardous_special_scheme_calculation_evidence': ['补充与起重/稳定性相关的验算书、设备选型依据和关键参数来源。'],
            'hazardous_special_scheme_emergency_targeted': ['围绕主要危险源补齐专项方案的应急处置流程、联络链路和现场动作。'],
            'hazardous_special_scheme_measure_linkage': ['将危险源、控制措施、监测监控和停工条件形成可执行闭环。'],
        }
        return mapping.get(candidate.candidateId, ['结合证据补充整改措施。'])

    def _load_json_array(self, content: str) -> list[dict[str, Any]]:
        text = content.strip()
        if text.startswith('```'):
            parts = text.split('```')
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith('json'):
                    text = text[4:]
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else []
