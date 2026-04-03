from __future__ import annotations

from collections import Counter

from src.review.schema import (
    AttachmentVisibilityMatrixItem,
    ConflictMatrix,
    HazardIdentificationMatrix,
    RuleHitMatrixRow,
    SectionStructureMatrixItem,
    StructuredReviewMatrices,
)


def build_review_matrices(parse_result, facts, rule_hits, final_issues) -> StructuredReviewMatrices:
    duplicate_keys = set(parse_result.visibilityReport.get('duplicateSectionTitles', []))
    section_structure = [
        SectionStructureMatrixItem(
            id=str(section['id']),
            title=str(section['title']),
            level=int(section['level']),
            parentId=section.get('parentId'),
            duplicate=str(section.get('key')) in duplicate_keys,
        )
        for section in parse_result.sections
    ]
    hazard_identification = HazardIdentificationMatrix(
        values={
            'liftingOperation': facts.hazardFacts.get('liftingOperation'),
            'gasArea': facts.hazardFacts.get('gasArea'),
            'hotWork': facts.hazardFacts.get('hotWork'),
            'temporaryPower': facts.hazardFacts.get('temporaryPower'),
            'specialEquipmentMentioned': facts.projectFacts.get('specialEquipmentMentioned'),
            'highRiskCategories': facts.hazardFacts.get('highRiskCategories'),
            'craneCapacityTon': facts.hazardFacts.get('craneCapacityTon'),
            'calculatedLiftWeightTon': facts.hazardFacts.get('calculatedLiftWeightTon'),
            'shutdownWindowDays': facts.scheduleFacts.get('shutdownWindowDays'),
            'laborTotal': facts.resourceFacts.get('laborTotal'),
            'sectionPresence': facts.projectFacts.get('sectionPresence'),
            'calculationEvidencePresent': facts.hazardFacts.get('calculationEvidencePresent'),
            'measureSectionPresent': facts.hazardFacts.get('measureSectionPresent'),
            'monitoringSectionPresent': facts.hazardFacts.get('monitoringSectionPresent'),
        }
    )
    rule_matrix = [
        RuleHitMatrixRow(
            ruleId=hit.ruleId,
            packId=hit.packId,
            status=hit.status,
            layerHint=hit.layerHint.value,
            severityHint=hit.severityHint,
            matchType=hit.matchType,
        )
        for hit in rule_hits
    ]
    conflicts = ConflictMatrix(
        values={
            'scheduleVsResources': {
                'shutdownWindowDays': facts.scheduleFacts.get('shutdownWindowDays'),
                'laborTotal': facts.resourceFacts.get('laborTotal'),
                'highRiskCategories': facts.hazardFacts.get('highRiskCategories'),
                'issueTriggered': any('组织压力' in issue.title for issue in final_issues),
            },
            'hazardVsMeasures': {
                'highRiskCategories': facts.hazardFacts.get('highRiskCategories'),
                'measureSectionPresent': facts.hazardFacts.get('measureSectionPresent'),
                'monitoringSectionPresent': facts.hazardFacts.get('monitoringSectionPresent'),
                'issueTriggered': any('闭环不足' in issue.title for issue in final_issues),
            },
        }
    )
    attachment_visibility = [
        AttachmentVisibilityMatrixItem.model_validate(item)
        for item in parse_result.attachments
    ]
    issue_layers = Counter(issue.layer.value for issue in final_issues)
    return StructuredReviewMatrices(
        hazardIdentification=hazard_identification,
        ruleHits=rule_matrix,
        conflicts=conflicts,
        attachmentVisibility=attachment_visibility,
        sectionStructure=section_structure,
        issueLayerCounts=dict(issue_layers),
    )
