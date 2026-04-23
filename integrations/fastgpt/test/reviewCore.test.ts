import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { buildReviewContext } from '../toolset/hermesStructuredReview/lib/context.js';
import {
  assembleFinalDecisionTool,
  renderFormalReportTool,
  runDeterministicReviewerTool,
  runSupportReview008Tool
} from '../toolset/hermesStructuredReview/lib/reviewCore.js';

async function makeContext() {
  return buildReviewContext({
    query: '请做正式审查',
    documentType: 'distribution_network_special_scheme',
    targetFiles: [
      {
        fileName: 'power-outage.md',
        fileType: 'md',
        content: `
# 工程概况
## 编制依据
GB/T 6995
## 风险辨识
## 安全措施
停电 验电 接地 挂牌 遮栏
## 应急处置
见附图一
        `
      }
    ]
  });
}

describe('reviewCore', () => {
  beforeAll(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        text: async () => '<html><body>现行 有效 实施</body></html>'
      }))
    );
  });

  afterAll(() => {
    vi.unstubAllGlobals();
  });

  it('builds support review and deterministic reviewer packets', async () => {
    const context = await makeContext();
    const support = await runSupportReview008Tool({
      reviewId: 'r-001',
      query: '请做正式审查',
      documentType: 'distribution_network_special_scheme',
      reviewContext: context
    });
    const deterministic = await runDeterministicReviewerTool({
      reviewId: 'r-001',
      reviewerId: 'normative_validity_reviewer',
      reviewContext: context
    });

    expect(support.supportPacket008.engine).toBe('008');
    expect(deterministic.packet.engine).toBe('hermes');
    expect(Array.isArray(deterministic.packet.findings)).toBe(true);
  });

  it('fails closed when no reviewer packet is available', async () => {
    const context = await makeContext();
    const support = await runSupportReview008Tool({
      reviewId: 'r-002',
      query: '请做正式审查',
      documentType: 'distribution_network_special_scheme',
      reviewContext: context
    });
    const finalDecision = assembleFinalDecisionTool({
      reviewId: 'r-002',
      documentType: 'distribution_network_special_scheme',
      enabledModules: ['evidence_validation'],
      supportReview: support,
      reviewerPackets: []
    });

    expect(finalDecision.degraded).toBe(true);
    expect(finalDecision.degradedReason.length).toBeGreaterThan(0);
  });

  it('renders markdown/html output for a successful decision', async () => {
    const context = await makeContext();
    const support = await runSupportReview008Tool({
      reviewId: 'r-003',
      query: '请做正式审查',
      documentType: 'distribution_network_special_scheme',
      reviewContext: context
    });
    const deterministic = await runDeterministicReviewerTool({
      reviewId: 'r-003',
      reviewerId: 'policy_compliance_reviewer',
      reviewContext: context
    });
    const finalDecision = assembleFinalDecisionTool({
      reviewId: 'r-003',
      documentType: 'distribution_network_special_scheme',
      enabledModules: ['legality_compliance'],
      supportReview: support,
      reviewerPackets: [deterministic.packet]
    });
    const rendered = renderFormalReportTool({
      documentType: 'distribution_network_special_scheme',
      finalDecision
    });

    expect(finalDecision.degraded).toBe(false);
    expect(rendered.finalReportMarkdown).toContain('总体评级结论');
    expect(rendered.reportHtml).toContain('<html');
  });
});
