from __future__ import annotations

from collections import Counter
import html
import re

from src.review.evidence.packs import get_evidence_pack_registry
from src.review.schema import (
    ResolvedReviewProfile,
    StructuredReviewMatrices,
    StructuredReviewSummary,
    StructuredReviewVisibilitySummary,
)

_STRUCTURED_REPORT_PRINT_CSS = """
.structured-report {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 32px 40px;
  color: #1f2937;
  background: #fffdf8;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  line-height: 1.72;
}

.structured-report, .structured-report * {
  box-sizing: border-box;
}

.structured-report h1,
.structured-report h2,
.structured-report h3,
.structured-report h4,
.structured-report p,
.structured-report li,
.structured-report td,
.structured-report th,
.structured-report div,
.structured-report span {
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.structured-report__title {
  font-size: 26px;
  font-weight: 800;
  margin: 0 0 18px;
}

.structured-report__section {
  margin: 0 0 28px;
  padding: 0 0 18px;
  border-bottom: 1px solid #ddd7ca;
}

.structured-report__section:last-child {
  border-bottom: 0;
}

.structured-report__section-title {
  font-size: 22px;
  font-weight: 800;
  margin: 0 0 14px;
}

.structured-report__subsection {
  margin: 18px 0 0;
}

.structured-report__subsection-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 10px;
}

.structured-report__section-intro,
.structured-report__subsection-intro {
  margin: 0 0 12px;
}

.structured-report__bullet-list,
.structured-report__basis-list,
.structured-report__fact-list,
.structured-report__requirement-list {
  margin: 8px 0 0 18px;
  padding: 0;
}

.structured-report__bullet-list li,
.structured-report__basis-list li,
.structured-report__fact-list li,
.structured-report__requirement-list li {
  margin: 6px 0;
}

.structured-report__overview-section {
  break-before: page;
  page-break-before: always;
}

.structured-report__overview-section > .structured-report__subsection-title,
.structured-report__table-wrap,
.structured-report__issue-card,
.structured-report__gap-item {
  page-break-inside: avoid;
  break-inside: avoid;
}

.structured-report__table-wrap {
  margin-top: 10px;
  overflow: hidden;
}

.structured-report table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  margin: 0;
  font-size: 14px;
}

.structured-report thead {
  display: table-header-group;
}

.structured-report th,
.structured-report td {
  border: 1px solid #d9d4c7;
  vertical-align: top;
  text-align: left;
  padding: 10px 12px;
  line-height: 1.68;
}

.structured-report th {
  background: #f4efe2;
  font-weight: 700;
}

.structured-overview-table th:nth-child(1),
.structured-overview-table td:nth-child(1) { width: 6%; }
.structured-overview-table th:nth-child(2),
.structured-overview-table td:nth-child(2) { width: 14%; }
.structured-overview-table th:nth-child(3),
.structured-overview-table td:nth-child(3) { width: 26%; }
.structured-overview-table th:nth-child(4),
.structured-overview-table td:nth-child(4) { width: 26%; }
.structured-overview-table th:nth-child(5),
.structured-overview-table td:nth-child(5) { width: 28%; }

.structured-completeness-table th:nth-child(1),
.structured-completeness-table td:nth-child(1) { width: 6%; }
.structured-completeness-table th:nth-child(2),
.structured-completeness-table td:nth-child(2) { width: 14%; }
.structured-completeness-table th:nth-child(3),
.structured-completeness-table td:nth-child(3) { width: 12%; }
.structured-completeness-table th:nth-child(4),
.structured-completeness-table td:nth-child(4) { width: 28%; }
.structured-completeness-table th:nth-child(5),
.structured-completeness-table td:nth-child(5) { width: 12%; }
.structured-completeness-table th:nth-child(6),
.structured-completeness-table td:nth-child(6) { width: 28%; }

.structured-report__followups {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.structured-report__gap-item {
  border: 1px solid #e3ded2;
  border-radius: 12px;
  padding: 18px 20px;
  background: #fffdfa;
}

.structured-report__followup-group + .structured-report__followup-group {
  margin-top: 18px;
}

.structured-report__followup-compact {
  padding: 10px 0 12px;
  border-bottom: 1px solid #2f2f2f;
}

.structured-report__followup-compact:first-child {
  border-top: 1px solid #2f2f2f;
}

.structured-report__followup-compact-title {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 6px;
}

.structured-report__followup-compact-line {
  margin: 2px 0;
}

.structured-report__gap-item-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 14px;
}

.structured-report__gap-item-block + .structured-report__gap-item-block {
  margin-top: 14px;
}

.structured-report__gap-item-label {
  font-weight: 700;
  margin-bottom: 6px;
  color: #374151;
}

.structured-report__gap-item-value {
  margin: 0;
}

.structured-report__gap-item-list {
  margin: 0 0 0 18px;
  padding: 0;
}

.structured-report__gap-item-list li + li {
  margin-top: 6px;
}

.structured-report__issue-card {
  margin: 18px 0 0;
  padding: 18px 20px;
  border: 1px solid #e3ded2;
  border-radius: 12px;
  background: #fffdfa;
}

.structured-report__issue-card-title {
  font-size: 20px;
  font-weight: 800;
  margin: 0 0 12px;
}

.structured-report__issue-card-section + .structured-report__issue-card-section {
  margin-top: 16px;
}

.structured-report__issue-card-section-title {
  font-weight: 700;
  margin-bottom: 6px;
}

.structured-report__issue-card-text {
  margin: 0;
}

.structured-report__issue-card-law-list {
  margin: 0 0 0 18px;
  padding: 0;
}

.structured-report__issue-card-law-item + .structured-report__issue-card-law-item {
  margin-top: 12px;
}

.structured-report__issue-card-law-title {
  font-weight: 600;
}

.structured-report__issue-card-law-requirements {
  margin: 6px 0 0 18px;
  padding: 0;
}

.structured-report__issue-card-law-requirement + .structured-report__issue-card-law-requirement {
  margin-top: 4px;
}

.structured-report__muted {
  color: #6b7280;
}

@media print {
  @page {
    size: A4 landscape;
    margin: 12mm;
  }

  body {
    background: #fff !important;
  }

  .structured-report {
    max-width: none;
    padding: 0;
    background: #fff;
  }

  .structured-report__overview-section {
    break-before: page;
    page-break-before: always;
  }

  .structured-report__section-title,
  .structured-report__subsection-title {
    page-break-after: avoid;
  }

  .structured-report table,
  .structured-report tr,
  .structured-report td,
  .structured-report th {
    page-break-inside: avoid;
    break-inside: avoid;
  }
}
"""


class StructuredReviewReportBuilder:
    _SEVERITY_ORDER = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
    _DOCUMENT_TYPE_LABELS = {
        'construction_org': '施工组织设计',
        'construction_scheme': '施工方案',
        'hazardous_special_scheme': '危大专项施工方案',
        'distribution_network_special_scheme': '配网工程专项施工方案',
        'supervision_plan': '监理规划',
        'review_support_material': '审查支持材料',
    }
    _ISSUE_KIND_LABELS = {
        'hard_defect': '硬缺陷',
        'visibility_gap': '可视域缺口',
        'evidence_gap': '证据缺口',
        'enhancement': '优化建议',
    }
    _SEVERITY_LABELS = {'high': '高', 'medium': '中', 'low': '低', 'info': '提示'}
    _GROUPED_SPECIAL_SCHEME_DOCUMENT_TYPES = {'hazardous_special_scheme', 'distribution_network_special_scheme'}
    _SPECIAL_SCHEME_STRUCTURE_POLICY_LABEL = 'review-control-plane-special-scheme-structure-policy'
    _APPLICABILITY_LABELS = {
        'applies': '已满足当前判定条件',
        'partial': '仅形成部分判定',
        'blocked_by_visibility': '受可视域限制，需人工结合原件复核',
        'blocked_by_missing_fact': '关键事实不足，暂不能形成闭合判定',
    }
    _PARSE_MODE_LABELS = {
        'docx_structured': '结构化文档解析',
        'pdf_text_only': 'PDF 文本受限解析',
        'markdown_text': 'Markdown 文本解析',
        'plain_text': '纯文本解析',
    }
    _FILE_TYPE_LABELS = {'docx': 'Word 文档', 'pdf': 'PDF 文档', 'md': 'Markdown 文档', 'txt': '文本文件'}
    _STRUCTURE_STATUS_LABELS = {
        'matched': '符合',
        'partial': '部分符合',
        'missing': '缺失',
        'blocked_by_visibility': '受可视域限制',
    }
    _MANUAL_REVIEW_REASON_LABELS = {
        'title_detected_without_attachment_body': '正文提到了附件，但本次未识别到附件正文内容，需结合原件核对。',
        'title_detected_but_body_not_reliably_parsed': '正文提到了附件，但本次未能稳定识别附件正文内容，需结合原件核对。',
        'reference_detected_in_limited_parser': '正文引用了附件，但当前未能稳定识别附件内容，需结合原件核对。',
        'reference_detected_without_attachment_body': '正文提到了附件，但本次未取得附件正文内容，需结合原件核对。',
        'attachment_unparsed': '附件内容尚未识别完整，需结合原件核对。',
        'referenced_only': '正文引用了附件，但本次未取得附件正文内容，需结合原件核对。',
        'visibility_unknown': '当前无法确认附件或附图的可视状态。',
        'parser_limited_pdf_requires_manual_review': '当前 PDF 仅完成基础文本识别，建议结合原件人工复核。',
        'weak_section_structure_signal': '关键章节或附件边界重复，正式定位结果不稳定。',
        'visibility_gap': '当前问题受附件可视域限制，需人工核验原件。',
        'drawing_visibility_gap': '相关图纸或节点详图未稳定进入当前可视域，需结合原件人工复核。',
        'complex_calculation_requires_manual_confirmation': '当前仅能识别存在复杂验算主题，尚不足以自动判断其充分性或正确性。',
        'forbidden_condition_requires_manual_confirmation': '当前仅识别到禁用条件信号，需结合地质、水文和现场条件人工确认。',
        'type_specific_attachment_visibility_gap': '类型专属图纸或附件未稳定进入当前可视域，需结合原件人工复核。',
        'manual_confirmation_required': '当前问题仍需人工确认。',
    }
    _BLOCKING_REASON_LABELS = {
        'visibility_gap': '当前问题受附件或图纸可视域限制。',
        'attachment_unparsed': '附件标题已识别，但正文未完成可靠解析。',
        'referenced_only': '正文已引用附件，但附件正文未进入当前可视域。',
        'visibility_unknown': '当前无法确认附件或图纸状态。',
        'parser_limited_pdf_requires_manual_review': 'PDF 受限解析路径不足以支撑直接下结论。',
        'weak_section_structure_signal': '章节结构存在重复或边界不稳，定位需谨慎。',
        'missing_fact': '完成判定所需关键事实尚未提取完整。',
        'parser_limited_source': '当前证据受 PDF 解析能力限制，建议结合原件复核。',
        'document_evidence_unavailable': '文档侧证据不足以支撑硬性结论。',
        'policy_evidence_unavailable': '条文依据链未完全闭合。',
        'drawing_visibility_gap': '相关图纸尚未进入当前稳定可视域。',
        'forbidden_condition_requires_manual_confirmation': '禁用条件信号需结合工程现场条件人工确认。',
        'type_specific_attachment_visibility_gap': '类型专属图纸或附件尚未进入当前稳定可视域。',
        'manual_confirmation_required': '仍需人工确认现场条件或附件内容。',
    }
    _VISIBILITY_VALUE_LABELS = {
        'parsed': '已进入可视域',
        'attachment_unparsed': '标题已识别但正文未解析',
        'referenced_only': '正文提及但附件未进入可视域',
        'unknown': '当前状态暂不能确认',
        'missing': '已识别为明确缺失',
    }
    _MISSING_FACT_LABELS = {
        'hazard.monitoringSectionPresent': '尚未提取到监测监控章节',
        'hazard.measureSectionPresent': '尚未提取到风险控制措施章节',
        'emergency.planTitles': '尚未提取到针对性应急预案标题',
        'hazard.calculationEvidencePresent': '尚未提取到验算依据',
        'hazard.calculatedLiftWeightTon': '尚未提取到计算吊重参数',
        'hazard.craneCapacityTon': '尚未提取到起重设备额定吨位',
        'project.foundationPitSupportSequencePresent': '尚未提取到基坑支护/降水/开挖关系',
        'project.formworkPourSequencePresent': '尚未提取到模板支撑预压或浇筑顺序',
        'project.steelSupportUnloadingPresent': '尚未提取到钢结构临时支撑或卸载条件',
        'project.liftingSiteBearingPresent': '尚未提取到起重站位承载依据',
        'project.liftingTemporaryFixationPresent': '尚未提取到起重临时固定措施',
        'project.liftingSupportDevicePresent': '尚未提取到起重辅助吊装装置',
        'project.scaffoldWallTiePresent': '尚未提取到脚手架连墙件或附着支撑',
        'project.scaffoldAntiFallPresent': '尚未提取到脚手架防坠落或防倾覆装置',
        'project.scaffoldMonitoringPresent': '尚未提取到脚手架监测项目或控制值',
        'project.demolitionSequencePresent': '尚未提取到拆除顺序或解体清运流程',
        'project.demolitionRetainedStructureControlPresent': '尚未提取到保留结构或平台控制要求',
        'project.demolitionSupportCalculationPresent': '尚未提取到拆除临时支撑或吊运计算依据',
        'project.undergroundWaterControlPresent': '尚未提取到暗挖地下水控制措施',
        'project.undergroundSupportParametersPresent': '尚未提取到暗挖支护参数',
        'project.undergroundMonitoringPresent': '尚未提取到暗挖监测项目或监测图信号',
        'project.curtainWallFacilityPresent': '尚未提取到幕墙安装操作设施或附着支座',
        'project.curtainWallTransportRoutePresent': '尚未提取到幕墙运输路线或吊装运行路线',
        'project.curtainWallProtectionMeasuresPresent': '尚未提取到幕墙安全防护设置',
        'project.manualBoredPileGasProtectionPresent': '尚未提取到人工挖孔桩有害气体或防触电措施',
        'project.manualBoredPileJumpExcavationPresent': '尚未提取到人工挖孔桩跳挖或分序要求',
        'project.manualBoredPileForbiddenConditionMentioned': '已识别到人工挖孔桩禁用条件信号',
        'schedule.shutdownWindowDays': '尚未提取到停机窗口时长',
        'resource.laborTotal': '尚未提取到劳动力总量',
        'project.duplicateSections': '章节结构重复导致定位不稳定',
    }
    _INTERNAL_POLICY_SOURCES = {
        'review-control-plane-support-scope-policy': '系统审查支持材料边界规则',
        'review-control-plane-visibility-policy': '系统附件识别与复核规则',
    }
    _HAZARD_VALUE_LABELS = {
        'liftingOperation': '涉及起重吊装作业',
        'gasArea': '涉及煤气区域作业',
        'hotWork': '涉及动火作业',
        'temporaryPower': '涉及临时用电',
        'specialEquipmentMentioned': '提及特种设备',
        'craneCapacityTon': '起重设备额定吨位',
        'calculatedLiftWeightTon': '计算吊重',
        'shutdownWindowDays': '停机窗口天数',
        'laborTotal': '劳动力总量',
        'calculationEvidencePresent': '已提取验算依据',
        'measureSectionPresent': '已识别风险控制措施章节',
        'monitoringSectionPresent': '已识别监测监控章节',
        'foundationPitSupportSequencePresent': '已识别基坑支护/降水/开挖关系',
        'formworkPourSequencePresent': '已识别模板支撑预压/浇筑顺序',
        'steelSupportUnloadingPresent': '已识别钢结构临时支撑/卸载条件',
    }
    _HIGH_RISK_CATEGORY_LABELS = {
        'lifting_operations': '起重吊装',
        'gas_area_ops': '煤气区域作业',
        'temporary_power': '临时用电',
        'hot_work': '动火作业',
        'working_at_height': '高处作业',
        'special_equipment': '特种设备作业',
    }
    _SECTION_PRESENCE_LABELS = {
        'engineeringOverview': '工程概况',
        'preparationBasis': '编制依据',
        'constructionPlan': '施工部署/施工计划',
        'schedulePlan': '施工进度计划',
        'resourcePlan': '施工准备与资源配置计划',
        'layoutPlan': '施工现场平面布置',
        'processMethod': '主要施工方案',
        'safetyMeasures': '安全管理措施',
        'emergencyPlan': '应急预案',
        'calculationBook': '计算书/验算书',
        'monitoringPlan': '监测监控',
        'staffingAndRoles': '人员配备与分工',
        'acceptanceRequirements': '验收要求',
        'drawingSet': '相关施工图纸',
        'riskIdentification': '风险辨识与分级',
        'siteLayout': '施工平面布置',
        'surroundingConditions': '周边环境条件',
        'participantResponsibilities': '参建各方责任主体单位',
        'technicalParameters': '技术参数',
        'processFlow': '工艺流程',
        'inspectionRequirements': '检查要求',
        'organizationMeasures': '组织保障措施',
        'technicalMeasures': '技术措施',
        'monitoringMeasures': '监测监控措施',
    }
    _L1_STRUCTURE_TITLES = {
        '施工组织设计核心章节不完整',
        '章节结构存在重复标题，正式审查定位不稳定',
        '配网工程专项施工方案通用章节不完整',
        '停电施工作业专项章节不完整',
    }
    _L1_PREFLIGHT_TITLES = {
        '附件处于可视域缺口，需人工复核原件',
    }
    _STRUCTURE_ITEM_KEYWORDS = {
        'preparationBasis': ('编制依据',),
        'engineeringOverview': ('工程概况',),
        'constructionDeployment': ('施工部署', '施工计划'),
        'schedulePlan': ('施工进度计划', '工期', '停机窗口'),
        'resourcePlan': ('资源', '劳动力', '投入人力'),
        'processMethod': ('专项方案', '施工方案', '起重吊装', '吊装'),
        'layoutPlan': ('平面布置', '附图', '附件'),
        'progressManagementPlan': ('进度管理', '停机窗口'),
        'qualityManagementPlan': ('质量',),
        'safetyManagementPlan': ('安全', '应急预案', '动火', '临时用电', '高风险作业', '监测监控'),
        'environmentManagementPlan': ('环境', '煤气'),
        'costManagementPlan': ('成本',),
        'specialEngineeringOverview': ('工程概况',),
        'specialPreparationBasis': ('编制依据',),
        'specialConstructionPlan': ('施工计划', '施工安排', '停电窗口'),
        'specialProcessTechnology': ('施工工艺', '施工方法', '作业流程'),
        'specialAssuranceMeasures': ('保证措施', '控制措施'),
        'specialStaffingAndRoles': ('人员', '分工', '工作负责人'),
        'specialAcceptanceRequirements': ('验收',),
        'specialEmergencyMeasures': ('应急',),
        'specialDrawings': ('图纸', '附图', '布置图'),
        'specialRiskIdentification': ('风险',),
        'specialLayoutEnvironment': ('平面布置', '周边环境', '作业边界'),
        'specialCalculationEvidence': ('计算', '验算'),
        'powerOutageScope': ('停电范围', '停电线路', '停电区域'),
        'powerOutageWorkContent': ('作业内容', '施工内容', '工作内容'),
        'powerOutageMajorRisk': ('主要风险', '风险辨识', '触电'),
        'powerOutageStaffing': ('施工人员', '作业人员', '工作负责人'),
        'powerOutageEquipment': ('机具', '工器具'),
        'powerOutageMaterials': ('材料',),
        'powerOutageSafetyControl': ('安全管控', '安全措施'),
        'powerOutageQualityControl': ('质量管控', '质量控制'),
        'powerOutageEmergencyMeasures': ('应急措施', '应急处置'),
    }

    def build_summary(
        self,
        *,
        document_type: str,
        selected_packs: list[str],
        issues,
        matrices: StructuredReviewMatrices,
        visibility,
        parse_warnings: list[str],
        unresolved_facts,
    ):
        layer_counts = Counter(issue.layer.value for issue in issues)
        manual_review_needed = visibility.manualReviewNeeded or any(issue.manualReviewNeeded for issue in issues)
        high_risk_issue = any(issue.layer.value == 'L1' and issue.severity in {'high', 'medium'} for issue in issues)
        if high_risk_issue:
            overall = '修改后重新报审'
        elif manual_review_needed:
            overall = '需人工复核'
        else:
            overall = '合格通过'
        visibility_summary = StructuredReviewVisibilitySummary(
            attachmentCount=visibility.attachmentCount,
            counts=visibility.counts,
            duplicateSectionTitles=visibility.duplicateSectionTitles,
            parseWarnings=visibility.parseWarnings or parse_warnings,
            reasonCounts=visibility.reasonCounts,
            manualReviewNeeded=visibility.manualReviewNeeded,
        )
        return StructuredReviewSummary(
            overallConclusion=overall,
            documentType=document_type,
            selectedPacks=selected_packs,
            manualReviewNeeded=manual_review_needed,
            issueCount=len(issues),
            layerCounts=dict(layer_counts),
            stats={
                'attachmentCount': len(matrices.attachmentVisibility),
                'ruleHitCount': sum(1 for item in matrices.ruleHits if item.status in {'hit', 'manual_review_needed'}),
                'unresolvedFactCount': len(unresolved_facts),
                'issueKindCounts': dict(Counter(issue.issueKind for issue in issues)),
                'preflightGateDecision': visibility.preflight.gateDecision,
                'blockedIssueCount': sum(
                    1 for issue in issues if issue.applicabilityState in {'blocked_by_visibility', 'blocked_by_missing_fact'}
                ),
            },
            visibilitySummary=visibility_summary,
        )

    def build_issue_buckets(self, issues) -> dict[str, list[dict[str, str]]]:
        bucket_order = ['hard_defect', 'visibility_gap', 'evidence_gap', 'enhancement']
        buckets = {bucket: [] for bucket in bucket_order}
        for issue in issues:
            buckets.setdefault(issue.issueKind, []).append(
                {
                    'id': issue.id,
                    'title': issue.title,
                    'layer': issue.layer.value,
                    'severity': issue.severity,
                }
            )
        return buckets

    def render(
        self,
        *,
        summary: StructuredReviewSummary,
        resolved_profile: ResolvedReviewProfile,
        issues,
        matrices: StructuredReviewMatrices,
        parse_result,
        unresolved_facts,
    ) -> str:
        document_label = self._document_type_label(summary.documentType)
        basis_files = self._collect_basis_files(summary.selectedPacks or resolved_profile.policyPackIds, issues)
        layer_sections = {
            'L1': '第二部分：L1 审查发现——合法合规与结构完整性',
            'L2': '第三部分：L2 审查发现——核心参数与规则实质性验证',
            'L3': '第四部分：L3 审查发现——工程逻辑与实施风险预判',
        }
        lines = [
            f'# {document_label}形式审查报告',
            '',
            '## 第一部分：审查结论与审查依据',
            '',
            '### 1. 总体审查结论',
            f'- 审查结论：{summary.overallConclusion}',
            f'- 文档类型：{document_label}',
            f'- 是否需人工复核：{"是" if summary.manualReviewNeeded else "否"}',
            f'- 当前识别问题总数：{summary.issueCount} 项',
            '',
            '### 2. 审查依据文件',
        ]
        if basis_files['primary']:
            lines.extend(['#### 主要审查依据文件', *[f'- {item}' for item in basis_files['primary']]])
        else:
            lines.append('#### 主要审查依据文件')
            lines.append('- 本次未提取到可直接展示的外部规范或法规条文来源。')
        if basis_files['supplemental']:
            lines.extend(['', '#### 补充说明依据', *[f'- {item}' for item in basis_files['supplemental']]])
        lines.append('')
        lines.extend(self._render_first_section_notes(parse_result.visibility))
        if matrices.structureCompleteness:
            overview_issue_map, _ = self._build_structure_related_issue_map(
                matrices.structureCompleteness,
                issues,
                compact=True,
            )
            lines.extend(
                [
                    '### 3. 审查总览表',
                    self._render_structure_overview_table_html(matrices.structureCompleteness, overview_issue_map),
                    '',
                ]
            )

        lines.extend(['## ' + layer_sections['L1'], ''])
        if summary.documentType == 'construction_org' and matrices.structureCompleteness:
            l1_structure_issues = [
                issue
                for issue in issues
                if issue.layer.value == 'L1' and issue.title in self._L1_STRUCTURE_TITLES
            ]
            l1_compliance_issues = [
                issue
                for issue in issues
                if issue.layer.value == 'L1' and issue.title not in self._L1_STRUCTURE_TITLES | self._L1_PREFLIGHT_TITLES
            ]
            lines.extend(self._render_construction_org_l1_section(matrices, l1_structure_issues, l1_compliance_issues, issues))
        elif matrices.structureCompleteness:
            l1_structure_issues = [
                issue for issue in issues if issue.layer.value == 'L1' and issue.title in self._L1_STRUCTURE_TITLES
            ]
            l1_compliance_issues = [
                issue for issue in issues if issue.layer.value == 'L1' and issue.title not in self._L1_STRUCTURE_TITLES | self._L1_PREFLIGHT_TITLES
            ]
            lines.extend(self._render_generic_structure_l1_section_markdown(matrices, l1_structure_issues, l1_compliance_issues, issues))
        else:
            l1_issues = sorted(
                [issue for issue in issues if issue.layer.value == 'L1'],
                key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title),
            )
            if l1_issues:
                basis_lines = self._render_layer_basis(l1_issues)
                if basis_lines:
                    lines.extend(['### 主要审查依据', *basis_lines, ''])
            if not l1_issues:
                lines.extend(['- 本层未发现需要单独提示的问题。', ''])
            else:
                for index, issue in enumerate(l1_issues, start=1):
                    lines.extend(self._render_issue(index, issue))

        for layer in ['L2', 'L3']:
            lines.extend(['## ' + layer_sections[layer], ''])
            layer_issues = sorted(
                [issue for issue in issues if issue.layer.value == layer],
                key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title),
            )
            if layer_issues:
                basis_lines = self._render_layer_basis(layer_issues)
                if basis_lines:
                    lines.extend(['### 主要审查依据', *basis_lines, ''])
            if not layer_issues:
                lines.extend(['- 本层未发现需要单独提示的问题。', ''])
                continue
            for index, issue in enumerate(layer_issues, start=1):
                lines.extend(self._render_issue(index, issue))

        lines.extend(
            [
                '## 第五部分：关键数据识别汇总',
                '',
                '### 1. 危大工程识别情况',
                *self._render_hazard_summary(matrices.hazardIdentification.values),
                '',
                '## 第六部分：解析说明与复核提示',
                '',
                '### 6.1 文档解析状态与预检结果',
                *self._render_visibility_section(parse_result.visibility),
                '',
                '### 6.2 附件解析与关联情况',
                *self._render_attachment_gaps(matrices.attachmentVisibility),
                '',
                '### 6.3 待人工确认事项',
                *self._render_unresolved_facts(unresolved_facts, parse_result.visibility),
                '',
                '说明：完整结构化结果、矩阵明细及可追溯工件已保留在系统结果与附件中，供复核和留档使用。',
            ]
        )
        return '\n'.join(lines)

    def render_html(
        self,
        *,
        summary: StructuredReviewSummary,
        resolved_profile: ResolvedReviewProfile,
        issues,
        matrices: StructuredReviewMatrices,
        parse_result,
        unresolved_facts,
    ) -> str:
        document_label = self._document_type_label(summary.documentType)
        basis_files = self._collect_basis_files(summary.selectedPacks or resolved_profile.policyPackIds, issues)
        html_parts = [
            '<article class="structured-report">',
            f'<h1 class="structured-report__title">{html.escape(document_label)}形式审查报告</h1>',
            *self._render_html_first_section(summary, basis_files, parse_result.visibility, matrices, issues),
            *self._render_html_l1_section(summary, matrices, issues),
            *self._render_html_layer_section("第三部分：L2 审查发现——核心参数与规则实质性验证", [issue for issue in issues if issue.layer.value == "L2"]),
            *self._render_html_layer_section("第四部分：L3 审查发现——工程逻辑与实施风险预判", [issue for issue in issues if issue.layer.value == "L3"]),
            *self._render_html_data_summary_section(matrices),
            *self._render_html_parse_notice_section(parse_result.visibility, matrices, unresolved_facts),
            '</article>',
        ]
        return ''.join(html_parts)

    def render_print_css(self) -> str:
        return _STRUCTURED_REPORT_PRINT_CSS

    def _render_first_section_notes(self, visibility) -> list[str]:
        lines = []
        lines.extend(self._render_pdf_limit_notice(visibility))
        if visibility.manualReviewNeeded and visibility.manualReviewReason:
            lines.append(f'- 复核提示：{self._manual_review_reason_text(visibility.manualReviewReason)}')
        if lines:
            lines.append('')
        return lines

    def _render_html_first_section(self, summary, basis_files, visibility, matrices, issues) -> list[str]:
        parts = [
            '<section class="structured-report__section">',
            '<h2 class="structured-report__section-title">第一部分：审查结论与审查依据</h2>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">1. 总体审查结论</h3>',
            '<ul class="structured-report__bullet-list">',
            f'<li>审查结论：{html.escape(summary.overallConclusion)}</li>',
            f'<li>文档类型：{html.escape(self._document_type_label(summary.documentType))}</li>',
            f'<li>是否需人工复核：{"是" if summary.manualReviewNeeded else "否"}</li>',
            f'<li>当前识别问题总数：{summary.issueCount} 项</li>',
            '</ul>',
            '</div>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">2. 审查依据文件</h3>',
        ]
        if basis_files['primary']:
            parts.extend(['<h4 class="structured-report__subsection-title">主要审查依据文件</h4>', '<ul class="structured-report__basis-list">'])
            parts.extend(f'<li>{html.escape(item)}</li>' for item in basis_files['primary'])
            parts.append('</ul>')
        if basis_files['supplemental']:
            parts.extend(['<h4 class="structured-report__subsection-title">补充说明依据</h4>', '<ul class="structured-report__basis-list">'])
            parts.extend(f'<li>{html.escape(item)}</li>' for item in basis_files['supplemental'])
            parts.append('</ul>')
        note_lines = self._render_first_section_notes(visibility)
        if note_lines:
            parts.append('<ul class="structured-report__bullet-list">')
            parts.extend(f'<li>{html.escape(line.removeprefix("- ").strip())}</li>' for line in note_lines if line.strip())
            parts.append('</ul>')
        parts.append('</div>')
        if matrices.structureCompleteness:
            overview_issue_map, _ = self._build_structure_related_issue_map(matrices.structureCompleteness, issues, compact=True)
            parts.extend([
                '<section class="structured-report__subsection structured-report__overview-section">',
                '<h3 class="structured-report__subsection-title">3. 审查总览表</h3>',
                '<div class="structured-report__table-wrap">',
                self._render_structure_overview_table_html(matrices.structureCompleteness, overview_issue_map),
                '</div>',
                '</section>',
            ])
        parts.append('</section>')
        return parts

    def _render_html_l1_section(self, summary, matrices, issues) -> list[str]:
        if not matrices.structureCompleteness:
            return []
        l1_structure_issues = [
            issue for issue in issues if issue.layer.value == 'L1' and issue.title in self._L1_STRUCTURE_TITLES
        ]
        l1_compliance_issues = [
            issue for issue in issues if issue.layer.value == 'L1' and issue.title not in self._L1_STRUCTURE_TITLES | self._L1_PREFLIGHT_TITLES
        ]
        if summary.documentType != 'construction_org':
            return self._render_generic_structure_l1_section_html(matrices, l1_structure_issues, l1_compliance_issues, issues)
        related_issue_map, mapped_issue_ids = self._build_structure_related_issue_map(matrices.structureCompleteness, issues, compact=False)
        supplemental_issues = [issue for issue in l1_compliance_issues if issue.id not in mapped_issue_ids]
        parts = [
            '<section class="structured-report__section">',
            '<h2 class="structured-report__section-title">第二部分：L1 审查发现——合法合规与结构完整性</h2>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">2.1 结构完整性与形式合规性</h3>',
            '<ul class="structured-report__bullet-list">',
            '<li>审查依据：本节仅依据《建筑施工组织设计规范》GB/T 50502-2009 进行结构完整性与形式合规性审查。</li>',
            f'<li>总体结论：{html.escape(self._structure_completeness_conclusion(matrices.structureCompleteness))}</li>',
            '</ul>',
            '<div class="structured-report__table-wrap">',
            self._render_structure_completeness_table_html(matrices.structureCompleteness, related_issue_map),
            '</div>',
            '<div class="structured-report__subsection">',
            '<h4 class="structured-report__subsection-title">缺项分析与补齐意见</h4>',
            '<div class="structured-report__followups">',
            *self._render_structure_followups_html(matrices.structureCompleteness),
            '</div>',
            '</div>',
        ]
        duplicate_issue = next((issue for issue in l1_structure_issues if issue.title == '章节结构存在重复标题，正式审查定位不稳定'), None)
        if duplicate_issue is not None:
            parts.extend([
                '<div class="structured-report__subsection">',
                '<h4 class="structured-report__subsection-title">结构稳定性提示</h4>',
                f'<p class="structured-report__issue-body">{html.escape(duplicate_issue.summary)}</p>',
                f'<p class="structured-report__muted">{html.escape(self._duplicate_issue_detail(duplicate_issue))}</p>',
                '</div>',
            ])
        parts.append('</div>')
        parts.extend(['<div class="structured-report__subsection">', '<h3 class="structured-report__subsection-title">2.2 补充审查意见</h3>'])
        if supplemental_issues:
            basis_lines = self._render_layer_basis(supplemental_issues)
            if basis_lines:
                parts.append('<ul class="structured-report__basis-list">')
                parts.extend(f'<li>{html.escape(item.removeprefix("- ").strip())}</li>' for item in basis_lines)
                parts.append('</ul>')
            parts.extend(self._render_issue_cards_html(supplemental_issues))
        else:
            parts.append('<p class="structured-report__muted">当前未发现需要在表外单列提示的补充意见。</p>')
        parts.extend(['</div>', '</section>'])
        return parts

    def _render_html_layer_section(self, title: str, layer_issues) -> list[str]:
        parts = [f'<section class="structured-report__section"><h2 class="structured-report__section-title">{html.escape(title)}</h2>']
        if layer_issues:
            basis_lines = self._render_layer_basis(layer_issues)
            if basis_lines:
                parts.extend(['<div class="structured-report__subsection">', '<h3 class="structured-report__subsection-title">主要审查依据</h3>', '<ul class="structured-report__basis-list">'])
                parts.extend(f'<li>{html.escape(item.removeprefix("- ").strip())}</li>' for item in basis_lines)
                parts.extend(['</ul>', '</div>'])
            parts.extend(self._render_issue_cards_html(layer_issues))
        else:
            parts.append('<p class="structured-report__muted">本层未发现需要单独提示的问题。</p>')
        parts.append('</section>')
        return parts

    def _render_html_data_summary_section(self, matrices) -> list[str]:
        lines = self._render_hazard_summary(matrices.hazardIdentification.values)
        return [
            '<section class="structured-report__section">',
            '<h2 class="structured-report__section-title">第五部分：关键数据识别汇总</h2>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">1. 危大工程识别情况</h3>',
            '<ul class="structured-report__fact-list">',
            *[f'<li>{html.escape(line.removeprefix("- ").strip())}</li>' for line in lines],
            '</ul>',
            '</div>',
            '</section>',
        ]

    def _render_html_parse_notice_section(self, visibility, attachment_visibility, unresolved_facts) -> list[str]:
        return [
            '<section class="structured-report__section">',
            '<h2 class="structured-report__section-title">第六部分：解析说明与复核提示</h2>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">6.1 文档解析状态与预检结果</h3>',
            '<ul class="structured-report__fact-list">',
            *[f'<li>{html.escape(line.removeprefix("- ").strip())}</li>' for line in self._render_visibility_section(visibility)],
            '</ul>',
            '</div>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">6.2 附件解析与关联情况</h3>',
            '<ul class="structured-report__fact-list">',
            *[f'<li>{html.escape(line.removeprefix("- ").strip())}</li>' for line in self._render_attachment_gaps(attachment_visibility.attachmentVisibility if hasattr(attachment_visibility, "attachmentVisibility") else attachment_visibility)],
            '</ul>',
            '</div>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">6.3 待人工确认事项</h3>',
            '<ul class="structured-report__fact-list">',
            *[f'<li>{html.escape(line.removeprefix("- ").strip())}</li>' for line in self._render_unresolved_facts(unresolved_facts, visibility)],
            '</ul>',
            '</div>',
            '<p class="structured-report__muted">说明：完整结构化结果、矩阵明细及可追溯工件已保留在系统结果与附件中，供复核和留档使用。</p>',
            '</section>',
        ]

    def _render_structure_followups_html(self, rows) -> list[str]:
        focus_rows = [row for row in rows if row.status in {'missing', 'partial', 'blocked_by_visibility'}]
        if not focus_rows:
            return ['<p class="structured-report__muted">结构完整性矩阵各项均已闭合，当前未形成额外补齐意见。</p>']
        parts: list[str] = []
        for index, row in enumerate(focus_rows, start=1):
            section_lines = self._matched_sections_display_list(row.matchedSections, limit=2)
            recommendation = self._structure_followup_recommendation(row)
            parts.extend([
                '<section class="structured-report__gap-item">',
                f'<h3 class="structured-report__gap-item-title">【{index}. {html.escape(row.requirementLabel)}】</h3>',
                '<div class="structured-report__gap-item-block">',
                '<div class="structured-report__gap-item-label">判定</div>',
                f'<div class="structured-report__gap-item-value">{html.escape(self._STRUCTURE_STATUS_LABELS.get(row.status, row.status))}</div>',
                '</div>',
                '<div class="structured-report__gap-item-block">',
                '<div class="structured-report__gap-item-label">识别章节</div>',
                '<ul class="structured-report__gap-item-list">',
                *([f'<li>{html.escape(item)}</li>' for item in section_lines] if section_lines else ['<li>未识别到稳定对应章节</li>']),
                '</ul>',
                '</div>',
                '<div class="structured-report__gap-item-block">',
                '<div class="structured-report__gap-item-label">补齐建议</div>',
                '<ul class="structured-report__gap-item-list">',
                f'<li>{html.escape(recommendation)}</li>',
                '</ul>',
                '</div>',
                '</section>',
            ])
        return parts

    def _render_structure_followups_grouped_html(self, rows) -> list[str]:
        groups = self._group_structure_rows(rows)
        parts: list[str] = []
        for group in groups:
            group_rows = [row for row in group['rows'] if row.status in {'missing', 'partial', 'blocked_by_visibility'}]
            if not group_rows:
                continue
            parts.extend(
                [
                    '<div class="structured-report__followup-group">',
                    f'<h4 class="structured-report__subsection-title">{html.escape(self._structure_group_followup_heading(str(group["scope"])))}</h4>',
                ]
            )
            for index, row in enumerate(group_rows, start=1):
                section_lines = self._matched_sections_display_list(row.matchedSections, limit=3)
                sections_text = '；'.join(section_lines) if section_lines else '未识别到稳定对应章节'
                recommendation = self._structure_followup_recommendation(row)
                parts.extend(
                    [
                        '<div class="structured-report__followup-compact">',
                        f'<p class="structured-report__followup-compact-title">【{index}. {html.escape(row.requirementLabel)}】</p>',
                        f'<p class="structured-report__followup-compact-line">判定：{html.escape(self._STRUCTURE_STATUS_LABELS.get(row.status, row.status))}</p>',
                        f'<p class="structured-report__followup-compact-line">识别章节：{html.escape(sections_text)}</p>',
                        f'<p class="structured-report__followup-compact-line">补齐建议：{html.escape(recommendation)}</p>',
                        '</div>',
                    ]
                )
            parts.append('</div>')
        return parts or ['<p class="structured-report__muted">当前未形成需要单列说明的缺项分析。</p>']

    def _render_issue_cards_html(self, issues) -> list[str]:
        parts: list[str] = []
        for index, issue in enumerate(issues, start=1):
            parts.extend([
                '<article class="structured-report__issue-card">',
                f'<h3 class="structured-report__issue-card-title">{index}. {html.escape(issue.title)}</h3>',
                '<section class="structured-report__issue-card-section">',
                '<div class="structured-report__issue-card-section-title">问题描述</div>',
                f'<p class="structured-report__issue-card-text">{html.escape(self._clean_report_text(issue.summary))}</p>',
                '</section>',
                '<section class="structured-report__issue-card-section">',
                '<div class="structured-report__issue-card-section-title">条文依据</div>',
                '<ul class="structured-report__issue-card-law-list">',
                *self._render_policy_requirements_html(issue),
                '</ul>',
                '</section>',
                '</article>',
            ])
        return parts

    def _render_policy_requirements_html(self, issue) -> list[str]:
        seen: set[str] = set()
        parts: list[str] = []
        for span in issue.policyEvidence:
            source_label, _ = self._normalize_policy_source(span.sourceId)
            excerpt = self._clean_report_text(span.excerpt.strip().replace('\n', ' '))
            clause_title = self._clean_report_text(span.clauseTitle or '相关条文要求')
            content = excerpt or f'{clause_title}提出相关要求。'
            dedupe_key = f'{source_label}|{content}'
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            parts.extend([
                '<li class="structured-report__issue-card-law-item">',
                f'<div class="structured-report__issue-card-law-title">{html.escape(source_label)}</div>',
                '<ul class="structured-report__issue-card-law-requirements">',
                f'<li class="structured-report__issue-card-law-requirement">要求：{html.escape(content)}</li>',
                '</ul>',
                '</li>',
            ])
        if not parts:
            parts.extend([
                '<li class="structured-report__issue-card-law-item">',
                '<div class="structured-report__issue-card-law-title">当前未单独提取到明确条文来源</div>',
                '<ul class="structured-report__issue-card-law-requirements">',
                '<li class="structured-report__issue-card-law-requirement">要求：建议结合本次命中的规范、法规和原文附件继续复核。</li>',
                '</ul>',
                '</li>',
            ])
        return parts

    def _document_type_label(self, document_type: str) -> str:
        return self._DOCUMENT_TYPE_LABELS.get(document_type, document_type)

    def _parse_mode_label(self, parse_mode: str | None) -> str:
        return self._PARSE_MODE_LABELS.get(parse_mode or '', '未识别解析方式')

    def _file_type_label(self, file_type: str | None) -> str:
        return self._FILE_TYPE_LABELS.get((file_type or '').lower(), file_type or '未识别文件类型')

    def _preflight_gate_label(self, gate: str | None) -> str:
        return '需先进入人工复核' if gate == 'manual_review_required' else '可进入正式审查'

    def _manual_review_reason_text(self, reason: str | None) -> str:
        if not reason:
            return '当前未触发额外人工复核说明。'
        return self._MANUAL_REVIEW_REASON_LABELS.get(reason, '当前问题仍需人工复核。')

    def _blocking_reason_text(self, reason: str) -> str:
        return self._BLOCKING_REASON_LABELS.get(reason, '当前存在需进一步人工核验的限制因素。')

    def _issue_kind_label(self, issue_kind: str) -> str:
        return self._ISSUE_KIND_LABELS.get(issue_kind, issue_kind)

    def _severity_label(self, severity: str) -> str:
        return self._SEVERITY_LABELS.get(severity, severity)

    def _applicability_label(self, applicability_state: str) -> str:
        return self._APPLICABILITY_LABELS.get(applicability_state, applicability_state)

    def _normalize_policy_source(self, source_id: str) -> tuple[str, bool]:
        if source_id in self._INTERNAL_POLICY_SOURCES:
            return self._INTERNAL_POLICY_SOURCES[source_id], False
        if '《' in source_id:
            return source_id[source_id.index('《'):], True
        return source_id, not source_id.startswith('review-control-plane-')

    def _collect_basis_files(self, selected_packs: list[str], issues) -> dict[str, list[str]]:
        primary: list[str] = []
        supplemental: list[str] = []
        seen: set[str] = set()
        for source_id in self._iter_policy_source_ids(selected_packs, issues):
            label, is_external = self._normalize_policy_source(source_id)
            if label in seen:
                continue
            seen.add(label)
            if is_external:
                primary.append(label)
            else:
                supplemental.append(label)
        return {'primary': primary, 'supplemental': supplemental}

    def _iter_policy_source_ids(self, selected_packs: list[str], issues):
        for issue in issues:
            for span in issue.policyEvidence:
                if span.sourceId:
                    yield span.sourceId
        registry = get_evidence_pack_registry()
        for pack_id in selected_packs:
            pack = registry.get(pack_id)
            if not pack:
                continue
            for clause in pack.clauses:
                if clause.sourceId:
                    yield clause.sourceId

    def _render_preflight_blocking_lines(self, blocking_reasons: list[str]) -> list[str]:
        if not blocking_reasons:
            return ['- 预检阻断说明：当前未识别额外阻断项。']
        filtered = [reason for reason in blocking_reasons if reason != 'parser_limited_pdf']
        if not filtered:
            return ['- 预检阻断说明：当前未识别额外阻断项。']
        details = '；'.join(self._blocking_reason_text(reason) for reason in filtered)
        return [f'- 预检阻断说明：{details}']

    def _render_pdf_limit_notice(self, visibility) -> list[str]:
        if not (visibility.fileType == 'pdf' and visibility.parserLimited):
            return []
        return ['- 提示：审核文件为 PDF，当前解析能力受限，可能存在审查不完整或判定偏差，建议结合原件人工复核。']

    def _render_visibility_observation_lines(self, visibility) -> list[str]:
        lines: list[str] = []
        counts = visibility.counts or {}
        if counts:
            observations = []
            if counts.get('parsed', 0):
                observations.append(f'已完整进入可视域的附件 {counts["parsed"]} 项')
            if counts.get('attachment_unparsed', 0):
                observations.append(f'标题已识别但正文未解析的附件 {counts["attachment_unparsed"]} 项')
            if counts.get('referenced_only', 0):
                observations.append(f'仅在正文中被提及的附件 {counts["referenced_only"]} 项')
            if counts.get('unknown', 0):
                observations.append(f'状态暂不能确认的附件 {counts["unknown"]} 项')
            if counts.get('missing', 0):
                observations.append(f'存在明确缺失证据的附件 {counts["missing"]} 项')
            if observations:
                lines.append(f'- 可视域概况：{"；".join(observations)}。')
        duplicates = visibility.duplicateSectionTitles or []
        if duplicates:
            lines.append(f'- 章节结构提示：存在重复标题，重点包括：{"、".join(duplicates[:5])}。')
        elif not lines:
            lines.append('- 可视域概况：当前未检测到额外的结构提示。')
        return lines

    def _render_visibility_section(self, visibility) -> list[str]:
        return [
            f'- 预检状态：{self._preflight_gate_label(visibility.preflight.gateDecision)}',
            f'- 当前解析方式：{self._parse_mode_label(visibility.parseMode)}',
            f'- 文件类型：{self._file_type_label(visibility.fileType)}',
            f'- 已识别附件数量：{visibility.attachmentCount}',
            f'- 人工复核说明：{self._manual_review_reason_text(visibility.manualReviewReason)}',
            *self._render_preflight_blocking_lines(visibility.preflight.blockingReasons),
            *self._render_visibility_observation_lines(visibility),
        ]

    def _render_attachment_gaps(self, attachment_items) -> list[str]:
        gap_items = [item for item in attachment_items if item.visibility.value != 'parsed' or item.manualReviewNeeded]
        if not gap_items:
            return ['- 当前未发现需要单独提示的附件可视域断链。']
        lines = []
        for item in gap_items:
            reason = self._manual_review_reason_text(item.reason) if item.reason else '当前附件未完全进入可视域。'
            lines.append(f'- {item.attachmentNumber}《{self._clean_report_text(item.title)}》：{reason}')
        return lines

    def _render_unresolved_facts(self, unresolved_facts, visibility=None) -> list[str]:
        if not unresolved_facts:
            return ['- 当前未形成单独列示的待人工确认事实。']
        parser_limited = bool(getattr(visibility, 'parserLimited', False))
        if parser_limited:
            grouped = self._render_grouped_unresolved_facts(unresolved_facts)
            if grouped:
                return grouped
        return [f'- {self._humanize_unresolved_summary(item.summary, parser_limited=parser_limited)}' for item in unresolved_facts]

    def _render_construction_org_l1_section(
        self,
        matrices: StructuredReviewMatrices,
        structure_issues,
        compliance_issues,
        all_issues,
    ) -> list[str]:
        related_issue_map, mapped_issue_ids = self._build_structure_related_issue_map(
            matrices.structureCompleteness,
            all_issues,
            compact=False,
        )
        supplemental_issues = [
            issue for issue in compliance_issues if issue.id not in mapped_issue_ids
        ]
        lines = [
            '### 2.1 结构完整性与形式合规性',
            '- 审查依据：本节仅依据《建筑施工组织设计规范》GB/T 50502-2009 进行结构完整性与形式合规性审查。',
            f'- 总体结论：{self._structure_completeness_conclusion(matrices.structureCompleteness)}',
            '',
            self._render_structure_completeness_table_html(matrices.structureCompleteness, related_issue_map),
            '',
            '#### 缺项分析与补齐意见',
        ]
        lines.extend(self._render_structure_followups(matrices.structureCompleteness))
        duplicate_issue = next((issue for issue in structure_issues if issue.title == '章节结构存在重复标题，正式审查定位不稳定'), None)
        if duplicate_issue is not None:
            lines.extend(
                [
                    '',
                    '#### 结构稳定性提示',
                    f'- {duplicate_issue.summary}',
                    f'- 说明：{self._duplicate_issue_detail(duplicate_issue)}',
                ]
            )
        lines.append('')
        lines.extend(['### 2.2 补充审查意见'])
        if supplemental_issues:
            basis_lines = self._render_layer_basis(supplemental_issues)
            if basis_lines:
                lines.extend(['- 主要审查依据：', *[f'  - {item[2:]}' if item.startswith('- ') else f'  - {item}' for item in basis_lines], ''])
            for index, issue in enumerate(
                sorted(supplemental_issues, key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title)),
                start=1,
            ):
                lines.extend(self._render_issue(index, issue))
        else:
            lines.extend(['- 当前未发现需要在表外单列提示的补充意见。', ''])
        return lines

    def _render_generic_structure_l1_section_markdown(
        self,
        matrices: StructuredReviewMatrices,
        structure_issues,
        compliance_issues,
        all_issues,
    ) -> list[str]:
        related_issue_map, mapped_issue_ids = self._build_structure_related_issue_map(
            matrices.structureCompleteness,
            all_issues,
            compact=False,
        )
        supplemental_issues = [issue for issue in compliance_issues if issue.id not in mapped_issue_ids]
        if any(row.scope == 'special' for row in matrices.structureCompleteness):
            groups = self._group_structure_rows(matrices.structureCompleteness)
            lines = [
                '### 2.1 结构完整性与形式合规性',
                f'- 总体结论：{self._structure_completeness_conclusion(matrices.structureCompleteness)}',
            ]
            basis_lines = self._render_layer_basis(structure_issues or supplemental_issues)
            if basis_lines:
                lines.extend(['- 主要审查依据：', *[f'  - {item[2:]}' if item.startswith('- ') else f'  - {item}' for item in basis_lines]])
            for index, group in enumerate(groups, start=1):
                group_scope = str(group['scope'])
                group_label = str(group['groupLabel'])
                group_rows = list(group['rows'])
                lines.extend(
                    [
                        '',
                        f'#### {self._structure_group_heading(group_scope, index)}',
                        f'- 主要审查依据：{self._SPECIAL_SCHEME_STRUCTURE_POLICY_LABEL}',
                        '',
                        self._render_structure_completeness_table_html(
                            group_rows,
                            related_issue_map,
                            basis_label_override=self._structure_group_basis_label(group_scope, group_label),
                        ),
                    ]
                )
            lines.extend(['', *self._render_structure_followups_grouped(matrices.structureCompleteness), '', '### 2.2 补充审查意见'])
            if supplemental_issues:
                for index, issue in enumerate(
                    sorted(supplemental_issues, key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title)),
                    start=1,
                ):
                    lines.extend(self._render_issue(index, issue))
            else:
                lines.extend(['- 当前未发现需要在表外单列提示的补充意见。', ''])
            return lines
        lines = [
            '### 2.1 结构完整性与形式合规性',
            f'- 总体结论：{self._structure_completeness_conclusion(matrices.structureCompleteness)}',
        ]
        basis_lines = self._render_layer_basis(structure_issues or supplemental_issues)
        if basis_lines:
            lines.extend(['- 主要审查依据：', *[f'  - {item[2:]}' if item.startswith('- ') else f'  - {item}' for item in basis_lines]])
        lines.extend(
            [
                '',
                self._render_structure_completeness_table_html(matrices.structureCompleteness, related_issue_map),
                '',
                '#### 缺项分析与补齐意见',
            ]
        )
        lines.extend(self._render_structure_followups(matrices.structureCompleteness))
        lines.append('')
        lines.extend(['### 2.2 补充审查意见'])
        if supplemental_issues:
            for index, issue in enumerate(
                sorted(supplemental_issues, key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title)),
                start=1,
            ):
                lines.extend(self._render_issue(index, issue))
        else:
            lines.extend(['- 当前未发现需要在表外单列提示的补充意见。', ''])
        return lines

    def _render_generic_structure_l1_section_html(
        self,
        matrices: StructuredReviewMatrices,
        structure_issues,
        compliance_issues,
        all_issues,
    ) -> list[str]:
        related_issue_map, mapped_issue_ids = self._build_structure_related_issue_map(
            matrices.structureCompleteness,
            all_issues,
            compact=False,
        )
        supplemental_issues = [issue for issue in compliance_issues if issue.id not in mapped_issue_ids]
        if any(row.scope == 'special' for row in matrices.structureCompleteness):
            groups = self._group_structure_rows(matrices.structureCompleteness)
            parts = [
                '<section class="structured-report__section">',
                '<h2 class="structured-report__section-title">第二部分：L1 审查发现——合法合规与结构完整性</h2>',
                '<div class="structured-report__subsection">',
                '<h3 class="structured-report__subsection-title">2.1 结构完整性与形式合规性</h3>',
                '<ul class="structured-report__bullet-list">',
                f'<li>总体结论：{html.escape(self._structure_completeness_conclusion(matrices.structureCompleteness))}</li>',
                '</ul>',
            ]
            basis_lines = self._render_layer_basis(structure_issues or supplemental_issues)
            if basis_lines:
                parts.extend(['<ul class="structured-report__basis-list">'])
                parts.extend(f'<li>{html.escape(item.removeprefix("- ").strip())}</li>' for item in basis_lines)
                parts.append('</ul>')
            for index, group in enumerate(groups, start=1):
                group_scope = str(group['scope'])
                group_label = str(group['groupLabel'])
                group_rows = list(group['rows'])
                parts.extend(
                    [
                        f'<h4 class="structured-report__subsection-title">{html.escape(self._structure_group_heading(group_scope, index))}</h4>',
                        f'<p class="structured-report__subsection-intro">主要审查依据：{html.escape(self._SPECIAL_SCHEME_STRUCTURE_POLICY_LABEL)}</p>',
                        '<div class="structured-report__table-wrap">',
                        self._render_structure_completeness_table_html(
                            group_rows,
                            related_issue_map,
                            basis_label_override=self._structure_group_basis_label(group_scope, group_label),
                        ),
                        '</div>',
                    ]
                )
            parts.extend(
                [
                    '<div class="structured-report__subsection">',
                    '<h4 class="structured-report__subsection-title">缺项分析与补齐意见</h4>',
                    *self._render_structure_followups_grouped_html(matrices.structureCompleteness),
                    '</div>',
                ]
            )
            parts.extend(['<div class="structured-report__subsection">', '<h3 class="structured-report__subsection-title">2.2 补充审查意见</h3>'])
            if supplemental_issues:
                parts.extend(
                    self._render_issue_cards_html(
                        sorted(supplemental_issues, key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title))
                    )
                )
            else:
                parts.append('<p class="structured-report__section-intro">当前未发现需要在表外单列提示的补充意见。</p>')
            parts.extend(['</div>', '</div>', '</section>'])
            return parts
        parts = [
            '<section class="structured-report__section">',
            '<h2 class="structured-report__section-title">第二部分：L1 审查发现——合法合规与结构完整性</h2>',
            '<div class="structured-report__subsection">',
            '<h3 class="structured-report__subsection-title">2.1 结构完整性与形式合规性</h3>',
            '<ul class="structured-report__bullet-list">',
            f'<li>总体结论：{html.escape(self._structure_completeness_conclusion(matrices.structureCompleteness))}</li>',
            '</ul>',
        ]
        basis_lines = self._render_layer_basis(structure_issues or supplemental_issues)
        if basis_lines:
            parts.extend(['<ul class="structured-report__basis-list">'])
            parts.extend(f'<li>{html.escape(item.removeprefix("- ").strip())}</li>' for item in basis_lines)
            parts.append('</ul>')
        parts.extend(
            [
                '<div class="structured-report__table-wrap">',
                self._render_structure_completeness_table_html(matrices.structureCompleteness, related_issue_map),
                '</div>',
                '<div class="structured-report__subsection">',
                '<h4 class="structured-report__subsection-title">缺项分析与补齐意见</h4>',
                '<div class="structured-report__followups">',
                *self._render_structure_followups_html(matrices.structureCompleteness),
                '</div>',
                '</div>',
            ]
        )
        parts.extend(['<div class="structured-report__subsection">', '<h3 class="structured-report__subsection-title">2.2 补充审查意见</h3>'])
        if supplemental_issues:
            parts.extend(
                self._render_issue_cards_html(
                    sorted(supplemental_issues, key=lambda issue: (self._SEVERITY_ORDER.get(issue.severity, 99), issue.title))
                )
            )
        else:
            parts.append('<p class="structured-report__section-intro">当前未发现需要在表外单列提示的补充意见。</p>')
        parts.extend(['</div>', '</div>', '</section>'])
        return parts

    def _structure_completeness_conclusion(self, rows) -> str:
        if not rows:
            return '当前未生成结构完整性矩阵。'
        missing_count = sum(1 for row in rows if row.status == 'missing')
        partial_count = sum(1 for row in rows if row.status == 'partial')
        blocked_count = sum(1 for row in rows if row.status == 'blocked_by_visibility')
        has_special_scheme_rows = any(str(getattr(row, 'itemKey', '')).startswith('special') or str(getattr(row, 'itemKey', '')).startswith('powerOutage') for row in rows)
        baseline = '对照专项施工方案目录要求，本文件结构主干'
        if not has_special_scheme_rows:
            baseline = '对照 GB/T 50502-2009，本文件结构主干'
        if missing_count == partial_count == blocked_count == 0:
            return f'{baseline}已形成闭合。'
        parts: list[str] = []
        if missing_count:
            parts.append(f'存在 {missing_count} 项明确缺项')
        if partial_count:
            parts.append(f'存在 {partial_count} 项仅部分识别')
        if blocked_count:
            parts.append(f'存在 {blocked_count} 项受可视域限制')
        return f'{baseline}未完全闭合，{"，".join(parts)}。'

    def _matched_sections_text(self, matched_sections) -> str:
        cleaned = self._matched_sections_display_list(matched_sections, limit=2)
        if not cleaned:
            return '未识别到稳定对应章节'
        return '；'.join(cleaned)

    def _matched_sections_display_list(self, matched_sections, *, limit: int = 2) -> list[str]:
        if not matched_sections:
            return []
        values: list[str] = []
        for item in matched_sections[:limit]:
            title = self._clean_section_title(item.title)
            title = self._truncate_title(title)
            values.append(title)
        if len(matched_sections) > limit:
            values.append('另命中若干相关章节，详见结构化结果')
        return values

    def _truncate_title(self, title: str, *, limit: int = 22) -> str:
        if len(title) <= limit:
            return title
        return title[: limit - 1].rstrip('、，；;：: ') + '…'

    def _clean_section_title(self, title: str | None) -> str:
        value = self._clean_report_text(title)
        value = re.sub(r'\s+\d{1,4}$', '', value)
        return value

    def _render_structure_followups(self, rows) -> list[str]:
        focus_rows = [row for row in rows if row.status in {'missing', 'partial', 'blocked_by_visibility'}]
        if not focus_rows:
            return ['- 结构完整性矩阵各项均已闭合，当前未形成额外补齐意见。']
        lines: list[str] = []
        for index, row in enumerate(focus_rows, start=1):
            section_lines = self._matched_sections_display_list(row.matchedSections, limit=2)
            lines.extend(
                [
                    f'【{index}. {row.requirementLabel}】',
                    f'判定：{self._STRUCTURE_STATUS_LABELS.get(row.status, row.status)}',
                    '识别章节：',
                    *([f'- {item}' for item in section_lines] if section_lines else ['- 未识别到稳定对应章节']),
                    f'补齐建议：{self._structure_followup_recommendation(row)}',
                    '---',
                ]
            )
        return lines

    def _group_structure_rows(self, rows) -> list[dict[str, object]]:
        groups: list[dict[str, object]] = []
        current_key: tuple[str, str] | None = None
        current_rows: list = []
        for row in rows:
            scope = str(getattr(row, 'scope', None) or 'common')
            group_label = self._clean_report_text(
                getattr(row, 'groupLabel', None)
                or ('专项补充要求' if scope == 'special' else '专项施工方案通用要求')
            )
            key = (scope, group_label)
            if current_key is None:
                current_key = key
            if key != current_key:
                groups.append(
                    {
                        'scope': current_key[0],
                        'groupLabel': current_key[1],
                        'rows': current_rows,
                    }
                )
                current_rows = []
                current_key = key
            current_rows.append(row)
        if current_key is not None:
            groups.append(
                {
                    'scope': current_key[0],
                    'groupLabel': current_key[1],
                    'rows': current_rows,
                }
            )
        return groups

    def _structure_group_heading(self, scope: str, index: int) -> str:
        label = '专项补充结构要求' if scope == 'special' else '专项施工方案通用要求'
        return f'2.1.{index} {label}'

    def _structure_group_basis_label(self, scope: str, group_label: str) -> str:
        if scope == 'special':
            return group_label
        return '专项施工方案通用要求'

    def _structure_group_followup_heading(self, scope: str) -> str:
        return '专项补充要求：缺项分析与补齐意见' if scope == 'special' else '通用要求：缺项分析与补齐意见'

    def _render_structure_followups_grouped(self, rows) -> list[str]:
        lines: list[str] = []
        groups = self._group_structure_rows(rows)
        for group in groups:
            group_rows = [row for row in group['rows'] if row.status in {'missing', 'partial', 'blocked_by_visibility'}]
            if not group_rows:
                continue
            lines.extend([f'#### {self._structure_group_followup_heading(str(group["scope"]))}'])
            lines.extend(self._render_structure_followups(group_rows))
            lines.append('')
        return lines or ['- 当前未形成需要单列说明的缺项分析。']

    def _duplicate_issue_detail(self, issue) -> str:
        details = []
        if issue.manualReviewNeeded and issue.manualReviewReason:
            details.append(self._manual_review_reason_text(issue.manualReviewReason))
        details.extend(self._blocking_reason_text(reason) for reason in issue.blockingReasons or [])
        return '；'.join(details) if details else '重复标题会降低章节映射与复核稳定性。'

    def _render_structure_completeness_table_html(
        self,
        rows,
        related_issue_map: dict[str, dict[str, list[str]]],
        *,
        basis_label_override: str | None = None,
    ) -> str:
        header = ''.join(f'<th>{label}</th>' for label in ['序号', '规范要求', '规范依据', '文档对应章节', '结构判定', '相关审查意见'])
        body_rows: list[str] = []
        for index, row in enumerate(rows, start=1):
            related_values = self._flatten_related_issue_values(related_issue_map.get(row.itemKey) or {})
            cells = [
                str(index),
                self._clean_report_text(row.requirementLabel),
                self._clean_report_text(basis_label_override or row.basisClause),
                self._matched_sections_text(row.matchedSections),
                self._STRUCTURE_STATUS_LABELS.get(row.status, row.status),
                self._related_issue_cell_text(related_values),
            ]
            body_rows.append('<tr>' + ''.join(f'<td>{html.escape(value)}</td>' for value in cells) + '</tr>')
        return (
            '<table class="structured-completeness-table">'
            '<thead><tr>' + header + '</tr></thead>'
            '<tbody>' + ''.join(body_rows) + '</tbody>'
            '</table>'
        )

    def _render_structure_overview_table_html(self, rows, related_issue_map: dict[str, dict[str, list[str]]]) -> str:
        header = ''.join(
            f'<th>{label}</th>'
            for label in ['序号', '结构项', 'L1 问题摘要', 'L2 问题摘要', 'L3 问题摘要']
        )
        body_rows: list[str] = []
        for index, row in enumerate(rows, start=1):
            layer_items = related_issue_map.get(row.itemKey) or {'L1': [], 'L2': [], 'L3': []}
            cells = [
                str(index),
                self._clean_report_text(row.requirementLabel),
                self._overview_issue_cell_text(layer_items.get('L1') or []),
                self._overview_issue_cell_text(layer_items.get('L2') or []),
                self._overview_issue_cell_text(layer_items.get('L3') or []),
            ]
            body_rows.append(
                '<tr>'
                + ''.join(f'<td>{html.escape(value).replace("；", "；<br/>")}</td>' for value in cells)
                + '</tr>'
            )
        return (
            '<table class="structured-overview-table">'
            '<thead><tr>' + header + '</tr></thead>'
            '<tbody>' + ''.join(body_rows) + '</tbody>'
            '</table>'
        )

    def _build_structure_related_issue_map(self, rows, issues, *, compact: bool) -> tuple[dict[str, dict[str, list[str]]], set[str]]:
        row_map = {row.itemKey: row for row in rows}
        related_map = {row.itemKey: {'L1': [], 'L2': [], 'L3': []} for row in rows}
        mapped_issue_ids: set[str] = set()
        for issue in issues:
            if issue.title in self._L1_STRUCTURE_TITLES | self._L1_PREFLIGHT_TITLES:
                continue
            matched_keys = self._match_issue_to_structure_item_keys(issue)
            if not matched_keys:
                continue
            layer = issue.layer.value
            for item_key in matched_keys[:2]:
                if item_key not in row_map:
                    continue
                summary = self._related_issue_summary_text(
                    issue,
                    compact=compact,
                    matched_sections=row_map[item_key].matchedSections,
                )
                if summary in related_map[item_key][layer]:
                    continue
                if len(related_map[item_key][layer]) >= 2:
                    continue
                related_map[item_key][layer].append(summary)
                mapped_issue_ids.add(issue.id)
        return related_map, mapped_issue_ids

    def _match_issue_to_structure_item_keys(self, issue) -> list[str]:
        matched: list[str] = []
        for key in issue.missingFactKeys or []:
            if key.startswith('project.structureCompleteness.'):
                item_key = key.split('.')[-1]
                if item_key not in matched:
                    matched.append(item_key)
        issue_text = self._clean_report_text(f'{issue.title} {issue.summary}')
        for item_key, keywords in self._STRUCTURE_ITEM_KEYWORDS.items():
            if item_key in matched:
                continue
            if any(keyword and keyword in issue_text for keyword in keywords):
                matched.append(item_key)
        return matched

    def _related_issue_summary_text(self, issue, *, compact: bool, matched_sections) -> str:
        text = self._clean_report_text(issue.title or issue.summary)
        text = self._truncate_title(text, limit=20 if compact else 26)
        position = self._issue_position_text(issue, matched_sections)
        return f'{position}：{text}' if position else text

    def _related_issue_cell_text(self, values: list[str]) -> str:
        if not values:
            return '—'
        return '；'.join(values[:2])

    def _flatten_related_issue_values(self, value: dict[str, list[str]] | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        flattened: list[str] = []
        for layer in ['L1', 'L2', 'L3']:
            flattened.extend(value.get(layer) or [])
        return flattened

    def _overview_issue_cell_text(self, values: list[str]) -> str:
        if not values:
            return '—'
        return '；'.join(values[:2])

    def _issue_position_text(self, issue, matched_sections) -> str:
        candidates: list[str] = []
        for section in matched_sections or []:
            title = getattr(section, 'title', None)
            if title:
                candidates.append(str(title))
        for span in issue.docEvidence or []:
            excerpt = getattr(span, 'excerpt', None)
            if excerpt:
                candidates.append(str(excerpt))
        for candidate in candidates:
            locator = self._extract_section_locator(candidate)
            if locator:
                return locator
        return ''

    def _extract_section_locator(self, text: str | None) -> str:
        value = self._clean_report_text(text)
        patterns = [
            r'(第[一二三四五六七八九十百零〇两]+章)',
            r'(第[一二三四五六七八九十百零〇两]+节)',
            r'((?:\d+\.)+\d+节?)',
            r'(\d+节)',
        ]
        for pattern in patterns:
            match = re.search(pattern, value)
            if match:
                return match.group(1)
        return ''

    def _structure_followup_recommendation(self, row) -> str:
        if row.status == 'partial':
            return f'建议补齐或单列“{row.requirementLabel}”。'
        if row.status == 'missing':
            return f'建议补齐“{row.requirementLabel}”专章或形成稳定章节标题。'
        if row.status == 'blocked_by_visibility':
            return f'建议结合原件、目录及附图附表复核“{row.requirementLabel}”是否完整设置。'
        return self._clean_report_text(row.reportExcerpt or '当前无需额外补齐。')

    def _clean_report_text(self, text: str | None) -> str:
        if not text:
            return ''
        value = str(text).replace('\n', ' ').replace('\r', ' ')
        if value.strip().lower() == 'demo':
            return '建议结合原文和附件补充完善后复核。'
        replacements = {
            'parser-limited': '受限解析路径',
            'pdf_text_only': 'PDF 文本受限解析',
            'manual_review_required': '需人工复核',
            'manual_confirmation_required': '需人工确认',
            'blocked_by_visibility': '受可视域限制',
            'working_at_height': '高处作业',
            'gas_area_ops': '煤气区域作业',
            'hot_work': '动火作业',
            'temporary_power': '临时用电',
            'lifting_operations': '起重吊装',
            'special_equipment': '特种设备作业',
            'calculationBook': '计算书/验算书',
            'engineeringOverview': '工程概况',
            'preparationBasis': '编制依据',
            'constructionPlan': '施工部署/施工计划',
            'processMethod': '主要施工方案',
            'safetyMeasures': '安全管理措施',
            'emergencyPlan': '应急预案',
            'Demo': '建议结合原文和附件补充完善后复核。',
            'demo': '建议结合原文和附件补充完善后复核。',
        }
        for source, target in replacements.items():
            value = value.replace(source, target)
        value = re.sub(r'（位置\s*\d+）', '', value)
        value = re.sub(r'\b位置\s*\d+\b', '', value)
        value = re.sub(r'[-—_\.]{6,}', ' ', value)
        value = re.sub(r'\s+', ' ', value).strip(' ；;，,。')
        return value

    def _missing_fact_label(self, fact_key: str) -> str:
        return self._MISSING_FACT_LABELS.get(fact_key, '存在尚未提取完整的关键事实')

    def _visibility_value_label(self, value: str | None) -> str:
        return self._VISIBILITY_VALUE_LABELS.get(value or '', '当前状态暂不能确认')

    def _high_risk_category_label(self, value: str) -> str:
        return self._HIGH_RISK_CATEGORY_LABELS.get(value, self._clean_report_text(value))

    def _section_presence_label(self, value: str) -> str:
        return self._SECTION_PRESENCE_LABELS.get(value, self._clean_report_text(value))

    def _humanize_unresolved_summary(self, summary: str, *, parser_limited: bool) -> str:
        value = self._clean_report_text(summary)
        if parser_limited:
            patterns = [
                (r'^当前解析路径受限，无法稳定确认', '尚无法稳定确认'),
                (r'^当前为受限解析路径，尚不能稳定判断', '尚无法稳定确认'),
                (r'^当前解析路径为受限解析路径，无法稳定确认', '尚无法稳定确认'),
                (r'^当前解析路径为 受限解析路径，无法稳定确认', '尚无法稳定确认'),
                (r'^已识别高风险场景，但当前解析路径为受限解析路径，无法稳定确认', '已识别高风险场景，但尚无法稳定确认'),
                (r'^已识别高风险场景，但当前解析路径为 受限解析路径，无法稳定确认', '已识别高风险场景，但尚无法稳定确认'),
            ]
            for pattern, replacement in patterns:
                value = re.sub(pattern, replacement, value)
        return value

    def _render_grouped_unresolved_facts(self, unresolved_facts) -> list[str]:
        structure_labels: list[str] = []
        support_section_labels: list[str] = []
        parameter_labels: list[str] = []
        monitoring_uncertain = False
        other_lines: list[str] = []
        seen_other: set[str] = set()
        for item in unresolved_facts:
            fact_key = getattr(item, 'factKey', '') or ''
            label = self._fact_key_business_label(fact_key)
            if fact_key.startswith('project.structureCompleteness.'):
                if label and label not in structure_labels:
                    structure_labels.append(label)
                continue
            if fact_key.startswith('project.sectionPresence.'):
                if label and label not in support_section_labels:
                    support_section_labels.append(label)
                continue
            if fact_key == 'hazard.monitoringSectionPresent':
                monitoring_uncertain = True
                continue
            if fact_key in {
                'hazard.calculatedLiftWeightTon',
                'schedule.shutdownWindowDays',
                'resource.laborTotal',
                'emergency.planTitles',
                'hazard.craneCapacityTon',
            }:
                if label and label not in parameter_labels:
                    parameter_labels.append(label)
                continue
            humanized = self._humanize_unresolved_summary(item.summary, parser_limited=True)
            if humanized not in seen_other:
                seen_other.add(humanized)
                other_lines.append(f'- {humanized}')
        lines: list[str] = []
        if structure_labels:
            lines.append(
                '- 因审核文件为 PDF 且当前解析能力受限，以下结构性章节尚无法稳定确认是否真实缺失：'
                + '、'.join(structure_labels)
                + '。'
            )
        if support_section_labels:
            lines.append('- 当前尚无法稳定确认以下支撑章节是否在正文中明确出现：' + '、'.join(support_section_labels) + '。')
        if parameter_labels:
            lines.append(
                '- 当前尚未稳定提取以下关键参数或支撑信息：'
                + '、'.join(parameter_labels)
                + '。'
            )
        if monitoring_uncertain:
            lines.append('- 已识别高风险场景，但“监测监控”等支撑章节是否在正文中明确出现，仍需结合原件复核。')
        if other_lines:
            lines.extend(other_lines[:4])
        return lines or ['- 当前待人工确认事项较少，建议结合原件进行复核。']

    def _fact_key_business_label(self, fact_key: str) -> str:
        structure_labels = {
            'project.structureCompleteness.preparationBasis': '编制依据',
            'project.structureCompleteness.engineeringOverview': '工程概况',
            'project.structureCompleteness.constructionDeployment': '施工部署',
            'project.structureCompleteness.schedulePlan': '施工进度计划',
            'project.structureCompleteness.resourcePlan': '施工准备与资源配置计划',
            'project.structureCompleteness.processMethod': '主要施工方案',
            'project.structureCompleteness.layoutPlan': '施工现场平面布置',
            'project.structureCompleteness.progressManagementPlan': '进度管理计划',
            'project.structureCompleteness.qualityManagementPlan': '质量管理计划',
            'project.structureCompleteness.safetyManagementPlan': '安全管理计划',
            'project.structureCompleteness.environmentManagementPlan': '环境管理计划',
            'project.structureCompleteness.costManagementPlan': '成本管理计划',
            'project.structureCompleteness.specialEngineeringOverview': '工程概况',
            'project.structureCompleteness.specialPreparationBasis': '编制依据',
            'project.structureCompleteness.specialConstructionPlan': '施工计划',
            'project.structureCompleteness.specialProcessTechnology': '施工工艺技术',
            'project.structureCompleteness.specialAssuranceMeasures': '施工保证措施',
            'project.structureCompleteness.specialStaffingAndRoles': '施工管理及作业人员配备和分工',
            'project.structureCompleteness.specialAcceptanceRequirements': '验收要求',
            'project.structureCompleteness.specialEmergencyMeasures': '应急处置措施',
            'project.structureCompleteness.specialDrawings': '相关施工图纸 / 节点详图 / 布置图',
            'project.structureCompleteness.specialRiskIdentification': '风险辨识与分级',
            'project.structureCompleteness.specialLayoutEnvironment': '施工平面布置或周边环境条件',
            'project.structureCompleteness.specialCalculationEvidence': '计算书及相关验算依据',
            'project.structureCompleteness.powerOutageScope': '停电范围',
            'project.structureCompleteness.powerOutageWorkContent': '作业内容',
            'project.structureCompleteness.powerOutageMajorRisk': '主要风险',
            'project.structureCompleteness.powerOutageStaffing': '施工人员',
            'project.structureCompleteness.powerOutageEquipment': '机具',
            'project.structureCompleteness.powerOutageMaterials': '材料',
            'project.structureCompleteness.powerOutageSafetyControl': '安全管控',
            'project.structureCompleteness.powerOutageQualityControl': '质量管控',
            'project.structureCompleteness.powerOutageEmergencyMeasures': '应急措施',
            'project.structureCompleteness.foundationPitSupportSequence': '支护、降水、开挖及加撑关系',
            'project.structureCompleteness.foundationPitMonitoring': '监测监控措施',
            'project.structureCompleteness.foundationPitEnvironmentDrawings': '周边环境与监测点相关图纸',
            'project.structureCompleteness.foundationPitAcceptance': '验收要求',
            'project.structureCompleteness.formworkSupportParameters': '技术参数',
            'project.structureCompleteness.formworkSupportProcessFlow': '工艺流程 / 浇筑顺序',
            'project.structureCompleteness.formworkSupportCalculation': '计算依据',
            'project.structureCompleteness.formworkSupportAcceptance': '验收要求',
            'project.structureCompleteness.steelStructureComponentParameters': '构件参数',
            'project.structureCompleteness.steelStructureLiftingEquipment': '吊装设备选型',
            'project.structureCompleteness.steelStructureInstallationProcess': '安装流程',
            'project.structureCompleteness.steelStructureSupportUnloading': '拼装胎架 / 临时支撑 / 卸载条件',
            'project.structureCompleteness.steelStructureDrawingsAcceptance': '措施图纸及验收章节',
        }
        direct = {
            'hazard.calculatedLiftWeightTon': '计算起重量',
            'hazard.craneCapacityTon': '起重设备额定吨位',
            'project.foundationPitSupportSequencePresent': '基坑支护/降水/开挖关系',
            'project.formworkPourSequencePresent': '模板支撑预压/浇筑顺序',
            'project.steelSupportUnloadingPresent': '钢结构临时支撑/卸载条件',
            'schedule.shutdownWindowDays': '停机窗口',
            'resource.laborTotal': '劳动力投入',
            'emergency.planTitles': '针对性应急预案标题',
            'hazard.monitoringSectionPresent': '监测监控',
            'project.sectionPresence.constructionPlan': '施工部署/施工计划',
            'project.sectionPresence.monitoringPlan': '监测监控',
        }
        return structure_labels.get(fact_key) or direct.get(fact_key) or self._MISSING_FACT_LABELS.get(fact_key, '')

    def _render_layer_basis(self, issues) -> list[str]:
        seen: set[str] = set()
        lines: list[str] = []
        for issue in issues:
            for source in self._issue_policy_source_lines(issue):
                if source in seen:
                    continue
                seen.add(source)
                lines.append(f'- {source}')
        return lines[:6]

    def _issue_policy_source_lines(self, issue) -> list[str]:
        sources: list[str] = []
        seen: set[str] = set()
        for span in issue.policyEvidence:
            source_label, _ = self._normalize_policy_source(span.sourceId)
            clause_title = span.clauseTitle or '相关条文要求'
            text = f'{source_label}：{self._clean_report_text(clause_title)}'
            if text in seen:
                continue
            seen.add(text)
            sources.append(text)
        return sources

    def _render_issue(self, index: int, issue) -> list[str]:
        policy_lines = self._render_policy_requirements(issue)
        lines = [
            f'### {index}. {issue.title}',
            '问题描述',
            f'- {self._clean_report_text(issue.summary)}',
            *policy_lines,
            '',
        ]
        return lines

    def _render_policy_requirements(self, issue) -> list[str]:
        lines = ['条文依据']
        seen: set[str] = set()
        items: list[tuple[str, str]] = []
        for span in issue.policyEvidence:
            source_label, _ = self._normalize_policy_source(span.sourceId)
            excerpt = self._clean_report_text(span.excerpt.strip().replace('\n', ' '))
            clause_title = span.clauseTitle or '相关条文要求'
            clause_title = self._clean_report_text(clause_title)
            content = excerpt or f'{clause_title}提出相关要求。'
            dedupe_key = f'{source_label}|{content}'
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            items.append((source_label, content))
        if not items:
            items.append(('当前未单独提取到明确条文来源', '建议结合本次命中的规范、法规和原文附件继续复核。'))
        for source_label, content in items:
            lines.append(f'- {source_label}')
            lines.append(f'  - 要求：{content}')
        return lines

    def _render_issue_risk_lines(self, issue) -> list[str]:
        details = [
            f'问题性质为“{self._issue_kind_label(issue.issueKind)}”，严重程度为“{self._severity_label(issue.severity)}”，当前状态为“{self._applicability_label(issue.applicabilityState)}”。'
        ]
        if issue.manualReviewNeeded:
            details.append(self._manual_review_reason_text(issue.manualReviewReason))
        if issue.missingFactKeys:
            details.append('；'.join(self._missing_fact_label(key) for key in issue.missingFactKeys) + '。')
        if issue.blockingReasons:
            details.extend(self._blocking_reason_text(reason) for reason in issue.blockingReasons)
        if issue.evidenceMissing and not issue.missingFactKeys and not issue.blockingReasons:
            details.append('当前证据链尚未完全闭合，建议结合原始资料继续核实。')
        return ['- 当前风险/限制：', *[f'  - {item}' for item in details]]

    def _render_hazard_summary(self, hazard_values: dict) -> list[str]:
        lines: list[str] = []
        active_categories = hazard_values.get('highRiskCategories') or []
        if active_categories:
            lines.append(f'- 已识别的高风险作业类型：{"、".join(self._high_risk_category_label(str(item)) for item in active_categories)}。')
        for key, label in self._HAZARD_VALUE_LABELS.items():
            value = hazard_values.get(key)
            if value in (None, '', [], {}):
                continue
            if isinstance(value, bool):
                lines.append(f'- {label}：{"是" if value else "否"}。')
            else:
                lines.append(f'- {label}：{self._clean_report_text(str(value))}。')
        section_presence = hazard_values.get('sectionPresence') or {}
        if isinstance(section_presence, dict):
            missing_sections = [self._section_presence_label(name) for name, present in section_presence.items() if present is False]
            if missing_sections:
                lines.append(f'- 结构提示：以下关键章节未明确识别到：{"、".join(missing_sections[:8])}。')
        if not lines:
            return ['- 当前未提取到明确的危大工程识别参数。']
        return lines

    def _render_attachment_matrix_summary(self, attachment_items, visibility) -> list[str]:
        counts = visibility.counts or {}
        lines = [
            f'- 已识别附件共 {visibility.attachmentCount} 项，其中完整进入可视域 {counts.get("parsed", 0)} 项。'
        ]
        if counts.get('attachment_unparsed', 0):
            lines.append(f'- 存在 {counts["attachment_unparsed"]} 项附件仅识别到标题，尚需补核正文或原件。')
        if counts.get('referenced_only', 0):
            lines.append(f'- 存在 {counts["referenced_only"]} 项附件仅在正文中被提及。')
        if counts.get('unknown', 0):
            lines.append(f'- 存在 {counts["unknown"]} 项附件状态暂不能确认。')
        if counts.get('missing', 0):
            lines.append(f'- 存在 {counts["missing"]} 项附件具有明确缺失证据。')
        example_items = [item for item in attachment_items if item.visibility.value != 'parsed'][:3]
        for item in example_items:
            lines.append(f'- 重点提示：{item.attachmentNumber}《{self._clean_report_text(item.title)}》当前状态为“{self._visibility_value_label(item.visibility.value)}”。')
        return lines

    def _render_section_structure_summary(self, section_items, visibility) -> list[str]:
        duplicate_count = sum(1 for item in section_items if item.duplicate)
        lines = [f'- 已识别章节 {len(section_items)} 个。']
        if duplicate_count:
            lines.append(f'- 其中存在重复标题章节 {duplicate_count} 个，可能影响正文与附件的精确定位。')
        if visibility.duplicateSectionTitles:
            lines.append(f'- 重点重复标题包括：{"、".join(visibility.duplicateSectionTitles[:5])}。')
        if duplicate_count == 0:
            lines.append('- 当前未检测到明显的重复章节结构问题。')
        return lines

    def _render_structure_completeness_summary(self, rows) -> list[str]:
        if not rows:
            return ['- 当前未生成施组结构完整性矩阵。']
        counts = Counter(row.status for row in rows)
        lines = [f'- 共核对 {len(rows)} 项结构要求，其中符合 {counts.get("matched", 0)} 项。']
        if counts.get('partial', 0):
            lines.append(f'- 仅部分符合 {counts["partial"]} 项。')
        if counts.get('missing', 0):
            lines.append(f'- 明确缺失 {counts["missing"]} 项。')
        if counts.get('blocked_by_visibility', 0):
            lines.append(f'- 受可视域限制 {counts["blocked_by_visibility"]} 项。')
        focus_rows = [row.requirementLabel for row in rows if row.status in {'partial', 'missing', 'blocked_by_visibility'}]
        if focus_rows:
            lines.append(f'- 重点关注项：{"、".join(focus_rows[:6])}。')
        return lines

    def _render_rule_hit_summary(self, rule_hits) -> list[str]:
        if not rule_hits:
            return ['- 本次未形成可单列展示的规则命中结果。']
        status_counts = Counter(item.status for item in rule_hits)
        layer_counts = Counter(item.layerHint for item in rule_hits)
        lines = [
            f'- 规则命中统计：命中 {status_counts.get("hit", 0)} 项，需人工复核 {status_counts.get("manual_review_needed", 0)} 项，不适用 {status_counts.get("not_applicable", 0)} 项，通过 {status_counts.get("pass", 0)} 项。',
            f'- 分层分布：L1 {layer_counts.get("L1", 0)} 项，L2 {layer_counts.get("L2", 0)} 项，L3 {layer_counts.get("L3", 0)} 项。',
        ]
        blocked = sum(1 for item in rule_hits if item.applicabilityState in {'blocked_by_visibility', 'blocked_by_missing_fact'})
        if blocked:
            lines.append(f'- 其中有 {blocked} 项规则受可视域或关键事实不足影响，需结合原文和附件进一步复核。')
        return lines

    def _render_conflict_summary(self, conflict_values: dict) -> list[str]:
        lines: list[str] = []
        schedule_vs_resources = conflict_values.get('scheduleVsResources') or {}
        if schedule_vs_resources:
            if schedule_vs_resources.get('issueTriggered'):
                lines.append('- 工期窗口与资源配置之间已触发组织压力提示，需重点核查停机窗口、劳动力投入和高风险工序是否匹配。')
            else:
                lines.append('- 当前未触发明显的工期与资源组织压力提示。')
        hazard_vs_measures = conflict_values.get('hazardVsMeasures') or {}
        if hazard_vs_measures:
            if hazard_vs_measures.get('issueTriggered'):
                lines.append('- 危险源识别与控制措施之间已出现闭环不足提示，需重点补核监测监控和风险控制衔接。')
            else:
                lines.append('- 当前未触发明显的危险源与控制措施闭环冲突提示。')
        if not lines:
            lines.append('- 当前未形成可单列展示的冲突联动提示。')
        return lines
