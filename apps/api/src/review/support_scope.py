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
    'construction_org': '施工组织设计审查',
    'construction_scheme': '一般施工方案审查',
    'hazardous_special_scheme': '危大工程专项施工方案',
    'distribution_network_special_scheme': '配电配网工程（停电施工专项）',
    'supervision_plan': '监理规划审查',
    'review_support_material': '审查辅助材料（边界说明）',
}

SPECIAL_SCHEME_CHILD_PACK_ORDER = {
    'hazardous_special_scheme': [
        'foundation_pit.base',
        'formwork_support.base',
        'lifting_installation_removal.base',
        'scaffold.base',
        'demolition.base',
        'underground_excavation.base',
        'curtain_wall_installation.base',
        'manual_bored_pile.base',
        'steel_structure_installation.base',
    ],
    'distribution_network_special_scheme': [
        'power_outage_work.base',
    ],
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
            'label': pack.label or pack.id,
            'readiness': pack.readiness,
            'docTypes': pack.docTypes,
            'disciplineTags': pack.disciplineTags,
            'defaultEnabled': pack.defaultEnabled,
            'description': pack.description,
            'promotionCriteria': pack.promotionCriteria,
            'entryKey': (
                'special_scheme_review'
                if pack.familyKey == 'hazardous_special_scheme'
                else 'general_management_review'
                if pack.familyKey == 'distribution_network_special_scheme'
                else 'general_management_review'
                if pack.id in {'temporary_power.base', 'hot_work.base', 'gas_area_ops.base'}
                else None
            ),
            'familyKey': pack.familyKey,
            'role': pack.role,
            'tier': pack.tier,
        }
        for pack in registry.values()
    ]


def get_special_scheme_capability_tree() -> list[dict[str, object]]:
    registry = get_policy_pack_registry()
    hazardous_families = []
    general_families = []
    for document_type in ['hazardous_special_scheme', 'distribution_network_special_scheme']:
        base_pack_id = f'{document_type}.base'
        base_pack = registry[base_pack_id]
        family_children = []
        for pack_id in SPECIAL_SCHEME_CHILD_PACK_ORDER.get(document_type, []):
            pack = registry.get(pack_id)
            if not pack or pack.familyKey != document_type or pack.role != 'third_level':
                continue
            family_children.append(
                {
                    'tag': pack.disciplineTags[0] if pack.disciplineTags else pack_id.replace('.base', ''),
                    'packId': pack.id,
                    'label': pack.label or pack.id,
                    'readiness': pack.readiness,
                    'promotionCriteria': pack.promotionCriteria,
                }
            )
        family_payload = (
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
        if document_type == 'hazardous_special_scheme':
            hazardous_families.append(family_payload)
        else:
            general_families.append(family_payload)

    cross_cutting_modules = []
    for pack in registry.values():
        if pack.role != 'cross_cutting':
            continue
        cross_cutting_modules.append(
            {
                'tag': pack.disciplineTags[0] if pack.disciplineTags else pack.id.replace('.base', ''),
                'packId': pack.id,
                'label': pack.label or pack.id,
                'readiness': pack.readiness,
                'docTypes': pack.docTypes,
                'promotionCriteria': pack.promotionCriteria,
            }
        )
    cross_cutting_modules.sort(key=lambda item: item['label'])

    return [
        {
            'entryKey': 'special_scheme_review',
            'label': '危大工程专项审查',
            'families': hazardous_families,
            'crossCuttingModules': cross_cutting_modules,
        },
        {
            'entryKey': 'general_management_review',
            'label': '一般专项与管理体系类审查',
            'families': general_families,
            'crossCuttingModules': cross_cutting_modules,
        },
    ]


def get_basis_mapping() -> dict[str, list[str]]:
    from src.review.basis_pack_resolver import BasisPackResolver
    from src.review.schema import ResolvedReviewProfile
    resolver = BasisPackResolver()
    
    mapping = {}
    for dt in ['construction_org', 'construction_scheme', 'hazardous_special_scheme', 'distribution_network_special_scheme', 'supervision_plan', 'review_support_material']:
        profile = ResolvedReviewProfile(documentType=dt, policyPackIds=[], disciplineTags=[], strictMode=False)
        resolved = resolver.resolve(profile)
        # Filter out internal engine policies to only show actual regulations/standards to users
        docs = [b.title for b in resolved.basis_documents if not b.basis_id.startswith('review-control-plane')]
        mapping[dt] = docs
    return mapping


def get_support_scope_payload() -> dict[str, object]:
    return {
        'documentTypes': get_document_type_support_scope(),
        'packs': get_pack_support_scope(),
        'capabilityTree': get_special_scheme_capability_tree(),
        'basisMapping': get_basis_mapping(),
    }
