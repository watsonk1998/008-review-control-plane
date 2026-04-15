from __future__ import annotations

import asyncio
import json
import re
from typing import Any

try:
    from duckduckgo_search import DDGS
except Exception:  # pragma: no cover
    DDGS = None


_OFFICIAL_DOMAIN_KEYWORDS = (
    'gov.cn',
    'samr.gov.cn',
    'std.samr.gov.cn',
    'openstd.samr.gov.cn',
    'nea.gov.cn',
    'mem.gov.cn',
    'mohurd.gov.cn',
    'csg.cn',
    'ceprei.com',
)

_NEGATIVE_HINTS = ('废止', '作废', '失效', '替代', '代替', '废除')
_POSITIVE_HINTS = ('现行', '有效', '实施', '继续有效')
_NON_NORMATIVE_HINTS = (
    '合同',
    '委托函',
    '中标通知书',
    '技术资料',
    '施工图',
    '设计图',
    '审批资料',
    '交底记录',
    '现场查勘',
    '查勘记录',
)
_NORMATIVE_CODE_PATTERN = re.compile(
    r'(?:(?:GB|GB/T|DL/T|DL|Q/CSG|Q/GDW|Q/SH|JGJ|NB/T|NB|AQ|DB|DBJ|YD/T|SL|GA|CECS)\s*[-/A-Z]*\s*\d{2,}(?:[-—]\d{2,4})?)',
    re.IGNORECASE,
)


class NormativeValidityChecker:
    def __init__(self, *, llm_gateway=None):
        self.llm_gateway = llm_gateway

    async def verify_candidates(self, candidates) -> list[dict[str, Any]]:
        return await self._verify_sources(self._extract_sources_from_candidates(candidates))

    async def verify_parse_result(self, parse_result) -> list[dict[str, Any]]:
        return await self._verify_sources(self._extract_sources_from_parse_result(parse_result))

    async def _verify_sources(self, sources: list[dict[str, str]]) -> list[dict[str, Any]]:
        if not sources:
            return []
        results = await asyncio.gather(*[self._verify_source(source) for source in sources])
        return [result for result in results if result]

    def _extract_sources_from_candidates(self, candidates) -> list[dict[str, str]]:
        seen: set[str] = set()
        sources: list[dict[str, str]] = []
        for candidate in candidates or []:
            for span in getattr(candidate, 'policyEvidence', []) or []:
                source_id = str(getattr(span, 'sourceId', '') or '').strip()
                if not source_id or self._skip_source(source_id):
                    continue
                title = self._normalize_source_title(source_id)
                if title in seen:
                    continue
                seen.add(title)
                sources.append({'sourceId': source_id, 'title': title})
        return sources

    def _extract_sources_from_parse_result(self, parse_result) -> list[dict[str, str]]:
        if parse_result is None:
            return []
        sections = list(getattr(parse_result, 'sections', []) or [])
        blocks = list(getattr(parse_result, 'blocks', []) or [])
        target_section_ids = [
            str(section.get('id') or '')
            for section in sections
            if any(keyword in str(section.get('title') or '') for keyword in ['编制依据', '编制说明'])
        ]
        if not target_section_ids:
            return []

        descendant_ids = self._collect_descendant_section_ids(sections, target_section_ids)
        scoped_section_ids = set(target_section_ids) | descendant_ids
        seen: set[str] = set()
        sources: list[dict[str, str]] = []
        for block in blocks:
            if str(block.get('type') or '') == 'heading':
                continue
            section_id = str(block.get('sectionId') or '')
            if section_id not in scoped_section_ids:
                continue
            text = self._clean_text(block.get('text'))
            for candidate in self._split_reference_candidates(text):
                title = self._extract_normative_title(candidate)
                if not title or title in seen:
                    continue
                seen.add(title)
                sources.append({'sourceId': title, 'title': title})
        return sources

    def _collect_descendant_section_ids(self, sections: list[dict[str, Any]], root_ids: list[str]) -> set[str]:
        children_by_parent: dict[str, list[str]] = {}
        for section in sections:
            section_id = str(section.get('id') or '')
            parent_id = str(section.get('parentId') or '')
            if section_id and parent_id:
                children_by_parent.setdefault(parent_id, []).append(section_id)
        pending = list(root_ids)
        descendants: set[str] = set()
        while pending:
            current = pending.pop()
            for child_id in children_by_parent.get(current, []):
                if child_id in descendants:
                    continue
                descendants.add(child_id)
                pending.append(child_id)
        return descendants

    def _split_reference_candidates(self, text: str) -> list[str]:
        value = self._clean_text(text)
        if not value:
            return []
        normalized = re.sub(r'^[（(]?\d+[)）.、]\s*', '', value)
        return [part.strip('；;。 ') for part in re.split(r'[；;]', normalized) if part.strip('；;。 ')]

    def _extract_normative_title(self, text: str) -> str:
        value = self._clean_text(text)
        if not value:
            return ''
        if any(hint in value for hint in _NON_NORMATIVE_HINTS):
            return ''
        if '《' not in value and not _NORMATIVE_CODE_PATTERN.search(value):
            return ''

        if '《' in value:
            start = value.index('《')
            value = value[start:]
        value = re.sub(r'^[（(]?\d+[)）.、]\s*', '', value)
        value = re.sub(r'\s+', ' ', value).strip('；;。 ')
        if any(hint in value for hint in _NON_NORMATIVE_HINTS):
            return ''
        if '《' not in value and not _NORMATIVE_CODE_PATTERN.search(value):
            return ''
        return value

    async def _verify_source(self, source: dict[str, str]) -> dict[str, Any]:
        title = source['title']
        web_task = asyncio.create_task(self._search_web(title))
        llm_task = asyncio.create_task(self._infer_with_llm(title))
        web_result, llm_result = await asyncio.gather(web_task, llm_task)
        final = web_result if web_result.get('status') != 'unknown' else llm_result
        if final.get('status') == 'unknown' and not final.get('summary'):
            final = self._heuristic_result(title)
        return {
            'sourceId': source['sourceId'],
            'title': title,
            **final,
        }

    async def _search_web(self, title: str) -> dict[str, Any]:
        if DDGS is None:
            return self._unknown_result('web', '当前环境未启用联网检索依赖。')
        return await asyncio.to_thread(self._search_web_sync, title)

    def _search_web_sync(self, title: str) -> dict[str, Any]:
        query = f'{title} 现行 有效 废止 替代'
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=8))
        except Exception as exc:  # pragma: no cover
            return self._unknown_result('web', f'联网检索失败：{exc}')
        official = [item for item in results if self._is_official_result(item)]
        pool = official or results
        if not pool:
            return self._unknown_result('web', '未检索到权威公开结果。')
        best = pool[0]
        haystack = ' '.join([str(best.get('title') or ''), str(best.get('body') or ''), str(best.get('href') or '')])
        if any(token in haystack for token in _NEGATIVE_HINTS):
            return {
                'status': 'superseded',
                'resolvedBy': 'web',
                'summary': '联网结果出现废止、作废或替代信号，需按最新版本复核。',
                'evidenceTitle': str(best.get('title') or ''),
                'evidenceUrl': str(best.get('href') or ''),
            }
        if any(token in haystack for token in _POSITIVE_HINTS):
            return {
                'status': 'current',
                'resolvedBy': 'web',
                'summary': '联网结果未见废止或替代信号，当前可按现行有效处理。',
                'evidenceTitle': str(best.get('title') or ''),
                'evidenceUrl': str(best.get('href') or ''),
            }
        return {
            'status': 'unknown',
            'resolvedBy': 'web',
            'summary': '已检索到公开结果，但未能从标题/摘要稳定判断现行状态。',
            'evidenceTitle': str(best.get('title') or ''),
            'evidenceUrl': str(best.get('href') or ''),
        }

    async def _infer_with_llm(self, title: str) -> dict[str, Any]:
        if self.llm_gateway is None:
            return self._heuristic_result(title)
        prompt = (
            '你是法规现行有效性校验助手。仅根据标题常识做保守判断，不允许编造。'
            '返回 JSON：{"status":"current|superseded|unknown","summary":"..."}。'
            f'\n标题：{title}'
        )
        try:
            response = await self.llm_gateway.chat(
                [
                    {'role': 'system', 'content': '你是谨慎的法规有效性判断助手。'},
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.0,
                max_tokens=300,
            )
            parsed = self._load_json_object(response.get('content', ''))
            status = str(parsed.get('status') or 'unknown')
            if status not in {'current', 'superseded', 'unknown'}:
                status = 'unknown'
            return {
                'status': status,
                'resolvedBy': 'llm',
                'summary': str(parsed.get('summary') or '模型未给出稳定判断。').strip(),
                'evidenceTitle': '模型判断',
                'evidenceUrl': '',
            }
        except Exception:
            return self._heuristic_result(title)

    def _heuristic_result(self, title: str) -> dict[str, Any]:
        if _NORMATIVE_CODE_PATTERN.search(title):
            return self._unknown_result('heuristic', '仅根据规范编号无法稳定判断现行状态，需联网或人工复核。')
        if '条例' in title or '工作规程' in title or '管理工作指引' in title:
            return {
                'status': 'current',
                'resolvedBy': 'heuristic',
                'summary': '基于标题常识做保守初判，暂未见明确废止信号；如用于正式结论，仍建议联网复核。',
                'evidenceTitle': '规则兜底',
                'evidenceUrl': '',
            }
        return self._unknown_result('heuristic', '当前仅能给出保守判断，建议人工核验。')

    def _unknown_result(self, resolved_by: str, summary: str) -> dict[str, Any]:
        return {
            'status': 'unknown',
            'resolvedBy': resolved_by,
            'summary': summary,
            'evidenceTitle': '',
            'evidenceUrl': '',
        }

    def _is_official_result(self, item: dict[str, Any]) -> bool:
        href = str(item.get('href') or '')
        return any(keyword in href for keyword in _OFFICIAL_DOMAIN_KEYWORDS)

    def _skip_source(self, source_id: str) -> bool:
        hidden_keywords = (
            'review-control-plane-',
            '监理工程师对停电施工方案的审核规则及要点',
            '危险性较大的分部分项工程专项施工方案编制指南',
        )
        return any(keyword in source_id for keyword in hidden_keywords)

    def _normalize_source_title(self, source_id: str) -> str:
        if '《' in source_id:
            return source_id[source_id.index('《'):]
        return source_id

    def _load_json_object(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if not text:
            return {}
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            text = match.group(0)
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ''
        return re.sub(r'\s+', ' ', str(value).replace('\n', ' ').replace('\r', ' ')).strip()
