from __future__ import annotations

PRIMARY_TEMPLATE_ID = 'structured_review_primary_worker'
PRIMARY_TEMPLATE_LEGACY_IDS = ('structure_completeness_reviewer',)
PRIMARY_TEMPLATE_IDS = (PRIMARY_TEMPLATE_ID, *PRIMARY_TEMPLATE_LEGACY_IDS)
PRIMARY_MODULE_ID = 'primary_support_review'
PRIMARY_MODULE_LEGACY_IDS = ('primary_review', 'structured_review_worker')
PRIMARY_MODULE_IDS = (PRIMARY_MODULE_ID, *PRIMARY_MODULE_LEGACY_IDS)


def normalize_template_id(template_id: str | None) -> str | None:
    if template_id in PRIMARY_TEMPLATE_IDS:
        return PRIMARY_TEMPLATE_ID
    return template_id


def normalize_module_id(module_id: str | None) -> str | None:
    if module_id in PRIMARY_MODULE_IDS:
        return PRIMARY_MODULE_ID
    return module_id


def is_primary_template_id(template_id: str | None) -> bool:
    return normalize_template_id(template_id) == PRIMARY_TEMPLATE_ID
