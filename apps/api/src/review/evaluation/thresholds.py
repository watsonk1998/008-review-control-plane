from __future__ import annotations

# Legacy stable baseline thresholds are regression floors, not release-quality targets.
# The primary merge-quality gate lives in VERSIONED_STAGE_THRESHOLDS over official
# versioned cases. These floors keep legacy behavior from materially regressing while
# allowing the official versioned stage gate to remain the stricter blocker.
THRESHOLDS = {
    'issue_recall': 0.75,
    'l1_hit_rate': 0.85,
    'pack_selection_accuracy': 0.95,
    'policy_ref_accuracy': 0.75,
    'attachment_visibility_accuracy': 0.55,
    'severity_accuracy': 0.75,
    'manual_review_flag_accuracy': 0.95,
}

VERSIONED_STAGE_THRESHOLDS = {
    'facts_accuracy': 0.90,
    'rule_hit_accuracy': 0.85,
    'hazard_identification_accuracy': 0.90,
    'attachment_visibility_accuracy': 0.90,
    'manual_review_flag_accuracy': 0.80,
}
