from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from src.domain.models import AttachmentVisibility, ConfidenceLevel, EvidenceSpan, TaskArtifact
from src.review.evidence.evidence_builder import EvidenceBuilder
from src.review.extractors.hazard_facts import extract_hazard_facts
from src.review.extractors.project_facts import extract_project_facts
from src.review.extractors.schedule_resource_facts import extract_schedule_resource_facts
from src.review.report.issue_builder import finalize_issues
from src.review.report.matrices import build_review_matrices
from src.review.report.report_builder import StructuredReviewReportBuilder
from src.review.rules.engine import ReviewRuleEngine
from src.review.rules.packs import select_policy_packs
from src.review.schema import (
    DocumentParseResult,
    ExtractedFacts,
    ResolvedReviewProfile,
    StructuredReviewResult,
    StructuredReviewTask,
)


class StructuredReviewExecutor:
    def __init__(self, *, document_loader, llm_gateway=None, fast_adapter=None):
        self.document_loader = document_loader
        self.llm_gateway = llm_gateway
        self.fast_adapter = fast_adapter
        self.rule_engine = ReviewRuleEngine()
        self.evidence_builder = EvidenceBuilder()
        self.report_builder = StructuredReviewReportBuilder()

    async def run(
        self,
        *,
        task_id: str,
        query: str,
        source_document_path: str,
        fixture_id: str | None = None,
        plan: dict[str, Any] | None = None,
        document_type: str | None = None,
        discipline_tags: list[str] | None = None,
        strict_mode: bool | None = None,
        policy_pack_ids: list[str] | None = None,
        emit: Callable[..., Any] | None = None,
        write_json_artifact: Callable[[str, Any], str] | None = None,
        write_text_artifact: Callable[[str, str, str], str] | None = None,
        execution_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        options = execution_options or {}
        requested_document_type = document_type
        requested_discipline_tags = list(discipline_tags or [])
        requested_policy_pack_ids = list(policy_pack_ids or [])
        structured_task = self._build_task(
            task_id=task_id,
            query=query,
            source_document_path=source_document_path,
            fixture_id=fixture_id,
            plan=plan,
            document_type=document_type,
            discipline_tags=discipline_tags,
            strict_mode=strict_mode,
            policy_pack_ids=policy_pack_ids,
        )
        parse_result = self.document_loader.parse_document(source_document_path)
        parse_result = self._apply_execution_options(parse_result, options)
        parse_artifact = write_json_artifact('structured-review-parse', parse_result.model_dump(mode='json')) if write_json_artifact else None
        if emit:
            emit('parse', 'structured_review', 'completed', 'Document parsed for structured review', artifact_path=parse_artifact)

        facts = self._extract_facts(parse_result)
        facts_artifact = write_json_artifact('structured-review-facts', facts.model_dump(mode='json')) if write_json_artifact else None
        if emit:
            emit('extract', 'structured_review', 'completed', 'Structured facts extracted', artifact_path=facts_artifact)

        resolved_profile = self._resolve_profile(
            structured_task,
            facts,
            plan,
            requested_document_type=requested_document_type,
            requested_discipline_tags=requested_discipline_tags,
            requested_policy_pack_ids=requested_policy_pack_ids,
        )
        packs = select_policy_packs(
            resolved_profile.documentType,
            resolved_profile.disciplineTags,
            requested_pack_ids=resolved_profile.requestedPolicyPackIds,
        )
        resolved_profile.policyPackIds = [pack.id for pack in packs]
        if options.get('disable_rule_engine'):
            rule_hits = []
        else:
            rule_hits = self.rule_engine.run(facts, packs, parse_result)
        rules_artifact = write_json_artifact('structured-review-rule-hits', [hit.model_dump(mode='json') for hit in rule_hits]) if write_json_artifact else None
        if emit:
            emit('rules', 'structured_review', 'completed', 'Rule engine finished', artifact_path=rules_artifact, debug={'selectedPacks': [pack.id for pack in packs]})

        candidates = self.evidence_builder.build(rule_hits, facts, parse_result, packs)
        evidence_artifact = write_json_artifact('structured-review-candidates', [candidate.model_dump(mode='json') for candidate in candidates]) if write_json_artifact else None
        if emit:
            emit('evidence', 'structured_review', 'completed', 'Evidence candidates assembled', artifact_path=evidence_artifact)

        llm_gateway = None if options.get('disable_llm_explanation') else self.llm_gateway
        final_issues = await finalize_issues(candidates, llm_gateway=llm_gateway)
        matrices = build_review_matrices(parse_result, facts, rule_hits, final_issues)
        summary = self.report_builder.build_summary(
            document_type=resolved_profile.documentType,
            selected_packs=resolved_profile.policyPackIds,
            issues=final_issues,
            matrices=matrices,
            visibility_report=parse_result.visibilityReport,
            parse_warnings=parse_result.parseWarnings,
            unresolved_facts=facts.unresolvedFacts,
        )
        report_markdown = self.report_builder.render(
            summary=summary,
            resolved_profile=resolved_profile,
            issues=final_issues,
            matrices=matrices,
            parse_result=parse_result,
            unresolved_facts=facts.unresolvedFacts,
        )
        if emit:
            emit('report', 'structured_review', 'completed', 'Structured review report assembled')

        report_artifacts: list[str] = []
        if write_json_artifact:
            report_artifacts.append(write_json_artifact('structured-review-result', {
                'summary': summary.model_dump(mode='json'),
                'resolvedProfile': resolved_profile.model_dump(mode='json'),
                'issues': [issue.model_dump(mode='json') for issue in final_issues],
                'matrices': matrices.model_dump(mode='json'),
                'unresolvedFacts': facts.unresolvedFacts,
            }))
            report_artifacts.append(write_json_artifact('hazard-identification-matrix', matrices.hazardIdentification.model_dump(mode='json')))
            report_artifacts.append(write_json_artifact('rule-hit-matrix', [item.model_dump(mode='json') for item in matrices.ruleHits]))
            report_artifacts.append(write_json_artifact('conflict-matrix', matrices.conflicts.model_dump(mode='json')))
            report_artifacts.append(write_json_artifact('attachment-visibility-matrix', [item.model_dump(mode='json') for item in matrices.attachmentVisibility]))
            report_artifacts.append(write_json_artifact('section-structure-matrix', [item.model_dump(mode='json') for item in matrices.sectionStructure]))
        if write_text_artifact:
            report_artifacts.append(write_text_artifact('structured-review-report', report_markdown, '.md'))
        artifact_index = self._build_artifact_index(task_id, report_artifacts)

        capabilities_used = ['structured_review_executor']
        if llm_gateway is not None:
            capabilities_used.append('llm_gateway')
        result = StructuredReviewResult(
            summary=summary,
            resolvedProfile=resolved_profile,
            issues=final_issues,
            matrices=matrices,
            artifactIndex=artifact_index,
            reportMarkdown=report_markdown,
            artifacts=[artifact.downloadUrl for artifact in artifact_index],
            unresolvedFacts=facts.unresolvedFacts,
            plan=plan,
            capabilitiesUsed=capabilities_used,
            finalAnswer=report_markdown,
            notice='这是正式结构化审查结果；若存在 visibility_gap / manual_review_needed，请结合附件原件人工复核。',
        )
        return result.model_dump(mode='json')

    def run_sync(
        self,
        *,
        task_id: str,
        query: str,
        source_document_path: str,
        fixture_id: str | None = None,
        plan: dict[str, Any] | None = None,
        document_type: str | None = None,
        discipline_tags: list[str] | None = None,
        strict_mode: bool | None = None,
        policy_pack_ids: list[str] | None = None,
        execution_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return asyncio.run(
            self.run(
                task_id=task_id,
                query=query,
                source_document_path=source_document_path,
                fixture_id=fixture_id,
                plan=plan,
                document_type=document_type,
                discipline_tags=discipline_tags,
                strict_mode=strict_mode,
                policy_pack_ids=policy_pack_ids,
                execution_options=execution_options,
            )
        )

    def _build_task(
        self,
        *,
        task_id: str,
        query: str,
        source_document_path: str,
        fixture_id: str | None,
        plan: dict[str, Any] | None,
        document_type: str | None,
        discipline_tags: list[str] | None,
        strict_mode: bool | None,
        policy_pack_ids: list[str] | None,
    ) -> StructuredReviewTask:
        plan_profile = dict((plan or {}).get('reviewProfile') or {})
        return StructuredReviewTask(
            taskId=task_id,
            requestId=task_id,
            documentType=document_type or plan_profile.get('requestedDocumentType') or 'construction_org',
            disciplineTags=list(discipline_tags or plan_profile.get('requestedDisciplineTags') or []),
            policyPackIds=list(policy_pack_ids or plan_profile.get('requestedPolicyPackIds') or []),
            strictMode=True if strict_mode is None else strict_mode,
            sourceDocumentPath=source_document_path,
            sourceFixtureId=fixture_id,
            useAssistArtifacts=False,
        )

    def _resolve_profile(
        self,
        structured_task: StructuredReviewTask,
        facts: ExtractedFacts,
        plan: dict[str, Any] | None,
        *,
        requested_document_type: str | None,
        requested_discipline_tags: list[str] | None,
        requested_policy_pack_ids: list[str] | None,
    ) -> ResolvedReviewProfile:
        plan_profile = dict((plan or {}).get('reviewProfile') or {})
        requested_discipline_tags = list(requested_discipline_tags or [])
        requested_policy_pack_ids = list(requested_policy_pack_ids or [])
        inferred_document_type = facts.projectFacts.get('documentTypeHint') or plan_profile.get('documentTypeHint') or structured_task.documentType
        document_type = requested_document_type or inferred_document_type or 'construction_org'
        discipline_tags = list(
            dict.fromkeys(
                [
                    *requested_discipline_tags,
                    *(plan_profile.get('disciplineTagHints') or []),
                    *self._infer_discipline_tags(facts),
                ]
            )
        )
        return ResolvedReviewProfile(
            requestedDocumentType=requested_document_type,
            requestedDisciplineTags=requested_discipline_tags,
            requestedPolicyPackIds=requested_policy_pack_ids,
            documentType=document_type,
            disciplineTags=discipline_tags,
            policyPackIds=list(requested_policy_pack_ids),
            strictMode=structured_task.strictMode,
        )

    def _extract_facts(self, parse_result: DocumentParseResult) -> ExtractedFacts:
        project_facts, project_refs, project_unresolved = extract_project_facts(parse_result)
        hazard_facts, hazard_refs, hazard_unresolved = extract_hazard_facts(parse_result)
        schedule_bundle, schedule_refs, schedule_unresolved = extract_schedule_resource_facts(parse_result)
        ref_map = {**project_refs, **hazard_refs, **schedule_refs}
        fact_evidence = {key: self._build_spans(parse_result, refs) for key, refs in ref_map.items()}
        return ExtractedFacts(
            projectFacts=project_facts,
            hazardFacts=hazard_facts,
            scheduleFacts=schedule_bundle.get('scheduleFacts', {}),
            resourceFacts=schedule_bundle.get('resourceFacts', {}),
            attachmentFacts={
                'attachments': parse_result.attachments,
                'visibilityReport': parse_result.visibilityReport,
            },
            emergencyFacts=schedule_bundle.get('emergencyFacts', {}),
            factEvidence=fact_evidence,
            unresolvedFacts=list(dict.fromkeys(project_unresolved + hazard_unresolved + schedule_unresolved)),
        )

    def _build_spans(self, parse_result: DocumentParseResult, refs: list[str]) -> list[EvidenceSpan]:
        spans: list[EvidenceSpan] = []
        block_index = {block['id']: block for block in parse_result.blocks}
        table_index = {table['id']: table for table in parse_result.tables}
        attachment_index = {attachment['id']: attachment for attachment in parse_result.attachments}
        for ref in refs:
            if not ref:
                continue
            if ref in block_index:
                block = block_index[ref]
                spans.append(
                    EvidenceSpan(
                        sourceType='document',
                        sourceId=parse_result.documentId,
                        locator={'blockId': block['id'], 'sectionId': block.get('sectionId')},
                        excerpt=str(block.get('text') or '')[:400],
                        confidence=ConfidenceLevel.high,
                    )
                )
            elif ref in table_index:
                table = table_index[ref]
                spans.append(
                    EvidenceSpan(
                        sourceType='document',
                        sourceId=parse_result.documentId,
                        locator={'tableId': table['id'], 'sectionId': table.get('sectionId')},
                        excerpt=str(table.get('preview') or '')[:400],
                        confidence=ConfidenceLevel.high,
                    )
                )
            elif ref in attachment_index:
                attachment = attachment_index[ref]
                spans.append(
                    EvidenceSpan(
                        sourceType='document',
                        sourceId=parse_result.documentId,
                        locator={'attachmentId': attachment['id']},
                        excerpt=attachment.get('title', ''),
                        visibility=AttachmentVisibility(attachment['visibility']),
                        confidence=ConfidenceLevel.medium,
                    )
                )
        return spans

    def _infer_discipline_tags(self, facts: ExtractedFacts) -> list[str]:
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
        return tags

    def _apply_execution_options(self, parse_result: DocumentParseResult, options: dict[str, Any]) -> DocumentParseResult:
        if options.get('disable_normalizer'):
            parse_result.normalizedText = '\n'.join(str(block.get('text') or '') for block in parse_result.blocks)
            parse_result.preview = parse_result.normalizedText[:4000]
            parse_result.parseWarnings.append('disable_normalizer')
        if options.get('disable_visibility_check'):
            for attachment in parse_result.attachments:
                attachment['visibility'] = 'parsed'
                attachment['parseState'] = 'parsed'
                attachment['manualReviewNeeded'] = False
                attachment['reason'] = None
            parse_result.visibilityReport = {
                **parse_result.visibilityReport,
                'manualReviewNeeded': False,
                'counts': {
                    'parsed': len(parse_result.attachments),
                    'attachment_unparsed': 0,
                    'referenced_only': 0,
                    'missing': 0,
                    'unknown': 0,
                },
                'reasonCounts': {},
            }
            parse_result.parseWarnings.append('disable_visibility_check')
        return parse_result

    def _build_artifact_index(self, task_id: str, artifact_paths: list[str]) -> list[TaskArtifact]:
        index: list[TaskArtifact] = []
        for raw_path in artifact_paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            media_type = 'text/markdown' if path.suffix == '.md' else 'application/json'
            index.append(
                TaskArtifact(
                    name=path.stem,
                    fileName=path.name,
                    mediaType=media_type,
                    sizeBytes=path.stat().st_size,
                    downloadUrl=f'/api/tasks/{task_id}/artifacts/{path.name}',
                )
            )
        return index
