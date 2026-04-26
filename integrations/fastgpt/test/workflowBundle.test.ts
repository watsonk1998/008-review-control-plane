import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import vm from 'node:vm';
import { beforeAll, describe, expect, it } from 'vitest';
import { generateBundle } from '../scripts/workflow_bundle_lib.mjs';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const artifactsDir = path.join(repoRoot, 'artifacts', 'fastgpt');
const workflowToolsDir = path.join(artifactsDir, 'workflow-tools');

function workflowFiles() {
  return [
    path.join(artifactsDir, 'hermes-main-review.workflow.json'),
    ...fs
      .readdirSync(workflowToolsDir)
      .filter((name) => name.endsWith('.workflow.json'))
      .map((name) => path.join(workflowToolsDir, name))
  ];
}

function readWorkflow(file: string) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function codeInput(node: any, key: string) {
  return node.inputs.find((input: any) => input.key === key);
}

function runCodeNode(code: string, args: Record<string, unknown>) {
  const script = new vm.Script(`${code}\nmain(__args);`, { filename: 'fastgpt-code-node.js' });
  return script.runInNewContext({ __args: args }, { timeout: 3000 });
}

function snapshotLinkedArtifacts() {
  const files = [
    ...fs
      .readdirSync(artifactsDir)
      .filter((name) => name.includes('.linked.'))
      .map((name) => path.join(artifactsDir, name)),
    ...fs
      .readdirSync(workflowToolsDir)
      .filter((name) => name.includes('.linked.'))
      .map((name) => path.join(workflowToolsDir, name))
  ];

  return new Map(files.map((file) => [file, fs.readFileSync(file, 'utf8')]));
}

function restoreLinkedArtifacts(snapshot: Map<string, string>) {
  const currentFiles = [
    ...fs
      .readdirSync(artifactsDir)
      .filter((name) => name.includes('.linked.'))
      .map((name) => path.join(artifactsDir, name)),
    ...fs
      .readdirSync(workflowToolsDir)
      .filter((name) => name.includes('.linked.'))
      .map((name) => path.join(workflowToolsDir, name))
  ];

  for (const file of currentFiles) {
    if (!snapshot.has(file)) fs.rmSync(file, { force: true });
  }

  for (const [file, content] of snapshot.entries()) {
    fs.writeFileSync(file, content);
  }
}

beforeAll(() => {
  generateBundle({ repoRoot });
});

describe('FastGPT workflow-tool bundle', () => {
  it('generates six workflow-tool template and create JSON files', () => {
    const templates = fs.readdirSync(workflowToolsDir).filter((name) => name.endsWith('.template.json'));
    const creates = fs.readdirSync(workflowToolsDir).filter((name) => name.endsWith('.create.json'));
    expect(templates).toHaveLength(6);
    expect(creates).toHaveLength(6);

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
    expect(pluginModules).toHaveLength(6);
    expect(JSON.stringify(workflow)).toContain('workflow+workflow-tools');
    expect(pluginModules.map((node: any) => node.nodeId)).toContain('callReviewConfigWft');
    const contextNode = pluginModules.find((node: any) => node.nodeId === 'callReviewContextWft');
    expect(JSON.stringify(contextNode.inputs)).toContain('targetFileUrls');
    expect(JSON.stringify(contextNode.inputs)).toContain('basisFileUrls');
    expect(JSON.stringify(contextNode.inputs)).toContain('contextFileUrls');
    expect(JSON.stringify(contextNode.inputs)).toContain('reviewConfig');
  });

  it('links workflow-tool placeholder IDs from a runtime registry', () => {
    const linkedSnapshot = snapshotLinkedArtifacts();
    const registryPath = path.join('/tmp', `hermes-fastgpt-registry-${Date.now()}.json`);
    const registry = JSON.parse(fs.readFileSync(path.join(artifactsDir, 'workflow_tool_registry.template.json'), 'utf8'));
    registry.aiModel = 'fastgpt-test-model';
    registry.workflowToolIds = {
      hermes_review_config_wft: 'wft_config_test',
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
      'wft_config_test',
      'wft_context_test',
      'wft_ai_test',
      'wft_det_test',
      'wft_support_test',
      'wft_final_test'
    ]);
    restoreLinkedArtifacts(linkedSnapshot);
  });

  it('builds a dashboard import package from workflow linked JSON, not create/template wrappers', () => {
    const linkedSnapshot = snapshotLinkedArtifacts();
    const registryPath = path.join('/tmp', `hermes-fastgpt-delivery-registry-${Date.now()}.json`);
    const registry = JSON.parse(fs.readFileSync(path.join(artifactsDir, 'workflow_tool_registry.template.json'), 'utf8'));
    registry.aiModel = 'fastgpt-test-model';
    registry.workflowToolIds = {
      hermes_review_config_wft: 'wft_config_test',
      hermes_review_context_wft: 'wft_context_test',
      hermes_ai_review_wft: 'wft_ai_test',
      hermes_deterministic_review_wft: 'wft_det_test',
      hermes_support_008_wft: 'wft_support_test',
      hermes_final_assembler_wft: 'wft_final_test'
    };
    fs.writeFileSync(registryPath, `${JSON.stringify(registry, null, 2)}\n`);
    execFileSync('node', [
      path.join(repoRoot, 'integrations', 'fastgpt', 'scripts', 'apply_runtime_overrides.mjs'),
      registryPath
    ], {
      cwd: path.join(repoRoot, 'integrations', 'fastgpt')
    });

    const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-fastgpt-delivery-'));
    execFileSync('node', [path.join(repoRoot, 'integrations', 'fastgpt', 'scripts', 'build_delivery_package.mjs'), outDir], {
      cwd: path.join(repoRoot, 'integrations', 'fastgpt')
    });

    const importDir = path.join(outDir, 'import');
    const importFiles = fs.readdirSync(importDir).filter((name) => name.endsWith('.json')).sort();
    expect(importFiles).toEqual([
      '01-tool-review-config.json',
      '02-tool-review-context.json',
      '03-tool-ai-review.json',
      '04-tool-deterministic-review.json',
      '05-tool-support-008.json',
      '06-tool-final-assembler.json',
      '07-main-review-app.json'
    ]);
    expect(importFiles.some((name) => name.includes('template') || name.includes('create'))).toBe(false);

    for (const file of importFiles) {
      const payload = JSON.parse(fs.readFileSync(path.join(importDir, file), 'utf8'));
      expect(Object.keys(payload).sort()).toEqual(['chatConfig', 'edges', 'nodes']);
      expect(payload).not.toHaveProperty('modules');
      expect(payload).not.toHaveProperty('workflow');
      expect(payload).not.toHaveProperty('type');
      expect(payload).not.toHaveProperty('name');
      expect(Array.isArray(payload.nodes)).toBe(true);
      expect(Array.isArray(payload.edges)).toBe(true);
      expect(typeof payload.chatConfig).toBe('object');
    }
    restoreLinkedArtifacts(linkedSnapshot);
  });

  it('emits code-node JavaScript that is syntactically valid for FastGPT sandbox import', () => {
    for (const file of workflowFiles()) {
      const payload = readWorkflow(file);
      for (const node of payload.nodes.filter((node: any) => node.flowNodeType === 'code')) {
        const code = codeInput(node, 'code')?.value;
        expect(typeof code).toBe('string');
        expect(() => new vm.Script(String(code), { filename: `${path.basename(file)}:${node.nodeId}` })).not.toThrow();
      }
    }
  });

  it('compiles generation-time governance assets into code nodes instead of hidden runtime object inputs', () => {
    const forbiddenRuntimeKeys = new Set(['governanceSnapshot', 'datasetManifest']);
    for (const file of workflowFiles()) {
      const payload = readWorkflow(file);
      for (const node of payload.nodes.filter((node: any) => node.flowNodeType === 'code')) {
        const dynamicInputs = node.inputs.filter((input: any) => !['system_addInputParam', 'codeType', 'code'].includes(input.key));
        expect(dynamicInputs.map((input: any) => input.key).filter((key: string) => forbiddenRuntimeKeys.has(key))).toEqual([]);

        const hiddenObjectInputs = dynamicInputs.filter(
          (input: any) => (input.renderTypeList || []).includes('hidden') && ['object', 'arrayObject', 'any'].includes(input.valueType)
        );
        expect(hiddenObjectInputs).toEqual([]);
      }
    }
  });

  it('selects reviewers from compiled governance data for multiple document types', () => {
    const aiWorkflow = readWorkflow(path.join(workflowToolsDir, 'hermes_ai_review_wft.workflow.json'));
    const prepareNode = aiWorkflow.nodes.find((node: any) => node.nodeId === 'prepareAiReview');
    const code = codeInput(prepareNode, 'code')?.value;

    const baseReviewContext = {
      reviewId: 'r-fastgpt-test',
      enabledModules: [
        'structure_completeness',
        'parameter_consistency',
        'legality_compliance',
        'execution_continuity',
        'evidence_validation'
      ]
    };

    const outage = runCodeNode(code, {
      reviewContext: { ...baseReviewContext, documentType: 'distribution_network_special_scheme' },
      aiModel: 'qwen3.5-flash'
    });
    const construction = runCodeNode(code, {
      reviewContext: { ...baseReviewContext, documentType: 'construction_org' },
      aiModel: 'qwen3.5-flash'
    });

    expect(outage.selectedReviewerIds.length).toBeGreaterThan(0);
    expect(outage.selectedReviewerIds).toContain('power_outage_operation_chain_reviewer');
    expect(outage.selectedReviewerIds).not.toContain('construction_org_structure_reviewer');
    expect(construction.selectedReviewerIds.length).toBeGreaterThan(0);
    expect(construction.selectedReviewerIds).toContain('construction_org_structure_reviewer');
    expect(construction.selectedReviewerIds).not.toContain('power_outage_operation_chain_reviewer');
    expect(construction.modulePrompts).toHaveProperty('legality_compliance');
    expect(construction.legalityPrompt).toContain('reviewerConfigs=');
  });

  it('resolves platform rule-pack config and fails closed for unknown documentType', () => {
    const configWorkflow = readWorkflow(path.join(workflowToolsDir, 'hermes_review_config_wft.workflow.json'));
    const configNode = configWorkflow.nodes.find((node: any) => node.nodeId === 'resolveReviewConfig');
    const code = codeInput(configNode, 'code')?.value;

    const known = runCodeNode(code, {
      documentType: 'hazardous_special_scheme',
      enabledModules: [],
      focusRequirements: [],
      strictMode: true
    });
    const unknown = runCodeNode(code, {
      documentType: 'unknown_scheme_type',
      enabledModules: [],
      focusRequirements: [],
      strictMode: true
    });

    expect(known.degraded).toBe(false);
    expect(known.reviewConfig.configKey).toBe('scheme_config__hazardous_special_scheme');
    expect(known.reviewConfig.reviewerConfigs.length).toBeGreaterThan(0);
    expect(unknown.degraded).toBe(true);
    expect(unknown.degradedReason).toContain('未知 documentType');
  });

  it('does not treat pass plus empty findings as an effective module conclusion', () => {
    const finalWorkflow = readWorkflow(path.join(workflowToolsDir, 'hermes_final_assembler_wft.workflow.json'));
    const assembleFinal = codeInput(finalWorkflow.nodes.find((node: any) => node.nodeId === 'assembleFinalDecision'), 'code')?.value;
    const result = runCodeNode(assembleFinal, {
      reviewContext: {
        reviewId: 'r-empty-pass',
        documentType: 'construction_org',
        enabledModules: ['legality_compliance'],
        reviewConfig: { degraded: false },
        resolvedBasisProfile: { basis_documents: [] },
        governedDatasetScope: { basisFileRefs: [] }
      },
      aiReviewResult: {
        reviewerPackets: [
          {
            review_id: 'r-empty-pass',
            engine: 'hermes',
            findings: [],
            overall_assessment: 'pass',
            degraded: false,
            error: '',
            metadata: {
              template_id: 'construction_org_compliance_reviewer',
              agent_id: 'construction_org_compliance_reviewer',
              review_modules: ['legality_compliance']
            }
          }
        ],
        traceability: [],
        degradedCount: 0
      },
      deterministicReviewResult: { reviewerPackets: [] },
      supportReviewResult: { supportPacket008: { findings: [] } }
    });

    expect(result.degraded).toBe(true);
    expect(result.degradedReason).toContain('未形成有效证据化结论');
  });

  it('closes generated business pipeline into Chinese formal or fail-closed output for different samples', () => {
    const configWorkflow = readWorkflow(path.join(workflowToolsDir, 'hermes_review_config_wft.workflow.json'));
    const contextWorkflow = readWorkflow(path.join(workflowToolsDir, 'hermes_review_context_wft.workflow.json'));
    const deterministicWorkflow = readWorkflow(path.join(workflowToolsDir, 'hermes_deterministic_review_wft.workflow.json'));
    const supportWorkflow = readWorkflow(path.join(workflowToolsDir, 'hermes_support_008_wft.workflow.json'));
    const finalWorkflow = readWorkflow(path.join(workflowToolsDir, 'hermes_final_assembler_wft.workflow.json'));

    const resolveConfig = codeInput(configWorkflow.nodes.find((node: any) => node.nodeId === 'resolveReviewConfig'), 'code')?.value;
    const buildContext = codeInput(contextWorkflow.nodes.find((node: any) => node.nodeId === 'buildReviewContext'), 'code')?.value;
    const runDeterministic = codeInput(
      deterministicWorkflow.nodes.find((node: any) => node.nodeId === 'runDeterministicReview'),
      'code'
    )?.value;
    const runSupport = codeInput(supportWorkflow.nodes.find((node: any) => node.nodeId === 'buildSupport008'), 'code')?.value;
    const assembleFinal = codeInput(finalWorkflow.nodes.find((node: any) => node.nodeId === 'assembleFinalDecision'), 'code')?.value;

    function runGeneratedPipeline(sample: { documentType: string; enabledModules: string[]; documentText: string; aiReviewResult?: any }) {
      const configResult = runCodeNode(resolveConfig, {
        documentType: sample.documentType,
        enabledModules: sample.enabledModules,
        focusRequirements: [],
        strictMode: true
      });
      const contextResult = runCodeNode(buildContext, {
        reviewId: `r-${sample.documentType}`,
        query: '请执行正式审查。',
        documentType: sample.documentType,
        disciplineTags: [],
        enabledModules: sample.enabledModules,
        disabledModules: [],
        focusRequirements: [],
        strictMode: true,
        targetFileUrls: ['sample.md'],
        basisFileUrls: [],
        contextFileUrls: [],
        reviewConfig: configResult.reviewConfig,
        documentText: sample.documentText
      });
      const aiReviewResult = sample.aiReviewResult || { reviewerPackets: [], traceability: [], degradedCount: 0 };
      const deterministicResult = runCodeNode(runDeterministic, {
        reviewContext: contextResult.reviewContext,
        aiReviewResult
      });
      const supportResult = runCodeNode(runSupport, {
        reviewContext: contextResult.reviewContext
      });
      return runCodeNode(assembleFinal, {
        reviewContext: contextResult.reviewContext,
        aiReviewResult,
        deterministicReviewResult: deterministicResult.deterministicReviewResult,
        supportReviewResult: supportResult.supportReviewResult
      });
    }

    const degradedOutage = runGeneratedPipeline({
      documentType: 'distribution_network_special_scheme',
      enabledModules: [
        'structure_completeness',
        'parameter_consistency',
        'legality_compliance',
        'execution_continuity',
        'evidence_validation'
      ],
      documentText: `
# 停电专项施工方案
## 编制依据
GB/T 6995
## 停电作业流程
停电、验电、接地、挂牌、遮栏、复电。
## 附件
详见附图一。
`
    });
    const formalConstruction = runGeneratedPipeline({
      documentType: 'construction_org',
      enabledModules: ['legality_compliance', 'evidence_validation'],
      documentText: `
# 施工组织设计
## 编制依据
《建设工程施工现场消防安全技术规范》GB 50720-2011
## 安全管理计划
现场设置消防通道、动火审批和应急处置流程。
`,
      aiReviewResult: {
        reviewerPackets: [
          {
            review_id: 'r-construction_org',
            engine: 'hermes',
            findings: [],
            overall_assessment: '合规主审已检查编制依据章节、安全管理计划、消防措施和可视证据边界，未形成高风险合规问题；计算和附件边界交由依据与验证模块复核。',
            degraded: false,
            error: '',
            metadata: {
              template_id: 'construction_org_compliance_reviewer',
              agent_id: 'construction_org_compliance_reviewer',
              review_modules: ['legality_compliance']
            }
          }
        ],
        traceability: [],
        degradedCount: 0
      }
    });

    expect(degradedOutage.degraded).toBe(true);
    expect(degradedOutage.degradedReason.length).toBeGreaterThan(0);
    expect(degradedOutage.finalAnswer).toContain('非正式审查报告');
    expect(/[审查报告结果原因]/.test(degradedOutage.finalAnswer)).toBe(true);

    expect(formalConstruction.degraded).toBe(false);
    expect(formalConstruction.finalReportPacket).not.toBeNull();
    expect(formalConstruction.finalReportMarkdown).toContain('总体评级结论');
    expect(formalConstruction.finalReportViewModel.normativeValidityChecks.length).toBeGreaterThan(0);
    expect(/[审查报告风险建议]/.test(formalConstruction.finalReportMarkdown)).toBe(true);
  });
});
