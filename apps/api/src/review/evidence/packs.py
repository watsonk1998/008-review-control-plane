from __future__ import annotations

from src.review.schema import EvidencePack, PolicyClause


def get_evidence_pack_registry() -> dict[str, EvidencePack]:
    return {
        'construction_org.base': EvidencePack(
            id='construction_org.base',
            version='1.0.0',
            docTypes=['construction_org'],
            applicability='construction_org',
            clauses=[
                PolicyClause(
                    id='construction_org_structure',
                    sourceId='construction-《建筑施工组织设计规范》GB/T 50502-2009',
                    title='施工组织设计结构完整性',
                    excerpt='施工组织设计应覆盖工程概况、部署、进度、资源、安全、应急和平面布置等核心章节，并保持结构清晰。',
                    forceLevel='should',
                    applicability='construction_org',
                ),
                PolicyClause(
                    id='construction_org_schedule_resource',
                    sourceId='construction-《建筑施工组织设计规范》GB/T 50502-2009',
                    title='进度与资源协调',
                    excerpt='施工部署、资源投入和工期窗口应相互匹配，尤其要控制交叉作业、高风险工序并行和停机窗口内的组织压力。',
                    forceLevel='should',
                    applicability='construction_org',
                ),
            ],
            severityMapping={
                'construction_org_structure_completeness': 'high',
                'construction_org_duplicate_sections': 'medium',
                'construction_org_shutdown_resource_conflict': 'medium',
            },
            ruleIds=['construction_org_structure_completeness', 'construction_org_duplicate_sections', 'construction_org_shutdown_resource_conflict'],
        ),
        'hazardous_special_scheme.base': EvidencePack(
            id='hazardous_special_scheme.base',
            version='1.0.0',
            docTypes=['hazardous_special_scheme'],
            applicability='hazardous_special_scheme',
            clauses=[
                PolicyClause(
                    id='dangerous_special_scheme',
                    sourceId='construction-《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）',
                    title='危大工程专项方案要求',
                    excerpt='识别到起重吊装、临时用电、动火等高风险作业后，应明确专项施工方案的适用范围、工艺安排、验算和控制措施。',
                    forceLevel='must',
                    applicability='hazardous_work',
                ),
                PolicyClause(
                    id='hazardous_scheme_structure',
                    sourceId='construction-《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）',
                    title='专项方案核心章节',
                    excerpt='专项施工方案通常应包含工程概况、编制依据、施工计划、施工工艺、安全保证措施、监测监控、应急处置和验算书。',
                    forceLevel='must',
                    applicability='hazardous_special_scheme',
                ),
                PolicyClause(
                    id='hazardous_scheme_calculation',
                    sourceId='construction-《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）',
                    title='专项方案验算与计算',
                    excerpt='涉及起重吊装、支撑体系、受力稳定或设备选型时，应形成可追溯的验算或计算依据。',
                    forceLevel='must',
                    applicability='hazardous_special_scheme',
                ),
                PolicyClause(
                    id='hazardous_scheme_measures',
                    sourceId='construction-《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）',
                    title='风险措施与监测监控',
                    excerpt='专项方案应将主要危险源、控制措施、监测监控和应急处置形成闭环，便于现场执行。',
                    forceLevel='should',
                    applicability='hazardous_special_scheme',
                ),
            ],
            severityMapping={
                'hazardous_special_scheme_core_sections': 'high',
                'hazardous_special_scheme_calculation_evidence': 'high',
                'lifting_operations_special_scheme_linkage': 'high',
                'lifting_operations_calculation_traceability': 'high',
                'temporary_power_control_linkage': 'medium',
                'hot_work_emergency_targeted': 'medium',
                'hazardous_special_scheme_measure_linkage': 'medium',
                'hazardous_special_scheme_emergency_targeted': 'medium',
            },
            ruleIds=[
                'hazardous_special_scheme_core_sections',
                'hazardous_special_scheme_calculation_evidence',
                'lifting_operations_special_scheme_linkage',
                'lifting_operations_calculation_traceability',
                'temporary_power_control_linkage',
                'hot_work_emergency_targeted',
                'hazardous_special_scheme_measure_linkage',
                'hazardous_special_scheme_emergency_targeted',
            ],
        ),
        'review.visibility': EvidencePack(
            id='review.visibility',
            version='1.0.0',
            docTypes=['construction_org', 'construction_scheme', 'hazardous_special_scheme', 'supervision_plan', 'review_support_material'],
            applicability='all_review_types',
            clauses=[
                PolicyClause(
                    id='review_visibility_gap',
                    sourceId='review-control-plane-visibility-policy',
                    title='附件可视域处理',
                    excerpt='当附件或图纸未进入当前解析可视域时，应标记为 visibility_gap / manual_review_needed，而不是直接判定缺失。',
                    forceLevel='guidance',
                    applicability='all_review_types',
                )
            ],
            severityMapping={
                'construction_org_attachment_visibility': 'medium',
                'hazardous_special_scheme_attachment_visibility': 'medium',
            },
            ruleIds=['construction_org_attachment_visibility', 'hazardous_special_scheme_attachment_visibility'],
        ),
        'review.emergency': EvidencePack(
            id='review.emergency',
            version='1.0.0',
            docTypes=['construction_org', 'hazardous_special_scheme'],
            applicability='construction_and_hazardous',
            clauses=[
                PolicyClause(
                    id='emergency_plan_targeted',
                    sourceId='construction-《建设工程安全生产管理条例》',
                    title='应急预案针对性',
                    excerpt='应急管理文件应与主要危险源相匹配，便于事故类型、联系链路和现场处置动作快速落地。',
                    forceLevel='should',
                    applicability='construction_org,hazardous_special_scheme',
                )
            ],
            severityMapping={
                'construction_org_emergency_plan_targeted': 'medium',
                'hazardous_special_scheme_emergency_targeted': 'medium',
                'temporary_power_control_linkage': 'medium',
                'hot_work_emergency_targeted': 'medium',
            },
            ruleIds=[
                'construction_org_emergency_plan_targeted',
                'hazardous_special_scheme_emergency_targeted',
                'temporary_power_control_linkage',
                'hot_work_emergency_targeted',
            ],
        ),
    }
