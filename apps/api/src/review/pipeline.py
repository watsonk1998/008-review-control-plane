from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import Any, Callable

from src.domain.models import (
    ArtifactCategory,
    AttachmentLocator,
    AttachmentVisibility,
    BlockLocator,
    ConfidenceLevel,
    EvidenceSpan,
    SectionLocator,
    SourceDocumentRef,
    TableLocator,
    TaskArtifact,
)
from src.review.evidence.evidence_builder import EvidenceBuilder
from src.review.extractors.hazard_facts import extract_hazard_facts
from src.review.extractors.project_facts import extract_project_facts
from src.review.extractors.schedule_resource_facts import extract_schedule_resource_facts
from src.review.profile_resolver import resolve_review_profile
from src.review.report.issue_builder import finalize_issues
from src.review.report.matrices import build_review_matrices
from src.review.report.report_builder import StructuredReviewReportBuilder
from src.review.rules.engine import ReviewRuleEngine
from src.review.schema import (
    DocumentParseResult,
    ExtractedFacts,
    StructuredReviewResult,
    StructuredReviewTask,
    UnresolvedFact,
    VisibilityAssessment,
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
        source_document_ref: SourceDocumentRef | None = None,
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
        allow_visibility_ablation: bool = False,
    ) -> dict[str, Any]:
        options = execution_options or {}
        artifact_records: list[dict[str, Any]] = []
        structured_task = self._build_task(
            task_id=task_id,
            query=query,
            source_document_path=source_document_path,
            source_document_ref=source_document_ref,
            fixture_id=fixture_id,
            plan=plan,
            document_type=document_type,
            discipline_tags=discipline_tags,
            strict_mode=strict_mode,
            policy_pack_ids=policy_pack_ids,
        )
        parse_result = self.document_loader.parse_document(source_document_path)
        parse_result = self._apply_execution_options(
            parse_result,
            options,
            allow_visibility_ablation=allow_visibility_ablation,
        )
        parse_artifact = write_json_artifact('structured-review-parse', parse_result.model_dump(mode='json')) if write_json_artifact else None
        self._record_artifact(artifact_records, parse_artifact, category='parse', stage='parse')
        l0_artifact = write_json_artifact(
            'structured-review-l0-visibility',
            self._build_l0_visibility_artifact(parse_result),
        ) if write_json_artifact else None
        self._record_artifact(artifact_records, l0_artifact, category='parse', stage='parse')
        if emit:
            emit('parse', 'structured_review', 'completed', 'Document parsed for structured review', artifact_path=parse_artifact)

        facts = self._extract_facts(parse_result)
        facts_artifact = write_json_artifact('structured-review-facts', facts.model_dump(mode='json')) if write_json_artifact else None
        self._record_artifact(artifact_records, facts_artifact, category='facts', stage='extract')
        if emit:
            emit('extract', 'structured_review', 'completed', 'Structured facts extracted', artifact_path=facts_artifact)

        resolved_profile, packs, executable_packs = resolve_review_profile(
            structured_task,
            facts,
            plan,
        )
        if options.get('disable_rule_engine'):
            rule_hits = []
        else:
            rule_hits = self.rule_engine.run(facts, executable_packs, parse_result)
        rules_artifact = write_json_artifact('structured-review-rule-hits', [hit.model_dump(mode='json') for hit in rule_hits]) if write_json_artifact else None
        self._record_artifact(artifact_records, rules_artifact, category='rule_hits', stage='rules')
        if emit:
            emit(
                'rules',
                'structured_review',
                'completed',
                'Rule engine finished',
                artifact_path=rules_artifact,
                debug={
                    'selectedPacks': [pack.id for pack in executable_packs],
                    'requestedPlaceholderPacks': [pack.id for pack in packs if pack.readiness != 'ready'],
                },
            )

        candidates = self.evidence_builder.build(rule_hits, facts, parse_result, executable_packs)
        evidence_artifact = write_json_artifact('structured-review-candidates', [candidate.model_dump(mode='json') for candidate in candidates]) if write_json_artifact else None
        self._record_artifact(artifact_records, evidence_artifact, category='candidates', stage='evidence')
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
            visibility=parse_result.visibility,
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
                'visibility': parse_result.visibility.model_dump(mode='json'),
                'resolvedProfile': resolved_profile.model_dump(mode='json'),
                'issues': [issue.model_dump(mode='json') for issue in final_issues],
                'matrices': matrices.model_dump(mode='json'),
                'unresolvedFacts': [item.model_dump(mode='json') for item in facts.unresolvedFacts],
                'executionOptions': options,
            }))
            report_artifacts.append(write_json_artifact('hazard-identification-matrix', matrices.hazardIdentification.model_dump(mode='json')))
            report_artifacts.append(write_json_artifact('rule-hit-matrix', [item.model_dump(mode='json') for item in matrices.ruleHits]))
            report_artifacts.append(write_json_artifact('conflict-matrix', matrices.conflicts.model_dump(mode='json')))
            report_artifacts.append(write_json_artifact('attachment-visibility-matrix', [item.model_dump(mode='json') for item in matrices.attachmentVisibility]))
            report_artifacts.append(write_json_artifact('section-structure-matrix', [item.model_dump(mode='json') for item in matrices.sectionStructure]))
            report_artifacts.append(write_json_artifact('structured-review-report-buckets', self.report_builder.build_issue_buckets(final_issues)))
        if write_text_artifact:
            report_artifacts.append(write_text_artifact('structured-review-report', report_markdown, '.md'))
        if report_artifacts:
            self._record_artifact(artifact_records, report_artifacts[0], category='result', stage='report')
        for path in report_artifacts[1:-1]:
            self._record_artifact(artifact_records, path, category='matrices', stage='report')
        if write_text_artifact and report_artifacts:
            self._record_artifact(artifact_records, report_artifacts[-1], category='report', stage='report', primary=True)
        artifact_index = self._build_artifact_index(task_id, artifact_records)

        capabilities_used = ['structured_review_executor']
        if llm_gateway is not None:
            capabilities_used.append('llm_gateway')
        result = StructuredReviewResult(
            summary=summary,
            visibility=parse_result.visibility,
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
        source_document_ref: SourceDocumentRef | None = None,
        fixture_id: str | None = None,
        plan: dict[str, Any] | None = None,
        document_type: str | None = None,
        discipline_tags: list[str] | None = None,
        strict_mode: bool | None = None,
        policy_pack_ids: list[str] | None = None,
        execution_options: dict[str, Any] | None = None,
        allow_visibility_ablation: bool = False,
        write_json_artifact: Callable[[str, Any], str] | None = None,
        write_text_artifact: Callable[[str, str, str], str] | None = None,
    ) -> dict[str, Any]:
        return asyncio.run(
            self.run(
                task_id=task_id,
                query=query,
                source_document_path=source_document_path,
                source_document_ref=source_document_ref,
                fixture_id=fixture_id,
                plan=plan,
                document_type=document_type,
                discipline_tags=discipline_tags,
                strict_mode=strict_mode,
                policy_pack_ids=policy_pack_ids,
                execution_options=execution_options,
                allow_visibility_ablation=allow_visibility_ablation,
                write_json_artifact=write_json_artifact,
                write_text_artifact=write_text_artifact,
            )
        )

    def _build_task(
        self,
        *,
        task_id: str,
        query: str,
        source_document_path: str,
        source_document_ref: SourceDocumentRef | None,
        fixture_id: str | None,
        plan: dict[str, Any] | None,
        document_type: str | None,
        discipline_tags: list[str] | None,
        strict_mode: bool | None,
        policy_pack_ids: list[str] | None,
        ) -> StructuredReviewTask:
        plan_profile = dict((plan or {}).get('reviewProfile') or {})
        resolved_source_document_ref = source_document_ref or SourceDocumentRef(
            refId=fixture_id or task_id,
            sourceType='fixture' if fixture_id else 'upload',
            fileName=Path(source_document_path).name,
            fileType=Path(source_document_path).suffix.lower().lstrip('.') or 'unknown',
            storagePath=source_document_path,
            displayName=Path(source_document_path).name,
            fixtureId=fixture_id,
            mediaType=mimetypes.guess_type(source_document_path)[0],
        )
        return StructuredReviewTask(
            taskId=task_id,
            requestId=task_id,
            documentType=document_type or plan_profile.get('requestedDocumentType') or 'construction_org',
            disciplineTags=list(discipline_tags or plan_profile.get('requestedDisciplineTags') or []),
            policyPackIds=list(policy_pack_ids or plan_profile.get('requestedPolicyPackIds') or []),
            strictMode=True if strict_mode is None else strict_mode,
            sourceDocumentRef=resolved_source_document_ref,
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
                'attachments': [item.model_dump(mode='json') for item in parse_result.attachments],
                'visibility': parse_result.visibility.model_dump(mode='json'),
            },
            emergencyFacts=schedule_bundle.get('emergencyFacts', {}),
            factEvidence=fact_evidence,
            unresolvedFacts=self._dedupe_unresolved_facts(project_unresolved + hazard_unresolved + schedule_unresolved),
        )

    def _build_spans(self, parse_result: DocumentParseResult, refs: list[str]) -> list[EvidenceSpan]:
        spans: list[EvidenceSpan] = []
        block_index = {block['id']: block for block in parse_result.blocks}
        table_index = {table['id']: table for table in parse_result.tables}
        attachment_index = {attachment.id: attachment for attachment in parse_result.attachments}
        for ref in refs:
            if not ref:
                continue
            if ref in block_index:
                block = block_index[ref]
                spans.append(
                    EvidenceSpan(
                        sourceType='document',
                        sourceId=parse_result.documentId,
                        locator=BlockLocator(blockId=block['id'], sectionId=block.get('sectionId')),
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
                        locator=TableLocator(tableId=table['id'], sectionId=table.get('sectionId')),
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
                        locator=AttachmentLocator(attachmentId=attachment.id),
                        excerpt=attachment.title,
                        visibility=attachment.visibility,
                        confidence=ConfidenceLevel.medium,
                    )
                )
        return spans

    def _build_l0_visibility_artifact(self, parse_result: DocumentParseResult) -> dict[str, Any]:
        return {
            'parseMode': parse_result.parseMode,
            'parserLimited': parse_result.parserLimited,
            'parseWarnings': list(parse_result.parseWarnings),
            'visibility': parse_result.visibility.model_dump(mode='json'),
            'manualReviewNeeded': parse_result.visibility.manualReviewNeeded,
            'manualReviewReason': parse_result.visibility.manualReviewReason,
            'attachmentVisibility': [item.model_dump(mode='json') for item in parse_result.attachments],
        }

    def _apply_execution_options(
        self,
        parse_result: DocumentParseResult,
        options: dict[str, Any],
        *,
        allow_visibility_ablation: bool = False,
    ) -> DocumentParseResult:
        if options.get('disable_normalizer'):
            parse_result.normalizedText = '\n'.join(str(block.get('text') or '') for block in parse_result.blocks)
            parse_result.preview = parse_result.normalizedText[:4000]
            parse_result.parseWarnings.append('disable_normalizer')
        if options.get('disable_visibility_check') and allow_visibility_ablation:
            for attachment in parse_result.attachments:
                attachment.visibility = AttachmentVisibility.parsed
                attachment.parseState = 'parsed'
                attachment.manualReviewNeeded = False
                attachment.reason = None
            parse_result.visibility = VisibilityAssessment(
                parserLimited=parse_result.parserLimited,
                fileType=parse_result.fileType,
                attachmentCount=len(parse_result.attachments),
                counts={
                    'parsed': len(parse_result.attachments),
                    'attachment_unparsed': 0,
                    'referenced_only': 0,
                    'missing': 0,
                    'unknown': 0,
                },
                reasonCounts={},
                duplicateSectionTitles=list(parse_result.visibility.duplicateSectionTitles),
                parseWarnings=list(parse_result.visibility.parseWarnings),
                manualReviewNeeded=False,
            )
            parse_result.parseWarnings.append('disable_visibility_check')
        parse_result.visibility.parseWarnings = list(dict.fromkeys(parse_result.parseWarnings))
        parse_result.parseWarnings = list(parse_result.visibility.parseWarnings)
        parse_result.visibilityReport = parse_result.visibility.model_dump(mode='json')
        return parse_result

    def _record_artifact(
        self,
        artifact_records: list[dict[str, Any]],
        artifact_path: str | None,
        *,
        category: ArtifactCategory,
        stage: str,
        primary: bool = False,
    ) -> None:
        if not artifact_path:
            return
        artifact_records.append(
            {
                'path': artifact_path,
                'category': category,
                'stage': stage,
                'primary': primary,
            }
        )

    def _build_artifact_index(self, task_id: str, artifact_records: list[dict[str, Any]]) -> list[TaskArtifact]:
        index: list[TaskArtifact] = []
        for record in artifact_records:
            path = Path(record['path'])
            if not path.exists():
                continue
            media_type = mimetypes.guess_type(path.name)[0] or ('text/markdown' if path.suffix == '.md' else 'application/json')
            index.append(
                TaskArtifact(
                    name=path.stem,
                    fileName=path.name,
                    mediaType=media_type,
                    sizeBytes=path.stat().st_size,
                    downloadUrl=f'/api/tasks/{task_id}/artifacts/{path.name}',
                    category=record.get('category'),
                    stage=record.get('stage'),
                    primary=bool(record.get('primary', False)),
                )
            )
        return index

    def _dedupe_unresolved_facts(self, items: list[dict[str, Any]]) -> list[UnresolvedFact]:
        deduped: dict[tuple[str, str], UnresolvedFact] = {}
        for item in items:
            unresolved = UnresolvedFact.model_validate(item)
            deduped[(unresolved.code, unresolved.factKey)] = unresolved
        return list(deduped.values())
