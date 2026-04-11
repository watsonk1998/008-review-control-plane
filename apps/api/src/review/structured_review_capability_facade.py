from __future__ import annotations

"""Structured review module boundary for HermesController-first structured review.

Status:
- official module boundary

Freeze boundary:
- exposes 008 capabilities to Hermes-side callers
- does not own controller orchestration or final-output assembly

Do not extend:
- no HermesController semantics
- no template selection
- no final report assembly
- no supplemental review orchestration
- no second contract layer
- no duplicated 008 implementation

Canonical path:
- Hermes-side callers use this facade as the only supported boundary into 008 structured-review capabilities
- executor internals stay behind this facade and are normalized before controller/module consumption
"""

from typing import Any

from pydantic import BaseModel, Field

from src.review.profile_resolver import resolve_review_profile


class ParseVisibilityOutput(BaseModel):
    module_id: str = 'parse_visibility'
    visibility: dict[str, Any]
    parse_result: dict[str, Any]
    manual_review_needed: bool


class FactExtractOutput(BaseModel):
    module_id: str = 'fact_extract'
    facts: dict[str, Any]


class ProfileAndPacksOutput(BaseModel):
    module_id: str = 'profile_and_packs'
    resolved_profile: dict[str, Any]
    packs: list[dict[str, Any]] = Field(default_factory=list)
    executable_pack_ids: list[str] = Field(default_factory=list)


class RuleAndEvidenceOutput(BaseModel):
    module_id: str = 'rule_and_evidence'
    rule_hits: list[dict[str, Any]] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class PrimaryReviewOutput(BaseModel):
    module_id: str = 'primary_review'
    normalized_result: dict[str, Any]
    packet: dict[str, Any]


class StructuredReviewCapabilityFacade:
    def __init__(self, *, structured_review_executor):
        self.executor = structured_review_executor

    def parse_visibility(self, *, workspace: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        parse_result = workspace.get('parse_result')
        if parse_result is None:
            parse_result = self.executor.document_loader.parse_document(context['source_document_path'])
            workspace['parse_result'] = parse_result
        output = ParseVisibilityOutput(
            parse_result=parse_result.model_dump(mode='json'),
            visibility=parse_result.visibility.model_dump(mode='json'),
            manual_review_needed=parse_result.visibility.manualReviewNeeded,
        )
        return output.model_dump(mode='json')

    def fact_extract(self, *, workspace: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        parse_result = workspace.get('parse_result')
        if parse_result is None:
            self.parse_visibility(workspace=workspace, context=context)
            parse_result = workspace['parse_result']
        facts = workspace.get('facts')
        if facts is None:
            facts = self.executor._extract_facts(parse_result)
            workspace['facts'] = facts
        return FactExtractOutput(facts=facts.model_dump(mode='json')).model_dump(mode='json')

    def profile_and_packs(self, *, workspace: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        facts = workspace.get('facts')
        if facts is None:
            self.fact_extract(workspace=workspace, context=context)
            facts = workspace['facts']
        structured_task = workspace.get('structured_task')
        if structured_task is None:
            structured_task = self.executor._build_task(
                task_id=context['task_id'],
                query=context['query'],
                source_document_path=context['source_document_path'],
                source_document_ref=context.get('source_document_ref'),
                fixture_id=context.get('fixture_id'),
                plan=context.get('plan'),
                document_type=context.get('document_type'),
                discipline_tags=context.get('discipline_tags'),
                strict_mode=context.get('strict_mode'),
                policy_pack_ids=context.get('policy_pack_ids'),
            )
            workspace['structured_task'] = structured_task
        resolved_profile, packs, executable_packs = resolve_review_profile(
            structured_task,
            facts,
            context.get('plan'),
        )
        workspace['resolved_profile'] = resolved_profile
        workspace['packs'] = packs
        workspace['executable_packs'] = executable_packs
        return ProfileAndPacksOutput(
            resolved_profile=resolved_profile.model_dump(mode='json'),
            packs=[pack.model_dump(mode='json') for pack in packs],
            executable_pack_ids=[pack.id for pack in executable_packs],
        ).model_dump(mode='json')

    def rule_and_evidence(self, *, workspace: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        parse_result = workspace.get('parse_result')
        if parse_result is None:
            self.parse_visibility(workspace=workspace, context=context)
            parse_result = workspace['parse_result']
        facts = workspace.get('facts')
        if facts is None:
            self.fact_extract(workspace=workspace, context=context)
            facts = workspace['facts']
        executable_packs = workspace.get('executable_packs')
        resolved_profile = workspace.get('resolved_profile')
        if executable_packs is None or resolved_profile is None:
            self.profile_and_packs(workspace=workspace, context=context)
            executable_packs = workspace['executable_packs']
            resolved_profile = workspace['resolved_profile']
        selected_pack_ids = {pack.id for pack in executable_packs}
        facts = self.executor._apply_structure_completeness_profile(
            facts,
            parse_result=parse_result,
            document_type=resolved_profile.documentType,
            selected_pack_ids=selected_pack_ids,
        )
        rule_hits = self.executor.rule_engine.run(facts, executable_packs, parse_result)
        rule_hits = self.executor._enrich_rule_hits(rule_hits, facts=facts, parse_result=parse_result)
        candidates = self.executor.evidence_builder.build(rule_hits, facts, parse_result, executable_packs)
        workspace['facts'] = facts
        workspace['rule_hits'] = rule_hits
        workspace['candidates'] = candidates
        return RuleAndEvidenceOutput(
            rule_hits=[hit.model_dump(mode='json') for hit in rule_hits],
            candidates=[candidate.model_dump(mode='json') for candidate in candidates],
        ).model_dump(mode='json')

    async def primary_review(self, *, workspace: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        result = await self.executor.run(
            task_id=context['task_id'],
            query=context['query'],
            source_document_path=context['source_document_path'],
            source_document_ref=context.get('source_document_ref'),
            fixture_id=context.get('fixture_id'),
            plan=context.get('plan'),
            document_type=context.get('document_type'),
            discipline_tags=context.get('discipline_tags'),
            strict_mode=context.get('strict_mode'),
            policy_pack_ids=context.get('policy_pack_ids'),
            emit=context.get('emit'),
            write_json_artifact=context.get('write_json_artifact'),
            write_text_artifact=context.get('write_text_artifact'),
            write_binary_artifact=context.get('write_binary_artifact'),
        )
        normalized_result = self._normalize_primary_review_result(result)
        workspace['structured_review_result'] = normalized_result
        packet = context['fact_packet_adapter'].adapt(context['task_id'], result)
        packet.metadata = {
            **packet.metadata,
            'module_id': 'primary_review',
            'worker_id': 'structured_review_executor',
        }
        workspace['primary_packet'] = packet
        return PrimaryReviewOutput(
            normalized_result=normalized_result,
            packet=packet.model_dump(mode='json'),
        ).model_dump(mode='json')

    def _normalize_primary_review_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Return the stable facade-owned normalized view of the 008 primary result.

        This preserves the current result shape needed by HermesReviewAssembler while
        making the facade the single place that decides which keys are supported across
        the controller boundary.
        """

        normalized = dict(result)
        normalized.setdefault('summary', {})
        normalized.setdefault('visibility', {})
        normalized.setdefault('issues', [])
        normalized.setdefault('artifactIndex', [])
        normalized.setdefault('reportMarkdown', '')
        normalized.setdefault('reportHtml', '')
        normalized.setdefault('reportPrintCss', '')
        normalized.setdefault('resolvedProfile', {})
        normalized.setdefault('unresolvedFacts', [])
        normalized.setdefault('matrices', {})
        normalized.setdefault('capabilitiesUsed', [])
        normalized.setdefault('artifacts', [])
        normalized.setdefault('finalAnswer', normalized.get('reportMarkdown') or '')
        return normalized
