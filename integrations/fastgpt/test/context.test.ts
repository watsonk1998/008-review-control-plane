import { describe, expect, it } from 'vitest';
import { buildReviewContext } from '../toolset/hermesStructuredReview/lib/context.js';

describe('buildReviewContext', () => {
  it('builds governed review context from markdown content', async () => {
    const result = await buildReviewContext({
      query: '请做正式审查',
      documentType: 'construction_org',
      targetFiles: [
        {
          fileName: 'sample.md',
          fileType: 'md',
          content: `
# 工程概况
## 编制依据
《建设工程施工现场消防安全技术规范》GB 50720-2011
## 施工部署
## 安全措施
见附图一
          `
        }
      ]
    });

    expect(result.parseResult.fileType).toBe('md');
    expect(result.ruleHits.length).toBeGreaterThan(0);
    expect(Array.isArray(result.candidates)).toBe(true);
    expect(result.governedSupportPacket).toHaveProperty('basis_summary');
  });
});
