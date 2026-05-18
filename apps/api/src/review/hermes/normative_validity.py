from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

try:
    from duckduckgo_search import DDGS
except Exception:  # pragma: no cover
    DDGS = None

# ---------------------------------------------------------------------------
# Web-search resilience constants
# ---------------------------------------------------------------------------
_WEB_SEARCH_TIMEOUT = 12.0  # seconds per DDGS call
_WEB_SEARCH_CONCURRENCY = 3  # max parallel web searches
_WEB_SEARCH_COOLDOWN = 60.0  # seconds to skip web after consecutive failures
_WEB_SEARCH_MAX_CONSECUTIVE_FAILS = 3  # failures before circuit opens


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
    r'(?:(?:GB|GB/T|GBJ|DL/T|DL|Q/CSG|Q/GDW|Q/SH|Q/BGJ|JGJ/T|JGJ|NB/T|NB|AQ|DB|DBJ|DGJ|YD/T|SL|GA|CECS|TSG|HG|CJJ|SH/T|YB|JB|CJ|YS|SY|HJ|TB|LB|MZ)\s*[-/A-Z]*\s*\d{2,}(?:\.\d+)?(?:[-—]\d{2,4})?)',
    re.IGNORECASE,
)
_VERSION_YEAR_PATTERN = re.compile(r'[-—]\d{4}(?:\b|$)')

# Gate: keywords that identify non-standard documents (laws, regulations,
# internal rules) which should NOT enter normative validity checking.
_EXCLUDED_DOCUMENT_KEYWORDS = (
    '条例',
    '办法',
    '规定',
    '实施细则',
    '通知',
    '通告',
    '意见',
    '决定',
    '命令',
    '管理制度',
    '规章',
    '管理办法',
    '管理规定',
    '暂行规定',
    '暂行办法',
)


class NormativeValidityChecker:
    def __init__(self, *, llm_gateway=None):
        self.llm_gateway = llm_gateway
        # Per-instance circuit breaker state (reset each verify call)
        self._web_circuit_open_until: float = 0.0
        self._web_consecutive_fails: int = 0

    async def verify_candidates(self, candidates) -> list[dict[str, Any]]:
        return await self._verify_sources(self._extract_sources_from_candidates(candidates))

    async def verify_parse_result(self, parse_result) -> list[dict[str, Any]]:
        return await self._verify_sources(self._extract_sources_from_parse_result(parse_result))

    async def _verify_sources(self, sources: list[dict[str, str]]) -> list[dict[str, Any]]:
        if not sources:
            return []
        # Reset circuit breaker for each batch
        self._web_circuit_open_until = 0.0
        self._web_consecutive_fails = 0
        semaphore = asyncio.Semaphore(_WEB_SEARCH_CONCURRENCY)

        async def _limited_verify(source: dict[str, str]) -> dict[str, Any]:
            async with semaphore:
                return await self._verify_source(source)

        results = await asyncio.gather(*[_limited_verify(s) for s in sources])
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
                if not self._is_standard_normative(title):
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
                if not self._is_standard_normative(title):
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

        # Gate: markdown table rows (pipe-separated cells from PDF/DOCX extractors).
        # Split by pipe into individual cells, then filter each cell:
        # keep cells that contain a recognized standard code OR a book-title (《》).
        pipe_count = value.count('|')
        if value.lstrip().startswith('|') or pipe_count >= 2:
            # Separator-only rows (e.g. |:---|---:|) → skip entirely
            if re.match(r'^[\s|\-:]+$', value):
                return []
            cells = [cell.strip() for cell in value.split('|') if cell.strip()]
            candidates = []
            for cell in cells:
                cleaned = re.sub(r'^\d+\.?\s*', '', cell).strip()
                if not cleaned:
                    continue
                # Skip table header cells (short generic labels)
                if cleaned in ('序号', '名称', '名 称', '编号', '编 号', '标准号', '规范名称', '备注'):
                    continue
                # Keep cells with a standard code or book-title marker
                if _NORMATIVE_CODE_PATTERN.search(cleaned) or '《' in cleaned:
                    candidates.append(cleaned)
            return candidates

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
        # GATE: bare standard numbers (no year/sub-part version) cannot be
        # declared 'current' unless evidence uniquely resolves to a specific
        # versioned standard.  Family standards without sub-part specifier
        # are always demoted.
        if final.get('status') == 'current' and not self._has_precise_version_anchor(title):
            final = self._demote_bare_to_manual_review(title, final)
        return {
            'sourceId': source['sourceId'],
            'title': title,
            **final,
        }

    async def _search_web(self, title: str) -> dict[str, Any]:
        # Circuit breaker: skip web search if too many consecutive failures
        if time.monotonic() < self._web_circuit_open_until:
            return self._unknown_result('web', '联网检索暂时不可用（连续失败冷却中）。')
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._search_web_sync, title),
                timeout=_WEB_SEARCH_TIMEOUT,
            )
        except asyncio.TimeoutError:
            self._record_web_failure()
            return self._unknown_result('web', f'联网检索超时（{_WEB_SEARCH_TIMEOUT}s）。')
        except Exception as exc:
            self._record_web_failure()
            return self._unknown_result('web', f'联网检索失败：{exc}')
        # If we got here, reset consecutive fail counter on any non-failure
        if result.get('resolvedBy') == 'web' and '失败' not in result.get('summary', ''):
            self._web_consecutive_fails = 0
        return result

    def _record_web_failure(self) -> None:
        self._web_consecutive_fails += 1
        if self._web_consecutive_fails >= _WEB_SEARCH_MAX_CONSECUTIVE_FAILS:
            self._web_circuit_open_until = time.monotonic() + _WEB_SEARCH_COOLDOWN

    def _search_web_sync(self, title: str) -> dict[str, Any]:
        """Search Chinese standards portals directly for standard validity."""
        # Extract standard code from title for targeted search
        code_match = _NORMATIVE_CODE_PATTERN.search(title)
        query_code = code_match.group(0) if code_match else title

        # Try standards portal first
        result = self._try_standards_portal(query_code, title)
        if result:
            return result

        # Fallback: try DDGS if available
        if DDGS is not None:
            return self._try_ddgs_search(title)

        return self._unknown_result('web', '当前环境未启用联网检索依赖。')

    def _try_standards_portal(self, query_code: str, title: str) -> dict[str, Any] | None:
        """Try scraping Chinese standards portals for standard status."""
        import urllib.request
        import urllib.parse

        # Try openstd.samr.gov.cn (national standards portal)
        try:
            search_url = f"https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno={urllib.parse.quote(query_code)}"
            req = urllib.request.Request(
                search_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; HermesReviewBot/1.0)',
                    'Accept': 'text/html,application/xhtml+xml',
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html_content = resp.read().decode('utf-8', errors='ignore')

            if any(hint in html_content for hint in ('废止', '作废', '被替代')):
                return {
                    'status': 'superseded',
                    'resolvedBy': 'web',
                    'summary': '国家标准信息平台显示该标准已废止或被替代。',
                    'evidenceTitle': f'国家标准信息平台 - {query_code}',
                    'evidenceUrl': search_url,
                }
            if any(hint in html_content for hint in ('现行', '有效', '实施')):
                return {
                    'status': 'current',
                    'resolvedBy': 'web',
                    'summary': '国家标准信息平台显示该标准现行有效。',
                    'evidenceTitle': f'国家标准信息平台 - {query_code}',
                    'evidenceUrl': search_url,
                }
        except Exception:
            pass

        # Try std.samr.gov.cn (Standardization Administration)
        try:
            search_url = f"https://std.samr.gov.cn/search?keyword={urllib.parse.quote(query_code)}"
            req = urllib.request.Request(
                search_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; HermesReviewBot/1.0)',
                    'Accept': 'text/html,application/xhtml+xml',
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html_content = resp.read().decode('utf-8', errors='ignore')

            if any(hint in html_content for hint in ('废止', '作废', '被替代')):
                return {
                    'status': 'superseded',
                    'resolvedBy': 'web',
                    'summary': '国家标准化管理委员会显示该标准已废止或被替代。',
                    'evidenceTitle': f'国标委 - {query_code}',
                    'evidenceUrl': search_url,
                }
            if any(hint in html_content for hint in ('现行', '有效', '实施')):
                return {
                    'status': 'current',
                    'resolvedBy': 'web',
                    'summary': '国家标准化管理委员会显示该标准现行有效。',
                    'evidenceTitle': f'国标委 - {query_code}',
                    'evidenceUrl': search_url,
                }
        except Exception:
            pass

        return None

    def _try_ddgs_search(self, title: str) -> dict[str, Any]:
        """Fallback to DuckDuckGo search."""
        query = f'{title} 现行 有效 废止 替代'
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=8))
        except Exception as exc:
            raise RuntimeError(f'联网检索失败：{exc}') from exc
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
        if '工作规程' in title or '管理工作指引' in title:
            return {
                'status': 'current',
                'resolvedBy': 'heuristic',
                'summary': '基于标题常识做保守初判，暂未见明确废止信号；如用于正式结论，仍建议联网复核。',
                'evidenceTitle': '规则兜底',
                'evidenceUrl': '',
            }
        return self._unknown_result('heuristic', '当前仅能给出保守判断，建议人工核验。')

    def _is_standard_normative(self, title: str) -> bool:
        """Return True if the title refers to a standard/specification that should
        enter normative validity checking.  Returns False for laws, regulations,
        administrative rules, or internal management documents.

        Logic:
        1. If the title contains a recognized standard code (GB, DL/T, Q/CSG …)
           → always True (even enterprise standards like Q/CSG are kept).
        2. Otherwise, if the title contains any excluded keyword (条例, 办法, …)
           → False.
        3. Default → True (unknown items still enter checking conservatively).
        """
        if _NORMATIVE_CODE_PATTERN.search(title):
            return True
        if any(keyword in title for keyword in _EXCLUDED_DOCUMENT_KEYWORDS):
            return False
        # Also exclude titles that look like laws: ending with 法》 pattern
        if re.search(r'[^办]法》', title):
            return False
        return True

    def _has_precise_version_anchor(self, title: str) -> bool:
        """Check if the title contains a standard code with a year suffix (e.g., -2015)."""
        code = _NORMATIVE_CODE_PATTERN.search(title)
        if not code:
            return False
        return bool(_VERSION_YEAR_PATTERN.search(code.group(0)))

    def _evidence_resolves_uniquely(self, input_title: str, evidence_title: str) -> bool:
        """Check if the web evidence uniquely maps the input to a single specific
        versioned standard.  Returns False for family/series standards where the
        input lacks a sub-part but the evidence points to a specific sub-part."""
        if not evidence_title:
            return False
        evidence_code = _NORMATIVE_CODE_PATTERN.search(evidence_title)
        if not evidence_code:
            return False
        ev_code = evidence_code.group(0)
        # Evidence must carry a year suffix.
        if not _VERSION_YEAR_PATTERN.search(ev_code):
            return False
        input_code = _NORMATIVE_CODE_PATTERN.search(input_title)
        if not input_code:
            return False
        input_base = re.sub(r'[-—]\d{4}.*$', '', input_code.group(0)).strip().replace(' ', '').lower()
        ev_base = re.sub(r'[-—]\d{4}.*$', '', ev_code).strip().replace(' ', '').lower()
        # Family gate: input has no sub-part (e.g. GB/T 6995) but evidence
        # resolves to a specific sub-part (e.g. GB/T 6995.1-2008) — not unique.
        if '.' not in input_base and '.' in ev_base:
            return False
        return input_base == ev_base

    def _demote_bare_to_manual_review(self, title: str, result: dict[str, Any]) -> dict[str, Any]:
        """Demote a 'current' verdict to 'unknown' when the input standard
        reference lacks a precise version anchor, unless web evidence can
        uniquely resolve it to a single versioned standard."""
        evidence_title = str(result.get('evidenceTitle') or '')
        if self._evidence_resolves_uniquely(title, evidence_title):
            # Evidence uniquely resolves — keep 'current' but annotate resolved title.
            result['resolvedTitle'] = evidence_title
            return result
        return {
            'status': 'unknown',
            'resolvedBy': result.get('resolvedBy', 'gate'),
            'summary': f'原文引用缺少年份或分册版本号，无法唯一映射到具体现行标准，需人工核验。',
            'evidenceTitle': evidence_title,
            'evidenceUrl': result.get('evidenceUrl', ''),
        }

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
