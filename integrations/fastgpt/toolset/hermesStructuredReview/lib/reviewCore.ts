import { getAssets } from './assets.js';
import type {
  Candidate,
  DeterministicReviewerResult,
  FactPacket,
  FinalDecisionResult,
  FinalReportPacket,
  Finding,
  NormativeValidityCheck,
  RenderedReportResult,
  ReviewContextResult,
  ReviewDocumentType,
  SupportReviewResult
} from './contracts.js';
import { verifyNormativeValidity } from './normativeValidity.js';
import { severityScore, unique } from './utils.js';

function docLabel(documentType: ReviewDocumentType): string {
  const assets = getAssets() as any;
  return assets.docTypeLabels[documentType] || documentType;
}

function inferModuleName(ruleOrTitle: string): string {
  const value = ruleOrTitle.toLowerCase();
  if (
    value.includes('visibility') ||
    value.includes('drawing') ||
    value.includes('normative') ||
    value.includes('calculation') ||
    value.includes('evidence')
  ) {
    return 'evidence_validation';
  }
  if (
    value.includes('consistency') ||
    value.includes('parameter') ||
    value.includes('resource') ||
    value.includes('conflict')
  ) {
    return 'parameter_consistency';
  }
  if (
    value.includes('operation_chain') ||
    value.includes('execution') ||
    value.includes('sequence') ||
    value.includes('temporary_power') ||
    value.includes('hot_work') ||
    value.includes('gas_area') ||
    value.includes('power_outage')
  ) {
    return 'execution_continuity';
  }
  if (value.includes('structure') || value.includes('章节') || value.includes('完整')) {
    return 'structure_completeness';
  }
  return 'legality_compliance';
}

function findingFromCandidate(candidate: Candidate, index: number, sourceEngine: string): Finding {
  const status = candidate.manualReviewNeeded
    ? 'visibility_gap'
    : candidate.evidenceMissing
      ? 'evidence_gap'
      : 'grounded';
  return {
    id: `${sourceEngine === '008' ? 'S' : 'H'}-${String(index).padStart(3, '0')}`,
    title: candidate.title,
    severity: candidate.severityHint,
    category: inferModuleName(candidate.candidateId),
    summary:
      candidate.ruleHits.map((hit) => hit.rationale).filter(Boolean).join('；') ||
      `${candidate.title} 已命中受治理审查规则。`,
    suggestion: candidate.manualReviewNeeded
      ? '当前证据存在可视域缺口，请结合原件或附件人工复核。'
      : '请根据命中规则补齐正文、附件或规范依据。',
    evidence_status: status,
    source_engine: sourceEngine,
    finding_type: candidate.findingType,
    manual_review_needed: candidate.manualReviewNeeded,
    raw_data: {
      candidateId: candidate.candidateId,
      module_name: inferModuleName(candidate.candidateId),
      blocking_reasons: candidate.blockingReasons,
      manual_review_reason: candidate.manualReviewReason
    }
  };
}

function makePacket({
  reviewId,
  engine,
  reviewerId,
  findings,
  overall,
  degraded = false,
  error
}: {
  reviewId: string;
  engine: string;
  reviewerId: string;
  findings: Finding[];
  overall: string;
  degraded?: boolean;
  error?: string;
}): FactPacket {
  return {
    review_id: reviewId,
    engine,
    findings,
    overall_assessment: overall,
    degraded,
    error,
    metadata: {
      template_id: reviewerId,
      agent_id: reviewerId,
      review_modules: unique(findings.map((item) => String(item.raw_data?.module_name || ''))).filter(Boolean)
    }
  };
}

function renderFormalMarkdown(packet: FinalReportPacket): string {
  const verdictLabel = {
    conditional_pass: '有条件通过',
    needs_revision: '需要修改',
    fail: '不通过'
  }[packet.verdict];
  const lines = [
    `# ${packet.title}`,
    '',
    `本次审查已由专业主审组件裁决完成，总体评级结论为：**${verdictLabel}**。`,
    '',
    '## 重点风险',
    ...(packet.top_risks.length ? packet.top_risks.map((item) => `- ${item}`) : ['- 未识别到需要单列的高风险事项']),
    '',
    '## 关键问题',
    ...(packet.key_findings.length
      ? packet.key_findings.map((item) => `- [${item.severity}] ${item.title}：${item.summary}`)
      : ['- 无']),
    '',
    '## 补充问题',
    ...(packet.supplemental_findings.length
      ? packet.supplemental_findings.map((item) => `- [${item.severity}] ${item.title}：${item.summary}`)
      : ['- 无'])
  ];
  return lines.join('\n');
}

function renderDegradedMarkdown(documentType: ReviewDocumentType, degradedReason: string): string {
  return [
    `# ${docLabel(documentType)} — 预检结果与支撑层数据（非正式审查报告）`,
    '',
    `> 审查主控链路未能形成正式裁决，系统已按 fail-closed 返回降级结果。原因：${degradedReason}`,
    '',
    '本结果仅供人工复核，不构成正式审查结论。'
  ].join('\n');
}

export async function runSupportReview008Tool(params: {
  reviewId: string;
  query: string;
  documentType: ReviewDocumentType;
  enabledModules?: string[];
  reviewContext: ReviewContextResult;
}): Promise<SupportReviewResult> {
  const findings = params.reviewContext.candidates.map((candidate, index) =>
    findingFromCandidate(candidate, index + 1, '008')
  );
  const reportMarkdown = [
    `# ${docLabel(params.documentType)} — 008 支撑层结果`,
    '',
    ...(findings.length
      ? findings.map((item) => `- [${item.severity}] ${item.title}：${item.summary}`)
      : ['- 未识别到需输出的问题'])
  ].join('\n');
  const supportPacket008 = makePacket({
    reviewId: params.reviewId,
    engine: '008',
    reviewerId: 'structured_review_primary_worker',
    findings,
    overall: findings.length ? '008 支撑层已形成结构化问题线索。' : '008 支撑层未识别到需输出的问题。'
  });

  return {
    supportResult008: {
      summary: {
        issueCount: findings.length,
        documentType: params.documentType
      },
      issues: findings,
      reportMarkdown,
      ownership: 'support_material'
    },
    supportPacket008,
    artifactIndex: [],
    supportLayerContext: {
      reportMarkdown,
      issueCount: findings.length,
      resolvedBasisProfile: params.reviewContext.resolvedBasisProfile
    }
  };
}

export async function runDeterministicReviewerTool(params: {
  reviewId: string;
  reviewerId: 'visibility_gap_reviewer' | 'policy_compliance_reviewer' | 'normative_validity_reviewer';
  reviewContext: ReviewContextResult;
}): Promise<DeterministicReviewerResult> {
  const { reviewerId, reviewContext, reviewId } = params;
  if (reviewerId === 'visibility_gap_reviewer') {
    const findings: Finding[] = reviewContext.parseResult.visibility.manualReviewNeeded
      ? [
          {
            id: 'H-VIS-001',
            title: '附件及图纸解析受限，请结合原件复核',
            severity: 'medium',
            category: 'evidence_validation',
            summary: '正文引用了附件或图纸，但当前可视域无法稳定获取其实质内容。',
            suggestion: '请补充附件原件或结合原件人工复核。',
            evidence_status: 'visibility_gap',
            source_engine: 'hermes',
            finding_type: 'visibility_gap',
            manual_review_needed: true,
            raw_data: { module_name: 'evidence_validation' }
          }
        ]
      : [];
    return {
      reviewerId,
      packet: makePacket({
        reviewId,
        engine: 'hermes',
        reviewerId,
        findings,
        overall: findings.length ? '可视域检查已完成。' : '未发现需要单列的可视域问题。'
      })
    };
  }

  if (reviewerId === 'policy_compliance_reviewer') {
    const findings = reviewContext.candidates.map((candidate, index) => {
      const finding = findingFromCandidate(candidate, index + 1, 'hermes');
      finding.raw_data = {
        ...(finding.raw_data || {}),
        module_name: 'legality_compliance',
        review_modules: ['legality_compliance']
      };
      return finding;
    });
    return {
      reviewerId,
      packet: makePacket({
        reviewId,
        engine: 'hermes',
        reviewerId,
        findings,
        overall: findings.length ? '规范命中与证据线索已整理。' : '未发现需要单列的规范命中问题。'
      })
    };
  }

  const checks: NormativeValidityCheck[] = await verifyNormativeValidity(reviewContext.parseResult);
  const findings: Finding[] = [];
  if (checks.length) {
    findings.push({
      id: 'H-NORM-SUM-001',
      title: '编制依据现行有效性核验',
      severity: 'info',
      category: 'evidence_validation',
      summary: `共核验 ${checks.length} 项编制依据，其中现行有效 ${checks.filter((item) => item.status === 'current').length} 项，疑似废止/替代 ${checks.filter((item) => item.status === 'superseded').length} 项，待人工核验 ${checks.filter((item) => item.status === 'unknown').length} 项。`,
      suggestion: '对状态不明或疑似替代的标准，请补做联网或人工复核。',
      evidence_status: checks.some((item) => item.resolvedBy === 'web') ? 'grounded' : 'inferred',
      source_engine: 'hermes',
      finding_type: 'normative_validity_summary',
      raw_data: {
        module_name: 'evidence_validation',
        normativeValidityChecks: checks
      }
    });
    checks
      .filter((item) => item.status !== 'current')
      .forEach((check, index) => {
        findings.push({
          id: `H-NORM-${String(index + 1).padStart(3, '0')}`,
          title: `编制依据现行有效性存在疑点：${check.title}`,
          severity: check.status === 'superseded' ? 'medium' : 'info',
          category: 'evidence_validation',
          summary: check.summary,
          suggestion: '如该编制依据已废止、被替代或状态不明，请改用现行版本并同步修正文内引用。',
          evidence_status: check.resolvedBy === 'web' ? 'grounded' : 'inferred',
          source_engine: 'hermes',
          finding_type: 'normative_validity_issue',
          raw_data: {
            module_name: 'evidence_validation',
            normativeValidityCheck: check
          }
        });
      });
  }
  return {
    reviewerId,
    packet: makePacket({
      reviewId,
      engine: 'hermes',
      reviewerId,
      findings,
      overall: checks.length
        ? '被审方案“编制依据”现行有效性核验已完成。'
        : '未识别到被审方案“编制依据”章节中可执行现行有效性核验的规范。'
    })
  };
}

export function assembleFinalDecisionTool(params: {
  reviewId: string;
  documentType: ReviewDocumentType;
  enabledModules?: string[];
  supportReview: SupportReviewResult;
  reviewerPackets?: FactPacket[];
  agentResults?: Array<Record<string, unknown>>;
}): FinalDecisionResult {
  const reviewerPackets = params.reviewerPackets || [];
  const enabledModules = params.enabledModules || [
    'structure_completeness',
    'parameter_consistency',
    'legality_compliance',
    'execution_continuity',
    'evidence_validation'
  ];

  const hermesOk = reviewerPackets.some((packet) => !packet.degraded);
  if (!hermesOk) {
    const degradedReason =
      reviewerPackets.find((packet) => packet.error)?.error ||
      'Hermes 主审 reviewer 未返回有效结果';
    return {
      degraded: true,
      degradedReason,
      finalReportPacket: null,
      finalAnswer: renderDegradedMarkdown(params.documentType, degradedReason),
      traceability: [],
      hermesController: {
        enabled: true,
        finalReportReady: false,
        degraded: true,
        degradedReason
      }
    };
  }

  const blockedModules = enabledModules.filter((moduleName) => {
    const packets = reviewerPackets.filter((packet) =>
      Array.isArray(packet.metadata.review_modules)
        ? (packet.metadata.review_modules as string[]).includes(moduleName)
        : false
    );
    return packets.length === 0 || packets.every((packet) => packet.degraded);
  });
  if (blockedModules.length) {
    const degradedReason = `以下模块未形成有效主审结论：${blockedModules.join('、')}`;
    return {
      degraded: true,
      degradedReason,
      finalReportPacket: null,
      finalAnswer: renderDegradedMarkdown(params.documentType, degradedReason),
      traceability: [],
      hermesController: {
        enabled: true,
        finalReportReady: false,
        degraded: true,
        degradedReason,
        blockedModules
      }
    };
  }

  const supportFindings = params.supportReview.supportPacket008.findings;
  const hermesFindings = reviewerPackets.flatMap((packet) => packet.findings);
  const supportTitles = new Set(supportFindings.map((item) => item.title));
  const supplementalFindings = hermesFindings.filter((item) => !supportTitles.has(item.title));
  const allFindings = [...supportFindings, ...supplementalFindings];
  const verdict: FinalReportPacket['verdict'] = allFindings.some((item) => item.severity === 'high')
    ? 'fail'
    : allFindings.some(
          (item) =>
            item.severity === 'medium' ||
            item.evidence_status === 'evidence_gap' ||
            item.manual_review_needed
        )
      ? 'needs_revision'
      : 'conditional_pass';

  const verdictLabel = {
    conditional_pass: '有条件通过',
    needs_revision: '需要修改',
    fail: '不通过'
  }[verdict];

  const top_risks = allFindings
    .slice()
    .sort((left, right) => severityScore(right.severity) - severityScore(left.severity))
    .map((item) => item.title)
    .filter(Boolean)
    .slice(0, 5);

  const traceability = allFindings.map((finding) => ({
    finding_id: finding.id,
    title: finding.title,
    source_engine: finding.source_engine || 'unknown',
    module_name: finding.raw_data?.module_name || null,
    template_id: finding.raw_data?.template_id || null
  }));

  const finalReportPacket: FinalReportPacket = {
    title: `${docLabel(params.documentType)}正式审查报告`,
    verdict,
    summary: `本次审查已由专业主审组件裁决完成，总体评级结论为：**${verdictLabel}**。`,
    top_risks,
    key_findings: supportFindings,
    supplemental_findings: supplementalFindings,
    traceability,
    report_markdown: '',
    metadata: {
      documentType: params.documentType,
      selected_review_modules: enabledModules
    }
  };
  finalReportPacket.report_markdown = renderFormalMarkdown(finalReportPacket);

  return {
    degraded: false,
    degradedReason: '',
    finalReportPacket,
    finalAnswer: finalReportPacket.report_markdown,
    traceability,
    hermesController: {
      enabled: true,
      finalReportReady: true,
      degraded: false
    }
  };
}

export function renderFormalReportTool(params: {
  documentType: ReviewDocumentType;
  finalDecision: FinalDecisionResult;
}): RenderedReportResult {
  const markdown =
    params.finalDecision.finalReportPacket?.report_markdown ||
    renderDegradedMarkdown(params.documentType, params.finalDecision.degradedReason);
  const reportHtml = `
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>${params.finalDecision.finalReportPacket?.title || docLabel(params.documentType)}</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px; color: #0f172a; }
      h1 { font-size: 28px; margin-bottom: 16px; }
      h2 { font-size: 18px; margin-top: 24px; border-left: 4px solid #2563eb; padding-left: 8px; }
      li { margin: 8px 0; }
      .muted { color: #64748b; }
      .warning { color: #b45309; }
    </style>
  </head>
  <body>
    ${markdown
      .split('\n')
      .map((line) => {
        if (line.startsWith('# ')) return `<h1>${line.slice(2)}</h1>`;
        if (line.startsWith('## ')) return `<h2>${line.slice(3)}</h2>`;
        if (line.startsWith('- ')) return `<li>${line.slice(2)}</li>`;
        if (!line.trim()) return '';
        return `<p>${line}</p>`;
      })
      .join('\n')}
  </body>
</html>`.trim();
  const reportPrintCss = `
body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; color: #0f172a; }
h1, h2 { break-after: avoid; }
ul, ol { padding-left: 20px; }
`.trim();

  return {
    finalReportMarkdown: markdown,
    reportHtml,
    reportPrintCss,
    finalReportViewModel: {
      title: params.finalDecision.finalReportPacket?.title || `${docLabel(params.documentType)}降级结果`,
      degraded: params.finalDecision.degraded,
      verdict: params.finalDecision.finalReportPacket?.verdict || null,
      executiveSummary:
        params.finalDecision.finalReportPacket?.summary ||
        `主审链路不可用，已按 fail-closed 返回降级结果：${params.finalDecision.degradedReason}`,
      topRisks: params.finalDecision.finalReportPacket?.top_risks || [],
      keyFindings: params.finalDecision.finalReportPacket?.key_findings || [],
      supplementalFindings: params.finalDecision.finalReportPacket?.supplemental_findings || [],
      traceabilityCount: params.finalDecision.traceability.length
    }
  };
}
