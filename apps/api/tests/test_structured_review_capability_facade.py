from __future__ import annotations

from pathlib import Path

from src.review.fact_packet_adapter import FactPacketAdapter
from src.review.hermes.module_registry import HermesModuleRegistry
from src.review.pipeline import StructuredReviewExecutor
from src.review.structured_review_capability_facade import (
    FactExtractOutput,
    ParseVisibilityOutput,
    PrimarySupportReviewOutput,
    ProfileAndPacksOutput,
    RuleAndEvidenceOutput,
    StructuredReviewCapabilityFacade,
)
from src.services.document_loader import DocumentLoader


class FakeLLM:
    def explain_issue_candidates(self, candidates):
        return [
            {
                "id": f"ISSUE-{index + 1:03d}",
                "title": candidate.title,
                "layer": candidate.layerHint,
                "severity": candidate.severityHint,
                "findingType": candidate.findingType,
                "summary": candidate.title,
                "manualReviewNeeded": candidate.manualReviewNeeded,
                "evidenceMissing": candidate.evidenceMissing,
                "manualReviewReason": candidate.manualReviewReason,
                "issueKind": getattr(candidate, "issueKind", "hard_defect"),
                "applicabilityState": getattr(
                    candidate, "applicabilityState", "applies"
                ),
                "docEvidence": [
                    span.model_dump(mode="json") for span in candidate.docEvidence
                ],
                "policyEvidence": [
                    span.model_dump(mode="json") for span in candidate.policyEvidence
                ],
                "recommendation": ["demo"],
                "confidence": "medium",
            }
            for index, candidate in enumerate(candidates)
        ]


def _write_sample(path: Path) -> Path:
    sample = path / "sample.md"
    sample.write_text(
        "# 施工组织设计\n\n## 第一节 工程概况\n项目名称：测试项目\n"
        "## 第二节 施工部署\n起重吊装 作业\n施工用电 作业\n动火作业\n"
        "附件1：施工总平面布置图\n",
        encoding="utf-8",
    )
    return sample


def _build_context(sample: Path) -> dict:
    return {
        "task_id": "facade-task-1",
        "query": "执行正式结构化审查",
        "source_document_path": str(sample),
        "source_document_ref": None,
        "fixture_id": None,
        "plan": {"reviewProfile": {"authority": "test"}},
        "document_type": "construction_org",
        "discipline_tags": ["lifting_operations", "temporary_power", "hot_work"],
        "strict_mode": True,
        "policy_pack_ids": ["construction_org.base"],
        "emit": None,
        "write_json_artifact": None,
        "write_text_artifact": None,
        "write_binary_artifact": None,
        "fact_packet_adapter": FactPacketAdapter(),
    }


async def test_structured_review_capability_facade_primary_review_matches_executor(
    tmp_path: Path,
):
    sample = _write_sample(tmp_path)
    executor = StructuredReviewExecutor(
        document_loader=DocumentLoader(), llm_gateway=FakeLLM(), fast_adapter=None
    )
    facade = StructuredReviewCapabilityFacade(structured_review_executor=executor)
    context = _build_context(sample)

    direct = await executor.run(
        task_id=context["task_id"],
        query=context["query"],
        source_document_path=context["source_document_path"],
        source_document_ref=context["source_document_ref"],
        fixture_id=context["fixture_id"],
        plan=context["plan"],
        document_type=context["document_type"],
        discipline_tags=context["discipline_tags"],
        strict_mode=context["strict_mode"],
        policy_pack_ids=context["policy_pack_ids"],
    )
    workspace: dict = {}
    primary = await facade.primary_support_review(workspace=workspace, context=context)
    result = primary["support_result"]

    for key in [
        "visibility",
        "artifactIndex",
        "reportMarkdown",
        "reportHtml",
        "reportPrintCss",
        "resolvedProfile",
    ]:
        assert result[key] == direct[key]
    assert (
        result["summary"]["overallConclusion"] == direct["summary"]["overallConclusion"]
    )
    assert [issue["id"] for issue in result["issues"]] == [
        issue["id"] for issue in direct["issues"]
    ]
    assert all(issue["ownership"] == "support_material" for issue in result["issues"])
    assert all(
        issue["supportCapabilities"] == ["primary_support_review"]
        for issue in result["issues"]
    )
    assert result["issues"][0]["supportModules"] == ["structure_completeness"]
    assert primary["module_id"] == "primary_support_review"
    assert workspace["structured_support_result_008"]["summary"] == direct["summary"]
    assert primary["support_packet"]["engine"] == "008"
    assert (
        PrimarySupportReviewOutput.model_validate(primary).support_result["summary"]
        == direct["summary"]
    )


def test_structured_review_capability_facade_exposes_incremental_capabilities(
    tmp_path: Path,
):
    sample = _write_sample(tmp_path)
    executor = StructuredReviewExecutor(
        document_loader=DocumentLoader(), llm_gateway=FakeLLM(), fast_adapter=None
    )
    facade = StructuredReviewCapabilityFacade(structured_review_executor=executor)
    context = _build_context(sample)
    workspace: dict = {}

    parse_result = facade.parse_visibility(workspace=workspace, context=context)
    facts_result = facade.fact_extract(workspace=workspace, context=context)
    profile_result = facade.profile_and_packs(workspace=workspace, context=context)
    rules_result = facade.rule_and_evidence(workspace=workspace, context=context)

    assert (
        ParseVisibilityOutput.model_validate(parse_result).module_id
        == "parse_visibility"
    )
    assert FactExtractOutput.model_validate(facts_result).module_id == "fact_extract"
    assert (
        ProfileAndPacksOutput.model_validate(profile_result).module_id
        == "profile_and_packs"
    )
    assert (
        RuleAndEvidenceOutput.model_validate(rules_result).module_id
        == "rule_and_evidence"
    )
    assert workspace["parse_result"].visibility.manualReviewNeeded is True
    assert workspace["resolved_profile"].documentType == "construction_org"
    assert isinstance(rules_result["candidates"], list)


class SpyFacade:
    def __init__(self):
        self.called = []

    def parse_visibility(self, *, workspace, context):
        self.called.append("parse_visibility")
        return {"module_id": "parse_visibility"}

    def fact_extract(self, *, workspace, context):
        self.called.append("fact_extract")
        return {"module_id": "fact_extract"}

    def profile_and_packs(self, *, workspace, context):
        self.called.append("profile_and_packs")
        return {"module_id": "profile_and_packs"}

    def rule_and_evidence(self, *, workspace, context):
        self.called.append("rule_and_evidence")
        return {"module_id": "rule_and_evidence"}

    async def primary_review(self, *, workspace, context):
        self.called.append("primary_review")
        return {"module_id": "primary_review"}

    async def primary_support_review(self, *, workspace, context):
        self.called.append("primary_support_review")
        return {"module_id": "primary_support_review"}


async def test_hermes_module_registry_routes_only_through_facade():
    registry = HermesModuleRegistry(capability_facade=SpyFacade())
    workspace: dict = {}
    context: dict = {}

    await registry.run_module(
        "structured_review_worker", workspace=workspace, context=context
    )
    assert await registry.run_module(
        "primary_review", workspace=workspace, context=context
    ) == {"module_id": "primary_support_review"}
    assert await registry.run_module(
        "primary_support_review", workspace=workspace, context=context
    ) == {"module_id": "primary_support_review"}
    assert registry.capability_facade.called == [
        "primary_support_review",
        "primary_support_review",
        "primary_support_review",
    ]


def test_hermes_module_registry_source_does_not_grab_executor_internals():
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "review"
        / "hermes"
        / "module_registry.py"
    ).read_text(encoding="utf-8")
    for forbidden in [
        "document_loader.parse_document",
        "._extract_facts",
        "._build_task",
        "rule_engine.run",
        "evidence_builder.build",
        "executor.run(",
    ]:
        assert forbidden not in source


def test_structured_review_capability_facade_source_declares_boundary_non_goals():
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "review"
        / "structured_review_capability_facade.py"
    ).read_text(encoding="utf-8")
    for phrase in [
        "no HermesController semantics",
        "no template selection",
        "no final report assembly",
        "no supplemental review orchestration",
        "no second contract layer",
        "no duplicated 008 implementation",
    ]:
        assert phrase in source
