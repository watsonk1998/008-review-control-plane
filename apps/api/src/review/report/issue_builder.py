from __future__ import annotations

from src.domain.models import ConfidenceLevel
from src.review.schema import FinalIssue, IssueCandidate


def _fallback_recommendations(candidate: IssueCandidate) -> list[str]:
    mapping = {
        'construction_org_structure_completeness': ['补齐工程概况、部署、进度、资源、安全、应急和平面布置等核心章节。'],
        'construction_org_duplicate_sections': ['统一章节编号与标题命名，消除重复“防火安全”等结构冲突。'],
        'construction_org_attachment_visibility': ['补充上传附件原件或补录附件正文内容，并在正式报告中标记人工复核结果。'],
        'construction_org_special_scheme_gap': ['针对识别出的起重吊装/动火/施工用电等高风险作业，明确专项方案或专项技术措施的正文挂接位置。'],
        'construction_org_emergency_plan_targeted': ['按主要危险源补齐对应事故类型、联络链路和现场处置动作。'],
        'construction_org_shutdown_resource_conflict': ['复核停机窗口、班组组织与交叉作业顺序，必要时拆分作业面或增加错峰安排。'],
        'construction_scheme_structure_completeness': ['补齐工程概况、编制依据、施工方法和安全措施等一般施工方案核心章节。'],
        'construction_scheme_attachment_visibility': ['补充施工方案附件原件或补录附件正文内容，并保留人工复核记录。'],
        'hazardous_special_scheme_core_sections': ['补齐专项方案的工程概况、编制依据、施工工艺、安全措施、应急处置与验算章节。'],
        'hazardous_special_scheme_attachment_visibility': ['补充专项方案附件原件或图纸正文，并将人工复核结论写回正式报告。'],
        'hazardous_special_scheme_calculation_evidence': ['补充与起重/稳定性相关的验算书、设备选型依据和关键参数来源。'],
        'hazardous_special_scheme_emergency_targeted': ['围绕主要危险源补齐专项方案的应急处置流程、联络链路和现场动作。'],
        'hazardous_special_scheme_measure_linkage': ['将危险源、控制措施、监测监控和停工条件形成可执行闭环。'],
        'supervision_plan_structure_completeness': ['补齐监理规划的工程概况、编制依据与监理控制措施等基础章节。'],
        'supervision_plan_monitoring_linkage': ['明确监测监控、旁站或巡视检查的触发条件、责任人与记录要求。'],
        'supervision_plan_attachment_visibility': ['补充监理规划附件原件或补录附件正文内容，并保留人工复核结论。'],
        'review_support_material_context_only': ['将该材料定位为背景/佐证材料，并补充对应的正式方案正文或审批文件。'],
        'review_support_material_attachment_visibility': ['补充支持材料附件原件或正文，避免把可视域缺口误读为材料缺失。'],
        'lifting_operations_special_scheme_linkage': ['在起重吊装相关章节明确专项方案、专项技术措施或附录挂接位置，并标注适用作业面。'],
        'lifting_operations_calculation_traceability': ['补齐吊装设备参数、计算起重量或验算书来源，并在正文中建立可追溯引用。'],
        'temporary_power_control_linkage': ['将临时用电/停送电作业的控制措施、监测要求和触电类应急处置串成同一条执行链。'],
        'hot_work_emergency_targeted': ['围绕动火作业补齐火灾/爆燃类应急标题、处置动作和联络链路。'],
        'gas_area_ops_control_linkage': ['围绕煤气区域作业补齐检测频率、监护要求、停工条件以及中毒/窒息/爆炸类应急处置。'],
    }
    return mapping.get(candidate.candidateId, ['结合证据补充整改措施。'])


async def finalize_issues(candidates: list[IssueCandidate], llm_gateway=None) -> list[FinalIssue]:
    if not candidates:
        return []
    if llm_gateway is not None:
        try:
            if hasattr(llm_gateway, 'aexplain_issue_candidates'):
                payloads = await llm_gateway.aexplain_issue_candidates(candidates)
            elif hasattr(llm_gateway, 'explain_issue_candidates'):
                payloads = llm_gateway.explain_issue_candidates(candidates)
            else:
                payloads = _fallback_issue_payloads(candidates)
            return [FinalIssue.model_validate(payload) for payload in _hydrate_issue_payloads(candidates, payloads)]
        except Exception:
            pass
    return [FinalIssue.model_validate(payload) for payload in _fallback_issue_payloads(candidates)]


def _fallback_issue_payloads(candidates: list[IssueCandidate]) -> list[dict]:
    payloads: list[dict] = []
    for index, candidate in enumerate(candidates, start=1):
        payloads.append(
            {
                'id': f'ISSUE-{index:03d}',
                'title': candidate.title,
                'layer': candidate.layerHint,
                'severity': candidate.severityHint,
                'findingType': candidate.findingType,
                'summary': _build_summary(candidate),
                'manualReviewNeeded': candidate.manualReviewNeeded,
                'evidenceMissing': candidate.evidenceMissing,
                'manualReviewReason': candidate.manualReviewReason,
                'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                'recommendation': _fallback_recommendations(candidate),
                'confidence': ConfidenceLevel.low if candidate.manualReviewNeeded else ConfidenceLevel.medium,
                'missingFactKeys': list(candidate.missingFactKeys),
                'blockingReasons': list(candidate.blockingReasons),
            }
        )
    return payloads


def _hydrate_issue_payloads(candidates: list[IssueCandidate], payloads: list[dict]) -> list[dict]:
    hydrated: list[dict] = []
    for index, candidate in enumerate(candidates):
        payload = dict(payloads[index]) if index < len(payloads) else {}
        payload.setdefault('title', candidate.title)
        payload.setdefault('layer', candidate.layerHint)
        payload.setdefault('severity', candidate.severityHint)
        payload.setdefault('findingType', candidate.findingType)
        payload.setdefault('summary', _build_summary(candidate))
        payload.setdefault('manualReviewNeeded', candidate.manualReviewNeeded)
        payload.setdefault('evidenceMissing', candidate.evidenceMissing)
        payload.setdefault('manualReviewReason', candidate.manualReviewReason)
        payload.setdefault('docEvidence', [span.model_dump(mode='json') for span in candidate.docEvidence])
        payload.setdefault('policyEvidence', [span.model_dump(mode='json') for span in candidate.policyEvidence])
        payload.setdefault('recommendation', _fallback_recommendations(candidate))
        payload.setdefault('confidence', ConfidenceLevel.low if candidate.manualReviewNeeded else ConfidenceLevel.medium)
        payload.setdefault('missingFactKeys', list(candidate.missingFactKeys))
        payload.setdefault('blockingReasons', list(candidate.blockingReasons))
        hydrated.append(payload)
    return hydrated


def _build_summary(candidate: IssueCandidate) -> str:
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
    if candidate.candidateId == 'construction_scheme_structure_completeness':
        return '一般施工方案缺少最小核心章节，难以判断其适用范围、施工方法和安全控制要求。'
    if candidate.candidateId == 'construction_scheme_attachment_visibility':
        return '施工方案附件存在可视域缺口，当前只能要求人工复核原件。'
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
    if candidate.candidateId == 'supervision_plan_structure_completeness':
        return '监理规划缺少基础章节，会削弱监理边界、依据链与控制措施的可读性。'
    if candidate.candidateId == 'supervision_plan_monitoring_linkage':
        return '监理规划未清楚交代监测监控、旁站或巡视安排，后续执行边界不清。'
    if candidate.candidateId == 'supervision_plan_attachment_visibility':
        return '监理规划附件未进入当前可视域，需人工复核原件。'
    if candidate.candidateId == 'review_support_material_context_only':
        return '当前材料更适合作为背景/佐证，不应直接替代正式方案正文进入 formal review 判断。'
    if candidate.candidateId == 'review_support_material_attachment_visibility':
        return '审查支持材料附件存在可视域缺口，需结合原件人工确认。'
    if candidate.candidateId == 'lifting_operations_special_scheme_linkage':
        return '已识别起重吊装场景，但当前专项方案/专项技术措施挂接位置仍不稳定或需人工确认。'
    if candidate.candidateId == 'lifting_operations_calculation_traceability':
        return '起重吊装涉及的吨位、起重量或验算依据缺少稳定引用，后续复核难以追溯。'
    if candidate.candidateId == 'temporary_power_control_linkage':
        return '临时用电/停送电相关控制措施、监测要求与触电类应急处置没有形成稳定闭环。'
    if candidate.candidateId == 'hot_work_emergency_targeted':
        return '已识别动火作业，但未看到足够明确的火灾/爆燃类针对性应急安排。'
    if candidate.candidateId == 'gas_area_ops_control_linkage':
        return '已识别煤气区域作业，但控制措施、监测监控和中毒/窒息/爆炸类应急处置未形成稳定闭环。'
    return candidate.title
