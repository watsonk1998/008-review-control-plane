from __future__ import annotations

THRESHOLDS = {
    'issue_recall': 0.80,
    'l1_hit_rate': 0.80,
    'pack_selection_accuracy': 0.85,
    'policy_ref_accuracy': 0.85,
    'attachment_visibility_accuracy': 0.90,
    'severity_accuracy': 0.75,
    'manual_review_flag_accuracy': 0.85,
}

VERSIONED_STAGE_THRESHOLDS = {
    'facts_accuracy': 0.90,
    'rule_hit_accuracy': 0.85,
    'hazard_identification_accuracy': 0.90,
    'attachment_visibility_accuracy': 0.90,
    'manual_review_flag_accuracy': 0.80,
}
