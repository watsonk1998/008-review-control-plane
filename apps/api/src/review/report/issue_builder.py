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
        'hazardous_special_scheme_core_sections': ['补齐专项方案的工程概况、编制依据、施工工艺、安全措施、应急处置与验算章节。'],
        'hazardous_special_scheme_attachment_visibility': ['补充专项方案附件原件或图纸正文，并将人工复核结论写回正式报告。'],
        'hazardous_special_scheme_calculation_evidence': ['补充与起重/稳定性相关的验算书、设备选型依据和关键参数来源。'],
        'hazardous_special_scheme_emergency_targeted': ['围绕主要危险源补齐专项方案的应急处置流程、联络链路和现场动作。'],
        'hazardous_special_scheme_measure_linkage': ['将危险源、控制措施、监测监控和停工条件形成可执行闭环。'],
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
            return [FinalIssue.model_validate(payload) for payload in payloads]
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
            }
        )
    return payloads


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
