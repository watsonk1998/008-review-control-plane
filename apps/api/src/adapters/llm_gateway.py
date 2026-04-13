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

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.2, max_tokens: int = 20000) -> dict[str, Any]:
        url = self.config.base_url.rstrip('/') + '/chat/completions'
        payload = {
            'model': self.config.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        async with httpx.AsyncClient(timeout=600.0) as client:
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
                    {'role': 'user', 'content': prompt[:200000]},
                ],
                temperature=0.1,
                max_tokens=20000,
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
        if candidate.candidateId == 'hazardous_special_scheme_staffing_completeness':
            return '危大专项方案未明确施工管理、专职安全和特种作业人员的配备与分工。'
        if candidate.candidateId == 'hazardous_special_scheme_acceptance_completeness':
            return '危大专项方案缺少验收标准、程序或关键验收内容，验收闭环不足。'
        if candidate.candidateId == 'hazardous_special_scheme_drawing_visibility':
            return '危大专项方案相关图纸未稳定进入当前可视域，需人工复核原件。'
        if candidate.candidateId == 'hazardous_special_scheme_risk_identification_completeness':
            return '危大专项方案缺少风险辨识与分级章节，后续控制链条不完整。'
        if candidate.candidateId == 'hazardous_special_scheme_layout_and_environment_completeness':
            return '危大专项方案缺少施工平面布置或周边环境条件章节，作业边界与影响对象不清。'
        if candidate.candidateId == 'hazardous_special_scheme_attachment_visibility':
            return '专项方案存在附件或图纸可视域缺口，当前只能标记人工复核。'
        if candidate.candidateId == 'hazardous_special_scheme_calculation_evidence':
            return '专项方案识别到吊装/稳定性场景，但未看到可追溯的验算或计算依据。'
        if candidate.candidateId == 'hazardous_special_scheme_emergency_targeted':
            return '专项方案的应急处置安排与主要危险源匹配不足。'
        if candidate.candidateId == 'hazardous_special_scheme_measure_linkage':
            return '危险源、控制措施与监测监控未形成完整闭环，现场执行风险较高。'
        if candidate.candidateId == 'foundation_pit_monitoring_and_drawings':
            return '基坑工程监测章节或相关图纸未稳定进入可视域，当前需人工复核。'
        if candidate.candidateId == 'foundation_pit_support_sequence_integrity':
            return '基坑工程未明确支护、降水、土方开挖与加撑之间的关系链。'
        if candidate.candidateId == 'foundation_pit_acceptance_completeness':
            return '基坑工程关键验收内容不完整，后续验收边界不清。'
        if candidate.candidateId == 'formwork_support_process_parameters':
            return '模板支撑体系缺少技术参数、工艺流程或浇筑顺序等关键过程信息。'
        if candidate.candidateId == 'formwork_support_calculation_traceability':
            return '模板支撑体系未看到强度、刚度、稳定性或基础承载力等计算依据。'
        if candidate.candidateId == 'formwork_support_acceptance_completeness':
            return '模板支撑体系缺少明确的验收标准、程序或阶段验收内容。'
        if candidate.candidateId == 'lifting_installation_removal_scheme_integrity':
            return '起重吊装及安装拆卸工程缺少设备参数、吊装流程或安装拆卸顺序等关键方案信息。'
        if candidate.candidateId == 'lifting_installation_removal_site_bearing_traceability':
            return '起重吊装及安装拆卸工程未明确站位处地基或支承面的承载能力依据。'
        if candidate.candidateId == 'lifting_installation_removal_temporary_fixation_completeness':
            return '起重吊装及安装拆卸工程缺少临时固定或辅助吊装装置说明。'
        if candidate.candidateId == 'lifting_installation_removal_drawing_visibility':
            return '起重吊装及安装拆卸工程相关图纸未稳定进入当前可视域，需人工复核。'
        if candidate.candidateId == 'scaffold_structure_parameters_completeness':
            return '脚手架工程缺少架体类型、高度、基础或主要构造参数。'
        if candidate.candidateId == 'scaffold_safety_device_and_wall_tie_completeness':
            return '脚手架工程缺少连墙件、附着支撑或防倾覆/防坠落装置说明。'
        if candidate.candidateId == 'scaffold_monitoring_and_acceptance_completeness':
            return '脚手架工程缺少明确的监测项目、控制值或关键验收内容。'
        if candidate.candidateId == 'demolition_sequence_integrity':
            return '拆除工程未明确拆除顺序、解体清运流程或关键步序控制。'
        if candidate.candidateId == 'demolition_retained_structure_control_completeness':
            return '拆除工程缺少保留结构、作业平台承载或稳定状态控制要求。'
        if candidate.candidateId == 'demolition_support_calculation_traceability':
            return '拆除工程未看到临时支撑、吊运或爆破等计算依据。'
        if candidate.candidateId == 'underground_excavation_water_control_completeness':
            return '暗挖工程缺少地下水控制、注浆或冻结等关键水控制措施。'
        if candidate.candidateId == 'underground_excavation_support_parameters_completeness':
            return '暗挖工程缺少开挖进尺、断面尺寸、支护参数或关键工装参数。'
        if candidate.candidateId == 'underground_excavation_monitoring_and_drawings':
            return '暗挖工程监测图纸或相关平剖面图未稳定进入当前可视域，需人工复核。'
        if candidate.candidateId == 'curtain_wall_installation_facility_integrity':
            return '建筑幕墙安装工程缺少安装操作设施、附着支座或安全防护装置说明。'
        if candidate.candidateId == 'curtain_wall_installation_route_and_layout_completeness':
            return '建筑幕墙安装工程缺少运输路线、吊装运行路线或堆放平面布置。'
        if candidate.candidateId == 'curtain_wall_installation_drawing_and_acceptance':
            return '建筑幕墙安装工程相关图纸或验收章节未稳定进入当前可视域，需人工复核。'
        if candidate.candidateId == 'manual_bored_pile_jump_excavation_integrity':
            return '人工挖孔桩工程缺少跳挖、分区分序等作业组织要求。'
        if candidate.candidateId == 'manual_bored_pile_gas_and_electric_safety_completeness':
            return '人工挖孔桩工程缺少有害气体检测、防中毒窒息或防触电措施。'
        if candidate.candidateId == 'manual_bored_pile_forbidden_conditions_manual_review':
            return '人工挖孔桩已出现禁用条件信号，需结合地质、水文和现场条件人工复核。'
        if candidate.candidateId == 'steel_structure_installation_lifting_scheme_integrity':
            return '钢结构安装缺少构件参数、吊装设备选型或安装流程等关键方案信息。'
        if candidate.candidateId == 'steel_structure_installation_support_and_unloading':
            return '钢结构安装缺少临时支撑、拼装胎架或卸载条件等关键支撑链信息。'
        if candidate.candidateId == 'steel_structure_installation_drawing_and_acceptance':
            return '钢结构安装相关措施图纸或验收章节未稳定进入当前可视域，需人工复核。'
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
            'hazardous_special_scheme_staffing_completeness': ['补齐施工管理、专职安全人员、特种作业人员及其他作业人员的配备和岗位职责。'],
            'hazardous_special_scheme_acceptance_completeness': ['补齐验收标准、验收程序、验收人员组成和关键验收内容。'],
            'hazardous_special_scheme_drawing_visibility': ['补充专项方案相关施工图纸、节点详图或布置图原件，并将人工复核结论写回正式报告。'],
            'hazardous_special_scheme_risk_identification_completeness': ['补齐风险辨识与分级章节，明确主要风险因素及风险等级。'],
            'hazardous_special_scheme_layout_and_environment_completeness': ['补齐施工平面布置和周边环境条件章节，明确作业边界与相邻影响对象。'],
            'hazardous_special_scheme_attachment_visibility': ['补充专项方案附件原件或图纸正文，并将人工复核结论写回正式报告。'],
            'hazardous_special_scheme_calculation_evidence': ['补充与起重/稳定性相关的验算书、设备选型依据和关键参数来源。'],
            'hazardous_special_scheme_emergency_targeted': ['围绕主要危险源补齐专项方案的应急处置流程、联络链路和现场动作。'],
            'hazardous_special_scheme_measure_linkage': ['将危险源、控制措施、监测监控和停工条件形成可执行闭环。'],
            'foundation_pit_monitoring_and_drawings': ['补齐基坑监测监控章节及监测点、周边环境、施工顺序等相关图纸，并保留人工复核记录。'],
            'foundation_pit_support_sequence_integrity': ['明确支护、降水、土方开挖与加撑的关系和施工顺序。'],
            'foundation_pit_acceptance_completeness': ['补齐基坑位移、沉降、轴力、排水和侧壁完整性等验收要求。'],
            'formwork_support_process_parameters': ['补齐模板支撑体系技术参数、工艺流程、预压方案及混凝土浇筑方式/顺序。'],
            'formwork_support_calculation_traceability': ['补齐模板支撑体系强度、刚度、稳定性和基础承载力等计算依据。'],
            'formwork_support_acceptance_completeness': ['补齐模板支撑体系的验收标准、程序和阶段验收内容。'],
            'lifting_installation_removal_scheme_integrity': ['补齐起重吊装及安装拆卸工程的设备参数、吊装流程和安装拆卸顺序。'],
            'lifting_installation_removal_site_bearing_traceability': ['补齐站位处地基或支承面的承载能力说明及相关验算依据。'],
            'lifting_installation_removal_temporary_fixation_completeness': ['明确临时固定、缆风绳、地锚、平衡梁和吊索具等稳定措施。'],
            'lifting_installation_removal_drawing_visibility': ['补齐站位图、平立面关系图或剖面图原件，并将人工复核结果写回正式报告。'],
            'scaffold_structure_parameters_completeness': ['补齐脚手架类型、高度、基础和主要构造参数。'],
            'scaffold_safety_device_and_wall_tie_completeness': ['补齐连墙件、附着支撑和防倾覆/防坠落装置说明。'],
            'scaffold_monitoring_and_acceptance_completeness': ['补齐监测项目、控制值及脚手架关键验收要求。'],
            'demolition_sequence_integrity': ['补齐拆除顺序、解体清运流程及关键步序控制。'],
            'demolition_retained_structure_control_completeness': ['明确保留结构、作业平台承载和稳定状态控制要求。'],
            'demolition_support_calculation_traceability': ['补齐临时支撑、吊运或爆破等计算依据。'],
            'underground_excavation_water_control_completeness': ['补齐地下水控制、注浆、冻结或相关水处理措施。'],
            'underground_excavation_support_parameters_completeness': ['补齐开挖进尺、断面尺寸、支护参数和关键工装参数。'],
            'underground_excavation_monitoring_and_drawings': ['补齐监测点布置图、周边环境平剖面图等材料，并保留人工复核记录。'],
            'curtain_wall_installation_facility_integrity': ['补齐安装操作设施、附着支座、动力设备和安全防护设置。'],
            'curtain_wall_installation_route_and_layout_completeness': ['补齐运输路线、吊装运行路线和堆放平面布置。'],
            'curtain_wall_installation_drawing_and_acceptance': ['补齐幕墙安装图纸及验收章节，并将人工复核结论写回正式报告。'],
            'manual_bored_pile_jump_excavation_integrity': ['补齐跳挖、分区分序等作业组织要求。'],
            'manual_bored_pile_gas_and_electric_safety_completeness': ['补齐有害气体检测、防中毒窒息和防触电措施。'],
            'manual_bored_pile_forbidden_conditions_manual_review': ['结合地质、水文和现场条件人工核验禁用条件，并在正式报告中记录复核结论。'],
            'steel_structure_installation_lifting_scheme_integrity': ['补齐钢结构构件参数、吊装设备选型、站位路线和安装流程等关键方案信息。'],
            'steel_structure_installation_support_and_unloading': ['明确拼装胎架、临时支撑、卸载条件及相关工装措施。'],
            'steel_structure_installation_drawing_and_acceptance': ['补齐钢结构安装措施图纸及验收章节，并将人工复核结果写回正式报告。'],
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
