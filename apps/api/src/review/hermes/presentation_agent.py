import logging
from typing import Any

from src.review.contracts import FinalReportPacket, PresentationResult

logger = logging.getLogger(__name__)


class PresentationConsistencyValidator:
    """
    Validates that the presentation sub-agent did not hallucinate or omit
    critical formal outcomes from the authoritative result.
    """
    def validate(self, authoritative: FinalReportPacket, presentation_md: str) -> list[str]:
        errors = []
        
        # 1. Conclusion Grade MUST match generally
        grade_mapping = {
            'conditional_pass': ['有条件通过', '条件通过'],
            'needs_revision': ['需要修改', '修改'],
            'fail': ['不通过', '拒绝']
        }
        if authoritative.final_grade:
            expected_keywords = grade_mapping.get(authoritative.final_grade, [])
            if expected_keywords and not any(kw in presentation_md for kw in expected_keywords):
                errors.append(f"Missing final grade conclusion keyword, expected one of: {expected_keywords}")
        
        # 2 & 3 & 8 & 9. Issue count and IDs MUST NOT be added or removed
        for finding in authoritative.all_findings:
            if finding.id not in presentation_md:
                # If we use strict ISSUE-id matching, it must be present
                errors.append(f"Missing finding ID from authoritative packet: {finding.id}")

        # 6. Manual review required flag MUST NOT be lost
        needs_manual = any(f.manual_review_needed for f in authoritative.all_findings)
        if needs_manual and "人工复核" not in presentation_md:
            errors.append("Missing explicit 'manual_review_needed' notice (人工复核)")
            
        # 7. Visibility gaps MUST NOT be lost
        has_visibility_gap = any(
            isinstance(f.evidence_status, str) and 'visibility' in f.evidence_status 
            for f in authoritative.all_findings
        )
        if has_visibility_gap and "可视域" not in presentation_md and "人工复核" not in presentation_md:
             errors.append("Missing visibility gap notice")
             
        # Degraded checks (if any degradation somehow leaked into formal packet)
        if authoritative.degradation_info:
            if "降级" not in presentation_md and "异常" not in presentation_md:
                errors.append("Missing degradation info notice")

        return errors


class HermesPresentationAgent:
    """
    Read-only presentation layer sub-agent.
    Responsible ONLY for polishing and presenting the authoritative report into natural Chinese.
    MUST NOT alter facts, conclusions, issue counts, severities, or manual review statuses.
    """
    def __init__(self, llm_gateway: Any):
        self.llm_gateway = llm_gateway
        self.validator = PresentationConsistencyValidator()
        
    async def generate_presentation(self, authoritative_packet: FinalReportPacket) -> PresentationResult:
        if not authoritative_packet.report_markdown:
            return PresentationResult(
                review_id=authoritative_packet.review_id,
                presentation_markdown=authoritative_packet.report_markdown,
                source_authoritative_review_id=authoritative_packet.review_id,
                consistency_validated=False,
                consistency_errors=["Source authoritative report_markdown is empty"]
            )
            
        prompt = f"""你是一个受严格治理的专业的资深工程安全审查总监（Hermes Final Synthesizer / Presentation Layer Agent）。
你的唯一职责是：依据下方提供的【权威原始正式报告】，对其进行符合“人类阅读习惯”的语言表达优化、转换和汇总，使其更加自然、专业、克制且易读。

必须要严格遵守以下 5 个章节展开报告：
1. 章节完整性
2. 参数一致性
3. 合法合规性
4. 工序连贯性
5. 证据验证

（如果某章节在原报告中没有被指出对应的问题，请客观地说明“暂未发现明显问题”或概述现有的合规情况。）

【硬性不可触碰的安全红线】：
1. 绝对不能修改、弱化、或隐藏“总体评级结论”（如有条件通过、不通过等）。必须严格忠于原始审查结论！
2. 绝对不可在给用户看的正文中暴露任何英文系统词汇（如 HIGH, MEDIUM, ISSUE 等），必须翻译为普通人友好的中文（如“高风险”、“严重”）。
3. 绝对不能修改问题数量、遗漏溯源编号（如 ISSUE-xxx, H-xxx）、更改风险等级本身。这三者是底层防篡改底线。为了既不干扰用户阅读又不切断溯源追踪，请务必将这些冰冷的英文溯源编号使用 HTML 隐藏注释（如：`<!-- ISSUE-001 -->`）的方式附在对应问题描述的末尾，绝不可暴露在人眼可见的正文中。
4. 绝对不能修改、合并或删减任何证据摘要、条文依据和整改建议的核心事实含义。必须忠于原始报告的引用依据。
5. 绝对不能把阻断风险说轻，也不能把必须进行“人工复核”的地方弱化。
6. 对于系统状态提示（如：可视域缺失问题、组件降级提示），必须原样保留或更显眼地提示，绝不可删除！
7. 全程使用纯正、专业的中文进行表达，去除冷冰冰的系统生成痕迹。但不增加你自己的臆断新事实，不做二次推理。

最终输出必须是纯 Markdown 格式。

【权威原始正式报告如下】：
{authoritative_packet.report_markdown}
"""
        
        result = PresentationResult(
            review_id=authoritative_packet.review_id,
            source_authoritative_review_id=authoritative_packet.review_id,
        )
        
        try:
            content = await self.llm_gateway.chat([
                {'role': 'system', 'content': '你是只读的正式报告中文表达层。只优化表达，绝不篡改事实、等级、原编号ID或强制提示。'},
                {'role': 'user', 'content': prompt}
            ], temperature=0.1, max_tokens=2500)
            
            generated_md = content.get('content', '').strip()
            if not generated_md:
                result.consistency_errors.append("LLM returned empty response")
                result.consistency_validated = False
                result.presentation_markdown = authoritative_packet.report_markdown
                return result
                
            errors = self.validator.validate(authoritative_packet, generated_md)
            if errors:
                logger.warning(f"[presentation_agent] Consistency validation failed! Redacting generated presentation. Errors: {errors}")
                result.consistency_errors = errors
                result.consistency_validated = False
                # Fallback to authoritative markup immediately upon ANY error
                result.presentation_markdown = authoritative_packet.report_markdown
            else:
                result.consistency_errors = []
                result.consistency_validated = True
                result.presentation_markdown = generated_md
                
        except Exception as exc:
            logger.warning(f"[presentation_agent] Presentation generation failed: {exc}")
            result.consistency_errors.append(f"Exception: {str(exc)}")
            result.consistency_validated = False
            result.presentation_markdown = authoritative_packet.report_markdown
            
        return result
