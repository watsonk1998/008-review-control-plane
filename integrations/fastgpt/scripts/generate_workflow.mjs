import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const artifactsDir = path.join(repoRoot, 'artifacts', 'fastgpt');
fs.mkdirSync(artifactsDir, { recursive: true });

const variables = [
  { key: 'documentType', label: 'documentType', type: 'input', required: true },
  { key: 'disciplineTags', label: 'disciplineTags', type: 'textarea', required: false },
  { key: 'enabledModules', label: 'enabledModules', type: 'textarea', required: false },
  { key: 'disabledModules', label: 'disabledModules', type: 'textarea', required: false },
  { key: 'focusRequirements', label: 'focusRequirements', type: 'textarea', required: false },
  { key: 'strictMode', label: 'strictMode', type: 'input', required: false }
];

const actualWorkflow = {
  nodes: [
    { nodeId: 'userGuide', name: '系统配置', intro: 'Hermes 结构化审查 FastGPT 工作流', avatar: 'core/workflow/template/systemConfig', flowNodeType: 'userGuide', position: { x: -320, y: -220 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'workflowStart', name: '流程开始', intro: '文件输入 + 变量输入', avatar: '/imgs/workflow/userChatInput.svg', flowNodeType: 'workflowStart', position: { x: 0, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'normalizeInput', name: '归一化输入', intro: '默认启用全部 5 个审核模块，并规范变量格式。', avatar: '/imgs/workflow/code.png', flowNodeType: 'code', position: { x: 340, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'buildReviewContextTool', name: '工具调用：buildReviewContext', intro: '调用 hermesStructuredReview.buildReviewContext。', avatar: '/imgs/workflow/tool.svg', flowNodeType: 'tools', showStatus: true, position: { x: 720, y: 0 }, inputs: [], outputs: [] },
    { nodeId: 'selectReviewers', name: '选择 reviewer', intro: '根据 enabledModules、supported_document_types、preferred_pack_ids 计算 reviewer 集。', avatar: '/imgs/workflow/code.png', flowNodeType: 'code', position: { x: 1080, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'parallelAiReviewers', name: '并行 reviewer', intro: '并行运行 AI reviewer。', avatar: '/imgs/workflow/loop.png', flowNodeType: 'parallelRun', position: { x: 1440, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'runDeterministicReviewerTool', name: '工具调用：runDeterministicReviewer', intro: '处理 visibility_gap / policy_compliance / normative_validity reviewer。', avatar: '/imgs/workflow/tool.svg', flowNodeType: 'tools', showStatus: true, position: { x: 1800, y: 0 }, inputs: [], outputs: [] },
    { nodeId: 'runSupportReview008Tool', name: '工具调用：runSupportReview008', intro: '生成 008 支撑层结果和 supportPacket008。', avatar: '/imgs/workflow/tool.svg', flowNodeType: 'tools', showStatus: true, position: { x: 2160, y: 0 }, inputs: [], outputs: [] },
    { nodeId: 'assembleFinalDecisionTool', name: '工具调用：assembleFinalDecision', intro: '执行 fail-closed、模块级门禁和 finalReportPacket 组装。', avatar: '/imgs/workflow/tool.svg', flowNodeType: 'tools', showStatus: true, position: { x: 2520, y: 0 }, inputs: [], outputs: [] },
    { nodeId: 'renderFormalReportTool', name: '工具调用：renderFormalReport', intro: '渲染正式报告 Markdown/HTML/JSON。', avatar: '/imgs/workflow/tool.svg', flowNodeType: 'tools', showStatus: true, position: { x: 2880, y: 0 }, inputs: [], outputs: [] },
    { nodeId: 'formalReply', name: '正式报告输出', intro: '输出正式报告 Markdown。', avatar: '/imgs/workflow/reply.png', flowNodeType: 'answerNode', position: { x: 3240, y: -140 }, inputs: [], outputs: [] },
    { nodeId: 'degradedReply', name: '降级结果输出', intro: '输出 fail-closed 降级说明。', avatar: '/imgs/workflow/reply.png', flowNodeType: 'answerNode', position: { x: 3240, y: 140 }, inputs: [], outputs: [] }
  ],
  edges: [
    { source: 'workflowStart', target: 'normalizeInput' },
    { source: 'normalizeInput', target: 'buildReviewContextTool' },
    { source: 'buildReviewContextTool', target: 'selectReviewers' },
    { source: 'selectReviewers', target: 'parallelAiReviewers' },
    { source: 'parallelAiReviewers', target: 'runDeterministicReviewerTool' },
    { source: 'runDeterministicReviewerTool', target: 'runSupportReview008Tool' },
    { source: 'runSupportReview008Tool', target: 'assembleFinalDecisionTool' },
    { source: 'assembleFinalDecisionTool', target: 'renderFormalReportTool' },
    { source: 'renderFormalReportTool', target: 'formalReply' },
    { source: 'assembleFinalDecisionTool', target: 'degradedReply' }
  ],
  chatConfig: {
    welcomeText: '上传施工方案后，我将执行 Hermes 结构化正式审查。',
    variables,
    autoExecute: false,
    questionGuide: { open: false },
    ttsConfig: { type: 'web' },
    whisperConfig: { open: false, autoSend: false, autoTTSResponse: false },
    chatInputGuide: { open: true, customUrl: '' },
    fileSelectConfig: { maxFiles: 10, canSelectFile: true, canSelectImg: false, canSelectVideo: false, canSelectAudio: false, canSelectCustomFileExtension: false, customFileExtensionList: [] },
    instruction: '通过 hermesStructuredReview 工具集完成正式审查。若主审结果不可用，必须 fail-closed，并输出非正式降级说明。'
  }
};

const baselineWorkflow = {
  nodes: [
    { nodeId: 'userGuide', name: '系统配置', intro: 'baseline validator-safe workflow', avatar: 'core/workflow/template/systemConfig', flowNodeType: 'userGuide', position: { x: -180, y: -180 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'workflowStart', name: '工作流开始', intro: 'entry', avatar: 'core/workflow/template/workflowStart', flowNodeType: 'workflowStart', position: { x: 0, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'normalizeInput', name: '归一化输入', intro: 'normalize variables', avatar: '/imgs/workflow/code.png', flowNodeType: 'code', position: { x: 360, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'toolBridgePlaceholder', name: '插件工具占位', intro: '实际导入版使用 tools 节点调用 hermesStructuredReview.buildReviewContext 等 5 个工具。', avatar: '/imgs/workflow/http.png', flowNodeType: 'httpRequest468', position: { x: 780, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'parallelAiReviewers', name: '并行 reviewer', intro: 'parallel placeholder', avatar: '/imgs/workflow/loop.png', flowNodeType: 'parallelRun', position: { x: 1160, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'moduleGate', name: '模块级门禁', intro: 'fail-closed gate', avatar: '/imgs/workflow/if.png', flowNodeType: 'ifElseNode', position: { x: 1540, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'renderFormalReport', name: '渲染正式报告', intro: 'render markdown/html/json', avatar: '/imgs/workflow/code.png', flowNodeType: 'code', position: { x: 1920, y: 0 }, version: 'latest', inputs: [], outputs: [] },
    { nodeId: 'finalResponse', name: '最终响应', intro: 'reply placeholder', avatar: '/imgs/workflow/chat.png', flowNodeType: 'chatNode', position: { x: 2300, y: 0 }, version: 'latest', inputs: [], outputs: [] }
  ],
  edges: [
    { source: 'workflowStart', target: 'normalizeInput' },
    { source: 'normalizeInput', target: 'toolBridgePlaceholder' },
    { source: 'toolBridgePlaceholder', target: 'parallelAiReviewers' },
    { source: 'parallelAiReviewers', target: 'moduleGate' },
    { source: 'moduleGate', target: 'renderFormalReport' },
    { source: 'renderFormalReport', target: 'finalResponse' }
  ],
  chatConfig: {
    welcomeText: 'Hermes 结构化正式审查（baseline validator-safe workflow）',
    variables,
    autoExecute: false,
    questionGuide: { open: false },
    ttsConfig: { type: 'web' },
    whisperConfig: { open: false, autoSend: false, autoTTSResponse: false },
    chatInputGuide: { open: true, customUrl: '' },
    fileSelectConfig: { maxFiles: 10, canSelectFile: true, canSelectImg: false, canSelectVideo: false, canSelectAudio: false, canSelectCustomFileExtension: false, customFileExtensionList: [] },
    instruction: 'Marker: hermesStructuredReview.buildReviewContext hermesStructuredReview.runSupportReview008 hermesStructuredReview.runDeterministicReviewer hermesStructuredReview.assembleFinalDecision hermesStructuredReview.renderFormalReport'
  }
};

fs.writeFileSync(path.join(artifactsDir, 'hermes-structured-review.workflow.json'), JSON.stringify(actualWorkflow, null, 2));
fs.writeFileSync(path.join(artifactsDir, 'hermes-structured-review.workflow.baseline.json'), JSON.stringify(baselineWorkflow, null, 2));
console.log('Generated workflow files in', artifactsDir);
