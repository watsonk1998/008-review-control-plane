from __future__ import annotations

from typing import Any

from src.review.hermes.constants import PRIMARY_MODULE_ID, normalize_module_id


class HermesModuleRegistry:
    def __init__(self, *, capability_facade):
        self.capability_facade = capability_facade

    async def run_module(self, module_id: str, *, workspace: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        normalized_module_id = normalize_module_id(module_id) or module_id
        if normalized_module_id == 'parse_visibility':
            return self.capability_facade.parse_visibility(workspace=workspace, context=context)
        if normalized_module_id == 'fact_extract':
            return self.capability_facade.fact_extract(workspace=workspace, context=context)
        if normalized_module_id == 'profile_and_packs':
            return self.capability_facade.profile_and_packs(workspace=workspace, context=context)
        if normalized_module_id == 'rule_and_evidence':
            return self.capability_facade.rule_and_evidence(workspace=workspace, context=context)
        if normalized_module_id == PRIMARY_MODULE_ID:
            return await self.capability_facade.primary_review(workspace=workspace, context=context)
        raise KeyError(f'Unsupported Hermes module: {module_id}')
