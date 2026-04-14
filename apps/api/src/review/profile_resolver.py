"""
Profile Resolver: YAML-driven profile resolution.

The profile resolver maps (documentType, disciplineTags, review_intent, hints)
into a resolved profile using ONLY the YAML profile_mapping.yaml as the System of Record.

Hardcoded pack selection logic (select_policy_packs) has been REMOVED.
New review profiles should be added by editing profile_mapping.yaml, NOT by writing Python code.
"""

from __future__ import annotations

import logging
import yaml
from pathlib import Path
from typing import Any

from src.review.schema import ExtractedFacts, PolicyPack, ResolvedReviewProfile, StructuredReviewTask
from src.review.rules.packs import get_policy_pack_registry

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parents[4] / "config" / "review_basis"


def _load_profile_mapping() -> dict[str, Any]:
    """Load profile_mapping.yaml — the ONLY truth source for profile resolution."""
    path = CONFIG_DIR / "profile_mapping.yaml"
    if not path.exists():
        logger.error("[profile_resolver] profile_mapping.yaml not found at %s", path)
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_pack_registry() -> dict[str, Any]:
    """Load pack_registry.yaml to validate pack existence and readiness."""
    path = CONFIG_DIR / "pack_registry.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("packs", {})


def resolve_review_profile(
    structured_task: StructuredReviewTask,
    facts: ExtractedFacts,
    plan: dict[str, Any] | None = None,
) -> tuple[ResolvedReviewProfile, list[PolicyPack], list[PolicyPack]]:
    """Resolve the review profile from YAML configuration only.

    Returns:
        (resolved_profile, all_selected_packs, executable_packs)
    """
    plan_profile = dict((plan or {}).get('reviewProfile') or {})
    requested_discipline_tags = list(structured_task.disciplineTags or [])
    requested_policy_pack_ids = list(structured_task.policyPackIds or [])

    # 1. Determine document type
    document_type = _resolve_document_type(structured_task, facts, plan_profile)

    # 2. Normalize tags for document type
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

    # 3. Load YAML registries
    profile_mapping = _load_profile_mapping()
    pack_registry = _load_pack_registry()

    # 4. Look up the profile from YAML
    mapping = profile_mapping.get(document_type, {})
    profile_id = mapping.get('profile_id', document_type)

    # 5. Collect pack IDs from mapping + requested
    default_pack_ids = list(mapping.get('default_pack_ids') or [])
    required_pack_ids = list(mapping.get('required_pack_ids') or [])
    optional_pack_ids = list(mapping.get('optional_pack_ids') or [])
    enterprise_pack_ids = list(mapping.get('enterprise_pack_ids') or [])
    rule_pack_ids = list(mapping.get('rule_pack_ids') or [])

    # Normalize requested pack IDs
    requested_policy_pack_ids = _normalize_requested_pack_ids(document_type, requested_policy_pack_ids)

    # Merge all pack IDs (deduplicated, order-preserved)
    all_pack_ids = list(dict.fromkeys(
        default_pack_ids + required_pack_ids + requested_policy_pack_ids
    ))

    # 6. Build PolicyPack objects from pack_registry YAML data
    selected_packs: list[PolicyPack] = []
    
    python_registry = get_policy_pack_registry()
    
    for pack_id in all_pack_ids:
        pack_entry = pack_registry.get(pack_id)
        if pack_entry is None:
            logger.warning(
                "[profile_resolver] Pack '%s' referenced in profile '%s' but missing from pack_registry.yaml",
                pack_id, profile_id,
            )
            # Still include as a degraded/placeholder pack
            selected_packs.append(PolicyPack(
                id=pack_id,
                version='0.0.0',
                docTypes=[],
                label=pack_id,
                role=pack_entry.get('role', 'base') if pack_entry else 'base',
                readiness='placeholder',
                description=f'Pack {pack_id} is referenced but not found in pack_registry.yaml.',
            ))
            continue

        python_pack = python_registry.get(pack_id)
        target_rule_ids = python_pack.ruleIds if python_pack else []
        target_evidence_pack_ids = python_pack.evidencePackIds if python_pack else []

        selected_packs.append(PolicyPack(
            id=pack_id,
            version='1.0.0',
            docTypes=pack_entry.get('default_profiles', []),
            label=pack_entry.get('display_name', pack_id),
            role=pack_entry.get('role', 'base'),
            readiness='ready' if pack_entry.get('status') == 'active' else 'placeholder',
            description=pack_entry.get('display_name', ''),
            ruleIds=target_rule_ids,
            evidencePackIds=target_evidence_pack_ids,
        ))

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

    logger.info(
        "[profile_resolver] Resolved: profile=%s, doc_type=%s, packs=%s, rule_packs=%s",
        profile_id, document_type,
        [p.id for p in executable_packs],
        rule_pack_ids,
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
