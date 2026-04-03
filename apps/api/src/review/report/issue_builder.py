from __future__ import annotations

from src.domain.models import ConfidenceLevel
from src.review.schema import FinalIssue, IssueCandidate


def _fallback_recommendations(candidate: IssueCandidate) -> list[str]:
    mapping = {
        'construction_org_duplicate_sections': ['统一章节编号与标题命名，消除重复“防火安全”等结构冲突。'],
        'construction_org_attachment_visibility': ['补充上传附件原件或补录附件正文内容，并在正式报告中标记人工复核结果。'],
        'construction_org_special_scheme_gap': ['针对识别出的起重吊装/动火/施工用电等高风险作业，明确专项方案或专项技术措施的正文挂接位置。'],
        'construction_org_emergency_plan_targeted': ['按主要危险源补齐对应事故类型、联络链路和现场处置动作。'],
        'construction_org_shutdown_resource_conflict': ['复核停机窗口、班组组织与交叉作业顺序，必要时拆分作业面或增加错峰安排。'],
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
                'docEvidence': [span.model_dump(mode='json') for span in candidate.docEvidence],
                'policyEvidence': [span.model_dump(mode='json') for span in candidate.policyEvidence],
                'recommendation': _fallback_recommendations(candidate),
                'confidence': ConfidenceLevel.low if candidate.manualReviewNeeded else ConfidenceLevel.medium,
                'whetherManualReviewNeeded': candidate.manualReviewNeeded,
            }
        )
    return payloads


def _build_summary(candidate: IssueCandidate) -> str:
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
    return candidate.title
