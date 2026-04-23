import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { beforeAll, describe, expect, it } from 'vitest';
import { generateBundle } from '../scripts/workflow_bundle_lib.mjs';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const artifactsDir = path.join(repoRoot, 'artifacts', 'fastgpt');
const workflowToolsDir = path.join(artifactsDir, 'workflow-tools');

beforeAll(() => {
  generateBundle({ repoRoot });
});

describe('FastGPT workflow-tool bundle', () => {
  it('generates five workflow-tool template and create JSON files', () => {
    const templates = fs.readdirSync(workflowToolsDir).filter((name) => name.endsWith('.template.json'));
    const creates = fs.readdirSync(workflowToolsDir).filter((name) => name.endsWith('.create.json'));
    expect(templates).toHaveLength(5);
    expect(creates).toHaveLength(5);

    for (const file of templates) {
      const payload = JSON.parse(fs.readFileSync(path.join(workflowToolsDir, file), 'utf8'));
      expect(payload.type).toBe('plugin');
      const nodeTypes = payload.workflow.nodes.map((node: any) => node.flowNodeType);
      expect(nodeTypes).toContain('pluginInput');
      expect(nodeTypes).toContain('pluginOutput');
      expect(nodeTypes).toContain('pluginConfig');
      expect(payload.workflow.nodes.find((node: any) => node.flowNodeType === 'pluginInput').inputs.every((input: any) => 'toolDescription' in input)).toBe(true);
    }
  });

  it('generates a main workflow that calls workflow tools with explicit file URL mapping', () => {
    const workflow = JSON.parse(fs.readFileSync(path.join(artifactsDir, 'hermes-main-review.workflow.json'), 'utf8'));
    const pluginModules = workflow.nodes.filter((node: any) => node.flowNodeType === 'pluginModule');
    expect(pluginModules).toHaveLength(5);
    expect(JSON.stringify(workflow)).toContain('workflow+workflow-tools');
    const contextNode = pluginModules.find((node: any) => node.nodeId === 'callReviewContextWft');
    expect(JSON.stringify(contextNode.inputs)).toContain('targetFileUrls');
    expect(JSON.stringify(contextNode.inputs)).toContain('basisFileUrls');
    expect(JSON.stringify(contextNode.inputs)).toContain('contextFileUrls');
  });

  it('links workflow-tool placeholder IDs from a runtime registry', () => {
    const registryPath = path.join('/tmp', `hermes-fastgpt-registry-${Date.now()}.json`);
    const registry = JSON.parse(fs.readFileSync(path.join(artifactsDir, 'workflow_tool_registry.template.json'), 'utf8'));
    registry.aiModel = 'fastgpt-test-model';
    registry.workflowToolIds = {
      hermes_review_context_wft: 'wft_context_test',
      hermes_ai_review_wft: 'wft_ai_test',
      hermes_deterministic_review_wft: 'wft_det_test',
      hermes_support_008_wft: 'wft_support_test',
      hermes_final_assembler_wft: 'wft_final_test'
    };
    fs.writeFileSync(registryPath, `${JSON.stringify(registry, null, 2)}\n`);
    execFileSync('node', [path.join(repoRoot, 'integrations', 'fastgpt', 'scripts', 'apply_runtime_overrides.mjs'), registryPath], {
      cwd: path.join(repoRoot, 'integrations', 'fastgpt')
    });
    const linked = JSON.parse(fs.readFileSync(path.join(artifactsDir, 'hermes-main-review.linked.workflow.json'), 'utf8'));
    expect(linked.nodes.filter((node: any) => node.flowNodeType === 'pluginModule').map((node: any) => node.pluginId)).toEqual([
      'wft_context_test',
      'wft_ai_test',
      'wft_det_test',
      'wft_support_test',
      'wft_final_test'
    ]);
    for (const file of fs.readdirSync(artifactsDir)) {
      if (file.includes('.linked.')) fs.rmSync(path.join(artifactsDir, file), { force: true });
    }
    for (const file of fs.readdirSync(workflowToolsDir)) {
      if (file.endsWith('.linked.json')) fs.rmSync(path.join(workflowToolsDir, file), { force: true });
    }
  });
});
