import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.review.contracts import FinalReportPacket, FindingItem
from src.review.hermes.presentation_agent import HermesPresentationAgent

def _mock_llm(reply_content: str):
    llm = MagicMock()
    llm.chat = AsyncMock(return_value={"content": reply_content})
    return llm

async def main():
    packet = FinalReportPacket(
        review_id="test_review_123",
        final_grade="needs_revision",
        all_findings=[
            FindingItem(
                id="ISSUE-001",
                title="高危断层点",
                severity="high",
                manual_review_needed=True,
                evidence_status="visibility_gap"
            )
        ],
        degradation_info={"hermes": {"reason": "timeout"}},
        report_markdown="# 正式报告\nISSUE-001 高危 断层点 需要人工复核 可视域异常 降级提示"
    )
    llm = _mock_llm("修改，ISSUE-001，一切正常无需任何提示。")
    agent = HermesPresentationAgent(llm)
    result = await agent.generate_presentation(packet)
    print("ERRORS:", result.consistency_errors)

asyncio.run(main())
