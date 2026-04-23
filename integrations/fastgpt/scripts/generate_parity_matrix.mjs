import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const artifactsDir = path.join(repoRoot, 'artifacts', 'fastgpt');
const workflowToolsDir = path.join(artifactsDir, 'workflow-tools');
const governanceDir = path.join(artifactsDir, 'governance');
const sharedScriptsDir = path.join(process.env.HOME || '/Users/lucas', '.codex', 'skills', 'fastgpt-shared', 'scripts');

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function write(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content.endsWith('\n') ? content : `${content}\n`);
}

function runPython(script, args) {
  const result = spawnSync('python3', [path.join(sharedScriptsDir, script), ...args], {
    cwd: repoRoot,
    encoding: 'utf8'
  });
  return {
    ok: result.status === 0,
    stdout: result.stdout || '',
    stderr: result.stderr || '',
    status: result.status
  };
}

const governanceSnapshot = readJson(path.join(governanceDir, 'governance_snapshot.json'));
const datasetManifest = readJson(path.join(governanceDir, 'dataset_manifest.json'));
const templates = governanceSnapshot.template_manifest || governanceSnapshot.templateManifest || [];
const moduleBindings = governanceSnapshot.module_bindings || governanceSnapshot.moduleBindings || {};
const docTypes = governanceSnapshot.doc_type_labels || governanceSnapshot.docTypeLabels || {};
const toolWorkflowFiles = fs.readdirSync(workflowToolsDir).filter((name) => name.endsWith('.workflow.json')).sort();
const mainWorkflowPath = path.join(artifactsDir, 'hermes-main-review.workflow.json');
const allWorkflowFiles = [mainWorkflowPath, ...toolWorkflowFiles.map((name) => path.join(workflowToolsDir, name))];

const validationRows = allWorkflowFiles.map((file) => {
  const workflow = runPython('validate_fastgpt_workflow.py', [file]);
  const layout = runPython('validate_fastgpt_layout.py', [file, '--strategy', 'swimlane']);
  return { file, workflow, layout };
});

const readiness = runPython('generate_import_readiness_report.py', [
  '--repo', repoRoot,
  '--workflow', mainWorkflowPath,
  '--format', 'markdown'
]);

const rows = [
  ['迁移模式', '已实现', '`workflow+workflow-tools`；无 repo-owned Helper API，无 MCP。'],
  ['主工作流', '已生成', '`hermes-main-review.workflow.json` 固定编排 5 个工作流工具。'],
  ['工作流工具数量', '已生成', `${toolWorkflowFiles.length} 个：review_context / ai_review / deterministic_review / support_008 / final_assembler。`],
  ['工具模板 JSON', '已生成', '每个工具输出 `.template.json`，内部 `type=plugin`，UI 语义为工作流工具。'],
  ['工具创建 JSON', '已生成', '每个工具输出 `.create.json`，用于 OpenAPI 创建。'],
  ['治理快照', '已生成', '`governance_snapshot.json` 来自 Python 真源，工作流代码节点只消费快照。'],
  ['数据集清单', '已生成', `dataset manifest 覆盖 ${datasetManifest.entries.length} 个 profile 依据范围。`],
  ['文档类型覆盖', '已覆盖', Object.keys(docTypes).join('、')],
  ['审核模块覆盖', '已覆盖', Object.keys(moduleBindings).join('、')],
  ['Reviewer 模板覆盖', '已导出', `${templates.length} 个 Hermes reviewer 模板已进入治理快照。`],
  ['文件透传', '已显式映射', '主工作流将 `targetFileUrls / basisFileUrls / contextFileUrls` 显式传入工作流工具。'],
  ['Fail-closed', '已实现', '最终组装工具保留 Hermes 全降级、模块级降级、`degradedReason` 非空。'],
  ['计算核验 fallback', '已实现', '确定性审查工具固定注入 `H-CALC-FALLBACK-001`。'],
  ['PDF 导出', '暂不承诺', 'v1 输出 Markdown / HTML / JSON；PDF 需要后续单独增加渲染能力。']
];

const md = ['# Hermes -> FastGPT 工作流工具迁移矩阵', '', '| 能力 | 状态 | 说明 |', '|---|---|---|'];
for (const row of rows) md.push(`| ${row[0]} | ${row[1]} | ${row[2]} |`);
md.push('', '## 生成产物', '');
md.push('- 主工作流：`/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-main-review.workflow.json`');
md.push('- 主工作流创建 JSON：`/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-main-review.create.json`');
md.push('- 工作流工具目录：`/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/workflow-tools/`');
md.push('- 治理快照目录：`/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/governance/`');
md.push('- 运行时 ID 回填模板：`/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/workflow_tool_registry.template.json`');
md.push('', '## 导入顺序', '');
md.push('1. 先导入 5 个工作流工具模板 JSON，确认它们出现在 FastGPT「我的工具」。');
md.push('2. 将导入后的工具 ID 和当前环境模型 ID 写入 `workflow_tool_registry.template.json` 的副本。');
md.push('3. 执行 `node scripts/apply_runtime_overrides.mjs <registry.json>` 生成 linked 主工作流 JSON。');
md.push('4. 导入 `hermes-main-review.linked.workflow.json` 或对应 create JSON。');

write(path.join(artifactsDir, 'hermes-fastgpt-parity-matrix.md'), md.join('\n'));

const layoutLines = ['# FastGPT 布局与结构校验报告', ''];
for (const row of validationRows) {
  layoutLines.push(`## ${path.relative(repoRoot, row.file)}`);
  layoutLines.push('', `- 结构校验：${row.workflow.ok ? '通过' : '失败'}`, `- 布局校验：${row.layout.ok ? '通过' : '失败'}`);
  if (row.workflow.stdout.trim()) layoutLines.push('', '```text', row.workflow.stdout.trim(), '```');
  if (row.workflow.stderr.trim()) layoutLines.push('', '```text', row.workflow.stderr.trim(), '```');
  if (row.layout.stdout.trim()) layoutLines.push('', '```text', row.layout.stdout.trim(), '```');
  if (row.layout.stderr.trim()) layoutLines.push('', '```text', row.layout.stderr.trim(), '```');
  layoutLines.push('');
}
write(path.join(artifactsDir, 'hermes-fastgpt-layout-validation.md'), layoutLines.join('\n'));
write(path.join(artifactsDir, 'hermes-fastgpt-import-readiness.md'), readiness.stdout || readiness.stderr || 'readiness report unavailable');

const failed = validationRows.filter((row) => !row.workflow.ok || !row.layout.ok);
if (failed.length) {
  console.error(`校验失败：${failed.length} 个 workflow 存在结构或布局问题。`);
  process.exitCode = 1;
} else {
  console.log('已生成 parity / readiness / layout 报告。');
}
