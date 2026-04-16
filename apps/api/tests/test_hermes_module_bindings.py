from __future__ import annotations

from src.review.hermes.module_bindings import (
    REVIEW_MODULE_BINDINGS,
    module_template_ids,
    template_review_modules,
)


def test_review_module_bindings_cover_all_five_modules():
    assert set(REVIEW_MODULE_BINDINGS) == {
        "structure_completeness",
        "parameter_consistency",
        "legality_compliance",
        "execution_continuity",
        "evidence_validation",
    }


def test_review_module_bindings_define_templates_support_and_result_buckets():
    for binding in REVIEW_MODULE_BINDINGS.values():
        assert binding.hermes_templates
        assert binding.support_capabilities
        assert binding.result_bucket == binding.module_name
        assert binding.decision_policy


def test_template_review_modules_and_module_template_ids_are_consistent():
    template_ids = module_template_ids(["execution_continuity"])
    assert "execution_risk_reviewer" in template_ids
    assert template_review_modules("execution_risk_reviewer") == [
        "execution_continuity"
    ]
