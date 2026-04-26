import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const defaultReportsDir = path.join(repoRoot, 'integrations', 'fastgpt', 'reports');

function parseArgs(argv) {
  const args = {
    inputs: [],
    latestDir: '',
    output: path.join(defaultReportsDir, `fastgpt-quality-diagnostics-${new Date().toISOString().slice(0, 10)}.md`),
    title: 'FastGPT 审查质量诊断报告'
  };
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (item === '--input') args.inputs.push(argv[++index]);
    else if (item === '--latest') args.latestDir = argv[++index];
    else if (item === '--output') args.output = argv[++index];
    else if (item === '--title') args.title = argv[++index];
    else throw new Error(`Unknown argument: ${item}`);
  }
  return args;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function ensureDir(file) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
}

function latestJsonFile(dir) {
  if (!dir || !fs.existsSync(dir)) return '';
  const files = fs
    .readdirSync(dir)
    .filter((name) => name.endsWith('.json'))
    .map((name) => path.join(dir, name))
    .filter((file) => fs.statSync(file).isFile())
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return files[0] || '';
}

function sanitize(value) {
  return String(value ?? '')
    .replace(/openapi-[A-Za-z0-9_-]{12,}/g, 'openapi-...[redacted]')
    .replace(/https?:\/\/[^\s)]+/g, (url) => {
      try {
        const parsed = new URL(url);
        return `${parsed.origin}${parsed.pathname}`;
      } catch {
        return '[url-redacted]';
      }
    });
}

function walk(value, visitor, pathStack = []) {
  visitor(value, pathStack);
  if (Array.isArray(value)) {
    value.forEach((item, index) => walk(item, visitor, [...pathStack, String(index)]));
  } else if (value && typeof value === 'object') {
    Object.entries(value).forEach(([key, item]) => walk(item, visitor, [...pathStack, key]));
  }
}

function firstNumber(...values) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number) && number >= 0) return number;
  }
  return null;
}

function collectFlowNodes(payload) {
  const nodes = [];
  walk(payload, (value) => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return;
    const looksLikeNode = value.nodeId || value.moduleName || value.moduleType || value.flowNodeType;
    if (!looksLikeNode) return;
    nodes.push({
      nodeId: value.nodeId || value.id || '',
      moduleType: value.moduleType || value.flowNodeType || '',
      moduleName: value.moduleName || value.name || '',
      errorText: value.errorText || value.error || null,
      durationMs: firstNumber(value.durationMs, value.duration, value.time, value.runningTime, value.runTime, value.elapsedMs),
      model: value.model || value.aiModel || value.modelName || '',
      inputTokens: firstNumber(value.inputTokens, value.promptTokens, value.prompt_tokens),
      outputTokens: firstNumber(value.outputTokens, value.completionTokens, value.completion_tokens),
      totalTokens: firstNumber(value.totalTokens, value.tokens, value.total_tokens)
    });
  });
  const seen = new Set();
  return nodes.filter((node) => {
    const key = `${node.nodeId}|${node.moduleType}|${node.moduleName}|${node.durationMs}|${node.errorText}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function collectArraysByKey(payload, keys) {
  const rows = [];
  walk(payload, (value, pathStack) => {
    const key = pathStack[pathStack.length - 1];
    if (Array.isArray(value) && keys.includes(key)) {
      rows.push({ key, path: pathStack.join('.'), value });
    }
  });
  return rows;
}

function collectStrings(payload) {
  const strings = [];
  walk(payload, (value, pathStack) => {
    if (typeof value === 'string' && value.trim()) strings.push({ path: pathStack.join('.'), value });
  });
  return strings;
}

function extractFinalContent(payload) {
  const direct = payload?.choices?.[0]?.message?.content || payload?.contentPreview || payload?.finalAnswer || '';
  if (direct) return String(direct);
  const strings = collectStrings(payload)
    .filter((item) => /正式审查报告|非正式审查报告|总体评级结论|关键问题/.test(item.value))
    .sort((a, b) => b.value.length - a.value.length);
  return strings[0]?.value || '';
}

function summarizeReviewers(payload) {
  const packetArrays = collectArraysByKey(payload, ['reviewerPackets', 'packets']);
  const packets = packetArrays.flatMap((row) => row.value).filter((item) => item && typeof item === 'object');
  const reviewerRows = packets
    .filter((packet) => packet.reviewerId || packet.metadata?.agent_id || packet.metadata?.template_id)
    .map((packet) => ({
      reviewerId: packet.reviewerId || packet.metadata?.agent_id || packet.metadata?.template_id || '',
      degraded: Boolean(packet.degraded),
      degradedReason: packet.error || packet.degradedReason || '',
      findingCount: Array.isArray(packet.findings) ? packet.findings.length : 0,
      modules: packet.metadata?.review_modules || []
    }));
  const selectedArrays = collectArraysByKey(payload, ['selectedReviewerIds', 'selectedAiTemplates', 'reviewerConfigs']);
  const selectedReviewers = selectedArrays.flatMap((row) =>
    row.value.map((item) => (typeof item === 'string' ? item : item?.reviewerId || item?.id || item?.template_id)).filter(Boolean)
  );
  return {
    selectedReviewers: Array.from(new Set(selectedReviewers)),
    reviewerRows
  };
}

function summarizeModules(payload, reviewerRows) {
  const moduleNames = ['structure_completeness', 'parameter_consistency', 'legality_compliance', 'execution_continuity', 'evidence_validation'];
  const moduleResults = [];
  for (const moduleName of moduleNames) {
    const reviewers = reviewerRows.filter((row) => Array.isArray(row.modules) && row.modules.includes(moduleName));
    moduleResults.push({
      moduleName,
      reviewerCount: reviewers.length,
      findingCount: reviewers.reduce((sum, row) => sum + row.findingCount, 0),
      degradedCount: reviewers.filter((row) => row.degraded).length,
      effective: reviewers.some((row) => !row.degraded && row.findingCount > 0)
    });
  }
  return moduleResults;
}

function summarizeCase(file, payload) {
  const nodes = collectFlowNodes(payload);
  const { selectedReviewers, reviewerRows } = summarizeReviewers(payload);
  const moduleResults = summarizeModules(payload, reviewerRows);
  const finalContent = extractFinalContent(payload);
  const traceabilityRows = collectArraysByKey(payload, ['traceability']).flatMap((row) => row.value);
  const modelSet = Array.from(new Set(nodes.map((node) => node.model).filter(Boolean)));
  const tokenRows = nodes.filter((node) => node.inputTokens != null || node.outputTokens != null || node.totalTokens != null);
  const durationRows = nodes.filter((node) => node.durationMs != null);
  return {
    file,
    nodes,
    nodeErrors: nodes.filter((node) => node.errorText),
    selectedReviewers,
    reviewerRows,
    moduleResults,
    finalContentLength: finalContent.length,
    finalContentPreview: sanitize(finalContent.slice(0, 220)),
    traceabilityCount: traceabilityRows.length,
    models: modelSet,
    tokenRows,
    durationRows,
    evidenceLevel: reviewerRows.length || traceabilityRows.length || durationRows.length || tokenRows.length ? 'flowResponses/detail' : 'summary-only'
  };
}

function renderReport(title, cases) {
  const lines = [
    `# ${title}`,
    '',
    `- 生成时间：${new Date().toISOString()}`,
    '- 原始 flowResponses/getResData JSON 不写入 repo；本报告仅保存脱敏摘要。',
    '- 若 evidenceLevel 为 `summary-only`，说明输入缺少完整后台流日志，token、耗时、reviewer 分包和 traceability 只能标记为证据不足。',
    '',
    '## 总览',
    '',
    '| 输入 | evidenceLevel | nodes | nodeErrors | selectedReviewers | reviewerPackets | finalLength | traceability |',
    '|---|---:|---:|---:|---:|---:|---:|---:|'
  ];
  for (const item of cases) {
    lines.push(`| ${sanitize(path.basename(item.file))} | ${item.evidenceLevel} | ${item.nodes.length} | ${item.nodeErrors.length} | ${item.selectedReviewers.length} | ${item.reviewerRows.length} | ${item.finalContentLength} | ${item.traceabilityCount} |`);
  }
  for (const item of cases) {
    lines.push('', `## ${sanitize(path.basename(item.file))}`, '');
    lines.push('### 节点耗时 / 模型 / Token', '');
    if (!item.durationRows.length && !item.tokenRows.length && !item.models.length) {
      lines.push('- 数据不足：输入中未发现节点耗时、模型或 token 字段。');
    } else {
      lines.push('| nodeId | moduleName | durationMs | model | inputTokens | outputTokens | totalTokens |');
      lines.push('|---|---|---:|---|---:|---:|---:|');
      for (const node of item.nodes) {
        lines.push(`| ${sanitize(node.nodeId)} | ${sanitize(node.moduleName)} | ${node.durationMs ?? ''} | ${sanitize(node.model)} | ${node.inputTokens ?? ''} | ${node.outputTokens ?? ''} | ${node.totalTokens ?? ''} |`);
      }
    }
    lines.push('', '### Reviewer 分包', '');
    if (!item.reviewerRows.length) {
      lines.push('- 数据不足：输入中未发现 reviewerPackets/packets。');
    } else {
      lines.push('| reviewerId | modules | degraded | findings | degradedReason |');
      lines.push('|---|---|---:|---:|---|');
      for (const row of item.reviewerRows) {
        lines.push(`| ${sanitize(row.reviewerId)} | ${sanitize((row.modules || []).join(','))} | ${row.degraded ? 'YES' : 'NO'} | ${row.findingCount} | ${sanitize(row.degradedReason)} |`);
      }
    }
    lines.push('', '### 模块有效结论', '');
    lines.push('| module | reviewerCount | degradedCount | findings | effectiveByFinding |');
    lines.push('|---|---:|---:|---:|---:|');
    for (const row of item.moduleResults) {
      lines.push(`| ${row.moduleName} | ${row.reviewerCount} | ${row.degradedCount} | ${row.findingCount} | ${row.effective ? 'YES' : 'NO'} |`);
    }
    lines.push('', '### 最终输出', '');
    lines.push(`- 字符数：${item.finalContentLength}`);
    lines.push(`- traceability 条目数：${item.traceabilityCount}`);
    if (item.finalContentPreview) lines.push('', '```text', item.finalContentPreview, '```');
  }
  return `${lines.join('\n')}\n`;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const inputs = [...args.inputs];
  if (args.latestDir) {
    const latest = latestJsonFile(args.latestDir);
    if (latest) inputs.push(latest);
  }
  if (!inputs.length) {
    throw new Error('No inputs. Use --input <raw-or-summary.json> or --latest <dir>.');
  }
  const cases = inputs.map((file) => summarizeCase(path.resolve(file), readJson(file)));
  const report = renderReport(args.title, cases);
  ensureDir(args.output);
  fs.writeFileSync(args.output, report);
  console.log(`已生成质量诊断摘要：${args.output}`);
}

main();
