from __future__ import annotations

from src.review.rules.packs import get_policy_pack_registry


OFFICIAL_DOCUMENT_TYPES = {'construction_org', 'hazardous_special_scheme'}


def get_document_type_support_scope() -> list[dict[str, str]]:
    return [
        {
            'documentType': document_type,
            'readiness': 'official' if document_type in OFFICIAL_DOCUMENT_TYPES else 'skeleton',
        }
        for document_type in [
            'construction_org',
            'construction_scheme',
            'hazardous_special_scheme',
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
            'readiness': pack.readiness,
            'docTypes': pack.docTypes,
            'disciplineTags': pack.disciplineTags,
            'defaultEnabled': pack.defaultEnabled,
            'description': pack.description,
        }
        for pack in registry.values()
    ]


def get_support_scope_payload() -> dict[str, object]:
    return {
        'documentTypes': get_document_type_support_scope(),
        'packs': get_pack_support_scope(),
    }
