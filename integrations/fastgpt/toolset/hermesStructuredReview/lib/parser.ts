import fs from 'node:fs/promises';
import path from 'node:path';
import { hashId, normalizeText, slugify } from './utils.js';
import type { ParseBlock, ParseResult, ParseSection, ReviewFileRef } from './contracts.js';

async function fetchBuffer(url: string): Promise<Buffer> {
  if (/^https?:\/\//i.test(url)) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
    return Buffer.from(await res.arrayBuffer());
  }
  if (url.startsWith('file://')) return fs.readFile(new URL(url));
  return fs.readFile(url);
}

async function extractRawText(file: ReviewFileRef): Promise<{ text: string; fileType: string; filePath?: string }> {
  const fileType = (file.fileType || file.fileName?.split('.').pop() || (file.path ? path.extname(file.path).slice(1) : 'txt')).toLowerCase();
  if (file.content) return { text: file.content, fileType, filePath: file.path || file.url };
  const source = file.path || file.url;
  if (!source) throw new Error('Review file must provide content, path or url');
  if (fileType === 'txt' || fileType === 'md') return { text: (await fetchBuffer(source)).toString('utf8'), fileType, filePath: source };
  if (fileType === 'docx') {
    const mammoth = await import('mammoth');
    const result = await mammoth.extractRawText({ buffer: await fetchBuffer(source) });
    return { text: result.value || '', fileType, filePath: source };
  }
  if (fileType === 'pdf') {
    const pdfParse = (await import('pdf-parse')).default;
    const result = await pdfParse(await fetchBuffer(source));
    return { text: result.text || '', fileType, filePath: source };
  }
  return { text: (await fetchBuffer(source)).toString('utf8'), fileType, filePath: source };
}

function detectHeadingLevel(text: string): number | null {
  if (/^#{1,6}\s+/.test(text)) return Math.min(text.match(/^#+/)?.[0].length || 1, 4);
  if (/^[一二三四五六七八九十]+[、.]/.test(text)) return 1;
  if (/^\d+[、.]/.test(text)) return 2;
  if (/^\(?[一二三四五六七八九十]+\)/.test(text) || /^\([0-9]+\)/.test(text)) return 3;
  return null;
}

export async function parseReviewFile(file: ReviewFileRef): Promise<ParseResult> {
  const { text, fileType, filePath } = await extractRawText(file);
  const lines = normalizeText(text).split('\n');
  const sections: ParseSection[] = [];
  const blocks: ParseBlock[] = [];
  const sectionStack: ParseSection[] = [];
  const parseWarnings: string[] = [];
  const attachments: Array<Record<string, unknown>> = [];
  const currentSectionId = () => sectionStack[sectionStack.length - 1]?.id ?? null;

  for (const [idx, rawLine] of lines.entries()) {
    const line = normalizeText(rawLine);
    if (!line) continue;
    const position = idx + 1;
    const headingLevel = detectHeadingLevel(line);
    const blockId = hashId('block', `${position}:${line}`);
    if (/附件|附图|附表|图纸|详图|见图/.test(line)) {
      attachments.push({ id: hashId('attachment', line), title: line, sectionId: currentSectionId(), visibility: /详图|图纸/.test(line) ? 'referenced_only' : 'parsed' });
    }
    if (headingLevel) {
      while (sectionStack.length && sectionStack[sectionStack.length - 1].level >= headingLevel) sectionStack.pop();
      const section: ParseSection = { id: hashId('section', `${position}:${line}`), title: line.replace(/^#+\s*/, ''), key: slugify(line.replace(/^#+\s*/, '')), level: headingLevel, parentId: currentSectionId(), blockId, position };
      sections.push(section);
      sectionStack.push(section);
    }
    blocks.push({ id: blockId, type: headingLevel ? 'heading' : 'paragraph', text: line, sectionId: currentSectionId(), headingLevel, position });
  }

  const titleCounts = new Map<string, number>();
  const duplicateSectionTitles: string[] = [];
  for (const section of sections.filter((s) => s.level <= 2)) {
    const next = (titleCounts.get(section.key) || 0) + 1;
    titleCounts.set(section.key, next);
    if (next === 2) duplicateSectionTitles.push(section.key);
  }
  if (fileType === 'txt' || fileType === 'md') parseWarnings.push('text_tables_not_preserved', 'text_attachment_boundaries_inferred_from_headings');

  const visibility = {
    attachmentCount: attachments.length,
    counts: attachments.reduce<Record<string, number>>((acc, item) => {
      const key = String(item.visibility || 'parsed');
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {}),
    reasonCounts: attachments.some((item) => item.visibility === 'referenced_only') ? { reference_detected_without_attachment_body: 1 } : {},
    duplicateSectionTitles,
    parseWarnings,
    manualReviewNeeded: attachments.some((item) => item.visibility !== 'parsed'),
    manualReviewReason: attachments.some((item) => item.visibility !== 'parsed') ? 'reference_detected_without_attachment_body' : null
  };

  return {
    documentId: path.basename(filePath || file.fileName || 'document', path.extname(filePath || file.fileName || '')),
    filePath,
    fileType,
    parseMode: fileType === 'md' ? 'markdown_text' : fileType === 'txt' ? 'plain_text' : `${fileType}_text`,
    parserLimited: false,
    sections,
    blocks,
    attachments,
    normalizedText: blocks.map((block) => block.text).join('\n'),
    preview: blocks.map((block) => block.text).join('\n').slice(0, 4000),
    visibility,
    parseWarnings
  };
}
