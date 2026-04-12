from __future__ import annotations

import yaml
from pathlib import Path
from pydantic import BaseModel
from typing import Any

from src.review.schema import ResolvedReviewProfile

CONFIG_DIR = Path(__file__).resolve().parents[4] / "config" / "review_basis"

class ResolvedBasis(BaseModel):
    basis_id: str
    title: str
    source_type: str
    effective_status: str
    jurisdiction: str
    degraded: bool = False

class ResolvedPack(BaseModel):
    pack_id: str
    status: str
    role: str
    family: str

class ResolvedBasisProfile(BaseModel):
    profile_id: str
    level1_classification: str
    level2_classification: str
    level3_classification: str | None = None
    packs: list[ResolvedPack]
    basis_documents: list[ResolvedBasis]
    degraded: bool = False
    degradation_reasons: list[str] = []

class BasisPackResolver:
    """
    Harness component responsible for mapping a resolved task profile 
    into a concrete set of review packs and normative basis documents.
    Operates strictly off the YAML configuration registries acting as the System of Record.
    """
    def __init__(self) -> None:
        self.profile_mapping: dict[str, Any] = self._load_yaml("profile_mapping.yaml")
        self.pack_registry: dict[str, Any] = self._load_yaml("pack_registry.yaml").get('packs', {})
        self.basis_registry: dict[str, Any] = self._load_yaml("basis_registry.yaml")

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        path = CONFIG_DIR / filename
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def resolve(self, profile: ResolvedReviewProfile) -> ResolvedBasisProfile:
        doc_type = profile.documentType
        requested_packs = profile.policyPackIds or []
        
        mapping = self.profile_mapping.get(doc_type)
        if not mapping:
            return ResolvedBasisProfile(
                profile_id=doc_type,
                level1_classification="Unknown",
                level2_classification="Unknown",
                packs=[],
                basis_documents=[],
                degraded=True,
                degradation_reasons=["Unknown profile mapping."]
            )

        classification = mapping.get('classification', {})
        default_pack_ids = mapping.get('default_pack_ids', [])
        
        # Merge requested packs with defaults
        all_pack_ids = list(dict.fromkeys(default_pack_ids + requested_packs))
        
        resolved_packs: list[ResolvedPack] = []
        degraded = False
        reasons = []

        for pack_id in all_pack_ids:
            if pack_id not in self.pack_registry:
                degraded = True
                reasons.append(f"Pack missing from registry: {pack_id}")
                continue
            pack_data = self.pack_registry[pack_id]
            resolved_packs.append(ResolvedPack(
                pack_id=pack_id,
                status=pack_data.get('status', 'unknown'),
                role=pack_data.get('role', 'unknown'),
                family=pack_data.get('family', 'unknown')
            ))

        # We will stub basis documents for now; in full implementation this 
        # fetches from rule_pack_registry.yaml -> basis_registry.yaml
        resolved_basis: list[ResolvedBasis] = []
        for basis_id, basis_data in self.basis_registry.items():
            # For this phase, if we load successfully, we consider it resolved
            # A more granular filter by pack_id is possible using rule_pack_registry
            resolved_basis.append(ResolvedBasis(
                basis_id=basis_id,
                title=basis_data.get('title', basis_id),
                source_type=basis_data.get('source_type', 'unknown'),
                effective_status=basis_data.get('effective_status', 'unknown'),
                jurisdiction=basis_data.get('jurisdiction', 'unknown')
            ))

        return ResolvedBasisProfile(
            profile_id=doc_type,
            level1_classification=classification.get('level1', 'Unknown'),
            level2_classification=classification.get('level2', 'Unknown'),
            level3_classification=classification.get('level3'),
            packs=resolved_packs,
            basis_documents=resolved_basis,
            degraded=degraded,
            degradation_reasons=reasons
        )
