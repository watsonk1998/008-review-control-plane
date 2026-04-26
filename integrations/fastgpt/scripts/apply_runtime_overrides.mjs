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

function collectPlaceholders(value, acc = new Set()) {
  if (typeof value === 'string') {
    for (const match of value.matchAll(/__[^"\s]+__/g)) {
      acc.add(match[0]);
    }
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
const workflowToolPlaceholders = {
  hermes_review_context_wft: '__WFT_HERMES_REVIEW_CONTEXT_ID__',
  hermes_ai_review_wft: '__WFT_HERMES_AI_REVIEW_ID__',
  hermes_deterministic_review_wft: '__WFT_HERMES_DETERMINISTIC_REVIEW_ID__',
  hermes_support_008_wft: '__WFT_HERMES_SUPPORT_008_ID__',
  hermes_final_assembler_wft: '__WFT_HERMES_FINAL_ASSEMBLER_ID__'
};
const workflowToolReplacements = {};
for (const [key, value] of Object.entries(registry.workflowToolIds || {})) {
  workflowToolReplacements[workflowToolPlaceholders[key] || key] = value;
}
const replacements = {
  '__FASTGPT_AI_MODEL__': registry.aiModel || '__FASTGPT_AI_MODEL__',
  ...workflowToolReplacements
};

const mainWorkflow = readJson(path.join(artifactsDir, 'hermes-main-review.workflow.json'));
const mainCreate = readJson(path.join(artifactsDir, 'hermes-main-review.create.json'));
const linkedArtifacts = [];

const linkedMainWorkflow = replaceDeep(mainWorkflow, replacements);
const linkedMainCreate = replaceDeep(mainCreate, replacements);
writeJson(path.join(artifactsDir, 'hermes-main-review.linked.workflow.json'), linkedMainWorkflow);
writeJson(path.join(artifactsDir, 'hermes-main-review.linked.create.json'), linkedMainCreate);
linkedArtifacts.push(['hermes-main-review.linked.workflow.json', linkedMainWorkflow]);
linkedArtifacts.push(['hermes-main-review.linked.create.json', linkedMainCreate]);

const workflowToolsDir = path.join(artifactsDir, 'workflow-tools');
for (const file of fs.readdirSync(workflowToolsDir)) {
  if (!file.endsWith('.json')) continue;
  if (file.includes('.linked.')) continue;
  const source = readJson(path.join(workflowToolsDir, file));
  const targetName = file.replace(/\.json$/, '.linked.json');
  const linked = replaceDeep(source, replacements);
  writeJson(path.join(workflowToolsDir, targetName), linked);
  linkedArtifacts.push([path.join('workflow-tools', targetName), linked]);
}

console.log(`已根据 ${registryPath} 生成 linked 工作流与工作流工具 JSON。`);

const unresolved = linkedArtifacts
  .map(([name, payload]) => [name, [...collectPlaceholders(payload)].sort()])
  .filter(([, placeholders]) => placeholders.length > 0);

if (unresolved.length) {
  console.warn('警告：以下 linked JSON 仍包含未替换占位符，请在导入前确认是否需要补齐：');
  for (const [name, placeholders] of unresolved) {
    console.warn(`- ${name}: ${placeholders.join(', ')}`);
  }
}
