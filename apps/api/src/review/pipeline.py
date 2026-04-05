from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import Any, Callable

from src.domain.models import (
    ApplicabilityState,
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
from src.review.evidence.clause_store import ClauseStore
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
        self.clause_store = self.evidence_builder.clause_store or ClauseStore()
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

        resolved_profile, packs, executable_packs = resolve_review_profile(
            structured_task,
            facts,
            plan,
        )
        if options.get('disable_rule_engine'):
            rule_hits = []
        else:
            rule_hits = self.rule_engine.run(facts, executable_packs, parse_result)
        rule_hits = self._enrich_rule_hits(rule_hits, facts=facts, parse_result=parse_result)
        facts.unresolvedFacts = self._link_unresolved_facts_to_rule_hits(facts.unresolvedFacts, rule_hits)
        facts_artifact = write_json_artifact('structured-review-facts', facts.model_dump(mode='json')) if write_json_artifact else None
        self._record_artifact(artifact_records, facts_artifact, category='facts', stage='extract')
        if emit:
            emit('extract', 'structured_review', 'completed', 'Structured facts extracted', artifact_path=facts_artifact)
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
        final_issues = self._link_issues_to_unresolved_facts(final_issues, facts.unresolvedFacts)
        facts.unresolvedFacts = self._link_unresolved_facts_to_issues(facts.unresolvedFacts, final_issues)
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
            report_artifacts.append(write_json_artifact('hazard-identification-matrix', matrices.hazardIdentification.model_dump(mode='json')))
            report_artifacts.append(write_json_artifact('rule-hit-matrix', [item.model_dump(mode='json') for item in matrices.ruleHits]))
            report_artifacts.append(write_json_artifact('conflict-matrix', matrices.conflicts.model_dump(mode='json')))
            report_artifacts.append(write_json_artifact('attachment-visibility-matrix', [item.model_dump(mode='json') for item in matrices.attachmentVisibility]))
            report_artifacts.append(write_json_artifact('section-structure-matrix', [item.model_dump(mode='json') for item in matrices.sectionStructure]))
            report_artifacts.append(write_json_artifact('structured-review-report-buckets', self.report_builder.build_issue_buckets(final_issues)))
        if write_text_artifact:
            report_artifacts.append(write_text_artifact('structured-review-report', report_markdown, '.md'))
        for path in report_artifacts[:-1] if write_text_artifact and report_artifacts else report_artifacts:
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
        if write_json_artifact:
            result_artifact = write_json_artifact(
                'structured-review-result',
                result.model_dump(mode='json') | {'executionOptions': options},
            )
            self._record_artifact(artifact_records, result_artifact, category='result', stage='report')
            artifact_index = self._build_artifact_index(task_id, artifact_records)
            result.artifactIndex = artifact_index
            result.artifacts = [artifact.downloadUrl for artifact in artifact_index]
            write_json_artifact(
                'structured-review-result',
                result.model_dump(mode='json') | {'executionOptions': options},
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
            'preflight': parse_result.visibility.preflight.model_dump(mode='json'),
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

    def _enrich_rule_hits(
        self,
        rule_hits,
        *,
        facts: ExtractedFacts,
        parse_result: DocumentParseResult,
    ):
        unresolved_by_fact = {item.factKey: item for item in facts.unresolvedFacts}
        attachment_visibility = (facts.attachmentFacts.get('visibility') or {}) if isinstance(facts.attachmentFacts, dict) else {}
        for hit in rule_hits:
            required_fact_keys = list(dict.fromkeys(hit.requiredFactKeys or hit.factRefs))
            missing_fact_keys = [fact_key for fact_key in required_fact_keys if fact_key in unresolved_by_fact]
            clause_ids = list(dict.fromkeys(hit.clauseIds or self.clause_store.get_clause_ids(hit.ruleId)))
            blocking_reasons = list(hit.blockingReasons)
            if hit.matchType == 'visibility_gap':
                blocking_reasons.append('visibility_gap')
            if self._rule_hit_depends_on_visibility(hit, required_fact_keys) and self._visibility_is_parser_limited_without_reliable_attachment(
                parse_result=parse_result,
                attachment_visibility=attachment_visibility,
            ):
                blocking_reasons.append('parser_limited_source')
            if missing_fact_keys:
                blocking_reasons.append('missing_fact')
            blocking_reasons.extend(
                unresolved.blockingReason
                for fact_key in missing_fact_keys
                if (unresolved := unresolved_by_fact.get(fact_key)) is not None and unresolved.blockingReason
            )
            if hit.status == 'manual_review_needed' and hit.matchType != 'visibility_gap':
                blocking_reasons.append('manual_confirmation_required')
            hit.requiredFactKeys = required_fact_keys
            hit.missingFactKeys = missing_fact_keys
            hit.clauseIds = clause_ids
            hit.blockingReasons = list(dict.fromkeys(blocking_reasons))
            hit.applicabilityState = self._derive_rule_hit_applicability_state(hit)
        return rule_hits

    def _link_unresolved_facts_to_rule_hits(self, unresolved_facts: list[UnresolvedFact], rule_hits) -> list[UnresolvedFact]:
        if not unresolved_facts:
            return unresolved_facts
        blocking_rules_by_fact: dict[str, list[str]] = {}
        for hit in rule_hits:
            for fact_key in hit.missingFactKeys:
                blocking_rules_by_fact.setdefault(fact_key, []).append(hit.ruleId)
        for item in unresolved_facts:
            item.blockingRuleIds = list(dict.fromkeys(blocking_rules_by_fact.get(item.factKey, [])))
        return unresolved_facts

    def _link_issues_to_unresolved_facts(
        self,
        final_issues,
        unresolved_facts: list[UnresolvedFact],
    ):
        if not final_issues or not unresolved_facts:
            return final_issues
        unresolved_by_fact = {item.factKey: item for item in unresolved_facts}
        for issue in final_issues:
            blocking_reasons = list(issue.blockingReasons or [])
            if issue.missingFactKeys:
                blocking_reasons.append('missing_fact')
            if issue.applicabilityState == 'blocked_by_visibility':
                blocking_reasons.append('visibility_gap')
            blocking_reasons.extend(
                unresolved.blockingReason
                for fact_key in issue.missingFactKeys
                if (unresolved := unresolved_by_fact.get(fact_key)) is not None and unresolved.blockingReason
            )
            issue.blockingReasons = list(dict.fromkeys(blocking_reasons))
            for fact_key in issue.missingFactKeys:
                unresolved = unresolved_by_fact.get(fact_key)
                if unresolved is None:
                    continue
                unresolved.blockingIssueIds = list(dict.fromkeys([*unresolved.blockingIssueIds, issue.id]))
                unresolved.blockingIssueTitles = list(dict.fromkeys([*unresolved.blockingIssueTitles, issue.title]))
        return final_issues

    def _link_unresolved_facts_to_issues(
        self,
        unresolved_facts: list[UnresolvedFact],
        final_issues,
    ) -> list[UnresolvedFact]:
        if not unresolved_facts:
            return unresolved_facts
        issue_ids_by_fact: dict[str, list[str]] = {}
        issue_titles_by_fact: dict[str, list[str]] = {}
        for issue in final_issues:
            for fact_key in issue.missingFactKeys:
                issue_ids_by_fact.setdefault(fact_key, []).append(issue.id)
                issue_titles_by_fact.setdefault(fact_key, []).append(issue.title)
        for item in unresolved_facts:
            item.blockingIssueIds = list(dict.fromkeys([*item.blockingIssueIds, *issue_ids_by_fact.get(item.factKey, [])]))
            item.blockingIssueTitles = list(
                dict.fromkeys([*item.blockingIssueTitles, *issue_titles_by_fact.get(item.factKey, [])])
            )
        return unresolved_facts

    def _dedupe_unresolved_facts(self, items: list[dict[str, Any]]) -> list[UnresolvedFact]:
        deduped: dict[tuple[str, str], UnresolvedFact] = {}
        for item in items:
            unresolved = UnresolvedFact.model_validate(item)
            deduped[(unresolved.code, unresolved.factKey)] = unresolved
        return list(deduped.values())

    def _rule_hit_depends_on_visibility(self, hit, required_fact_keys: list[str]) -> bool:
        if hit.matchType == 'visibility_gap':
            return True
        refs = [*required_fact_keys, *(hit.factRefs or [])]
        return any(str(ref).startswith('attachments.') for ref in refs)

    def _visibility_is_parser_limited_without_reliable_attachment(
        self,
        *,
        parse_result: DocumentParseResult,
        attachment_visibility: dict[str, Any],
    ) -> bool:
        if not parse_result.visibility.parserLimited:
            return False
        parsed_count = int((attachment_visibility or {}).get('counts', {}).get('parsed', 0))
        attachment_count = int((attachment_visibility or {}).get('attachmentCount', len(parse_result.attachments) or 0))
        return attachment_count == 0 or parsed_count == 0

    def _derive_rule_hit_applicability_state(self, hit) -> ApplicabilityState:
        blocking_reasons = set(hit.blockingReasons or [])
        visibility_reasons = {
            'visibility_gap',
            'attachment_unparsed',
            'referenced_only',
            'visibility_unknown',
            'parser_limited_pdf_requires_manual_review',
            'attachment_unknown',
            'attachment_missing_confirmed',
        }
        if hit.matchType == 'visibility_gap' or blocking_reasons & visibility_reasons:
            return 'blocked_by_visibility'
        if hit.missingFactKeys:
            return 'blocked_by_missing_fact'
        if hit.status == 'manual_review_needed':
            return 'partial'
        return 'applies'
