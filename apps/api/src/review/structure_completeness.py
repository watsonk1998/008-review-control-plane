from __future__ import annotations

from typing import Any


_MATCHABLE_SECTION_LEVEL = 4

_CONSTRUCTION_ORG_STRUCTURE_ITEMS: tuple[dict[str, Any], ...] = (
    {
        'itemKey': 'preparationBasis',
        'requirementLabel': '编制依据',
        'basisClause': '3.0.4',
        'basisRequirement': '施工组织设计应包括编制依据。',
        'primaryKeywords': ('编制依据', '编制说明'),
        'secondaryKeywords': (),
        'contentKeywords': ('编制依据', '编制说明'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 10,
    },
    {
        'itemKey': 'engineeringOverview',
        'requirementLabel': '工程概况',
        'basisClause': '3.0.4、5.1',
        'basisRequirement': '施工组织设计应包括工程概况，并说明工程主要情况、设计简介和施工条件。',
        'primaryKeywords': ('工程概况', '工程简介'),
        'secondaryKeywords': ('工程主要情况',),
        'contentKeywords': ('工程概况', '工程简介', '工程主要情况'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 20,
    },
    {
        'itemKey': 'constructionDeployment',
        'requirementLabel': '施工部署',
        'basisClause': '3.0.4、5.2',
        'basisRequirement': '施工组织设计应包括施工部署，并明确施工目标、施工顺序和总体安排。',
        'primaryKeywords': ('施工部署', '施工总部署', '施工安排'),
        'secondaryKeywords': ('施工阶段', '部署'),
        'contentKeywords': ('施工部署', '施工安排', '施工阶段', '总体安排'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 30,
    },
    {
        'itemKey': 'schedulePlan',
        'requirementLabel': '施工进度计划',
        'basisClause': '3.0.4、5.3',
        'basisRequirement': '施工组织设计应包括施工进度计划，并按施工部署编制。',
        'primaryKeywords': ('施工进度计划', '进度管理计划'),
        'secondaryKeywords': ('施工网络进度表', '网络进度表', '工期安排'),
        'contentKeywords': ('施工进度计划', '停电窗口', '工期安排', '进度安排', '网络进度表'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 40,
    },
    {
        'itemKey': 'resourcePlan',
        'requirementLabel': '施工准备与资源配置计划',
        'basisClause': '3.0.4、5.4',
        'basisRequirement': '施工组织设计应包括施工准备与资源配置计划，覆盖技术准备、现场准备、资金准备及资源配置。',
        'primaryKeywords': ('施工准备与资源配置计划', '资源配置计划', '资源管理计划'),
        'secondaryKeywords': ('施工准备', '施工劳动力安排', '劳动力安排', '机械设备计划', '机械设备', '劳动力计划'),
        'contentKeywords': ('资源配置', '施工准备', '劳动力', '机械设备', '机具', '材料'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 50,
    },
    {
        'itemKey': 'processMethod',
        'requirementLabel': '主要施工方案',
        'basisClause': '3.0.4、5.5',
        'basisRequirement': '施工组织设计应包括主要施工方案，对主要分部、分项工程及专项工程作出安排。',
        'primaryKeywords': ('主要施工方案', '施工方案'),
        'secondaryKeywords': ('施工方法', '施工工艺', '工艺流程'),
        'contentKeywords': ('施工方案', '施工方法', '施工工艺', '工艺流程'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 60,
    },
    {
        'itemKey': 'layoutPlan',
        'requirementLabel': '施工现场平面布置',
        'basisClause': '3.0.4、5.6',
        'basisRequirement': '施工组织设计应包括施工现场平面布置，并结合不同施工阶段进行绘制或说明。',
        'primaryKeywords': ('施工现场平面布置', '施工总平面布置', '施工平面布置', '施工平面管理计划'),
        'secondaryKeywords': ('平面布置',),
        'contentKeywords': ('平面布置', '总平面', '现场布置'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 70,
    },
    {
        'itemKey': 'progressManagementPlan',
        'requirementLabel': '进度管理计划',
        'basisClause': '7.1.1、7.2',
        'basisRequirement': '主要施工管理计划应包括进度管理计划，并明确分解目标、职责及控制措施。',
        'primaryKeywords': ('进度管理计划',),
        'secondaryKeywords': ('施工进度计划', '施工网络进度表', '网络进度表'),
        'contentKeywords': ('进度管理', '停电窗口', '进度计划'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 80,
    },
    {
        'itemKey': 'qualityManagementPlan',
        'requirementLabel': '质量管理计划',
        'basisClause': '7.1.1、7.3',
        'basisRequirement': '主要施工管理计划应包括质量管理计划，并明确质量目标、组织职责和保障措施。',
        'primaryKeywords': ('质量管理计划',),
        'secondaryKeywords': ('质量控制措施', '质量保证措施', '质量管理目标'),
        'contentKeywords': ('质量管理', '质量控制', '质量保证'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 90,
    },
    {
        'itemKey': 'safetyManagementPlan',
        'requirementLabel': '安全管理计划',
        'basisClause': '7.1.1、7.4',
        'basisRequirement': '主要施工管理计划应包括安全管理计划，并明确危险源、组织职责、控制措施和应急安排。',
        'primaryKeywords': ('安全管理计划',),
        'secondaryKeywords': ('安全保证措施', '安全管理措施', '专项安全措施', '施工用电安全'),
        'contentKeywords': ('安全管理', '安全措施', '危险源', '应急安排'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 100,
    },
    {
        'itemKey': 'environmentManagementPlan',
        'requirementLabel': '环境管理计划',
        'basisClause': '7.1.1、7.5',
        'basisRequirement': '主要施工管理计划应包括环境管理计划，并明确环境目标、组织职责和控制措施。',
        'primaryKeywords': ('环境管理计划',),
        'secondaryKeywords': ('文明施工措施', '环境因素控制措施'),
        'contentKeywords': ('环境管理', '文明施工', '环境因素'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 110,
    },
    {
        'itemKey': 'costManagementPlan',
        'requirementLabel': '成本管理计划',
        'basisClause': '7.1.1、7.6.1~7.6.2',
        'basisRequirement': '主要施工管理计划应包括成本管理计划，并以施工预算和施工进度计划为依据编制。',
        'primaryKeywords': ('成本管理计划',),
        'secondaryKeywords': ('成本控制', '成本目标', '成本预算', '成本核算'),
        'contentKeywords': ('成本管理', '成本控制', '成本预算'),
        'scope': 'common',
        'groupLabel': '施工组织设计通用要求',
        'displayOrder': 120,
    },
)

_SPECIAL_SCHEME_COMMON_ITEMS: tuple[dict[str, Any], ...] = (
    {
        'itemKey': 'specialEngineeringOverview',
        'requirementLabel': '工程概况',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现工程概况。',
        'primaryKeywords': ('工程概况', '工程简介'),
        'secondaryKeywords': (),
        'contentKeywords': ('工程概况', '工程简介'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 110,
    },
    {
        'itemKey': 'specialPreparationBasis',
        'requirementLabel': '编制依据',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现编制依据。',
        'primaryKeywords': ('编制依据', '编制说明'),
        'secondaryKeywords': (),
        'contentKeywords': ('编制依据', '编制说明'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 120,
    },
    {
        'itemKey': 'specialConstructionPlan',
        'requirementLabel': '施工计划',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现施工计划。',
        'primaryKeywords': ('施工计划', '施工安排'),
        'secondaryKeywords': ('施工部署',),
        'contentKeywords': ('施工计划', '施工安排', '停电窗口', '作业计划'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 130,
    },
    {
        'itemKey': 'specialProcessTechnology',
        'requirementLabel': '施工工艺技术',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现施工工艺技术。',
        'primaryKeywords': ('施工工艺技术',),
        'secondaryKeywords': ('施工工艺', '施工方法', '工艺流程'),
        'contentKeywords': ('施工工艺', '施工方法', '工艺流程', '作业流程'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 140,
    },
    {
        'itemKey': 'specialAssuranceMeasures',
        'requirementLabel': '施工保证措施',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现施工保证措施。',
        'primaryKeywords': ('施工保证措施', '安全保证措施'),
        'secondaryKeywords': ('保障措施', '控制措施'),
        'contentKeywords': ('保证措施', '保障措施', '控制措施'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 150,
    },
    {
        'itemKey': 'specialStaffingAndRoles',
        'requirementLabel': '施工管理及作业人员配备和分工',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现施工管理及作业人员配备和分工。',
        'primaryKeywords': ('施工管理及作业人员配备和分工',),
        'secondaryKeywords': ('人员配备', '岗位分工', '人员分工'),
        'contentKeywords': ('人员配备', '作业人员', '岗位分工', '职责分工'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 160,
    },
    {
        'itemKey': 'specialAcceptanceRequirements',
        'requirementLabel': '验收要求',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现验收要求。',
        'primaryKeywords': ('验收要求',),
        'secondaryKeywords': ('验收标准', '验收程序'),
        'contentKeywords': ('验收要求', '验收标准', '验收程序'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 170,
    },
    {
        'itemKey': 'specialEmergencyMeasures',
        'requirementLabel': '应急处置措施',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现应急处置措施。',
        'primaryKeywords': ('应急处置措施',),
        'secondaryKeywords': ('应急措施', '应急预案'),
        'contentKeywords': ('应急处置', '应急措施', '应急预案'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 180,
    },
    {
        'itemKey': 'specialDrawings',
        'requirementLabel': '相关施工图纸 / 节点详图 / 布置图',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现相关施工图纸、节点详图或布置图。',
        'primaryKeywords': ('施工图纸', '节点详图', '布置图'),
        'secondaryKeywords': ('附图', '图纸'),
        'contentKeywords': ('图纸', '附图', '节点详图', '布置图'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 190,
    },
    {
        'itemKey': 'specialRiskIdentification',
        'requirementLabel': '风险辨识与分级',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现风险辨识与分级。',
        'primaryKeywords': ('风险辨识与分级',),
        'secondaryKeywords': ('风险辨识', '风险分级'),
        'contentKeywords': ('风险辨识', '风险分级', '主要风险'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 200,
    },
    {
        'itemKey': 'specialLayoutEnvironment',
        'requirementLabel': '施工平面布置或周边环境条件',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现施工平面布置或周边环境条件。',
        'primaryKeywords': ('施工平面布置', '周边环境条件'),
        'secondaryKeywords': ('平面布置', '周边环境'),
        'contentKeywords': ('平面布置', '周边环境', '作业边界', '施工现场'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 210,
    },
    {
        'itemKey': 'specialCalculationEvidence',
        'requirementLabel': '计算书及相关验算依据',
        'basisClause': '专项施工方案通用要求',
        'basisRequirement': '专项施工方案应体现计算书及相关验算依据。',
        'primaryKeywords': ('计算书', '验算依据'),
        'secondaryKeywords': ('验算书', '计算依据'),
        'contentKeywords': ('计算书', '验算', '计算依据'),
        'scope': 'common',
        'groupLabel': '专项施工方案通用要求',
        'displayOrder': 220,
    },
)


_FOUNDATION_PIT_SPECIAL_ITEMS: tuple[dict[str, Any], ...] = (
    {
        'itemKey': 'foundationPitSupportSequence',
        'requirementLabel': '支护、降水、开挖及加撑关系',
        'basisClause': '基坑工程专项补充要求',
        'basisRequirement': '基坑工程应明确支护、降水、开挖及加撑关系。',
        'primaryKeywords': ('支护、降水、开挖及加撑关系',),
        'secondaryKeywords': ('支护', '降水', '开挖', '加撑'),
        'contentKeywords': ('支护', '降水', '开挖', '加撑', '土方开挖'),
        'scope': 'special',
        'groupLabel': '基坑工程专项要求',
        'displayOrder': 10,
    },
    {
        'itemKey': 'foundationPitMonitoring',
        'requirementLabel': '监测监控措施',
        'basisClause': '基坑工程专项补充要求',
        'basisRequirement': '基坑工程应明确监测监控措施。',
        'primaryKeywords': ('监测监控措施',),
        'secondaryKeywords': ('监测监控', '监测措施', '监测方案'),
        'contentKeywords': ('监测监控', '监测措施', '监测方案', '监测点'),
        'scope': 'special',
        'groupLabel': '基坑工程专项要求',
        'displayOrder': 20,
    },
    {
        'itemKey': 'foundationPitEnvironmentDrawings',
        'requirementLabel': '周边环境与监测点相关图纸',
        'basisClause': '基坑工程专项补充要求',
        'basisRequirement': '基坑工程应附周边环境与监测点相关图纸。',
        'primaryKeywords': ('周边环境与监测点相关图纸',),
        'secondaryKeywords': ('周边环境', '监测点', '相关图纸'),
        'contentKeywords': ('周边环境', '监测点', '图纸', '附图'),
        'scope': 'special',
        'groupLabel': '基坑工程专项要求',
        'displayOrder': 30,
    },
    {
        'itemKey': 'foundationPitAcceptance',
        'requirementLabel': '验收要求',
        'basisClause': '基坑工程专项补充要求',
        'basisRequirement': '基坑工程应明确验收要求。',
        'primaryKeywords': ('验收要求',),
        'secondaryKeywords': ('验收标准', '验收程序'),
        'contentKeywords': ('验收要求', '验收标准', '验收程序', '位移', '沉降', '轴力'),
        'scope': 'special',
        'groupLabel': '基坑工程专项要求',
        'displayOrder': 40,
    },
)

_FORMWORK_SUPPORT_SPECIAL_ITEMS: tuple[dict[str, Any], ...] = (
    {
        'itemKey': 'formworkSupportParameters',
        'requirementLabel': '技术参数',
        'basisClause': '模板支撑体系专项补充要求',
        'basisRequirement': '模板支撑体系应明确技术参数。',
        'primaryKeywords': ('技术参数',),
        'secondaryKeywords': ('参数', '设计参数'),
        'contentKeywords': ('技术参数', '参数', '设计参数', '立杆', '步距'),
        'scope': 'special',
        'groupLabel': '模板支撑体系专项要求',
        'displayOrder': 10,
    },
    {
        'itemKey': 'formworkSupportProcessFlow',
        'requirementLabel': '工艺流程 / 浇筑顺序',
        'basisClause': '模板支撑体系专项补充要求',
        'basisRequirement': '模板支撑体系应明确工艺流程及浇筑顺序。',
        'primaryKeywords': ('工艺流程', '浇筑顺序'),
        'secondaryKeywords': ('施工流程', '工艺顺序', '浇筑方式'),
        'contentKeywords': ('工艺流程', '浇筑顺序', '施工流程', '预压', '混凝土浇筑'),
        'scope': 'special',
        'groupLabel': '模板支撑体系专项要求',
        'displayOrder': 20,
    },
    {
        'itemKey': 'formworkSupportCalculation',
        'requirementLabel': '计算依据',
        'basisClause': '模板支撑体系专项补充要求',
        'basisRequirement': '模板支撑体系应明确计算依据。',
        'primaryKeywords': ('计算依据', '计算书'),
        'secondaryKeywords': ('验算依据', '验算书'),
        'contentKeywords': ('计算依据', '计算书', '验算', '承载力', '稳定性'),
        'scope': 'special',
        'groupLabel': '模板支撑体系专项要求',
        'displayOrder': 30,
    },
    {
        'itemKey': 'formworkSupportAcceptance',
        'requirementLabel': '验收要求',
        'basisClause': '模板支撑体系专项补充要求',
        'basisRequirement': '模板支撑体系应明确验收要求。',
        'primaryKeywords': ('验收要求',),
        'secondaryKeywords': ('验收标准', '验收程序'),
        'contentKeywords': ('验收要求', '验收标准', '验收程序'),
        'scope': 'special',
        'groupLabel': '模板支撑体系专项要求',
        'displayOrder': 40,
    },
)

_STEEL_STRUCTURE_INSTALLATION_SPECIAL_ITEMS: tuple[dict[str, Any], ...] = (
    {
        'itemKey': 'steelStructureComponentParameters',
        'requirementLabel': '构件参数',
        'basisClause': '钢结构安装专项补充要求',
        'basisRequirement': '钢结构安装应明确构件参数。',
        'primaryKeywords': ('构件参数',),
        'secondaryKeywords': ('构件', '构件信息'),
        'contentKeywords': ('构件参数', '构件信息', '构件重量', '构件尺寸'),
        'scope': 'special',
        'groupLabel': '钢结构安装专项要求',
        'displayOrder': 10,
    },
    {
        'itemKey': 'steelStructureLiftingEquipment',
        'requirementLabel': '吊装设备选型',
        'basisClause': '钢结构安装专项补充要求',
        'basisRequirement': '钢结构安装应明确吊装设备选型。',
        'primaryKeywords': ('吊装设备选型',),
        'secondaryKeywords': ('设备选型', '吊装设备'),
        'contentKeywords': ('吊装设备', '设备选型', '起重机', '吊车', '汽车吊'),
        'scope': 'special',
        'groupLabel': '钢结构安装专项要求',
        'displayOrder': 20,
    },
    {
        'itemKey': 'steelStructureInstallationProcess',
        'requirementLabel': '安装流程',
        'basisClause': '钢结构安装专项补充要求',
        'basisRequirement': '钢结构安装应明确安装流程。',
        'primaryKeywords': ('安装流程',),
        'secondaryKeywords': ('安装顺序', '施工流程'),
        'contentKeywords': ('安装流程', '安装顺序', '施工流程', '吊装流程'),
        'scope': 'special',
        'groupLabel': '钢结构安装专项要求',
        'displayOrder': 30,
    },
    {
        'itemKey': 'steelStructureSupportUnloading',
        'requirementLabel': '拼装胎架 / 临时支撑 / 卸载条件',
        'basisClause': '钢结构安装专项补充要求',
        'basisRequirement': '钢结构安装应明确拼装胎架、临时支撑及卸载条件。',
        'primaryKeywords': ('拼装胎架', '临时支撑', '卸载条件'),
        'secondaryKeywords': ('胎架', '支撑', '卸载'),
        'contentKeywords': ('拼装胎架', '临时支撑', '卸载条件', '胎架', '支撑'),
        'scope': 'special',
        'groupLabel': '钢结构安装专项要求',
        'displayOrder': 40,
    },
    {
        'itemKey': 'steelStructureDrawingsAcceptance',
        'requirementLabel': '措施图纸及验收章节',
        'basisClause': '钢结构安装专项补充要求',
        'basisRequirement': '钢结构安装应明确措施图纸及验收章节。',
        'primaryKeywords': ('措施图纸', '验收章节'),
        'secondaryKeywords': ('图纸', '验收要求'),
        'contentKeywords': ('措施图纸', '图纸', '验收章节', '验收要求'),
        'scope': 'special',
        'groupLabel': '钢结构安装专项要求',
        'displayOrder': 50,
    },
)

_POWER_OUTAGE_WORK_SPECIAL_ITEMS: tuple[dict[str, Any], ...] = (
    {
        'itemKey': 'powerOutageScope',
        'requirementLabel': '停电范围',
        'basisClause': '停电施工作业专项补充要求',
        'basisRequirement': '停电施工作业应明确停电范围。',
        'primaryKeywords': ('停电范围',),
        'secondaryKeywords': ('停电线路', '停电区域'),
        'contentKeywords': ('停电范围', '停电线路', '停电区域', '停电设备'),
        'scope': 'special',
        'groupLabel': '停电施工作业专项要求',
        'displayOrder': 10,
    },
    {
        'itemKey': 'powerOutageWorkContent',
        'requirementLabel': '作业内容',
        'basisClause': '停电施工作业专项补充要求',
        'basisRequirement': '停电施工作业应明确作业内容。',
        'primaryKeywords': ('作业内容',),
        'secondaryKeywords': ('施工内容', '工作内容'),
        'contentKeywords': ('作业内容', '施工内容', '工作内容', '停送电作业流程'),
        'scope': 'special',
        'groupLabel': '停电施工作业专项要求',
        'displayOrder': 20,
    },
    {
        'itemKey': 'powerOutageMajorRisk',
        'requirementLabel': '主要风险',
        'basisClause': '停电施工作业专项补充要求',
        'basisRequirement': '停电施工作业应明确主要风险。',
        'primaryKeywords': ('主要风险',),
        'secondaryKeywords': ('风险分析', '风险辨识'),
        'contentKeywords': ('主要风险', '风险分析', '风险辨识', '触电'),
        'scope': 'special',
        'groupLabel': '停电施工作业专项要求',
        'displayOrder': 30,
    },
    {
        'itemKey': 'powerOutageStaffing',
        'requirementLabel': '施工人员',
        'basisClause': '停电施工作业专项补充要求',
        'basisRequirement': '停电施工作业应明确施工人员。',
        'primaryKeywords': ('施工人员',),
        'secondaryKeywords': ('作业人员', '人员安排'),
        'contentKeywords': ('施工人员', '作业人员', '人员安排', '工作负责人'),
        'scope': 'special',
        'groupLabel': '停电施工作业专项要求',
        'displayOrder': 40,
    },
    {
        'itemKey': 'powerOutageEquipment',
        'requirementLabel': '机具',
        'basisClause': '停电施工作业专项补充要求',
        'basisRequirement': '停电施工作业应明确机具。',
        'primaryKeywords': ('机具',),
        'secondaryKeywords': ('施工机具', '机械设备'),
        'contentKeywords': ('机具', '施工机具', '机械设备', '工器具'),
        'scope': 'special',
        'groupLabel': '停电施工作业专项要求',
        'displayOrder': 50,
    },
    {
        'itemKey': 'powerOutageMaterials',
        'requirementLabel': '材料',
        'basisClause': '停电施工作业专项补充要求',
        'basisRequirement': '停电施工作业应明确材料。',
        'primaryKeywords': ('材料',),
        'secondaryKeywords': ('主要材料',),
        'contentKeywords': ('材料', '主要材料', '备品备件'),
        'scope': 'special',
        'groupLabel': '停电施工作业专项要求',
        'displayOrder': 60,
    },
    {
        'itemKey': 'powerOutageSafetyControl',
        'requirementLabel': '安全管控',
        'basisClause': '停电施工作业专项补充要求',
        'basisRequirement': '停电施工作业应明确安全管控。',
        'primaryKeywords': ('安全管控',),
        'secondaryKeywords': ('安全措施', '安全控制'),
        'contentKeywords': ('安全管控', '安全措施', '安全控制', '停电安全措施'),
        'scope': 'special',
        'groupLabel': '停电施工作业专项要求',
        'displayOrder': 70,
    },
    {
        'itemKey': 'powerOutageQualityControl',
        'requirementLabel': '质量管控',
        'basisClause': '停电施工作业专项补充要求',
        'basisRequirement': '停电施工作业应明确质量管控。',
        'primaryKeywords': ('质量管控',),
        'secondaryKeywords': ('质量控制', '质量措施'),
        'contentKeywords': ('质量管控', '质量控制', '质量措施'),
        'scope': 'special',
        'groupLabel': '停电施工作业专项要求',
        'displayOrder': 80,
    },
    {
        'itemKey': 'powerOutageEmergencyMeasures',
        'requirementLabel': '应急措施',
        'basisClause': '停电施工作业专项补充要求',
        'basisRequirement': '停电施工作业应明确应急措施。',
        'primaryKeywords': ('应急措施',),
        'secondaryKeywords': ('应急处置', '应急预案'),
        'contentKeywords': ('应急措施', '应急处置', '应急预案', '触电应急'),
        'scope': 'special',
        'groupLabel': '停电施工作业专项要求',
        'displayOrder': 90,
    },
)


def _section_match_score(title: str, *, primary_keywords: tuple[str, ...], secondary_keywords: tuple[str, ...]) -> tuple[int, str | None]:
    for keyword in primary_keywords:
        if keyword and keyword in title:
            return 2, keyword
    for keyword in secondary_keywords:
        if keyword and keyword in title:
            return 1, keyword
    return 0, None


def _section_content_index(parse_result) -> dict[str, str]:
    index: dict[str, list[str]] = {}
    for block in parse_result.blocks:
        section_id = str(block.get('sectionId') or '')
        text = str(block.get('text') or '').strip()
        if not section_id or not text:
            continue
        index.setdefault(section_id, []).append(text)
    return {key: ' '.join(values) for key, values in index.items()}


def _select_matches(
    parse_result,
    *,
    primary_keywords: tuple[str, ...],
    secondary_keywords: tuple[str, ...],
    content_keywords: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    section_content = _section_content_index(parse_result)
    primary: list[dict[str, Any]] = []
    secondary: list[dict[str, Any]] = []
    for section in parse_result.sections:
        title = str(section.get('title') or '')
        if not title:
            continue
        level = int(section.get('level', 99) or 99)
        if level > _MATCHABLE_SECTION_LEVEL:
            continue
        score, matched_keyword = _section_match_score(
            title,
            primary_keywords=primary_keywords,
            secondary_keywords=secondary_keywords,
        )
        section_id = str(section.get('id') or '')
        content_text = section_content.get(section_id, '')
        content_match = next((keyword for keyword in content_keywords if keyword and keyword in content_text), None)
        if score == 0 and not content_match:
            continue
        section_copy = {
            'sectionId': section.get('id'),
            'blockId': section.get('blockId'),
            'title': title,
            'position': section.get('position'),
            'level': level,
            'matchedKeyword': matched_keyword or content_match,
        }
        if score == 2 and level <= 3:
            primary.append(section_copy)
        else:
            secondary.append(section_copy)
    primary.sort(key=lambda item: (item.get('level', 99), item.get('position', 10**9), item['title']))
    secondary.sort(key=lambda item: (item.get('level', 99), item.get('position', 10**9), item['title']))
    return primary[:3], secondary[:3]


def _report_excerpt(label: str, status: str, matches: list[dict[str, Any]]) -> str:
    matched_titles = '、'.join(item['title'] for item in matches[:2])
    if status == 'matched':
        return f'已识别到“{matched_titles}”等内容，可支撑“{label}”结构审查。'
    if status == 'partial':
        return f'已识别到与“{label}”相关的内容信号，但结构呈现仍不完整。'
    if status == 'blocked_by_visibility':
        return f'当前解析受限，未能稳定确认“{label}”是否完整存在，需结合原件人工复核。'
    return f'当前未识别到可稳定对应“{label}”的章节或内容信号。'


def _analysis_text(label: str, status: str, matches: list[dict[str, Any]], *, parser_limited: bool) -> str:
    matched_titles = '、'.join(item['title'] for item in matches[:3])
    if status == 'matched':
        return f'命中章节：{matched_titles}。'
    if status == 'partial':
        return f'已识别到局部相关章节或内容信号：{matched_titles}；建议补齐或单列“{label}”。'
    if status == 'blocked_by_visibility':
        reason = '当前为受限解析路径' if parser_limited else '章节信号不足'
        return f'{reason}，尚不能稳定判断“{label}”是否真实缺失。'
    return f'当前正文中未识别到可稳定映射“{label}”的章节标题或内容信号。'


def _build_structure_rows(parse_result, specs: tuple[dict[str, Any], ...]) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    refs: dict[str, list[str]] = {}
    unresolved: list[dict[str, Any]] = []
    parser_limited = bool(parse_result.parserLimited)
    for spec in specs:
        primary_matches, secondary_matches = _select_matches(
            parse_result,
            primary_keywords=spec['primaryKeywords'],
            secondary_keywords=spec['secondaryKeywords'],
            content_keywords=spec.get('contentKeywords') or spec['secondaryKeywords'] or spec['primaryKeywords'],
        )
        matched_sections = primary_matches or secondary_matches
        if primary_matches:
            status = 'matched'
        elif secondary_matches:
            status = 'partial'
        elif parser_limited:
            status = 'blocked_by_visibility'
        else:
            status = 'missing'
        fact_key = f'project.structureCompleteness.{spec["itemKey"]}'
        refs[fact_key] = [str(item['blockId']) for item in matched_sections if item.get('blockId')]
        if parser_limited and status != 'matched':
            unresolved.append(
                {
                    'code': f'unresolved_structure_completeness_{spec["itemKey"]}',
                    'factKey': fact_key,
                    'summary': f'当前解析路径受限，无法稳定确认“{spec["requirementLabel"]}”是否真实缺失。',
                    'sourceExtractor': 'project_facts',
                    'blockingReason': 'parser_limited_source',
                    'visibilityLimited': True,
                }
            )
        rows.append(
            {
                'itemKey': spec['itemKey'],
                'requirementLabel': spec['requirementLabel'],
                'basisClause': spec['basisClause'],
                'basisRequirement': spec['basisRequirement'],
                'status': status,
                'matchedSections': [
                    {
                        'sectionId': item.get('sectionId'),
                        'blockId': item.get('blockId'),
                        'title': item['title'],
                        'position': item.get('position'),
                        'level': item.get('level'),
                    }
                    for item in matched_sections
                ],
                'analysis': _analysis_text(
                    spec['requirementLabel'],
                    status,
                    matched_sections,
                    parser_limited=parser_limited,
                ),
                'reportExcerpt': _report_excerpt(spec['requirementLabel'], status, matched_sections),
                'scope': spec['scope'],
                'displayOrder': spec['displayOrder'],
                'groupLabel': spec.get('groupLabel'),
            }
        )
    rows.sort(key=lambda item: (0 if item.get('scope') == 'special' else 1, item.get('displayOrder', 9999), item['requirementLabel']))
    return rows, refs, unresolved


def build_construction_org_structure_matrix(parse_result) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]]]:
    return _build_structure_rows(parse_result, _CONSTRUCTION_ORG_STRUCTURE_ITEMS)


def build_special_scheme_structure_matrix(
    parse_result,
    *,
    document_type: str,
    selected_pack_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]]]:
    selected_pack_ids = selected_pack_ids or set()
    specs: list[dict[str, Any]] = []
    hazardous_special_pack_specs: tuple[tuple[str, tuple[dict[str, Any], ...]], ...] = (
        ('foundation_pit.base', _FOUNDATION_PIT_SPECIAL_ITEMS),
        ('formwork_support.base', _FORMWORK_SUPPORT_SPECIAL_ITEMS),
        ('steel_structure_installation.base', _STEEL_STRUCTURE_INSTALLATION_SPECIAL_ITEMS),
    )
    if document_type == 'hazardous_special_scheme':
        for pack_id, pack_specs in hazardous_special_pack_specs:
            if pack_id in selected_pack_ids:
                specs.extend(pack_specs)
                specs.extend(_SPECIAL_SCHEME_COMMON_ITEMS)
                break
    if document_type == 'distribution_network_special_scheme' and 'power_outage_work.base' in selected_pack_ids:
        specs.extend(_POWER_OUTAGE_WORK_SPECIAL_ITEMS)
        specs.extend(_SPECIAL_SCHEME_COMMON_ITEMS)
    if not specs:
        return [], {}, []
    return _build_structure_rows(parse_result, tuple(specs))


def build_structure_completeness_matrix(
    parse_result,
    *,
    document_type: str,
    selected_pack_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]]]:
    if document_type == 'construction_org':
        return build_construction_org_structure_matrix(parse_result)
    return build_special_scheme_structure_matrix(
        parse_result,
        document_type=document_type,
        selected_pack_ids=selected_pack_ids,
    )
