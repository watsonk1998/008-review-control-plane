import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const artifactsDir = path.join(repoRoot, 'artifacts', 'fastgpt');
const defaultOutDir = path.resolve(repoRoot, '..', '..', 'fastgpt', 'fastgpt-review-agent');
const outDir = path.resolve(process.argv[2] || defaultOutDir);

const IMPORT_FILES = [
  {
    order: 1,
    area: '工作流工具 / 我的工具',
    source: path.join(artifactsDir, 'workflow-tools', 'hermes_review_context_wft.workflow.linked.json'),
    target: '01-tool-review-context.json',
    title: 'Hermes 审查上下文工具'
  },
  {
    order: 2,
    area: '工作流工具 / 我的工具',
    source: path.join(artifactsDir, 'workflow-tools', 'hermes_ai_review_wft.workflow.linked.json'),
    target: '02-tool-ai-review.json',
    title: 'Hermes AI 审查工具'
  },
  {
    order: 3,
    area: '工作流工具 / 我的工具',
    source: path.join(artifactsDir, 'workflow-tools', 'hermes_deterministic_review_wft.workflow.linked.json'),
    target: '03-tool-deterministic-review.json',
    title: 'Hermes 确定性审查工具'
  },
  {
    order: 4,
    area: '工作流工具 / 我的工具',
    source: path.join(artifactsDir, 'workflow-tools', 'hermes_support_008_wft.workflow.linked.json'),
    target: '04-tool-support-008.json',
    title: 'Hermes 008 支撑层工具'
  },
  {
    order: 5,
    area: '工作流工具 / 我的工具',
    source: path.join(artifactsDir, 'workflow-tools', 'hermes_final_assembler_wft.workflow.linked.json'),
    target: '05-tool-final-assembler.json',
    title: 'Hermes 最终组装工具'
  },
  {
    order: 6,
    area: '应用导入配置',
    source: path.join(artifactsDir, 'hermes-main-review.linked.workflow.json'),
    target: '06-main-review-app.json',
    title: 'Hermes 主审查应用'
  }
];

const REPORT_FILES = [
  ['hermes-fastgpt-import-readiness.md', 'import-readiness.md'],
  ['hermes-fastgpt-layout-validation.md', 'layout-validation.md'],
  ['hermes-fastgpt-parity-matrix.md', 'parity-matrix.md']
];

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeText(file, content) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, content.endsWith('\n') ? content : `${content}\n`);
}

function writeJson(file, payload) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, `${JSON.stringify(payload, null, 2)}\n`);
}

function assertDashboardImportShape(file, payload) {
  const keys = Object.keys(payload).sort();
  const expected = ['chatConfig', 'edges', 'nodes'];
  if (JSON.stringify(keys) !== JSON.stringify(expected)) {
    throw new Error(`${file} must use FastGPT dashboard import shape chatConfig/edges/nodes; got ${keys.join(',')}`);
  }
  if (!Array.isArray(payload.nodes)) throw new Error(`${file} nodes must be an array`);
  if (!Array.isArray(payload.edges)) throw new Error(`${file} edges must be an array`);
  if (!payload.chatConfig || typeof payload.chatConfig !== 'object' || Array.isArray(payload.chatConfig)) {
    throw new Error(`${file} chatConfig must be an object`);
  }
}

function collectPlaceholders(value, acc = new Set()) {
  if (typeof value === 'string') {
    for (const match of value.matchAll(/__[^"\s]+__/g)) acc.add(match[0]);
    return acc;
  }
  if (Array.isArray(value)) {
    value.forEach((item) => collectPlaceholders(item, acc));
    return acc;
  }
  if (value && typeof value === 'object') {
    Object.values(value).forEach((item) => collectPlaceholders(item, acc));
  }
  return acc;
}

function registryInfo() {
  const registryPath = path.join(artifactsDir, 'workflow_tool_registry.local.json');
  if (!fs.existsSync(registryPath)) return { aiModel: 'qwen3.5-flash', workflowToolIds: {}, fastgptVersion: '' };
  const registry = readJson(registryPath);
  return {
    aiModel: registry.aiModel || 'qwen3.5-flash',
    workflowToolIds: registry.workflowToolIds || {},
    fastgptVersion: registry.source?.fastgptVersion || ''
  };
}

function renderReadme(info) {
  return `# FastGPT Review Agent 导入包

这是 Hermes FastGPT 审查应用的压缩导入包。只使用 \`import/\` 目录里的 6 个 JSON。

## 关键修正

FastGPT「导入配置」入口读取的是顶层 \`nodes / edges / chatConfig\`。因此本包中的 6 个 JSON 都是 dashboard workflow 结构，不是 \`create\` 结构，也不是 \`template\` 包装结构。

## 导入顺序

### 1. 工作流工具导入

进入 FastGPT 的「工作流工具 / 我的工具」，分别新建或打开对应工作流工具，在「导入配置」入口依次导入：

1. \`import/01-tool-review-context.json\` — Hermes 审查上下文工具
2. \`import/02-tool-ai-review.json\` — Hermes AI 审查工具
3. \`import/03-tool-deterministic-review.json\` — Hermes 确定性审查工具
4. \`import/04-tool-support-008.json\` — Hermes 008 支撑层工具
5. \`import/05-tool-final-assembler.json\` — Hermes 最终组装工具

### 2. 主应用导入

进入 FastGPT 主应用的「导入配置」入口，导入：

6. \`import/06-main-review-app.json\` — Hermes 主审查应用

## 不要导入的文件

不要导入任何名字包含 \`template\` 或 \`create\` 的 JSON。

- \`template\` 是模板市场/开发包装结构，不适用于当前「导入配置」入口。
- \`create\` 是 OpenAPI 创建应用 payload，顶层是 \`modules\`，不适用于当前「导入配置」入口。

## 当前实例绑定

本包已经绑定当前实例的 5 个工作流工具 AppId，并使用模型：

\`\`\`text
${info.aiModel}
\`\`\`

如果换 FastGPT 实例，不能复用 \`import/06-main-review-app.json\` 中的工具 AppId，必须重新导入 5 个工具并重新生成主应用绑定文件。

## 目录说明

\`\`\`text
fastgpt-review-agent/
  import/      # 只导入这里的 6 个 JSON
  reports/     # 校验报告
  README.md
  MANIFEST.md
\`\`\`

源代码和生成器仍在：

\`\`\`text
/Users/lucas/repos/review/hermes-review-agent/integrations/fastgpt
\`\`\`
`;
}

function renderManifest(info) {
  const rows = IMPORT_FILES.map((item) => `| ${item.order} | ${item.area} | \`import/${item.target}\` | ${item.title} |`).join('\n');
  const idRows = Object.entries(info.workflowToolIds)
    .map(([key, value]) => `- \`${key}\`: \`${value}\``)
    .join('\n') || '- none';
  return `# Hermes FastGPT Review Agent Manifest

## Purpose

This directory is an import-only delivery package for FastGPT. It is not the source of record.

- Source of record: \`/Users/lucas/repos/review/hermes-review-agent\`
- Generator source: \`/Users/lucas/repos/review/hermes-review-agent/integrations/fastgpt\`
- Generated artifacts source: \`/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt\`
- Delivery package: \`/Users/lucas/repos/fastgpt/fastgpt-review-agent\`

## Import Files

Use these files only:

| Order | FastGPT area | File | Name |
|---:|---|---|---|
${rows}

## File Shape

- All import files use top-level \`nodes/edges/chatConfig\`.
- Tool files contain \`pluginConfig\`, \`pluginInput\`, and \`pluginOutput\` nodes.
- Main app file contains 5 \`pluginModule\` nodes bound to current instance-local workflow tool AppIds.
- No \`template\` or \`create\` JSON is included in this delivery package.

## Bound Runtime

- Migration mode: \`workflow+workflow-tools\`
- Helper API: none
- MCP: none
- Model: \`${info.aiModel}\`
- Bound FastGPT version noted by source registry: \`${info.fastgptVersion || 'unknown'}\`

Current workflow tool AppIds embedded in the main app:

${idRows}

These AppIds are instance-local. Rebuild bindings before importing into another FastGPT instance.

## Reports

- \`reports/import-readiness.md\`
- \`reports/layout-validation.md\`
- \`reports/parity-matrix.md\`

## Validation

The package should satisfy:

- exactly 6 files under \`import/\`
- each import JSON has top-level \`nodes/edges/chatConfig\`
- no files with \`template\` or \`create\` in their names
- no \`node_modules\`
- no \`.DS_Store\`
- no API keys or secrets
`;
}

function main() {
  const importDir = path.join(outDir, 'import');
  const reportsDir = path.join(outDir, 'reports');
  ensureDir(importDir);
  ensureDir(reportsDir);

  for (const item of IMPORT_FILES) {
    const payload = readJson(item.source);
    assertDashboardImportShape(item.source, payload);
    const placeholders = collectPlaceholders(payload);
    const blockerPlaceholders = [...placeholders].filter((item) => item === '__FASTGPT_AI_MODEL__' || /^__WFT_[A-Z0-9_]+__$/.test(item));
    if (blockerPlaceholders.length) {
      throw new Error(`${item.source} still has blocker placeholders: ${blockerPlaceholders.join(', ')}`);
    }
    writeJson(path.join(importDir, item.target), payload);
  }

  for (const [sourceName, targetName] of REPORT_FILES) {
    const source = path.join(artifactsDir, sourceName);
    if (fs.existsSync(source)) {
      writeText(path.join(reportsDir, targetName), fs.readFileSync(source, 'utf8'));
    }
  }

  const info = registryInfo();
  writeText(path.join(outDir, 'README.md'), renderReadme(info));
  writeText(path.join(outDir, 'MANIFEST.md'), renderManifest(info));

  console.log(`已生成 FastGPT dashboard 导入包：${outDir}`);
}

main();
