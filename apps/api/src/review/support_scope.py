from __future__ import annotations

from src.review.rules.packs import get_policy_pack_registry


OFFICIAL_DOCUMENT_TYPES = {'construction_org', 'hazardous_special_scheme'}
EXPERIMENTAL_DOCUMENT_TYPES = {
    'construction_scheme',
    'distribution_network_special_scheme',
    'supervision_plan',
    'review_support_material',
}

DOCUMENT_TYPE_LABELS = {
    'construction_org': '施工组织设计',
    'construction_scheme': '一般施工方案',
    'hazardous_special_scheme': '危大工程专项施工方案',
    'distribution_network_special_scheme': '配网工程专项施工方案',
    'supervision_plan': '监理规划',
    'review_support_material': '审查辅助材料',
}

PACK_PRODUCT_META = {
    'hazardous_special_scheme.base': {
        'label': '危大工程专项施工方案',
        'entryKey': 'special_scheme_review',
        'familyKey': 'hazardous_special_scheme',
        'role': 'base',
        'tier': 2,
    },
    'distribution_network_special_scheme.base': {
        'label': '配网工程专项施工方案',
        'entryKey': 'special_scheme_review',
        'familyKey': 'distribution_network_special_scheme',
        'role': 'base',
        'tier': 2,
    },
    'foundation_pit.base': {'label': '基坑工程', 'entryKey': 'special_scheme_review', 'familyKey': 'hazardous_special_scheme', 'role': 'third_level', 'tier': 3},
    'formwork_support.base': {'label': '模板支撑体系', 'entryKey': 'special_scheme_review', 'familyKey': 'hazardous_special_scheme', 'role': 'third_level', 'tier': 3},
    'lifting_installation_removal.base': {'label': '起重吊装及安装拆卸', 'entryKey': 'special_scheme_review', 'familyKey': 'hazardous_special_scheme', 'role': 'third_level', 'tier': 3},
    'scaffold.base': {'label': '脚手架工程', 'entryKey': 'special_scheme_review', 'familyKey': 'hazardous_special_scheme', 'role': 'third_level', 'tier': 3},
    'demolition.base': {'label': '拆除工程', 'entryKey': 'special_scheme_review', 'familyKey': 'hazardous_special_scheme', 'role': 'third_level', 'tier': 3},
    'underground_excavation.base': {'label': '暗挖工程', 'entryKey': 'special_scheme_review', 'familyKey': 'hazardous_special_scheme', 'role': 'third_level', 'tier': 3},
    'curtain_wall_installation.base': {'label': '建筑幕墙安装', 'entryKey': 'special_scheme_review', 'familyKey': 'hazardous_special_scheme', 'role': 'third_level', 'tier': 3},
    'manual_bored_pile.base': {'label': '人工挖孔桩', 'entryKey': 'special_scheme_review', 'familyKey': 'hazardous_special_scheme', 'role': 'third_level', 'tier': 3},
    'steel_structure_installation.base': {'label': '钢结构安装', 'entryKey': 'special_scheme_review', 'familyKey': 'hazardous_special_scheme', 'role': 'third_level', 'tier': 3},
    'power_outage_work.base': {'label': '停电施工作业', 'entryKey': 'special_scheme_review', 'familyKey': 'distribution_network_special_scheme', 'role': 'third_level', 'tier': 3},
    'temporary_power.base': {'label': '临时用电 / 停送电', 'entryKey': 'special_scheme_review', 'role': 'cross_cutting', 'tier': None},
    'hot_work.base': {'label': '动火作业', 'entryKey': 'special_scheme_review', 'role': 'cross_cutting', 'tier': None},
    'gas_area_ops.base': {'label': '煤气区域', 'entryKey': 'special_scheme_review', 'role': 'cross_cutting', 'tier': None},
    'lifting_operations.base': {'label': '起重吊装（横向风险）', 'entryKey': 'special_scheme_review', 'role': 'cross_cutting', 'tier': None},
}


def get_document_type_readiness(document_type: str | None) -> str:
    if not document_type:
        return 'skeleton'
    if document_type in OFFICIAL_DOCUMENT_TYPES:
        return 'official'
    if document_type in EXPERIMENTAL_DOCUMENT_TYPES:
        return 'experimental'
    return 'skeleton'


def get_document_type_support_scope() -> list[dict[str, str]]:
    return [
        {
            'documentType': document_type,
            'label': DOCUMENT_TYPE_LABELS.get(document_type, document_type),
            'readiness': get_document_type_readiness(document_type),
        }
        for document_type in [
            'construction_org',
            'construction_scheme',
            'hazardous_special_scheme',
            'distribution_network_special_scheme',
            'supervision_plan',
            'review_support_material',
        ]
    ]


def is_official_document_type(document_type: str | None) -> bool:
    return bool(document_type and document_type in OFFICIAL_DOCUMENT_TYPES)


def get_pack_support_scope() -> list[dict[str, object]]:
    registry = get_policy_pack_registry()
    return [
        {
            'packId': pack.id,
            'label': PACK_PRODUCT_META.get(pack.id, {}).get('label', pack.id),
            'readiness': pack.readiness,
            'docTypes': pack.docTypes,
            'disciplineTags': pack.disciplineTags,
            'defaultEnabled': pack.defaultEnabled,
            'description': pack.description,
            'promotionCriteria': pack.promotionCriteria,
            'entryKey': PACK_PRODUCT_META.get(pack.id, {}).get('entryKey'),
            'familyKey': PACK_PRODUCT_META.get(pack.id, {}).get('familyKey'),
            'role': PACK_PRODUCT_META.get(pack.id, {}).get('role'),
            'tier': PACK_PRODUCT_META.get(pack.id, {}).get('tier'),
        }
        for pack in registry.values()
    ]


def get_special_scheme_capability_tree() -> list[dict[str, object]]:
    registry = get_policy_pack_registry()
    families = []
    for document_type in ['hazardous_special_scheme', 'distribution_network_special_scheme']:
        base_pack_id = f'{document_type}.base'
        base_pack = registry[base_pack_id]
        family_children = []
        for pack_id, meta in PACK_PRODUCT_META.items():
            if meta.get('familyKey') != document_type or meta.get('role') != 'third_level':
                continue
            pack = registry.get(pack_id)
            if not pack:
                continue
            family_children.append(
                {
                    'tag': pack.disciplineTags[0] if pack.disciplineTags else pack_id.replace('.base', ''),
                    'packId': pack.id,
                    'label': meta['label'],
                    'readiness': pack.readiness,
                    'promotionCriteria': pack.promotionCriteria,
                }
            )
        families.append(
            {
                'familyKey': document_type,
                'documentType': document_type,
                'label': DOCUMENT_TYPE_LABELS.get(document_type, document_type),
                'readiness': get_document_type_readiness(document_type),
                'basePackId': base_pack.id,
                'basePackReadiness': base_pack.readiness,
                'children': family_children,
            }
        )

    cross_cutting_modules = []
    for pack_id, meta in PACK_PRODUCT_META.items():
        if meta.get('role') != 'cross_cutting':
            continue
        pack = registry.get(pack_id)
        if not pack:
            continue
        cross_cutting_modules.append(
            {
                'tag': pack.disciplineTags[0] if pack.disciplineTags else pack_id.replace('.base', ''),
                'packId': pack.id,
                'label': meta['label'],
                'readiness': pack.readiness,
                'docTypes': pack.docTypes,
                'promotionCriteria': pack.promotionCriteria,
            }
        )

    return [
        {
            'entryKey': 'special_scheme_review',
            'label': '专项方案审查',
            'families': families,
            'crossCuttingModules': cross_cutting_modules,
        }
    ]


def get_support_scope_payload() -> dict[str, object]:
    return {
        'documentTypes': get_document_type_support_scope(),
        'packs': get_pack_support_scope(),
        'capabilityTree': get_special_scheme_capability_tree(),
    }
