import pytest
from unittest.mock import MagicMock
from src.review.support_packet_builder import SupportPacketBuilder
from src.review.schema import ExtractedFacts, ResolvedReviewProfile
from src.review.basis_pack_resolver import ResolvedBasisProfile
from src.domain.models import TaskRecord, EvidenceSpan, SourceDocumentRef


def test_support_packet_builder_registers_both_fact_and_policy_spans():
    builder = SupportPacketBuilder()

    # Mock TaskRecord
    task_record = MagicMock(spec=TaskRecord)
    task_record.id = "test-task"

    # Mock ResolvedReviewProfile
    profile = MagicMock(spec=ResolvedReviewProfile)
    profile.documentType = "distribution_network_special_scheme"

    # Mock ResolvedBasisProfile
    basis_profile = MagicMock(spec=ResolvedBasisProfile)
    basis_profile.degraded = False
    basis_profile.basis_documents = [
        MagicMock(
            basis_id="policy-1",
            title="Policy 1",
            file_refs=[],
            degraded=False,
            source_type="standard",
            effective_status="current",
        )
    ]
    basis_profile.rule_packs = []

    # Mock ExtractedFacts with evidence spans
    fact_span = EvidenceSpan(
        sourceType="document",
        sourceId="doc-1",
        locator={"page": 1},
        excerpt="Document fact excerpt",
        clauseTitle="Section 1",
    )
    facts = ExtractedFacts(factEvidence={"fact-1": [fact_span]})

    # We need to mock _load_basis_fulltext_context to return a predictable span
    # Or just let it run if we mock the file system, but it's easier to verify
    # if we check the registry after build_packet

    # Patch _load_basis_fulltext_context to add a policy span to the registry
    original_load = builder._load_basis_fulltext_context

    def mock_load(bp, registry):
        policy_span = EvidenceSpan(
            sourceType="policy",
            sourceId="policy-1",
            locator={"blockId": "fulltext"},
            excerpt="Policy excerpt",
            clauseTitle="Policy Title",
        )
        builder._register_span(registry, policy_span)
        return [
            {
                "basis_id": "policy-1",
                "title": "Policy 1",
                "evidence_span_id": policy_span.span_id,
            }
        ]

    builder._load_basis_fulltext_context = mock_load

    packet = builder.build_packet(
        review_record=task_record,
        profile=profile,
        basis_profile=basis_profile,
        facts=facts,
    )

    # Verify provenance_registry
    registry = packet.provenance_registry

    # Should have at least 2 spans: one from facts, one from policy
    assert len(registry) >= 2

    # Check for document span
    doc_spans = [s for s in registry.values() if s.sourceType == "document"]
    assert len(doc_spans) == 1
    assert doc_spans[0].excerpt == "Document fact excerpt"

    # Check for policy span
    policy_spans = [s for s in registry.values() if s.sourceType == "policy"]
    assert len(policy_spans) == 1
    assert policy_spans[0].excerpt == "Policy excerpt"


if __name__ == "__main__":
    pytest.main([__file__])
