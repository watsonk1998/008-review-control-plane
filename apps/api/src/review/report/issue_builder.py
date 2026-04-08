from __future__ import annotations

from src.domain.models import ConfidenceLevel
from src.review.schema import FinalIssue, IssueCandidate


_STRUCTURE_ITEM_LABELS = {
    'preparationBasis': '编制依据',
    'engineeringOverview': '工程概况',
    'constructionDeployment': '施工部署',
    'schedulePlan': '施工进度计划',
    'resourcePlan': '施工准备与资源配置计划',
    'processMethod': '主要施工方案',
    'layoutPlan': '施工现场平面布置',
    'progressManagementPlan': '进度管理计划',
    'qualityManagementPlan': '质量管理计划',
    'safetyManagementPlan': '安全管理计划',
    'environmentManagementPlan': '环境管理计划',
    'costManagementPlan': '成本管理计划',
}


def _structure_item_labels(candidate: IssueCandidate) -> list[str]:
    labels: list[str] = []
    for hit in candidate.ruleHits:
        for fact_ref in hit.factRefs:
            if not fact_ref.startswith('project.structureCompleteness.'):
                continue
            item_key = fact_ref.rsplit('.', 1)[-1]
            label = _STRUCTURE_ITEM_LABELS.get(item_key, item_key)
            if label not in labels:
                labels.append(label)
    return labels


def _fallback_recommendations(candidate: IssueCandidate) -> list[str]:
    structure_labels = _structure_item_labels(candidate)
    mapping = {
        'construction_org_structure_completeness': [
            f'按《建筑施工组织设计规范》GB/T 50502-2009 补齐以下结构项：{"、".join(structure_labels)}。'
            if structure_labels
            else '按《建筑施工组织设计规范》GB/T 50502-2009 补齐结构完整性矩阵中未闭合的章节。'
        ],
        'construction_org_duplicate_sections': ['统一章节编号与标题命名，消除重复“防火安全”等结构冲突。'],
        'construction_org_attachment_visibility': ['补充上传附件原件或补录附件正文内容，并在正式报告中标记人工复核结果。'],
        'construction_org_special_scheme_gap': ['针对识别出的起重吊装/动火/施工用电等高风险作业，明确专项方案或专项技术措施的正文挂接位置。'],
        'construction_org_emergency_plan_targeted': ['按主要危险源补齐对应事故类型、联络链路和现场处置动作。'],
        'construction_org_shutdown_resource_conflict': ['复核停机窗口、班组组织与交叉作业顺序，必要时拆分作业面或增加错峰安排。'],
        'construction_scheme_structure_completeness': ['补齐工程概况、编制依据、施工方法和安全措施等一般施工方案核心章节。'],
        'construction_scheme_attachment_visibility': ['补充施工方案附件原件或补录附件正文内容，并保留人工复核记录。'],
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
        'steel_structure_installation_lifting_scheme_integrity': ['补齐钢结构构件参数、吊装设备选型、站位路线和安装流程等关键方案信息。'],
        'steel_structure_installation_support_and_unloading': ['明确拼装胎架、临时支撑、卸载条件及相关工装措施。'],
        'steel_structure_installation_drawing_and_acceptance': ['补齐钢结构安装措施图纸及验收章节，并将人工复核结果写回正式报告。'],
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
        structure_labels = _structure_item_labels(candidate)
        if structure_labels:
            return f'结构完整性矩阵显示以下项目存在缺项或仅部分识别：{"、".join(structure_labels)}。'
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
    if candidate.candidateId == 'hazardous_special_scheme_staffing_completeness':
        return '危大专项方案未明确施工管理、专职安全和特种作业人员的配备与分工。'
    if candidate.candidateId == 'hazardous_special_scheme_acceptance_completeness':
        return '危大专项方案缺少验收标准、程序或关键验收内容，验收闭环不足。'
    if candidate.candidateId == 'hazardous_special_scheme_drawing_visibility':
        return '危大专项方案相关图纸未稳定进入当前可视域，需人工复核原件。'
    if candidate.candidateId == 'hazardous_special_scheme_risk_identification_completeness':
        return '危大专项方案缺少明确的风险辨识与分级章节，后续控制链条不完整。'
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
    if candidate.candidateId == 'steel_structure_installation_lifting_scheme_integrity':
        return '钢结构安装缺少构件参数、吊装设备选型或安装流程等关键方案信息。'
    if candidate.candidateId == 'steel_structure_installation_support_and_unloading':
        return '钢结构安装缺少临时支撑、拼装胎架或卸载条件等关键支撑链信息。'
    if candidate.candidateId == 'steel_structure_installation_drawing_and_acceptance':
        return '钢结构安装相关措施图纸或验收章节未稳定进入当前可视域，需人工复核。'
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
