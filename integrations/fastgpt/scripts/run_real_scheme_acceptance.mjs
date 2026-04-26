import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';

const DEFAULT_CHAT_URL = 'https://xtaiqa.jg-pm.com/api/v1/chat/completions';
const ALL_MODULES = [
  'structure_completeness',
  'parameter_consistency',
  'legality_compliance',
  'execution_continuity',
  'evidence_validation'
];

const CASES = [
  {
    id: 'power-outage',
    title: '停电施工方案-威彦达',
    documentType: 'distribution_network_special_scheme',
    fileUrlEnv: 'FASTGPT_ACCEPTANCE_OUTAGE_URL'
  },
  {
    id: 'construction-org',
    title: '施工组织设计-冷轧厂2030单元三台行车电气系统改造',
    documentType: 'construction_org',
    fileUrlEnv: 'FASTGPT_ACCEPTANCE_CONSTRUCTION_ORG_URL'
  }
];

function parseArgs(argv) {
  const args = {
    chatUrl: process.env.FASTGPT_CHAT_URL || DEFAULT_CHAT_URL,
    outDir: process.env.FASTGPT_ACCEPTANCE_OUT_DIR || path.join(os.tmpdir(), `hermes-fastgpt-acceptance-${Date.now()}`),
    timeoutMs: Number(process.env.FASTGPT_ACCEPTANCE_TIMEOUT_MS || 300000),
    keyFromStdin: false,
    caseId: '',
    json: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (item === '--chat-url') args.chatUrl = argv[++index];
    else if (item === '--api-key-stdin') args.keyFromStdin = true;
    else if (item === '--out-dir') args.outDir = argv[++index];
    else if (item === '--timeout-ms') args.timeoutMs = Number(argv[++index]);
    else if (item === '--case') args.caseId = argv[++index];
    else if (item === '--json') args.json = true;
    else throw new Error(`Unknown argument: ${item}`);
  }
  return args;
}

function readStdin() {
  return fs.readFileSync(0, 'utf8').trim();
}

function readApiKey(args) {
  if (args.keyFromStdin) return readStdin();
  const key = process.env.FASTGPT_API_KEY || '';
  if (!key.trim()) throw new Error('Missing FASTGPT_API_KEY or --api-key-stdin');
  return key.trim();
}

function keyFingerprint(key) {
  if (key.length >= 16) return `${key.slice(0, 8)}...${key.slice(-6)}`;
  return `sha256:${crypto.createHash('sha256').update(key).digest('hex').slice(0, 12)}`;
}

function compactNode(item) {
  return {
    nodeId: item?.nodeId ?? null,
    moduleType: item?.moduleType ?? null,
    moduleName: item?.moduleName ?? null,
    errorText: item?.errorText ?? null
  };
}

function collectNodes(body) {
  return Array.isArray(body?.responseData) ? body.responseData.filter((item) => item && typeof item === 'object').map(compactNode) : [];
}

function extractContent(body) {
  return body?.choices?.[0]?.message?.content || '';
}

function containsAny(text, words) {
  return words.some((word) => text.includes(word));
}

function evaluateCase({ body, httpStatus }) {
  const content = extractContent(body);
  const nodes = collectNodes(body);
  const nodeIds = nodes.map((node) => node.nodeId).filter(Boolean);
  const nodeErrors = nodes.filter((node) => node.errorText);
  const hasFormal = nodeIds.includes('formalReply');
  const hasDegraded = nodeIds.includes('degradedReply');
  const isChinese = /[\u4e00-\u9fff]/.test(content);
  const hasReportClosure = hasFormal || hasDegraded;
  const hasBusinessSignals = containsAny(content, ['风险', '依据', '证据', '整改', '复核', '审查', '问题']);
  const hasRiskSignals = containsAny(content, ['风险', '关键问题', '重点风险', '不通过', '需要修改', '有条件通过']);
  const hasEvidenceBoundary = containsAny(content, ['依据', '证据', '可视域', '人工复核', '解析', '附件']);
  const hasRemediation = containsAny(content, ['整改', '补充', '复核', '修改', '完善', '需']);
  const finalStatus = hasDegraded ? 'degraded' : hasFormal ? 'formal' : 'unknown';

  return {
    httpStatus,
    contentLength: content.length,
    contentPreview: content.slice(0, 260),
    finalStatus,
    nodeCount: nodes.length,
    nodes,
    nodeErrors,
    passed:
      httpStatus >= 200 &&
      httpStatus < 300 &&
      content.length > 0 &&
      isChinese &&
      hasReportClosure &&
      nodeErrors.length === 0 &&
      hasBusinessSignals &&
      hasRiskSignals &&
      hasEvidenceBoundary &&
      hasRemediation,
    checks: {
      chineseNonEmpty: content.length > 0 && isChinese,
      formalOrDegradedReply: hasReportClosure,
      responseDataNoNodeErrors: nodeErrors.length === 0,
      businessSignals: hasBusinessSignals,
      riskSignals: hasRiskSignals,
      evidenceBoundarySignals: hasEvidenceBoundary,
      remediationOrManualReviewSignals: hasRemediation
    }
  };
}

async function postCase({ args, apiKey, testCase }) {
  const fileUrl = process.env[testCase.fileUrlEnv];
  if (!fileUrl) throw new Error(`Missing ${testCase.fileUrlEnv}`);
  const chatId = `real-docx-${testCase.id}-${Date.now()}`;
  const payload = {
    stream: false,
    detail: true,
    chatId,
    variables: {
      documentType: testCase.documentType,
      enabledModules: JSON.stringify(ALL_MODULES),
      strictMode: 'true'
    },
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: `请对该真实方案执行正式审查。documentType=${testCase.documentType}；enabledModules=${ALL_MODULES.join(',')}。`
          },
          {
            type: 'file_url',
            name: `${testCase.title}.docx`,
            url: fileUrl
          }
        ]
      }
    ]
  };

  const startedAt = new Date().toISOString();
  const response = await fetch(args.chatUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`
    },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(args.timeoutMs)
  });
  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = { raw: text };
  }
  const endedAt = new Date().toISOString();
  return {
    startedAt,
    endedAt,
    chatId,
    fileUrl,
    requestPayload: payload,
    httpStatus: response.status,
    body,
    summary: evaluateCase({ body, httpStatus: response.status })
  };
}

function renderMarkdown({ args, keyFp, results }) {
  const lines = [
    '# FastGPT 真实方案验收结果',
    '',
    `- 验收时间：${new Date().toISOString()}`,
    `- Chat URL：${args.chatUrl}`,
    `- Key 指纹：${keyFp}`,
    `- 原始响应目录：\`${args.outDir}\``,
    '',
    '## 结论',
    '',
    '| 案例 | documentType | 出口 | 是否通过 | contentLength | nodeErrors |',
    '|---|---|---:|---:|---:|---:|'
  ];
  for (const result of results) {
    lines.push(
      `| ${result.title} | \`${result.documentType}\` | ${result.summary.finalStatus} | ${result.summary.passed ? 'PASS' : 'FAIL'} | ${result.summary.contentLength} | ${result.summary.nodeErrors.length} |`
    );
  }
  lines.push('', '## 节点链', '');
  for (const result of results) {
    lines.push(`### ${result.title}`, '');
    for (const node of result.summary.nodes) {
      lines.push(`- ${node.nodeId} / ${node.moduleType} / ${node.moduleName} / error=${node.errorText || 'null'}`);
    }
    lines.push('', '检查项：');
    for (const [key, value] of Object.entries(result.summary.checks)) {
      lines.push(`- ${key}: ${value ? 'PASS' : 'FAIL'}`);
    }
    lines.push('', '正文预览：', '', '```text', result.summary.contentPreview, '```', '');
  }
  return `${lines.join('\n')}\n`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const apiKey = readApiKey(args);
  const selectedCases = args.caseId ? CASES.filter((item) => item.id === args.caseId) : CASES;
  if (!selectedCases.length) throw new Error(`Unknown case: ${args.caseId}`);
  fs.mkdirSync(args.outDir, { recursive: true });

  const results = [];
  for (const testCase of selectedCases) {
    const result = await postCase({ args, apiKey, testCase });
    const rawPath = path.join(args.outDir, `${testCase.id}.raw.json`);
    const summaryPath = path.join(args.outDir, `${testCase.id}.summary.json`);
    fs.writeFileSync(rawPath, `${JSON.stringify(result, null, 2)}\n`);
    fs.writeFileSync(summaryPath, `${JSON.stringify(result.summary, null, 2)}\n`);
    results.push({
      ...testCase,
      rawPath,
      summaryPath,
      summary: result.summary
    });
  }
  const report = renderMarkdown({ args, keyFp: keyFingerprint(apiKey), results });
  const reportPath = path.join(args.outDir, 'acceptance-report.md');
  fs.writeFileSync(reportPath, report);

  const output = { reportPath, keyFingerprint: keyFingerprint(apiKey), results };
  if (args.json) {
    console.log(JSON.stringify(output, null, 2));
  } else {
    console.log(report);
  }
  process.exit(results.every((item) => item.summary.passed) ? 0 : 1);
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
