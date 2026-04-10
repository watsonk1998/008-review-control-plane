from __future__ import annotations

"""Structured review capability facade.

This facade exposes 008 structured-review capabilities to Hermes-side callers
without leaking StructuredReviewExecutor internals into controller code.

Non-goals:
- no HermesController semantics
- no template selection
- no final report assembly
- no supplemental review orchestration
- no second contract layer
- no duplicated 008 implementation
"""

from typing import Any

from src.review.profile_resolver import resolve_review_profile


class StructuredReviewCapabilityFacade:
    def __init__(self, *, structured_review_executor):
        self.executor = structured_review_executor

    def parse_visibility(self, *, workspace: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        parse_result = workspace.get('parse_result')
        if parse_result is None:
            parse_result = self.executor.document_loader.parse_document(context['source_document_path'])
            workspace['parse_result'] = parse_result
        return {
            'module_id': 'parse_visibility',
            'parse_result': parse_result.model_dump(mode='json'),
            'visibility': parse_result.visibility.model_dump(mode='json'),
            'manual_review_needed': parse_result.visibility.manualReviewNeeded,
        }

    def fact_extract(self, *, workspace: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        parse_result = workspace.get('parse_result')
        if parse_result is None:
            self.parse_visibility(workspace=workspace, context=context)
            parse_result = workspace['parse_result']
        facts = workspace.get('facts')
        if facts is None:
            facts = self.executor._extract_facts(parse_result)
            workspace['facts'] = facts
        return {
            'module_id': 'fact_extract',
            'facts': facts.model_dump(mode='json'),
        }

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
        return {
            'module_id': 'profile_and_packs',
            'resolved_profile': resolved_profile.model_dump(mode='json'),
            'packs': [pack.model_dump(mode='json') for pack in packs],
            'executable_pack_ids': [pack.id for pack in executable_packs],
        }

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
        return {
            'module_id': 'rule_and_evidence',
            'rule_hits': [hit.model_dump(mode='json') for hit in rule_hits],
            'candidates': [candidate.model_dump(mode='json') for candidate in candidates],
        }

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
        workspace['structured_review_result'] = result
        packet = context['fact_packet_adapter'].adapt(context['task_id'], result)
        packet.metadata = {
            **packet.metadata,
            'module_id': 'primary_review',
            'worker_id': 'structured_review_executor',
        }
        workspace['primary_packet'] = packet
        return {
            'module_id': 'primary_review',
            'result': result,
            'packet': packet.model_dump(mode='json'),
        }
