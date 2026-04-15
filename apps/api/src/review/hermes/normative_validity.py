from __future__ import annotations

import asyncio
import json
import re
from typing import Any

try:
    from duckduckgo_search import DDGS
except Exception:  # pragma: no cover - optional import guard
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


class NormativeValidityChecker:
    def __init__(self, *, llm_gateway=None):
        self.llm_gateway = llm_gateway

    async def verify_candidates(self, candidates) -> list[dict[str, Any]]:
        sources = self._extract_sources(candidates)
        if not sources:
            return []
        results = await asyncio.gather(*[self._verify_source(source) for source in sources])
        return [result for result in results if result]

    def _extract_sources(self, candidates) -> list[dict[str, str]]:
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
        except Exception as exc:  # pragma: no cover - network defensive guard
            return self._unknown_result('web', f'联网检索失败：{exc}')
        official = [item for item in results if self._is_official_result(item)]
        pool = official or results
        if not pool:
            return self._unknown_result('web', '未检索到权威公开结果。')
        best = pool[0]
        haystack = ' '.join(
            [
                str(best.get('title') or ''),
                str(best.get('body') or ''),
                str(best.get('href') or ''),
            ]
        )
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
        if re.search(r'GB\s*/?T?\s*\d{4,}-\d{4}', title):
            return self._unknown_result('heuristic', '仅根据标准编号无法稳定判断现行状态，需联网或人工复核。')
        if '条例' in title or '管理工作指引' in title:
            return {
                'status': 'current',
                'resolvedBy': 'heuristic',
                'summary': '基于常识做保守初判，暂未见明确废止信号；如用于正式结论，仍建议联网复核。',
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
        return source_id.startswith('review-control-plane-') or '监理工程师对停电施工方案的审核规则及要点' in source_id

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
