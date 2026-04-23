import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const artifactsDir = path.join(repoRoot, 'artifacts', 'fastgpt');

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeJson(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(payload, null, 2)}\n`);
}

function replaceDeep(value, replacements) {
  if (typeof value === 'string') {
    let next = value;
    for (const [from, to] of Object.entries(replacements)) {
      next = next.split(from).join(String(to));
    }
    return next;
  }
  if (Array.isArray(value)) {
    return value.map((item) => replaceDeep(item, replacements));
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, replaceDeep(item, replacements)]));
  }
  return value;
}

const registryPath = process.argv[2] || path.join(artifactsDir, 'workflow_tool_registry.template.json');
const registry = readJson(registryPath);
const replacements = {
  '__FASTGPT_AI_MODEL__': registry.aiModel || '__FASTGPT_AI_MODEL__',
  ...(registry.workflowToolIds || {})
};

const mainWorkflow = readJson(path.join(artifactsDir, 'hermes-main-review.workflow.json'));
const mainCreate = readJson(path.join(artifactsDir, 'hermes-main-review.create.json'));
writeJson(path.join(artifactsDir, 'hermes-main-review.linked.workflow.json'), replaceDeep(mainWorkflow, replacements));
writeJson(path.join(artifactsDir, 'hermes-main-review.linked.create.json'), replaceDeep(mainCreate, replacements));

const workflowToolsDir = path.join(artifactsDir, 'workflow-tools');
for (const file of fs.readdirSync(workflowToolsDir)) {
  if (!file.endsWith('.json')) continue;
  const source = readJson(path.join(workflowToolsDir, file));
  const targetName = file.replace(/\.json$/, '.linked.json');
  writeJson(path.join(workflowToolsDir, targetName), replaceDeep(source, replacements));
}

console.log(`已根据 ${registryPath} 生成 linked 工作流与工作流工具 JSON。`);
