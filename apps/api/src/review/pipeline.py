from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from src.domain.models import AttachmentVisibility, ConfidenceLevel, EvidenceSpan, FindingType, ReviewLayer
from src.review.evidence.evidence_builder import EvidenceBuilder
from src.review.extractors.hazard_facts import extract_hazard_facts
from src.review.extractors.project_facts import extract_project_facts
from src.review.extractors.schedule_resource_facts import extract_schedule_resource_facts
from src.review.report.issue_builder import finalize_issues
from src.review.report.matrices import build_review_matrices
from src.review.report.report_builder import StructuredReviewReportBuilder
from src.review.rules.engine import ReviewRuleEngine
from src.review.rules.packs import select_policy_packs
from src.review.schema import DocumentParseResult, ExtractedFacts, StructuredReviewResult, StructuredReviewTask


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
        emit: Callable[..., Any] | None = None,
        write_json_artifact: Callable[[str, Any], str] | None = None,
        write_text_artifact: Callable[[str, str, str], str] | None = None,
    ) -> dict[str, Any]:
        structured_task = self._build_task(task_id=task_id, query=query, source_document_path=source_document_path, fixture_id=fixture_id, plan=plan)
        parse_result = self.document_loader.parse_document(source_document_path)
        parse_artifact = write_json_artifact('structured-review-parse', parse_result.model_dump(mode='json')) if write_json_artifact else None
        if emit:
            emit('parse', 'structured_review', 'completed', 'Document parsed for structured review', artifact_path=parse_artifact)

        facts = self._extract_facts(parse_result)
        facts_artifact = write_json_artifact('structured-review-facts', facts.model_dump(mode='json')) if write_json_artifact else None
        if emit:
            emit('extract', 'structured_review', 'completed', 'Structured facts extracted', artifact_path=facts_artifact)

        discipline_tags = self._infer_discipline_tags(facts)
        packs = select_policy_packs(structured_task.documentType, discipline_tags)
        rule_hits = self.rule_engine.run(facts, packs, parse_result)
        rules_artifact = write_json_artifact('structured-review-rule-hits', [hit.model_dump(mode='json') for hit in rule_hits]) if write_json_artifact else None
        if emit:
            emit('rules', 'structured_review', 'completed', 'Rule engine finished', artifact_path=rules_artifact, debug={'selectedPacks': [pack.id for pack in packs]})

        candidates = self.evidence_builder.build(rule_hits, facts, parse_result, packs)
        evidence_artifact = write_json_artifact('structured-review-candidates', [candidate.model_dump(mode='json') for candidate in candidates]) if write_json_artifact else None
        if emit:
            emit('evidence', 'structured_review', 'completed', 'Evidence candidates assembled', artifact_path=evidence_artifact)

        final_issues = await finalize_issues(candidates, llm_gateway=self.llm_gateway)
        matrices = build_review_matrices(parse_result, facts, rule_hits, final_issues)
        summary = self.report_builder.build_summary(
            document_type=structured_task.documentType,
            selected_packs=[pack.id for pack in packs],
            issues=final_issues,
            matrices=matrices,
            visibility_report=parse_result.visibilityReport,
        )
        report_markdown = self.report_builder.render(summary=summary, issues=final_issues, matrices=matrices, parse_result=parse_result)
        if emit:
            emit('report', 'structured_review', 'completed', 'Structured review report assembled')

        report_artifacts: list[str] = []
        if write_json_artifact:
            report_artifacts.append(write_json_artifact('structured-review-result', {
                'summary': summary.model_dump(mode='json'),
                'issues': [issue.model_dump(mode='json') for issue in final_issues],
                'matrices': matrices,
            }))
            report_artifacts.append(write_json_artifact('hazard-identification-matrix', matrices['hazardIdentification']))
            report_artifacts.append(write_json_artifact('rule-hit-matrix', matrices['ruleHits']))
            report_artifacts.append(write_json_artifact('conflict-matrix', matrices['conflicts']))
            report_artifacts.append(write_json_artifact('attachment-visibility-matrix', matrices['attachmentVisibility']))
            report_artifacts.append(write_json_artifact('section-structure-matrix', matrices['sectionStructure']))
        if write_text_artifact:
            report_artifacts.append(write_text_artifact('structured-review-report', report_markdown, '.md'))

        capabilities_used = ['structured_review_executor']
        if self.llm_gateway is not None:
            capabilities_used.append('llm_gateway')
        result = StructuredReviewResult(
            summary=summary,
            issues=final_issues,
            matrices=matrices,
            reportMarkdown=report_markdown,
            artifacts=report_artifacts,
            plan=plan,
            capabilitiesUsed=capabilities_used,
            finalAnswer=report_markdown,
            notice='这是正式结构化审查结果；若存在 visibility_gap / manual_review_needed，请结合附件原件人工复核。',
        )
        return result.model_dump(mode='json')

    def run_sync(self, *, task_id: str, query: str, source_document_path: str, fixture_id: str | None = None, plan: dict[str, Any] | None = None) -> dict[str, Any]:
        return asyncio.run(self.run(task_id=task_id, query=query, source_document_path=source_document_path, fixture_id=fixture_id, plan=plan))

    def _build_task(self, *, task_id: str, query: str, source_document_path: str, fixture_id: str | None, plan: dict[str, Any] | None) -> StructuredReviewTask:
        document_type = 'construction_org' if '施工组织设计' in query or 'construction_org' in str(plan or {}) else 'review_support_material'
        return StructuredReviewTask(
            taskId=task_id,
            requestId=task_id,
            documentType=document_type,
            disciplineTags=[],
            policyPackIds=[],
            strictMode=True,
            sourceDocumentPath=source_document_path,
            sourceFixtureId=fixture_id,
            useAssistArtifacts=False,
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
            unresolvedFacts=project_unresolved + hazard_unresolved + schedule_unresolved,
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
        return tags
