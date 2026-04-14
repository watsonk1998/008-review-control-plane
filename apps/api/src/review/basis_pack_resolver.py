"""
BasisPackResolver: Resolves basis documents by following the chain:

    profile → pack_ids → rule_pack_ids → basis_ids → concrete basis metadata

Operates strictly off the YAML configuration registries (System of Record).
Does NOT scan all basis documents — only loads those linked through the
resolved packs and rule packs for the given profile.

FORBIDDEN:
- Full-scan of basis_registry
- Fallback to "give Hermes everything"
- Silent swallowing of missing packs/basis/rule packs
"""

from __future__ import annotations

import logging
import yaml
from pathlib import Path
from pydantic import BaseModel
from typing import Any

from src.review.schema import ResolvedReviewProfile, ExtractedFacts

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parents[4] / "config" / "review_basis"


class ResolvedBasis(BaseModel):
    basis_id: str
    title: str
    source_type: str
    effective_status: str
    jurisdiction: str
    file_refs: list[str] = []
    degraded: bool = False
    degradation_reason: str | None = None


class ResolvedRulePack(BaseModel):
    rule_pack_id: str
    scope: str
    related_pack_ids: list[str]
    evidence_requirements: list[str] = []
    degraded: bool = False
    degradation_reason: str | None = None


class ResolvedPack(BaseModel):
    pack_id: str
    status: str
    role: str
    family: str
    basis_ids: list[str] = []


class ResolvedBasisProfile(BaseModel):
    profile_id: str
    level1_classification: str
    level2_classification: str
    level3_classification: str | None = None
    packs: list[ResolvedPack]
    rule_packs: list[ResolvedRulePack] = []
    basis_documents: list[ResolvedBasis]
    degraded: bool = False
    degradation_reasons: list[str] = []


class BasisPackResolver:
    """
    Harness component responsible for mapping a resolved task profile
    into a concrete set of review packs, rule packs, and normative basis documents.

    Resolution chain:
        profile (from profile_mapping.yaml)
        → pack_ids (from profile's default_pack_ids + requested)
        → rule_pack_ids (from profile's rule_pack_ids + rule_pack_registry's related_pack_ids)
        → basis_ids (from pack's basis_ids)
        → concrete basis documents (from basis_registry.yaml)

    Does NOT scan all basis entries. Only resolves what is linked.
    """

    def __init__(self) -> None:
        self.profile_mapping: dict[str, Any] = self._load_yaml("profile_mapping.yaml")
        self.pack_registry: dict[str, Any] = self._load_yaml("pack_registry.yaml").get('packs', {})
        self.rule_pack_registry: dict[str, Any] = self._load_yaml("rule_pack_registry.yaml").get('rule_packs', {})
        self.basis_registry: dict[str, Any] = self._load_yaml("basis_registry.yaml")
        
        # Build tag index to avoid full scanning resolving basis per request
        self._tag_to_basis_ids: dict[str, list[str]] = {}
        for b_id, b_data in self.basis_registry.items():
            for tag in b_data.get('applicability_tags', []):
                self._tag_to_basis_ids.setdefault(tag, []).append(b_id)

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        path = CONFIG_DIR / filename
        if not path.exists():
            logger.warning("[basis_pack_resolver] YAML file not found: %s", path)
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            logger.error("[basis_pack_resolver] Failed to load %s: %s", path, exc)
            return {}

    def resolve(
        self,
        profile: ResolvedReviewProfile,
        task_context: dict[str, Any] | None = None,
        facts: ExtractedFacts | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> ResolvedBasisProfile:
        doc_type = profile.documentType
        requested_packs = profile.policyPackIds or []

        mapping = self.profile_mapping.get(doc_type)
        if not mapping:
            return ResolvedBasisProfile(
                profile_id=doc_type,
                level1_classification="Unknown",
                level2_classification="Unknown",
                packs=[],
                rule_packs=[],
                basis_documents=[],
                degraded=True,
                degradation_reasons=[f"profile_mapping.yaml 中未找到 '{doc_type}' 对应的配置"]
            )

        classification = mapping.get('classification', {})
        profile_id = mapping.get('profile_id', doc_type)
        default_pack_ids = mapping.get('default_pack_ids', [])
        profile_rule_pack_ids = list(dict.fromkeys((mapping.get('rule_pack_ids', []) or []) + (profile.rulePackIds or [])))

        # 1. Merge requested packs with defaults (deduplicated, order-preserved)
        all_pack_ids = list(dict.fromkeys(default_pack_ids + requested_packs))

        # 2. Resolve packs
        resolved_packs: list[ResolvedPack] = []
        degraded = False
        reasons: list[str] = []
        collected_basis_ids: list[str] = []

        for pack_id in all_pack_ids:
            if pack_id not in self.pack_registry:
                degraded = True
                reasons.append(f"审查包缺失: {pack_id} (在 pack_registry.yaml 中未注册)")
                continue
            pack_data = self.pack_registry[pack_id]
            pack_basis_ids = pack_data.get('basis_ids', [])
            collected_basis_ids.extend(pack_basis_ids)
            resolved_packs.append(ResolvedPack(
                pack_id=pack_id,
                status=pack_data.get('status', 'unknown'),
                role=pack_data.get('role', 'unknown'),
                family=pack_data.get('family', 'unknown'),
                basis_ids=pack_basis_ids,
            ))

        # 3. Resolve rule packs AND pull in their related packs
        resolved_rule_packs: list[ResolvedRulePack] = []
        resolved_pack_ids_set = set(all_pack_ids)  # Track what's already resolved
        rule_pack_contributed_pack_ids: list[str] = []

        for rp_id in profile_rule_pack_ids:
            if rp_id not in self.rule_pack_registry:
                degraded = True
                reasons.append(f"规则包缺失: {rp_id} (在 rule_pack_registry.yaml 中未注册)")
                resolved_rule_packs.append(ResolvedRulePack(
                    rule_pack_id=rp_id,
                    scope="unknown",
                    related_pack_ids=[],
                    degraded=True,
                    degradation_reason=f"规则包 {rp_id} 未在 rule_pack_registry.yaml 中注册",
                ))
                continue
            rp_data = self.rule_pack_registry[rp_id]
            related_pack_ids = rp_data.get('related_pack_ids', [])
            resolved_rule_packs.append(ResolvedRulePack(
                rule_pack_id=rp_id,
                scope=rp_data.get('scope', ''),
                related_pack_ids=related_pack_ids,
                evidence_requirements=rp_data.get('evidence_requirements', []),
            ))
            # Collect packs referenced by rule_packs that haven't been resolved yet
            for related_id in related_pack_ids:
                if related_id not in resolved_pack_ids_set:
                    rule_pack_contributed_pack_ids.append(related_id)
                    resolved_pack_ids_set.add(related_id)

        # 3b. Resolve additional packs contributed by rule_packs
        for pack_id in rule_pack_contributed_pack_ids:
            if pack_id not in self.pack_registry:
                degraded = True
                reasons.append(
                    f"规则包关联的审查包缺失: {pack_id} (在 pack_registry.yaml 中未注册)"
                )
                continue
            pack_data = self.pack_registry[pack_id]
            pack_basis_ids = pack_data.get('basis_ids', [])
            collected_basis_ids.extend(pack_basis_ids)
            resolved_packs.append(ResolvedPack(
                pack_id=pack_id,
                status=pack_data.get('status', 'unknown'),
                role=pack_data.get('role', 'unknown'),
                family=pack_data.get('family', 'unknown'),
                basis_ids=pack_basis_ids,
            ))

        # Auto-discover bases matching the active context (profile, level tags, pack families)
        tags_to_match = {profile_id, doc_type, classification.get("level1"), "all"}
        for p in resolved_packs:
            tags_to_match.add(p.pack_id)
            tags_to_match.add(p.family)
            
        tags_to_match.discard(None)  # Remove empty values if any

        for tag in tags_to_match:
            if tag in self._tag_to_basis_ids:
                collected_basis_ids.extend(self._tag_to_basis_ids[tag])

        # 4. Deduplicate basis IDs (order-preserved)
        unique_basis_ids = list(dict.fromkeys(collected_basis_ids))

        # 5. Resolve basis documents — ONLY those referenced by resolved packs
        #    Full-scan is avoided via the pre-built _tag_to_basis_ids index mappings.
        resolved_basis: list[ResolvedBasis] = []
        for basis_id in unique_basis_ids:
            if basis_id not in self.basis_registry:
                degraded = True
                reasons.append(f"依据文件缺失: {basis_id} (在 basis_registry.yaml 中未注册)")
                resolved_basis.append(ResolvedBasis(
                    basis_id=basis_id,
                    title=basis_id,
                    source_type="unknown",
                    effective_status="unknown",
                    jurisdiction="unknown",
                    degraded=True,
                    degradation_reason=f"依据 {basis_id} 未在 basis_registry.yaml 中注册",
                ))
                continue
            basis_data = self.basis_registry[basis_id]
            resolved_basis.append(ResolvedBasis(
                basis_id=basis_id,
                title=basis_data.get('title', basis_id),
                source_type=basis_data.get('source_type', 'unknown'),
                effective_status=basis_data.get('effective_status', 'unknown'),
                jurisdiction=basis_data.get('jurisdiction', 'unknown'),
                file_refs=basis_data.get('file_refs', []),
            ))

        logger.info(
            "[basis_pack_resolver] Resolved: profile=%s, packs=%d (direct=%d, rule_pack_contributed=%d), "
            "rule_packs=%d, basis=%d, degraded=%s",
            profile_id,
            len(resolved_packs),
            len(resolved_packs) - len(rule_pack_contributed_pack_ids),
            len(rule_pack_contributed_pack_ids),
            len(resolved_rule_packs),
            len(resolved_basis),
            degraded,
        )

        return ResolvedBasisProfile(
            profile_id=profile_id,
            level1_classification=classification.get('level1', 'Unknown'),
            level2_classification=classification.get('level2', 'Unknown'),
            level3_classification=classification.get('level3'),
            packs=resolved_packs,
            rule_packs=resolved_rule_packs,
            basis_documents=resolved_basis,
            degraded=degraded,
            degradation_reasons=reasons,
        )
