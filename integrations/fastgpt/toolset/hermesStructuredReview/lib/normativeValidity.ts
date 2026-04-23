import type { NormativeValidityCheck, ParseResult } from './contracts.js';
import { normalizeText, unique } from './utils.js';

const NEGATIVE_HINTS = ['废止', '作废', '失效', '替代', '代替', '废除'];
const POSITIVE_HINTS = ['现行', '有效', '实施', '继续有效'];
const EXCLUDED_DOCUMENT_KEYWORDS = [
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
  '暂行办法'
];
const NON_NORMATIVE_HINTS = [
  '合同',
  '委托函',
  '中标通知书',
  '技术资料',
  '施工图',
  '设计图',
  '审批资料',
  '交底记录',
  '现场查勘',
  '查勘记录'
];

export const NORMATIVE_CODE_PATTERN =
  /(?:(?:GB|GB\/T|GBJ|DL\/T|DL|Q\/CSG|Q\/GDW|Q\/SH|Q\/BGJ|JGJ|NB\/T|NB|AQ|DB|DBJ|DGJ|YD\/T|SL|GA|CECS|TSG|HG|CJJ|SH\/T|YB|JB|CJ|YS|SY|HJ|TB|LB|MZ)\s*[-/A-Z]*\s*\d{2,}(?:\.\d+)?(?:[-—]\d{2,4})?)/i;
const VERSION_YEAR_PATTERN = /[-—]\d{4}(?:\b|$)/;

function isStandardNormative(title: string): boolean {
  if (NORMATIVE_CODE_PATTERN.test(title)) return true;
  if (EXCLUDED_DOCUMENT_KEYWORDS.some((keyword) => title.includes(keyword))) return false;
  if (/[^办]法》/.test(title)) return false;
  return true;
}

function splitReferenceCandidates(text: string): string[] {
  const value = normalizeText(text);
  if (!value) return [];
  if (value.trim().startsWith('|') || value.split('|').length >= 3) {
    if (/^[\s|\-:]+$/.test(value)) return [];
    return value
      .split('|')
      .map((cell) => normalizeText(cell))
      .filter(Boolean)
      .filter(
        (cell) =>
          !['序号', '名称', '名 称', '编号', '编 号', '标准号', '规范名称', '备注'].includes(cell)
      )
      .filter((cell) => NORMATIVE_CODE_PATTERN.test(cell) || cell.includes('《'));
  }
  return value
    .replace(/^[（(]?\d+[)）.、]\s*/, '')
    .split(/[；;]/)
    .map((part) => part.trim().replace(/[。;；]+$/g, ''))
    .filter(Boolean);
}

function extractNormativeTitle(text: string): string {
  let value = normalizeText(text);
  if (!value) return '';
  if (NON_NORMATIVE_HINTS.some((hint) => value.includes(hint))) return '';
  if (!value.includes('《') && !NORMATIVE_CODE_PATTERN.test(value)) return '';
  if (value.includes('《')) value = value.slice(value.indexOf('《'));
  value = value.replace(/^[（(]?\d+[)）.、]\s*/, '').replace(/\s+/g, ' ').trim();
  if (NON_NORMATIVE_HINTS.some((hint) => value.includes(hint))) return '';
  return value;
}

function hasPreciseVersionAnchor(title: string): boolean {
  const match = title.match(NORMATIVE_CODE_PATTERN);
  return Boolean(match && VERSION_YEAR_PATTERN.test(match[0]));
}

async function searchWeb(title: string): Promise<Partial<NormativeValidityCheck>> {
  const query = encodeURIComponent(`${title} 现行 有效 废止 替代`);
  try {
    const res = await fetch(`https://duckduckgo.com/html/?q=${query}`, {
      headers: { 'User-Agent': 'Mozilla/5.0 hermes-fastgpt/1.0' }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    const compact = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').slice(0, 8000);
    if (NEGATIVE_HINTS.some((token) => compact.includes(token))) {
      return {
        status: 'superseded',
        resolvedBy: 'web',
        summary: '联网结果出现废止、作废或替代信号，需按最新版本复核。',
        evidenceTitle: title,
        evidenceUrl: `https://duckduckgo.com/html/?q=${query}`
      };
    }
    if (POSITIVE_HINTS.some((token) => compact.includes(token))) {
      return {
        status: 'current',
        resolvedBy: 'web',
        summary: '联网结果未见废止或替代信号，当前可按现行有效处理。',
        evidenceTitle: title,
        evidenceUrl: `https://duckduckgo.com/html/?q=${query}`
      };
    }
    return {
      status: 'unknown',
      resolvedBy: 'web',
      summary: '已检索到公开结果，但未能稳定判断现行状态。',
      evidenceTitle: title,
      evidenceUrl: `https://duckduckgo.com/html/?q=${query}`
    };
  } catch {
    return {
      status: 'unknown',
      resolvedBy: 'heuristic',
      summary: '联网检索不可用，当前仅能给出保守判断。'
    };
  }
}

function demoteBareCodeTitle(title: string, partial: Partial<NormativeValidityCheck>): NormativeValidityCheck {
  return {
    sourceId: title,
    title,
    status: 'unknown',
    resolvedBy: partial.resolvedBy === 'web' ? 'web' : 'heuristic',
    summary: '标准号缺少年份或分册锚点，不能直接判定为现行有效，需人工核验。',
    evidenceTitle: partial.evidenceTitle,
    evidenceUrl: partial.evidenceUrl,
    note: '裸标准号不得直接判定 current。'
  };
}

export async function verifyNormativeValidity(parseResult: ParseResult): Promise<NormativeValidityCheck[]> {
  const targetSectionIds = new Set(
    parseResult.sections
      .filter((section) => ['编制依据', '编制说明'].some((keyword) => section.title.includes(keyword)))
      .map((section) => section.id)
  );
  if (targetSectionIds.size === 0) return [];

  const sources = unique(
    parseResult.blocks
      .filter((block) => block.type !== 'heading')
      .filter((block) => (block.sectionId ? targetSectionIds.has(block.sectionId) : false))
      .flatMap((block) => splitReferenceCandidates(block.text))
      .map(extractNormativeTitle)
      .filter(Boolean)
      .filter(isStandardNormative)
  );

  const results = await Promise.all(
    sources.map(async (title): Promise<NormativeValidityCheck> => {
      const web = await searchWeb(title);
      if (!hasPreciseVersionAnchor(title)) {
        return demoteBareCodeTitle(title, web);
      }
      return {
        sourceId: title,
        title,
        status: (web.status as NormativeValidityCheck['status']) || 'unknown',
        resolvedBy: (web.resolvedBy as NormativeValidityCheck['resolvedBy']) || 'heuristic',
        summary: web.summary || '当前仅能给出保守判断，建议人工核验。',
        evidenceTitle: web.evidenceTitle,
        evidenceUrl: web.evidenceUrl,
        resolvedTitle: title,
        note:
          web.status === 'current'
            ? '已匹配到带年份版本锚点的标准标题。'
            : '需结合权威来源进一步人工核验。'
      };
    })
  );

  return results;
}
