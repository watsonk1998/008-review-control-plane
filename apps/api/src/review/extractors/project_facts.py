from __future__ import annotations

from typing import Any

from src.review.parser.normalizer import section_key
from src.review.structure_completeness import build_construction_org_structure_matrix


def _find_block(blocks: list[dict[str, Any]], pattern: str) -> dict[str, Any] | None:
    for block in blocks:
        if pattern in str(block.get('text') or ''):
            return block
    return None


def _extract_value(blocks: list[dict[str, Any]], prefix: str) -> tuple[str | None, str | None]:
    block = _find_block(blocks, prefix)
    if block is None:
        return None, None
    text = str(block.get('text') or '')
    if '：' in text:
        return text.split('：', 1)[1].strip(), block['id']
    if ':' in text:
        return text.split(':', 1)[1].strip(), block['id']
    return text, block['id']


_DOC_TYPE_HINTS = {
    'distribution_network_special_scheme': ['配网工程专项施工方案', '配网专项施工方案', '停电施工作业专项施工方案'],
    'hazardous_special_scheme': ['专项施工方案', '危大'],
    'construction_org': ['施工组织设计', '施工组织'],
    'construction_scheme': ['施工方案'],
    'supervision_plan': ['监理规划', '监理实施规划', '监理'],
}

_CONTEXT_ONLY_MARKERS = (
    '补充背景',
    '背景说明',
    '辅助材料',
    '支持材料',
    '不形成正式方案',
    '不作为正式方案',
    '仅供审查参考',
)

_SECTION_PRESENCE_LABELS = {
    'engineeringOverview': '工程概况',
    'preparationBasis': '编制依据',
    'constructionPlan': '施工部署/施工计划',
    'schedulePlan': '施工进度计划',
    'resourcePlan': '资源配置计划',
    'layoutPlan': '施工平面布置',
    'processMethod': '施工工艺/施工方法',
    'safetyMeasures': '安全措施',
    'emergencyPlan': '应急预案',
    'calculationBook': '计算书/验算',
    'monitoringPlan': '监测监控',
    'staffingAndRoles': '施工管理及作业人员配备和分工',
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

_STRUCTURE_COMPLETENESS_TO_SECTION_PRESENCE = {
    'engineeringOverview': 'engineeringOverview',
    'preparationBasis': 'preparationBasis',
    'schedulePlan': 'schedulePlan',
    'resourcePlan': 'resourcePlan',
    'processMethod': 'processMethod',
    'layoutPlan': 'layoutPlan',
}

_WEAK_STRUCTURE_SECTION_KEYWORDS = (
    '工程概况',
    '工程简介',
    '编制依据',
    '编制说明',
    '施工计划',
    '施工部署',
    '施工进度计划',
    '进度计划',
    '工期安排',
    '资源配置',
    '资源配置计划',
    '劳动力计划',
    '机械设备计划',
    '施工总平面布置',
    '平面布置',
    '施工工艺',
    '工艺流程',
    '施工方法',
    '安全保证措施',
    '安全技术措施',
    '安全管理措施',
    '应急预案',
    '应急处置',
    '应急救援',
    '计算书',
    '验算',
    '受力计算',
    '监测监控',
    '监控监测',
)


def _infer_document_type_hint(text: str) -> str:
    for document_type, keywords in _DOC_TYPE_HINTS.items():
        if any(keyword in text for keyword in keywords):
            return document_type
    return 'review_support_material'


def _collect_section_presence(parse_result) -> tuple[dict[str, bool], dict[str, list[str]]]:
    presence = {
        'engineeringOverview': False,
        'preparationBasis': False,
        'constructionPlan': False,
        'schedulePlan': False,
        'resourcePlan': False,
        'layoutPlan': False,
        'processMethod': False,
        'safetyMeasures': False,
        'emergencyPlan': False,
        'calculationBook': False,
        'monitoringPlan': False,
        'staffingAndRoles': False,
        'acceptanceRequirements': False,
        'drawingSet': False,
        'riskIdentification': False,
        'siteLayout': False,
        'surroundingConditions': False,
        'participantResponsibilities': False,
        'technicalParameters': False,
        'processFlow': False,
        'inspectionRequirements': False,
        'organizationMeasures': False,
        'technicalMeasures': False,
        'monitoringMeasures': False,
    }
    refs = {f'project.sectionPresence.{key}': [] for key in presence}
    for section in parse_result.sections:
        title = str(section.get('title') or '')
        block_id = section.get('blockId')
        if any(keyword in title for keyword in ['工程概况', '工程简介']):
            presence['engineeringOverview'] = True
            if block_id:
                refs['project.sectionPresence.engineeringOverview'].append(block_id)
        if any(keyword in title for keyword in ['编制依据', '编制说明']):
            presence['preparationBasis'] = True
            if block_id:
                refs['project.sectionPresence.preparationBasis'].append(block_id)
        if any(keyword in title for keyword in ['施工计划', '施工部署', '施工总部署', '施工安排']):
            presence['constructionPlan'] = True
            if block_id:
                refs['project.sectionPresence.constructionPlan'].append(block_id)
        if any(keyword in title for keyword in ['施工进度计划', '进度计划', '工期安排', '进度管理计划', '施工网络进度表', '网络进度表']):
            presence['schedulePlan'] = True
            if block_id:
                refs['project.sectionPresence.schedulePlan'].append(block_id)
        if any(keyword in title for keyword in ['资源配置', '资源配置计划', '劳动力计划', '机械设备计划', '资源管理计划', '施工劳动力安排', '施工准备']):
            presence['resourcePlan'] = True
            if block_id:
                refs['project.sectionPresence.resourcePlan'].append(block_id)
        if any(keyword in title for keyword in ['施工总平面布置', '施工现场平面布置', '施工平面布置', '施工平面管理计划', '平面布置']):
            presence['layoutPlan'] = True
            if block_id:
                refs['project.sectionPresence.layoutPlan'].append(block_id)
        if any(keyword in title for keyword in ['施工总平面布置', '施工现场平面布置', '施工平面布置', '平面图', '立面图', '剖面图']):
            presence['siteLayout'] = True
            if block_id:
                refs['project.sectionPresence.siteLayout'].append(block_id)
        if any(keyword in title for keyword in ['施工工艺', '工艺流程', '施工方法', '施工方案']):
            presence['processMethod'] = True
            if block_id:
                refs['project.sectionPresence.processMethod'].append(block_id)
        if any(keyword in title for keyword in ['技术参数', '设计参数']):
            presence['technicalParameters'] = True
            if block_id:
                refs['project.sectionPresence.technicalParameters'].append(block_id)
        if any(keyword in title for keyword in ['工艺流程', '施工流程', '施工顺序', '步序图']):
            presence['processFlow'] = True
            if block_id:
                refs['project.sectionPresence.processFlow'].append(block_id)
        if any(keyword in title for keyword in ['检查要求', '检查内容', '质量检查']):
            presence['inspectionRequirements'] = True
            if block_id:
                refs['project.sectionPresence.inspectionRequirements'].append(block_id)
        if any(keyword in title for keyword in ['安全保证措施', '安全技术措施', '安全管理措施', '安全管理计划', '专项安全措施', '施工用电安全']):
            presence['safetyMeasures'] = True
            if block_id:
                refs['project.sectionPresence.safetyMeasures'].append(block_id)
        if any(keyword in title for keyword in ['组织保障措施', '安全组织机构', '安全保证体系']):
            presence['organizationMeasures'] = True
            if block_id:
                refs['project.sectionPresence.organizationMeasures'].append(block_id)
        if any(keyword in title for keyword in ['技术措施', '质量技术保证措施', '季节性施工保证措施', '防台风施工保证措施']):
            presence['technicalMeasures'] = True
            if block_id:
                refs['project.sectionPresence.technicalMeasures'].append(block_id)
        if any(keyword in title for keyword in ['监测监控措施', '监测监控', '监控监测']):
            presence['monitoringMeasures'] = True
            if block_id:
                refs['project.sectionPresence.monitoringMeasures'].append(block_id)
        if any(keyword in title for keyword in ['应急预案', '应急处置', '应急救援']):
            presence['emergencyPlan'] = True
            if block_id:
                refs['project.sectionPresence.emergencyPlan'].append(block_id)
        if any(keyword in title for keyword in ['计算书', '验算', '受力计算']):
            presence['calculationBook'] = True
            if block_id:
                refs['project.sectionPresence.calculationBook'].append(block_id)
        if any(keyword in title for keyword in ['相关施工图纸', '相关图纸', '节点详图', '平面布置图', '剖面图', '立面图', '监测点平面图', '监测平面布置图']):
            presence['drawingSet'] = True
            if block_id:
                refs['project.sectionPresence.drawingSet'].append(block_id)
        if any(keyword in title for keyword in ['监测监控', '监控监测']):
            presence['monitoringPlan'] = True
            if block_id:
                refs['project.sectionPresence.monitoringPlan'].append(block_id)
        if any(keyword in title for keyword in ['施工管理及作业人员配备和分工', '作业人员配备和分工', '人员配备和分工', '施工管理人员', '作业人员配备']):
            presence['staffingAndRoles'] = True
            if block_id:
                refs['project.sectionPresence.staffingAndRoles'].append(block_id)
        if any(keyword in title for keyword in ['验收要求', '验收标准', '验收程序', '验收内容']):
            presence['acceptanceRequirements'] = True
            if block_id:
                refs['project.sectionPresence.acceptanceRequirements'].append(block_id)
        if any(keyword in title for keyword in ['风险辨识与分级', '风险辨识', '安全风险分级', '风险分级']):
            presence['riskIdentification'] = True
            if block_id:
                refs['project.sectionPresence.riskIdentification'].append(block_id)
        if any(keyword in title for keyword in ['周边环境条件', '周边环境', '环境条件']):
            presence['surroundingConditions'] = True
            if block_id:
                refs['project.sectionPresence.surroundingConditions'].append(block_id)
        if any(keyword in title for keyword in ['参建各方责任主体单位', '责任主体单位', '参建各方']):
            presence['participantResponsibilities'] = True
            if block_id:
                refs['project.sectionPresence.participantResponsibilities'].append(block_id)
    return presence, refs


def _infer_hazardous_scheme_type_hints(parse_result) -> tuple[list[str], dict[str, list[str]], dict[str, bool]]:
    hints: list[str] = []
    refs: dict[str, list[str]] = {
        'project.hazardousSchemeTypeHints': [],
        'project.foundationPitSupportSequencePresent': [],
        'project.foundationPitMonitoringDrawingPresent': [],
        'project.formworkPourSequencePresent': [],
        'project.formworkPreloadPresent': [],
        'project.liftingSiteBearingPresent': [],
        'project.liftingTemporaryFixationPresent': [],
        'project.liftingSupportDevicePresent': [],
        'project.scaffoldWallTiePresent': [],
        'project.scaffoldAntiFallPresent': [],
        'project.scaffoldMonitoringPresent': [],
        'project.demolitionSequencePresent': [],
        'project.demolitionRetainedStructureControlPresent': [],
        'project.demolitionSupportCalculationPresent': [],
        'project.undergroundWaterControlPresent': [],
        'project.undergroundSupportParametersPresent': [],
        'project.undergroundMonitoringPresent': [],
        'project.curtainWallFacilityPresent': [],
        'project.curtainWallTransportRoutePresent': [],
        'project.curtainWallProtectionMeasuresPresent': [],
        'project.manualBoredPileGasProtectionPresent': [],
        'project.manualBoredPileJumpExcavationPresent': [],
        'project.manualBoredPileForbiddenConditionMentioned': [],
        'project.steelSupportUnloadingPresent': [],
        'project.steelTireFramePresent': [],
        'project.steelMultiStageSimulationPresent': [],
    }

    def _match_type(tag: str, keywords: tuple[str, ...]) -> None:
        for block in parse_result.blocks:
            content = str(block.get('text') or '')
            if any(keyword in content for keyword in keywords):
                if tag not in hints:
                    hints.append(tag)
                refs['project.hazardousSchemeTypeHints'].append(block['id'])
                break

    _match_type('foundation_pit', ('基坑工程', '基坑支护', '土方开挖', '降水'))
    _match_type('formwork_support', ('模板支撑体系', '模板支撑', '支撑体系', '模架'))
    _match_type('lifting_installation_removal', ('起重吊装', '安装拆卸工程', '安装拆卸', '汽车吊', '吊装'))
    _match_type('scaffold', ('脚手架工程', '脚手架', '连墙件', '附着式升降脚手架', '吊篮'))
    _match_type('demolition', ('拆除工程', '拆除顺序', '爆破拆除', '静力破碎'))
    _match_type('underground_excavation', ('暗挖工程', '顶管', '盾构', '冻结壁', '地下水控制'))
    _match_type('curtain_wall_installation', ('建筑幕墙安装工程', '幕墙安装', '幕墙工程'))
    _match_type('manual_bored_pile', ('人工挖孔桩工程', '人工挖孔桩', '护壁'))
    _match_type('steel_structure_installation', ('钢结构安装工程', '钢结构安装', '钢构件', '拼装胎架'))

    support_keywords = ('支护', '降水', '帷幕', '土方开挖', '加撑')
    foundation_monitor_keywords = ('监测点平面图', '监测布置图', '周边环境平面图', '周边环境剖面图')
    pour_keywords = ('浇筑顺序', '浇筑方式', '模架使用')
    preload_keywords = ('预压', '支架预压')
    lifting_site_keywords = ('地基承载力', '支承面承载能力', '站位图', '站位处地基承载力')
    lifting_fixation_keywords = ('临时固定', '缆风绳', '地锚', '临时稳固', '稳定措施')
    lifting_support_keywords = ('辅助起重设备', '吊索具', '吊耳', '平衡梁')
    scaffold_walltie_keywords = ('连墙件', '附着支撑结构', '附墙支座')
    scaffold_antifall_keywords = ('防倾覆', '防坠落', '安全锁')
    scaffold_monitor_keywords = ('监测范围', '监测项目', '预警值', '控制值')
    demolition_sequence_keywords = ('拆除顺序', '解体', '清运', '施工总体流程')
    demolition_retained_keywords = ('保留结构', '作业平台承载', '稳定状态控制')
    demolition_calc_keywords = ('移动式拆除机械', '临时支撑计算书', '爆破计算书', '吊运计算')
    underground_water_keywords = ('地下水控制', '地下水位', '注浆量', '注浆压力', '冻结壁')
    underground_support_keywords = ('支护技术参数', '开挖断面尺寸', '开挖进尺', '反力架', '钢套筒')
    underground_monitor_keywords = ('监测范围', '监测项目', '监测频率', '监测点布置图')
    curtain_facility_keywords = ('安装操作设施', '附墙支座', '动力设备', '运输设备')
    curtain_route_keywords = ('运输路线', '吊装运行路线', '堆放平面图')
    curtain_protection_keywords = ('安全防护设置', '防倾覆', '防坠落', '安全锁')
    pile_gas_keywords = ('有害气体检测', '防中毒', '防窒息', '防止触电', '地下水抽排')
    pile_jump_keywords = ('跳挖', '分区', '分序')
    pile_forbidden_keywords = ('不得使用人工挖孔桩', '流塑状泥', '厚度超过 2m 的砂层', '地下水丰富', '有毒气体')
    steel_keywords = ('临时支撑', '拼装胎架', '卸载条件', '卸载', '吊耳')
    steel_tire_keywords = ('拼装胎架', '胎架')
    steel_simulation_keywords = ('模拟计算', '不同施工阶段', '多机抬吊吊重分配', '结构强度', '变形')

    derived_flags = {
        'foundationPitSupportSequencePresent': False,
        'foundationPitMonitoringDrawingPresent': False,
        'formworkPourSequencePresent': False,
        'formworkPreloadPresent': False,
        'liftingSiteBearingPresent': False,
        'liftingTemporaryFixationPresent': False,
        'liftingSupportDevicePresent': False,
        'scaffoldWallTiePresent': False,
        'scaffoldAntiFallPresent': False,
        'scaffoldMonitoringPresent': False,
        'demolitionSequencePresent': False,
        'demolitionRetainedStructureControlPresent': False,
        'demolitionSupportCalculationPresent': False,
        'undergroundWaterControlPresent': False,
        'undergroundSupportParametersPresent': False,
        'undergroundMonitoringPresent': False,
        'curtainWallFacilityPresent': False,
        'curtainWallTransportRoutePresent': False,
        'curtainWallProtectionMeasuresPresent': False,
        'manualBoredPileGasProtectionPresent': False,
        'manualBoredPileJumpExcavationPresent': False,
        'manualBoredPileForbiddenConditionMentioned': False,
        'steelSupportUnloadingPresent': False,
        'steelTireFramePresent': False,
        'steelMultiStageSimulationPresent': False,
    }
    for block in parse_result.blocks:
        content = str(block.get('text') or '')
        if any(keyword in content for keyword in support_keywords):
            derived_flags['foundationPitSupportSequencePresent'] = True
            refs['project.foundationPitSupportSequencePresent'].append(block['id'])
        if any(keyword in content for keyword in foundation_monitor_keywords):
            derived_flags['foundationPitMonitoringDrawingPresent'] = True
            refs['project.foundationPitMonitoringDrawingPresent'].append(block['id'])
        if any(keyword in content for keyword in pour_keywords):
            derived_flags['formworkPourSequencePresent'] = True
            refs['project.formworkPourSequencePresent'].append(block['id'])
        if any(keyword in content for keyword in preload_keywords):
            derived_flags['formworkPreloadPresent'] = True
            refs['project.formworkPreloadPresent'].append(block['id'])
        if any(keyword in content for keyword in lifting_site_keywords):
            derived_flags['liftingSiteBearingPresent'] = True
            refs['project.liftingSiteBearingPresent'].append(block['id'])
        if any(keyword in content for keyword in lifting_fixation_keywords):
            derived_flags['liftingTemporaryFixationPresent'] = True
            refs['project.liftingTemporaryFixationPresent'].append(block['id'])
        if any(keyword in content for keyword in lifting_support_keywords):
            derived_flags['liftingSupportDevicePresent'] = True
            refs['project.liftingSupportDevicePresent'].append(block['id'])
        if any(keyword in content for keyword in scaffold_walltie_keywords):
            derived_flags['scaffoldWallTiePresent'] = True
            refs['project.scaffoldWallTiePresent'].append(block['id'])
        if any(keyword in content for keyword in scaffold_antifall_keywords):
            derived_flags['scaffoldAntiFallPresent'] = True
            refs['project.scaffoldAntiFallPresent'].append(block['id'])
        if any(keyword in content for keyword in scaffold_monitor_keywords):
            derived_flags['scaffoldMonitoringPresent'] = True
            refs['project.scaffoldMonitoringPresent'].append(block['id'])
        if any(keyword in content for keyword in demolition_sequence_keywords):
            derived_flags['demolitionSequencePresent'] = True
            refs['project.demolitionSequencePresent'].append(block['id'])
        if any(keyword in content for keyword in demolition_retained_keywords):
            derived_flags['demolitionRetainedStructureControlPresent'] = True
            refs['project.demolitionRetainedStructureControlPresent'].append(block['id'])
        if any(keyword in content for keyword in demolition_calc_keywords):
            derived_flags['demolitionSupportCalculationPresent'] = True
            refs['project.demolitionSupportCalculationPresent'].append(block['id'])
        if any(keyword in content for keyword in underground_water_keywords):
            derived_flags['undergroundWaterControlPresent'] = True
            refs['project.undergroundWaterControlPresent'].append(block['id'])
        if any(keyword in content for keyword in underground_support_keywords):
            derived_flags['undergroundSupportParametersPresent'] = True
            refs['project.undergroundSupportParametersPresent'].append(block['id'])
        if any(keyword in content for keyword in underground_monitor_keywords):
            derived_flags['undergroundMonitoringPresent'] = True
            refs['project.undergroundMonitoringPresent'].append(block['id'])
        if any(keyword in content for keyword in curtain_facility_keywords):
            derived_flags['curtainWallFacilityPresent'] = True
            refs['project.curtainWallFacilityPresent'].append(block['id'])
        if any(keyword in content for keyword in curtain_route_keywords):
            derived_flags['curtainWallTransportRoutePresent'] = True
            refs['project.curtainWallTransportRoutePresent'].append(block['id'])
        if any(keyword in content for keyword in curtain_protection_keywords):
            derived_flags['curtainWallProtectionMeasuresPresent'] = True
            refs['project.curtainWallProtectionMeasuresPresent'].append(block['id'])
        if any(keyword in content for keyword in pile_gas_keywords):
            derived_flags['manualBoredPileGasProtectionPresent'] = True
            refs['project.manualBoredPileGasProtectionPresent'].append(block['id'])
        if any(keyword in content for keyword in pile_jump_keywords):
            derived_flags['manualBoredPileJumpExcavationPresent'] = True
            refs['project.manualBoredPileJumpExcavationPresent'].append(block['id'])
        if any(keyword in content for keyword in pile_forbidden_keywords):
            derived_flags['manualBoredPileForbiddenConditionMentioned'] = True
            refs['project.manualBoredPileForbiddenConditionMentioned'].append(block['id'])
        if any(keyword in content for keyword in steel_keywords):
            derived_flags['steelSupportUnloadingPresent'] = True
            refs['project.steelSupportUnloadingPresent'].append(block['id'])
        if any(keyword in content for keyword in steel_tire_keywords):
            derived_flags['steelTireFramePresent'] = True
            refs['project.steelTireFramePresent'].append(block['id'])
        if any(keyword in content for keyword in steel_simulation_keywords):
            derived_flags['steelMultiStageSimulationPresent'] = True
            refs['project.steelMultiStageSimulationPresent'].append(block['id'])

    for key in refs:
        refs[key] = list(dict.fromkeys(refs[key]))
    return hints, refs, derived_flags


def _find_weak_section_structure_duplicates(parse_result) -> tuple[list[str], list[str]]:
    duplicates = {str(title) for title in parse_result.visibility.duplicateSectionTitles if title}
    if not duplicates:
        return [], []
    impacted_titles: list[str] = []
    impacted_refs: list[str] = []
    seen: set[str] = set()
    for section in parse_result.sections:
        title = str(section.get('title') or '')
        key = str(section.get('key') or section_key(title))
        if not title or not key or key not in duplicates:
            continue
        if int(section.get('level', 99)) > 2:
            continue
        if title.startswith(('附件', '附录')):
            if key not in seen:
                seen.add(key)
                impacted_titles.append(key)
            if section.get('blockId'):
                impacted_refs.append(str(section['blockId']))
            continue
        if title.startswith('第') and any(keyword in title for keyword in _WEAK_STRUCTURE_SECTION_KEYWORDS):
            if key not in seen:
                seen.add(key)
                impacted_titles.append(key)
            if section.get('blockId'):
                impacted_refs.append(str(section['blockId']))
    return impacted_titles, list(dict.fromkeys(impacted_refs))


def extract_project_facts(parse_result) -> tuple[dict[str, Any], dict[str, list[str]], list[dict[str, Any]]]:
    blocks = parse_result.blocks
    project_name, project_name_ref = _extract_value(blocks, '项目名称')
    project_code, project_code_ref = _extract_value(blocks, '项目编号')
    location, location_ref = _extract_value(blocks, '施工地点')

    duplicate_map: dict[str, list[str]] = {}
    for section in parse_result.sections:
        if int(section.get('level', 99)) > 2 or not str(section.get('title', '')).startswith('第'):
            continue
        duplicate_map.setdefault(section_key(section['title']), []).append(section['blockId'])
    duplicate_sections = [title for title, refs in duplicate_map.items() if len(refs) > 1]

    document_type_hint = _infer_document_type_hint(parse_result.normalizedText[:3000])
    special_equipment_blocks = [block['id'] for block in blocks if '特种设备' in str(block.get('text') or '') or '行车' in str(block.get('text') or '')]
    context_only_blocks = [
        block['id']
        for block in blocks
        if any(marker in str(block.get('text') or '') for marker in _CONTEXT_ONLY_MARKERS)
    ]
    section_presence, section_presence_refs = _collect_section_presence(parse_result)
    weak_structure_duplicates, weak_structure_refs = _find_weak_section_structure_duplicates(parse_result)
    hazardous_scheme_type_hints, type_hint_refs, derived_type_flags = _infer_hazardous_scheme_type_hints(parse_result)

    structure_completeness: list[dict[str, Any]] = []
    structure_refs: dict[str, list[str]] = {}
    structure_unresolved: list[dict[str, Any]] = []
    if document_type_hint == 'construction_org':
        structure_completeness, structure_refs, structure_unresolved = build_construction_org_structure_matrix(parse_result)
        for row in structure_completeness:
            mapped_presence_key = _STRUCTURE_COMPLETENESS_TO_SECTION_PRESENCE.get(row['itemKey'])
            if mapped_presence_key and row['status'] in {'matched', 'partial'}:
                section_presence[mapped_presence_key] = True

    facts = {
        'documentTypeHint': document_type_hint,
        'projectName': project_name,
        'projectCode': project_code,
        'location': location,
        'duplicateSections': duplicate_sections,
        'specialEquipmentMentioned': bool(special_equipment_blocks),
        'contextOnly': bool(context_only_blocks),
        'sectionCount': len(parse_result.sections),
        'tableCount': len(parse_result.tables),
        'sectionPresence': section_presence,
        'structureCompleteness': structure_completeness,
        'hazardousSchemeTypeHints': hazardous_scheme_type_hints,
        **derived_type_flags,
    }
    refs = {
        'project.projectName': [project_name_ref] if project_name_ref else [],
        'project.projectCode': [project_code_ref] if project_code_ref else [],
        'project.location': [location_ref] if location_ref else [],
        'project.duplicateSections': [ref for title in duplicate_sections for ref in duplicate_map.get(title, [])],
        'project.specialEquipmentMentioned': special_equipment_blocks,
        'project.contextOnly': context_only_blocks,
        **section_presence_refs,
        **structure_refs,
        **type_hint_refs,
    }
    unresolved = []
    if weak_structure_duplicates:
        unresolved.append(
            {
                'code': 'weak_section_structure_signal',
                'factKey': 'project.duplicateSections',
                'summary': '关键章节或附件边界标题重复，canonical section extraction 不稳定，需人工复核章节归属。',
                'sourceExtractor': 'project_facts',
                'blockingReason': 'weak_section_structure_signal',
                'visibilityLimited': True,
            }
        )
    if not project_name:
        unresolved.append(
            {
                'code': 'missing_project_name',
                'factKey': 'project.projectName',
                'summary': '未解析到项目名称，需人工确认文档基础信息。',
                'sourceExtractor': 'project_facts',
                'blockingReason': 'parser_limited_source' if parse_result.parserLimited else 'missing_fact',
                'visibilityLimited': bool(parse_result.parserLimited),
            }
        )
    if not project_code:
        unresolved.append(
            {
                'code': 'missing_project_code',
                'factKey': 'project.projectCode',
                'summary': '未解析到项目编号，需人工确认文档标识信息。',
                'sourceExtractor': 'project_facts',
                'blockingReason': 'parser_limited_source' if parse_result.parserLimited else 'missing_fact',
                'visibilityLimited': bool(parse_result.parserLimited),
            }
        )
    if parse_result.parserLimited:
        for key, label in _SECTION_PRESENCE_LABELS.items():
            if section_presence.get(key):
                continue
            unresolved.append(
                {
                    'code': f'unresolved_section_presence_{key}',
                    'factKey': f'project.sectionPresence.{key}',
                    'summary': f'当前解析路径为 parser-limited，无法稳定确认“{label}”章节是否真实缺失。',
                    'sourceExtractor': 'project_facts',
                    'blockingReason': 'parser_limited_source',
                    'visibilityLimited': True,
                }
            )
    if weak_structure_refs:
        refs['project.duplicateSections'] = list(
            dict.fromkeys([*refs.get('project.duplicateSections', []), *weak_structure_refs])
        )
    return facts, refs, unresolved + structure_unresolved
