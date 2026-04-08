from __future__ import annotations

from typing import Any

from src.review.rules.packs import select_policy_packs
from src.review.schema import ExtractedFacts, PolicyPack, ResolvedReviewProfile, StructuredReviewTask


def resolve_review_profile(
    structured_task: StructuredReviewTask,
    facts: ExtractedFacts,
    plan: dict[str, Any] | None = None,
) -> tuple[ResolvedReviewProfile, list[PolicyPack], list[PolicyPack]]:
    plan_profile = dict((plan or {}).get('reviewProfile') or {})
    requested_discipline_tags = list(structured_task.disciplineTags or [])
    requested_policy_pack_ids = list(structured_task.policyPackIds or [])
    document_type = _resolve_document_type(structured_task, facts, plan_profile)
    requested_policy_pack_ids = _normalize_requested_pack_ids(document_type, requested_policy_pack_ids)
    discipline_tags = list(
        dict.fromkeys(
            [
                *requested_discipline_tags,
                *_infer_discipline_tags(facts),
                *(plan_profile.get('disciplineTagHints') or []),
            ]
        )
    )
    discipline_tags = _normalize_hazardous_type_tags(document_type, discipline_tags)
    selected_packs = select_policy_packs(
        document_type,
        discipline_tags,
        requested_pack_ids=requested_policy_pack_ids,
    )
    executable_packs = [pack for pack in selected_packs if pack.readiness == 'ready']
    resolved_profile = ResolvedReviewProfile(
        requestedDocumentType=plan_profile.get('requestedDocumentType') or structured_task.documentType,
        requestedDisciplineTags=requested_discipline_tags,
        requestedPolicyPackIds=requested_policy_pack_ids,
        documentType=document_type,
        disciplineTags=discipline_tags,
        policyPackIds=[pack.id for pack in executable_packs],
        strictMode=structured_task.strictMode,
    )
    return resolved_profile, selected_packs, executable_packs


def _resolve_document_type(
    structured_task: StructuredReviewTask,
    facts: ExtractedFacts,
    plan_profile: dict[str, Any],
) -> str:
    return (
        structured_task.documentType
        or facts.projectFacts.get('documentTypeHint')
        or plan_profile.get('documentTypeHint')
        or 'construction_org'
    )


def _infer_discipline_tags(facts: ExtractedFacts) -> list[str]:
    tags: list[str] = []
    if facts.hazardFacts.get('liftingOperation'):
        tags.append('lifting_operations')
    if facts.hazardFacts.get('temporaryPower'):
        tags.append('temporary_power')
    if facts.hazardFacts.get('hotWork'):
        tags.append('hot_work')
    if facts.hazardFacts.get('gasArea'):
        tags.append('gas_area_ops')
    if facts.projectFacts.get('specialEquipmentMentioned'):
        tags.append('special_equipment')
    if 'working_at_height' in (facts.hazardFacts.get('highRiskCategories') or []):
        tags.append('working_at_height')
    for tag in facts.projectFacts.get('hazardousSchemeTypeHints') or []:
        if tag not in tags:
            tags.append(tag)
    return tags


def _normalize_hazardous_type_tags(document_type: str, discipline_tags: list[str]) -> list[str]:
    tags = list(discipline_tags)
    normalized: list[str] = []
    for tag in tags:
        mapped = tag
        if document_type == 'hazardous_special_scheme' and tag == 'lifting_operations':
            mapped = 'lifting_installation_removal'
        if document_type == 'distribution_network_special_scheme' and tag == 'temporary_power':
            mapped = 'power_outage_work'
        if mapped not in normalized:
            normalized.append(mapped)
    return normalized


def _normalize_requested_pack_ids(document_type: str, requested_pack_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    for pack_id in requested_pack_ids:
        mapped = pack_id
        if document_type == 'hazardous_special_scheme' and pack_id == 'lifting_operations.base':
            mapped = 'lifting_installation_removal.base'
        if document_type == 'distribution_network_special_scheme' and pack_id == 'temporary_power.base':
            mapped = 'power_outage_work.base'
        if mapped not in normalized:
            normalized.append(mapped)
    return normalized
