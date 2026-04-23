import crypto from 'node:crypto';
export function slugify(value: string): string { return value.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '_').replace(/^_+|_+$/g, '') || 'item'; }
export function normalizeText(value: string): string { return value.replace(/\r\n/g, '\n').replace(/\u00a0/g, ' ').trim(); }
export function unique(items: string[]): string[] { return [...new Set(items)]; }
export function hashId(prefix: string, raw: string): string { return `${prefix}-${crypto.createHash('md5').update(raw).digest('hex').slice(0, 8)}`; }
export function severityScore(severity: string): number { return ({ high: 3, medium: 2, low: 1, info: 0 } as Record<string, number>)[severity] ?? 0; }
