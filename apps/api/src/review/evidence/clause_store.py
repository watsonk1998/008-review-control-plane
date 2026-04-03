from __future__ import annotations

from src.domain.models import ConfidenceLevel, EvidenceSpan
from src.review.schema import PolicyClause


class ClauseStore:
    def __init__(self):
        self._clauses: dict[str, PolicyClause] = {
            'construction_org_structure': PolicyClause(
                id='construction_org_structure',
                sourceId='construction-《建筑施工组织设计规范》GB:T 50502-2009',
                title='施工组织设计结构完整性',
                excerpt='施工组织设计应覆盖工程概况、部署、进度、资源、安全、应急和平面布置等核心章节，并保持结构清晰。',
                forceLevel='should',
                applicability='construction_org',
            ),
            'review_visibility_gap': PolicyClause(
                id='review_visibility_gap',
                sourceId='review-control-plane-visibility-policy',
                title='附件可视域处理',
                excerpt='当附件或图纸未进入当前解析可视域时，应标记为 visibility_gap / manual_review_needed，而不是直接判定缺失。',
                forceLevel='guidance',
                applicability='all_review_types',
            ),
            'dangerous_special_scheme': PolicyClause(
                id='dangerous_special_scheme',
                sourceId='construction-《危险性较大的分部分项工程专项施工方案编制指南》（建办质〔2021〕48号）',
                title='危大工程专项方案要求',
                excerpt='识别到起重吊装、临时用电、动火等高风险作业后，应明确专项施工方案或专项技术措施的挂接位置与适用范围。',
                forceLevel='must',
                applicability='hazardous_work',
            ),
            'emergency_plan_targeted': PolicyClause(
                id='emergency_plan_targeted',
                sourceId='construction-《建设工程安全生产管理条例》',
                title='应急预案针对性',
                excerpt='应急管理文件应与主要危险源相匹配，便于事故类型、联系链路和现场处置动作快速落地。',
                forceLevel='should',
                applicability='construction_org',
            ),
            'construction_org_schedule_resource': PolicyClause(
                id='construction_org_schedule_resource',
                sourceId='construction-《建筑施工组织设计规范》GB:T 50502-2009',
                title='进度与资源协调',
                excerpt='施工部署、资源投入和工期窗口应相互匹配，尤其要控制交叉作业、高风险工序并行和停机窗口内的组织压力。',
                forceLevel='should',
                applicability='construction_org',
            ),
        }
        self._rule_map = {
            'construction_org_duplicate_sections': ['construction_org_structure'],
            'construction_org_attachment_visibility': ['review_visibility_gap'],
            'construction_org_special_scheme_gap': ['dangerous_special_scheme'],
            'construction_org_emergency_plan_targeted': ['emergency_plan_targeted'],
            'construction_org_shutdown_resource_conflict': ['construction_org_schedule_resource'],
        }

    def get_policy_evidence(self, rule_id: str) -> list[EvidenceSpan]:
        evidence: list[EvidenceSpan] = []
        for clause_id in self._rule_map.get(rule_id, []):
            clause = self._clauses[clause_id]
            evidence.append(
                EvidenceSpan(
                    sourceType='policy',
                    sourceId=clause.sourceId,
                    locator={'clauseId': clause.id, 'title': clause.title},
                    excerpt=clause.excerpt,
                    confidence=ConfidenceLevel.high,
                )
            )
        return evidence
