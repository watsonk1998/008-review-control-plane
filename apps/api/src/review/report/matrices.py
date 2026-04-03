from __future__ import annotations

from collections import Counter


def build_review_matrices(parse_result, facts, rule_hits, final_issues):
    section_structure = [
        {
            'id': section['id'],
            'title': section['title'],
            'level': section['level'],
            'parentId': section['parentId'],
            'duplicate': section['key'] in set(parse_result.visibilityReport.get('duplicateSectionTitles', [])),
        }
        for section in parse_result.sections
    ]
    hazard_identification = {
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
    }
    rule_matrix = [
        {
            'ruleId': hit.ruleId,
            'packId': hit.packId,
            'status': hit.status,
            'layerHint': hit.layerHint.value,
            'severityHint': hit.severityHint,
            'matchType': hit.matchType,
        }
        for hit in rule_hits
    ]
    conflicts = {
        'scheduleVsResources': {
            'shutdownWindowDays': facts.scheduleFacts.get('shutdownWindowDays'),
            'laborTotal': facts.resourceFacts.get('laborTotal'),
            'highRiskCategories': facts.hazardFacts.get('highRiskCategories'),
            'issueTriggered': any(issue.id == 'ISSUE-004' or '组织压力' in issue.title for issue in final_issues),
        }
    }
    attachment_visibility = parse_result.attachments
    issue_layers = Counter(issue.layer.value for issue in final_issues)
    return {
        'hazardIdentification': hazard_identification,
        'ruleHits': rule_matrix,
        'conflicts': conflicts,
        'attachmentVisibility': attachment_visibility,
        'sectionStructure': section_structure,
        'issueLayerCounts': dict(issue_layers),
    }
