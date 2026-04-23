import fs from 'node:fs';
import path from 'node:path';

export const DOC_TYPES = [
  'construction_org',
  'construction_scheme',
  'hazardous_special_scheme',
  'distribution_network_special_scheme',
  'supervision_plan',
  'review_support_material'
];

export const DEFAULT_MODULES = [
  'structure_completeness',
  'parameter_consistency',
  'legality_compliance',
  'execution_continuity',
  'evidence_validation'
];

export const WORKFLOW_TOOL_SPECS = [
  {
    key: 'hermes_review_context_wft',
    name: 'Hermes 审查上下文工具',
    intro: '读取文件、解析正文、生成 facts/profile/basis/governed context。',
    description: 'Hermes review context workflow tool',
    avatar: 'core/app/type/pluginFill',
    tags: ['review', 'workflow-tool', 'hermes']
  },
  {
    key: 'hermes_ai_review_wft',
    name: 'Hermes AI 主审工具',
    intro: '选择 AI reviewer，并生成 Hermes 主审 reviewer packets。',
    description: 'Hermes AI review workflow tool',
    avatar: 'core/app/type/pluginFill',
    tags: ['review', 'workflow-tool', 'hermes']
  },
  {
    key: 'hermes_deterministic_review_wft',
    name: 'Hermes 确定性审查工具',
    intro: '执行可视域、合规、规范有效性与计算 fallback 审查。',
    description: 'Hermes deterministic review workflow tool',
    avatar: 'core/app/type/pluginFill',
    tags: ['review', 'workflow-tool', 'hermes']
  },
  {
    key: 'hermes_support_008_wft',
    name: 'Hermes 008 支撑层工具',
    intro: '生成 008 支撑层结果与 supportPacket008。',
    description: 'Hermes support 008 workflow tool',
    avatar: 'core/app/type/pluginFill',
    tags: ['review', 'workflow-tool', 'hermes']
  },
  {
    key: 'hermes_final_assembler_wft',
    name: 'Hermes 最终组装工具',
    intro: '执行 fail-closed、模块门禁、最终报告与降级出口组装。',
    description: 'Hermes final assembler workflow tool',
    avatar: 'core/app/type/pluginFill',
    tags: ['review', 'workflow-tool', 'hermes']
  }
];

export const PLACEHOLDER_AI_MODEL = '__FASTGPT_AI_MODEL__';
export const WORKFLOW_TOOL_ID_PLACEHOLDER_PREFIX = '__FASTGPT_WORKFLOW_TOOL_ID__';

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function unique(items = []) {
  return [...new Set((items || []).filter(Boolean))];
}

function slugify(value = '') {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fff]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'item';
}

function placeholderToolId(key) {
  return `${WORKFLOW_TOOL_ID_PLACEHOLDER_PREFIX}${key}__`;
}

function makeDatasetPlaceholder(index) {
  return `__FASTGPT_DATASET_ID_${String(index).padStart(3, '0')}__`;
}

function pos(x, y) {
  return { x, y };
}

function ref(nodeId, outputKey) {
  return [[nodeId, outputKey]];
}

function renderTypesForValueType(valueType, mode = 'reference') {
  const byMode = {
    reference: {
      string: ['reference', 'textarea'],
      number: ['reference', 'numberInput'],
      boolean: ['reference', 'switch'],
      object: ['reference', 'JSONEditor'],
      arrayObject: ['reference', 'JSONEditor'],
      arrayString: ['reference', 'JSONEditor'],
      any: ['reference', 'JSONEditor'],
      chatHistory: ['reference']
    },
    input: {
      string: ['input', 'reference'],
      number: ['numberInput', 'reference'],
      boolean: ['switch', 'reference'],
      object: ['JSONEditor', 'reference'],
      arrayObject: ['JSONEditor', 'reference'],
      arrayString: ['JSONEditor', 'reference'],
      any: ['JSONEditor', 'reference'],
      chatHistory: ['reference']
    }
  };
  return (byMode[mode] && byMode[mode][valueType]) || ['reference'];
}

function inputField({
  key,
  label,
  valueType = 'string',
  required = false,
  renderTypeList,
  value,
  description,
  placeholder,
  toolDescription,
  maxLength,
  isToolOutput
}) {
  const item = {
    key,
    label: label || key,
    valueType,
    renderTypeList: renderTypeList || renderTypesForValueType(valueType, value === undefined ? 'input' : 'reference')
  };
  if (required) item.required = true;
  if (value !== undefined) item.value = value;
  if (description) item.description = description;
  if (placeholder) item.placeholder = placeholder;
  if (toolDescription !== undefined) item.toolDescription = toolDescription;
  if (maxLength !== undefined) item.maxLength = maxLength;
  if (isToolOutput !== undefined) item.isToolOutput = isToolOutput;
  return item;
}

function staticOutput(key, label, valueType = 'string', description = '') {
  return {
    id: key,
    key,
    label: label || key,
    type: 'static',
    valueType,
    description
  };
}

function dynamicOutput(key, label, valueType = 'any', description = '') {
  return {
    id: key,
    key,
    label: label || key,
    type: 'dynamic',
    valueType,
    description
  };
}

function pluginInputNode(inputs, x, y) {
  return {
    nodeId: 'pluginInput',
    name: '工具输入',
    avatar: 'core/workflow/template/workflowStart',
    flowNodeType: 'pluginInput',
    showStatus: false,
    position: pos(x, y),
    version: '489',
    inputs,
    outputs: [
      ...inputs.map((item) =>
        staticOutput(item.key, item.label || item.key, item.valueType, item.description || '')
      ),
      staticOutput('userFiles', '会话上传文件', 'arrayString', '插件单独运行时的会话文件链接')
    ]
  };
}

function pluginOutputNode(inputs, x, y) {
  return {
    nodeId: 'pluginOutput',
    name: '工具输出',
    avatar: 'core/workflow/template/pluginOutput',
    flowNodeType: 'pluginOutput',
    showStatus: false,
    position: pos(x, y),
    version: '489',
    inputs,
    outputs: []
  };
}

function pluginConfigNode(x, y) {
  return {
    nodeId: 'pluginConfig',
    name: '系统配置',
    intro: '',
    avatar: 'core/workflow/template/systemConfig',
    flowNodeType: 'pluginConfig',
    position: pos(x, y),
    version: '489',
    inputs: [],
    outputs: []
  };
}

function readFilesNode({
  nodeId,
  name,
  x,
  y,
  fileUrlRef,
  parentNodeId
}) {
  return {
    nodeId,
    parentNodeId,
    name,
    intro: '读取文件正文',
    avatar: 'core/workflow/template/readFiles',
    flowNodeType: 'readFiles',
    showStatus: true,
    position: pos(x, y),
    version: '489',
    inputs: [
      inputField({
        key: 'fileUrlList',
        label: '文件链接',
        valueType: 'arrayString',
        required: true,
        renderTypeList: ['reference', 'input'],
        value: fileUrlRef
      })
    ],
    outputs: [
      staticOutput('text', '读取结果', 'string', '拼接后的文件正文'),
      staticOutput('system_rawResponse', '原始读取结果', 'arrayObject', '每个文件的读取结果'),
      staticOutput('error', '错误', 'string', '读取文件时的错误信息')
    ]
  };
}

function codeNode({
  nodeId,
  name,
  intro,
  x,
  y,
  inputs,
  outputs,
  code,
  parentNodeId
}) {
  return {
    nodeId,
    parentNodeId,
    name,
    intro,
    avatar: 'core/workflow/template/codeRun',
    flowNodeType: 'code',
    showStatus: true,
    position: pos(x, y),
    version: '489',
    catchError: false,
    inputs: [
      ...inputs,
      {
        key: 'codeType',
        renderTypeList: ['hidden'],
        label: '',
        valueType: 'string',
        value: 'js'
      },
      {
        key: 'code',
        renderTypeList: ['custom'],
        label: '',
        valueType: 'string',
        value: code
      }
    ],
    outputs: [
      staticOutput('system_rawResponse', '完整返回', 'object', '代码节点的完整返回对象'),
      ...outputs,
      staticOutput('error', '错误', 'string', '代码执行错误')
    ]
  };
}

function chatNode({
  nodeId,
  name,
  intro,
  x,
  y,
  modelValue,
  systemPromptRef,
  userPromptRef,
  fileUrlRef,
  parentNodeId
}) {
  return {
    nodeId,
    parentNodeId,
    name,
    intro,
    avatar: 'core/workflow/template/aiChat',
    flowNodeType: 'chatNode',
    showStatus: true,
    position: pos(x, y),
    version: '489',
    catchError: false,
    inputs: [
      {
        key: 'model',
        renderTypeList: ['settingLLMModel', 'reference'],
        label: '模型',
        valueType: 'string',
        required: true,
        value: modelValue
      },
      { key: 'temperature', renderTypeList: ['hidden'], label: '', valueType: 'number', value: 0.2 },
      { key: 'maxToken', renderTypeList: ['hidden'], label: '', valueType: 'number', value: 4000 },
      { key: 'isResponseAnswerText', renderTypeList: ['hidden'], label: '', valueType: 'boolean', value: true },
      { key: 'quoteRole', renderTypeList: ['hidden'], label: '', valueType: 'string', value: 'system' },
      { key: 'quoteTemplate', renderTypeList: ['hidden'], label: '', valueType: 'string', value: '' },
      { key: 'quotePrompt', renderTypeList: ['hidden'], label: '', valueType: 'string', value: '' },
      { key: 'aiChatVision', renderTypeList: ['hidden'], label: '', valueType: 'boolean', value: true },
      { key: 'aiChatReasoning', renderTypeList: ['hidden'], label: '', valueType: 'boolean', value: false },
      { key: 'aiChatTopP', renderTypeList: ['hidden'], label: '', valueType: 'number', value: 1 },
      { key: 'aiChatStopSign', renderTypeList: ['hidden'], label: '', valueType: 'string', value: '' },
      { key: 'aiChatResponseFormat', renderTypeList: ['hidden'], label: '', valueType: 'string', value: 'json_object' },
      { key: 'aiChatJsonSchema', renderTypeList: ['hidden'], label: '', valueType: 'string', value: '' },
      {
        key: 'systemPrompt',
        renderTypeList: ['reference', 'textarea'],
        label: '系统提示词',
        valueType: 'string',
        value: systemPromptRef
      },
      {
        key: 'history',
        renderTypeList: ['reference', 'numberInput'],
        label: '历史消息',
        valueType: 'chatHistory',
        value: 0,
        required: true
      },
      {
        key: 'fileUrlList',
        renderTypeList: ['reference', 'input'],
        label: '用户文件',
        valueType: 'arrayString',
        value: fileUrlRef || []
      },
      {
        key: 'userChatInput',
        renderTypeList: ['reference', 'textarea'],
        label: '用户输入',
        valueType: 'string',
        required: true,
        value: userPromptRef,
        toolDescription: '用户问题'
      }
    ],
    outputs: [
      staticOutput('history', '新上下文', 'chatHistory', '模型返回后的上下文'),
      staticOutput('text', '模型输出', 'string', 'AI 节点输出文本'),
      staticOutput('reasoningText', '推理内容', 'string', '模型推理内容'),
      staticOutput('error', '错误', 'string', 'AI 节点错误')
    ]
  };
}

function workflowStartNode(x, y) {
  return {
    nodeId: 'workflowStart',
    name: '工作流开始',
    intro: '接收用户输入与文件',
    avatar: 'core/workflow/template/workflowStart',
    flowNodeType: 'workflowStart',
    position: pos(x, y),
    version: '489',
    inputs: [
      {
        key: 'userChatInput',
        renderTypeList: ['reference', 'textarea'],
        valueType: 'string',
        label: '用户问题',
        required: true,
        toolDescription: '用户问题'
      }
    ],
    outputs: [
      staticOutput('userChatInput', '用户问题', 'string', '标准化后的文本输入'),
      staticOutput('userFiles', '上传文件', 'arrayString', '用户上传文件链接')
    ]
  };
}

function answerNode(nodeId, x, y, answerRef) {
  return {
    nodeId,
    name: '输出结果',
    intro: '返回最终审查结果',
    avatar: 'core/workflow/template/reply',
    flowNodeType: 'answerNode',
    position: pos(x, y),
    version: '489',
    showStatus: true,
    inputs: [
      {
        key: 'answerText',
        renderTypeList: ['reference', 'textarea'],
        valueType: 'any',
        required: true,
        isRichText: false,
        maxLength: 100000,
        label: '响应内容',
        value: answerRef
      }
    ],
    outputs: []
  };
}

function pluginModuleNode({
  nodeId,
  name,
  intro,
  key,
  x,
  y,
  inputs,
  outputs
}) {
  return {
    nodeId,
    name,
    intro,
    avatar: 'core/app/type/pluginFill',
    flowNodeType: 'pluginModule',
    showStatus: true,
    position: pos(x, y),
    version: '489',
    pluginId: placeholderToolId(key),
    inputs,
    outputs
  };
}

function systemConfigNode(x, y) {
  return {
    nodeId: 'userGuide',
    name: '系统配置',
    intro: 'Hermes 结构化审查主工作流',
    avatar: 'core/workflow/template/systemConfig',
    flowNodeType: 'userGuide',
    position: pos(x, y),
    version: '489',
    inputs: [],
    outputs: []
  };
}

function reverseTemplateModules(moduleBindings = {}) {
  const result = {};
  for (const [moduleName, binding] of Object.entries(moduleBindings)) {
    for (const templateId of binding?.hermes_templates || []) {
      if (!result[templateId]) result[templateId] = [];
      result[templateId].push(moduleName);
    }
  }
  return result;
}

export function buildDatasetManifest(basisRegistry = {}) {
  const basisDatasets = {};
  const datasetGroups = {};
  let index = 1;
  for (const [basisId, basis] of Object.entries(basisRegistry)) {
    const placeholder = makeDatasetPlaceholder(index++);
    const payload = {
      basisId,
      title: basis.title || basisId,
      sourceType: basis.source_type || 'unknown',
      effectiveStatus: basis.effective_status || 'unknown',
      applicabilityTags: basis.applicability_tags || [],
      fileRefs: basis.file_refs || [],
      datasetIdPlaceholder: placeholder
    };
    basisDatasets[basisId] = payload;
    for (const tag of basis.applicability_tags || []) {
      if (tag === 'all') {
        for (const docType of DOC_TYPES) {
          datasetGroups[docType] = unique([...(datasetGroups[docType] || []), basisId]);
        }
      } else if (DOC_TYPES.includes(tag)) {
        datasetGroups[tag] = unique([...(datasetGroups[tag] || []), basisId]);
      }
    }
  }
  return { basisDatasets, datasetGroups };
}

export function loadGeneratedAssets(repoRoot) {
  const generatedDir = path.join(
    repoRoot,
    'integrations',
    'fastgpt',
    'toolset',
    'hermesStructuredReview',
    'assets',
    'generated'
  );
  const read = (name) => JSON.parse(fs.readFileSync(path.join(generatedDir, name), 'utf8'));
  const assets = {
    generatedDir,
    moduleBindings: read('module_bindings.json'),
    moduleTitles: read('module_titles.json'),
    docTypeLabels: read('doc_type_labels.json'),
    templateManifest: read('template_manifest.json'),
    profileMapping: read('profile_mapping.json'),
    packRegistry: read('pack_registry.json'),
    rulePackRegistry: read('rule_pack_registry.json'),
    basisRegistry: read('basis_registry.json'),
    evidenceTitles: read('evidence_titles.json'),
    evidenceFindingTypes: read('evidence_finding_types.json'),
    evidenceManualReviewReasons: read('evidence_manual_review_reasons.json')
  };
  assets.datasetManifest = buildDatasetManifest(assets.basisRegistry);
  assets.templateModuleMap = reverseTemplateModules(assets.moduleBindings);
  return assets;
}

function reviewContextCode() {
  return String.raw`function main(input) {
  const {
    query = '',
    documentType = '',
    disciplineTags = [],
    enabledModules = [],
    disabledModules = [],
    focusRequirements = [],
    strictMode = true,
    targetFilesText = '',
    targetFilesRaw = [],
    basisFilesRaw = [],
    contextFilesRaw = [],
    snapshot = {}
  } = input || {};

  const DEFAULT_MODULES = ['structure_completeness', 'parameter_consistency', 'legality_compliance', 'execution_continuity', 'evidence_validation'];
  const unique = (items) => [...new Set((Array.isArray(items) ? items : []).filter(Boolean))];
  const normalizeText = (value) => String(value || '').replace(/\r\n/g, '\n').replace(/\u00a0/g, ' ').trim();
  const slugify = (value) => String(value || '').toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '_').replace(/^_+|_+$/g, '') || 'item';
  const hasAnyKeyword = (text, keywords) => (keywords || []).some((keyword) => text.includes(keyword));
  const extractContent = (entry) => {
    const raw = String(entry && entry.text ? entry.text : '');
    const match = raw.match(/<Content>\n?([\s\S]*?)\n?<\/Content>/i);
    return normalizeText(match ? match[1] : raw.replace(/^File:[^\n]*\n?/i, ''));
  };
  const fileLabel = (entry, index) => {
    return (entry && (entry.filename || entry.url)) || 'document_' + (index + 1);
  };
  const detectHeadingLevel = (text) => {
    if (/^#{1,6}\s+/.test(text)) return Math.min((text.match(/^#+/) || ['#'])[0].length, 4);
    if (/^[一二三四五六七八九十]+[、.]/.test(text)) return 1;
    if (/^\d+[、.]/.test(text)) return 2;
    if (/^\(?[一二三四五六七八九十]+\)/.test(text) || /^\([0-9]+\)/.test(text)) return 3;
    return null;
  };

  const targetRaw = Array.isArray(targetFilesRaw) ? targetFilesRaw : [];
  const targetContents = targetRaw.map(extractContent).filter(Boolean);
  const normalizedTextValue = normalizeText(targetContents.length ? targetContents.join('\n\n') : targetFilesText);
  const lines = normalizedTextValue.split('\n').map((line) => normalizeText(line)).filter(Boolean);
  const sections = [];
  const blocks = [];
  const attachments = [];
  const sectionStack = [];
  const currentSectionId = () => sectionStack.length ? sectionStack[sectionStack.length - 1].id : null;

  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    const headingLevel = detectHeadingLevel(line);
    const blockId = 'block_' + (index + 1);
    if (/附件|附图|附表|图纸|详图|见图/.test(line)) {
      attachments.push({
        id: 'attachment_' + attachments.length,
        title: line,
        sectionId: currentSectionId(),
        visibility: /详图|图纸/.test(line) ? 'referenced_only' : 'parsed'
      });
    }
    if (headingLevel) {
      while (sectionStack.length && sectionStack[sectionStack.length - 1].level >= headingLevel) {
        sectionStack.pop();
      }
      const sectionId = 'section_' + (sections.length + 1);
      const section = {
        id: sectionId,
        title: line.replace(/^#+\s*/, ''),
        key: slugify(line.replace(/^#+\s*/, '')),
        level: headingLevel,
        parentId: currentSectionId(),
        blockId,
        position: index + 1
      };
      sections.push(section);
      sectionStack.push(section);
    }
    blocks.push({
      id: blockId,
      type: headingLevel ? 'heading' : 'paragraph',
      text: line,
      sectionId: currentSectionId(),
      headingLevel,
      position: index + 1
    });
  }

  const titleCounts = {};
  const duplicateSectionTitles = [];
  sections.filter((section) => section.level <= 2).forEach((section) => {
    titleCounts[section.key] = (titleCounts[section.key] || 0) + 1;
    if (titleCounts[section.key] === 2) duplicateSectionTitles.push(section.key);
  });

  const visibility = {
    attachmentCount: attachments.length,
    counts: attachments.reduce((acc, item) => {
      const key = String(item.visibility || 'parsed');
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {}),
    reasonCounts: attachments.some((item) => item.visibility === 'referenced_only') ? { reference_detected_without_attachment_body: 1 } : {},
    duplicateSectionTitles,
    parseWarnings: ['text_tables_not_preserved', 'text_attachment_boundaries_inferred_from_headings'],
    manualReviewNeeded: attachments.some((item) => item.visibility !== 'parsed'),
    manualReviewReason: attachments.some((item) => item.visibility !== 'parsed') ? 'reference_detected_without_attachment_body' : null
  };

  const parseResult = {
    documentId: fileLabel(targetRaw[0], 0).replace(/\.[^.]+$/, ''),
    fileType: 'readFiles',
    parseMode: 'fastgpt_readfiles_text',
    parserLimited: false,
    sections,
    blocks,
    attachments,
    normalizedText: normalizedTextValue,
    preview: normalizedTextValue.slice(0, 4000),
    visibility,
    parseWarnings: visibility.parseWarnings
  };

  const coreSectionKeywords = {
    construction_org: [
      { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
      { itemKey: 'preparationBasis', keywords: ['编制依据', '编制说明'] },
      { itemKey: 'constructionDeployment', keywords: ['施工部署'] },
      { itemKey: 'schedulePlan', keywords: ['施工进度', '进度计划'] },
      { itemKey: 'resourcePlan', keywords: ['资源配置', '人员计划'] },
      { itemKey: 'safetyMeasures', keywords: ['安全措施', '安全技术'] },
      { itemKey: 'emergencyPlan', keywords: ['应急预案', '应急处置'] },
      { itemKey: 'siteLayout', keywords: ['平面布置', '施工总平面'] }
    ],
    construction_scheme: [
      { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
      { itemKey: 'preparationBasis', keywords: ['编制依据', '编制说明'] },
      { itemKey: 'processMethod', keywords: ['施工方法', '工艺流程'] },
      { itemKey: 'safetyMeasures', keywords: ['安全措施', '安全技术'] }
    ],
    hazardous_special_scheme: [
      { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
      { itemKey: 'preparationBasis', keywords: ['编制依据', '编制说明'] },
      { itemKey: 'constructionPlan', keywords: ['施工计划', '施工方案'] },
      { itemKey: 'processMethod', keywords: ['工艺流程', '施工工艺'] },
      { itemKey: 'safetyMeasures', keywords: ['安全措施', '安全技术'] },
      { itemKey: 'emergencyPlan', keywords: ['应急预案', '应急处置'] },
      { itemKey: 'calculationBook', keywords: ['计算书', '验算'] }
    ],
    distribution_network_special_scheme: [
      { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
      { itemKey: 'preparationBasis', keywords: ['编制依据', '编制说明'] },
      { itemKey: 'riskIdentification', keywords: ['风险辨识', '风险分级'] },
      { itemKey: 'safetyMeasures', keywords: ['安全措施', '停电', '验电', '接地'] },
      { itemKey: 'emergencyPlan', keywords: ['应急预案', '应急处置'] },
      { itemKey: 'ticketChain', keywords: ['工作票', '操作票', '现场勘察'] }
    ],
    supervision_plan: [
      { itemKey: 'engineeringOverview', keywords: ['工程概况'] },
      { itemKey: 'monitoringPlan', keywords: ['监测监控', '旁站', '巡视'] },
      { itemKey: 'safetyMeasures', keywords: ['安全监理', '安全控制'] }
    ],
    review_support_material: [
      { itemKey: 'materialScope', keywords: ['审查支持材料', '支持材料'] }
    ]
  };

  const sectionsForDoc = coreSectionKeywords[documentType] || [];
  const sectionPresence = Object.fromEntries(sectionsForDoc.map((item) => [item.itemKey, hasAnyKeyword(normalizedTextValue, item.keywords)]));
  const structureCompleteness = sectionsForDoc.map((item) => ({
    itemKey: item.itemKey,
    scope: 'common',
    status: sectionPresence[item.itemKey] ? 'complete' : 'missing'
  }));
  const hazardKeywords = {
    lifting_operations: ['吊装', '起重'],
    temporary_power: ['临时用电', '停送电'],
    hot_work: ['动火'],
    gas_area_ops: ['煤气', '有毒有害气体']
  };
  const highRiskCategories = Object.keys(hazardKeywords).filter((key) => hasAnyKeyword(normalizedTextValue, hazardKeywords[key]));
  const facts = {
    projectFacts: {
      sectionPresence,
      structureCompleteness,
      duplicateSections: duplicateSectionTitles
    },
    attachmentFacts: { attachments },
    hazardFacts: {
      highRiskCategories,
      specialSchemePlanStatus: normalizedTextValue.includes('专项方案') ? 'explicit_section' : (highRiskCategories.length ? 'generic_mention_only' : 'not_applicable')
    },
    emergencyFacts: {
      targetedPlanCount: (normalizedTextValue.match(/应急预案|应急处置/g) || []).length,
      planTitles: normalizedTextValue.includes('应急预案') ? ['应急预案'] : []
    },
    scheduleFacts: {
      shutdownWindowDays: Number((normalizedTextValue.match(/(\d+)\s*天/) || [])[1] || 0) || null
    },
    resourceFacts: {
      laborTotal: Number((normalizedTextValue.match(/(\d+)\s*人/) || [])[1] || 0) || null
    }
  };

  const profileMapping = snapshot.profileMapping || {};
  const packRegistry = (snapshot.packRegistry && (snapshot.packRegistry.packs || snapshot.packRegistry)) || {};
  const rulePackRegistry = (snapshot.rulePackRegistry && (snapshot.rulePackRegistry.rule_packs || snapshot.rulePackRegistry)) || {};
  const basisRegistry = snapshot.basisRegistry || {};
  const datasetManifest = snapshot.datasetManifest || {};
  const mapping = profileMapping[documentType] || {};
  const requestedPackIds = unique((Array.isArray(focusRequirements) ? focusRequirements : []).filter((item) => String(item).endsWith('.base')));
  const requestedRulePackIds = unique((Array.isArray(focusRequirements) ? focusRequirements : []).filter((item) => String(item).includes('.v1')));
  const basePackIds = unique([...(mapping.default_pack_ids || []), ...requestedPackIds]);
  const rulePackIds = unique([...(mapping.rule_pack_ids || []), ...requestedRulePackIds]);
  const degradationReasons = [];
  let degraded = false;
  const packIds = new Set();
  const packs = [];
  const rulePacks = [];
  const basisIds = [];

  basePackIds.forEach((packId) => {
    const pack = packRegistry[packId];
    if (!pack) {
      degraded = true;
      degradationReasons.push('missing pack: ' + packId);
      return;
    }
    packIds.add(packId);
    packs.push({
      pack_id: packId,
      status: pack.status || 'unknown',
      role: pack.role || 'unknown',
      family: pack.family || 'unknown',
      basis_ids: pack.basis_ids || []
    });
    basisIds.push(...(pack.basis_ids || []));
  });

  rulePackIds.forEach((rulePackId) => {
    const rulePack = rulePackRegistry[rulePackId];
    if (!rulePack) {
      degraded = true;
      degradationReasons.push('missing rule pack: ' + rulePackId);
      return;
    }
    rulePacks.push({
      rule_pack_id: rulePackId,
      scope: rulePack.scope || '',
      related_pack_ids: rulePack.related_pack_ids || [],
      evidence_requirements: rulePack.evidence_requirements || []
    });
    (rulePack.related_pack_ids || []).forEach((relatedPackId) => {
      if (packIds.has(relatedPackId)) return;
      const relatedPack = packRegistry[relatedPackId];
      if (!relatedPack) return;
      packIds.add(relatedPackId);
      packs.push({
        pack_id: relatedPackId,
        status: relatedPack.status || 'unknown',
        role: relatedPack.role || 'unknown',
        family: relatedPack.family || 'unknown',
        basis_ids: relatedPack.basis_ids || []
      });
      basisIds.push(...(relatedPack.basis_ids || []));
    });
  });

  const resolvedBasisProfile = {
    profile_id: mapping.profile_id || documentType,
    level1_classification: mapping.classification && mapping.classification.level1 || 'Unknown',
    level2_classification: mapping.classification && mapping.classification.level2 || 'Unknown',
    level3_classification: mapping.classification && mapping.classification.level3 || null,
    packs,
    rule_packs: rulePacks,
    basis_documents: unique(basisIds).map((basisId) => {
      const basis = basisRegistry[basisId];
      if (!basis) {
        degraded = true;
        degradationReasons.push('missing basis: ' + basisId);
        return {
          basis_id: basisId,
          title: basisId,
          degraded: true,
          degradation_reason: 'missing basis ' + basisId
        };
      }
      return {
        basis_id: basisId,
        title: basis.title || basisId,
        source_type: basis.source_type || 'unknown',
        effective_status: basis.effective_status || 'unknown',
        jurisdiction: basis.jurisdiction || 'unknown',
        file_refs: basis.file_refs || []
      };
    }),
    degraded,
    degradation_reasons: degradationReasons
  };

  const governedDatasetScope = {
    basisIds: resolvedBasisProfile.basis_documents.map((item) => item.basis_id),
    datasetIds: resolvedBasisProfile.basis_documents.map((item) => {
      const dataset = datasetManifest.basisDatasets && datasetManifest.basisDatasets[item.basis_id];
      return dataset ? dataset.datasetIdPlaceholder : null;
    }).filter(Boolean),
    byDocumentType: (datasetManifest.datasetGroups && datasetManifest.datasetGroups[documentType]) || []
  };

  const structureRuleMap = {
    construction_org: 'construction_org_structure_completeness',
    construction_scheme: 'construction_scheme_structure_completeness',
    hazardous_special_scheme: 'hazardous_special_scheme_core_sections',
    distribution_network_special_scheme: 'distribution_network_special_scheme_structure_completeness',
    supervision_plan: 'supervision_plan_structure_completeness',
    review_support_material: 'review_support_material_context_only'
  };
  const ruleHits = [];
  const missingSections = structureCompleteness.filter((item) => item.status !== 'complete');
  const basePackId = String((packs[0] && packs[0].pack_id) || (documentType + '.base'));
  ruleHits.push({
    ruleId: structureRuleMap[documentType] || (documentType + '_structure_completeness'),
    packId: basePackId,
    packReadiness: 'ready',
    matchType: 'direct_hit',
    status: missingSections.length ? 'hit' : 'pass',
    layerHint: 'L1',
    severityHint: missingSections.length >= 2 ? 'high' : 'medium',
    factRefs: missingSections.map((item) => 'project.structureCompleteness.' + item.itemKey),
    evidenceRefs: ['policy:structure'],
    rationale: '核心章节缺失或结构不完整。'
  });
  if (parseResult.visibility.manualReviewNeeded) {
    ruleHits.push({
      ruleId: documentType + '_attachment_visibility',
      packId: basePackId,
      packReadiness: 'ready',
      matchType: 'visibility_gap',
      status: 'manual_review_needed',
      layerHint: 'L1',
      severityHint: 'medium',
      factRefs: ['attachments.visibility'],
      evidenceRefs: ['policy:review_visibility_gap'],
      rationale: '附件或图纸存在可视域缺口。',
      applicabilityState: 'blocked_by_visibility',
      blockingReasons: ['visibility_gap']
    });
  }
  if (highRiskCategories.length && (facts.emergencyFacts.targetedPlanCount || 0) < 2) {
    ruleHits.push({
      ruleId: documentType + '_emergency_targeted',
      packId: basePackId,
      packReadiness: 'ready',
      matchType: 'direct_hit',
      status: 'hit',
      layerHint: 'L2',
      severityHint: 'medium',
      factRefs: ['emergency.planTitles'],
      evidenceRefs: ['policy:emergency_plan_targeted'],
      rationale: '高风险场景下应急安排针对性不足。'
    });
  }

  const inferModuleName = (value) => {
    const lower = String(value || '').toLowerCase();
    if (lower.includes('visibility') || lower.includes('evidence') || lower.includes('normative') || lower.includes('calculation')) return 'evidence_validation';
    if (lower.includes('structure') || lower.includes('完整')) return 'structure_completeness';
    if (lower.includes('consistency') || lower.includes('parameter') || lower.includes('resource')) return 'parameter_consistency';
    if (lower.includes('operation_chain') || lower.includes('execution') || lower.includes('ticket') || lower.includes('power_outage')) return 'execution_continuity';
    return 'legality_compliance';
  };

  const candidates = ruleHits
    .filter((hit) => hit.status === 'hit' || hit.status === 'manual_review_needed')
    .map((hit, index) => ({
      candidateId: hit.ruleId,
      title: (snapshot.evidenceTitles && snapshot.evidenceTitles[hit.ruleId]) || hit.ruleId,
      layerHint: hit.layerHint,
      severityHint: hit.severityHint,
      findingType: (snapshot.evidenceFindingTypes && snapshot.evidenceFindingTypes[hit.ruleId]) || (hit.status === 'manual_review_needed' ? 'visibility_gap' : 'hard_evidence'),
      ruleHits: [hit],
      evidenceMissing: hit.status === 'manual_review_needed',
      manualReviewNeeded: hit.status === 'manual_review_needed',
      manualReviewReason: (snapshot.evidenceManualReviewReasons && snapshot.evidenceManualReviewReasons[hit.ruleId]) || (hit.status === 'manual_review_needed' ? 'visibility_gap' : undefined),
      blockingReasons: hit.blockingReasons || [],
      moduleName: inferModuleName(hit.ruleId)
    }));

  const normalizedEnabledModules = unique((Array.isArray(enabledModules) && enabledModules.length ? enabledModules : DEFAULT_MODULES).filter((item) => !(Array.isArray(disabledModules) && disabledModules.includes(item))));
  const resolvedProfile = {
    profileId: resolvedBasisProfile.profile_id,
    documentType,
    disciplineTags: Array.isArray(disciplineTags) ? disciplineTags : [],
    enabledModules: normalizedEnabledModules,
    strictMode: strictMode !== false
  };

  const supportPacketBase = {
    document_type: documentType,
    profile: resolvedBasisProfile,
    facts,
    basis_summary: resolvedBasisProfile.basis_documents.map((item) => ({
      basis_id: item.basis_id,
      title: item.title,
      effective_status: item.effective_status || 'unknown'
    })),
    rule_pack_summary: resolvedBasisProfile.rule_packs,
    warning_signals: resolvedBasisProfile.degradation_reasons,
    degraded: resolvedBasisProfile.degraded
  };

  return {
    reviewContext: {
      query,
      documentType,
      disciplineTags: Array.isArray(disciplineTags) ? disciplineTags : [],
      enabledModules: normalizedEnabledModules,
      disabledModules: Array.isArray(disabledModules) ? disabledModules : [],
      focusRequirements: Array.isArray(focusRequirements) ? focusRequirements : [],
      strictMode: strictMode !== false,
      parseResult,
      docTextPreview: parseResult.preview,
      facts,
      ruleHits,
      candidates,
      resolvedProfile,
      resolvedBasisProfile,
      governedDatasetScope,
      supportPacketBase,
      targetFileUrls: (targetRaw || []).map((item) => item.url).filter(Boolean),
      basisFileUrls: (basisFilesRaw || []).map((item) => item.url).filter(Boolean),
      contextFileUrls: (contextFilesRaw || []).map((item) => item.url).filter(Boolean)
    },
    parseResult,
    docTextPreview: parseResult.preview,
    resolvedProfile,
    resolvedBasisProfile,
    governedDatasetScope,
    supportPacketBase
  };
}`;
}

function aiReviewPlannerCode() {
  return String.raw`function main(input) {
  const {
    reviewId = '',
    query = '',
    documentType = '',
    enabledModules = [],
    focusRequirements = [],
    strictMode = true,
    reviewContext = {},
    targetFileUrls = [],
    snapshot = {},
    aiModel = '__FASTGPT_AI_MODEL__'
  } = input || {};

  const DEFAULT_MODULES = ['structure_completeness', 'parameter_consistency', 'legality_compliance', 'execution_continuity', 'evidence_validation'];
  const unique = (items) => [...new Set((Array.isArray(items) ? items : []).filter(Boolean))];
  const moduleBindings = snapshot.moduleBindings || {};
  const templateManifest = Array.isArray(snapshot.templateManifest) ? snapshot.templateManifest : [];
  const templateModuleMap = snapshot.templateModuleMap || {};
  const deterministicReviewers = new Set(['visibility_gap_reviewer', 'policy_compliance_reviewer', 'normative_validity_reviewer']);
  const modules = unique((Array.isArray(enabledModules) && enabledModules.length ? enabledModules : DEFAULT_MODULES));
  const selectedTemplateIds = unique(modules.flatMap((moduleName) => (moduleBindings[moduleName] && moduleBindings[moduleName].hermes_templates) || []));

  const selectedReviewers = selectedTemplateIds
    .filter((templateId) => !deterministicReviewers.has(templateId))
    .map((templateId) => templateManifest.find((item) => item.id === templateId))
    .filter(Boolean)
    .filter((template) => !Array.isArray(template.supported_document_types) || template.supported_document_types.length === 0 || template.supported_document_types.includes(documentType))
    .map((template) => ({
      reviewerId: template.id,
      agentName: template.agent_name || template.id,
      agentPurpose: template.agent_purpose || '',
      prompt: template.prompt || '',
      instructions: template.instructions || '',
      reviewModules: templateModuleMap[template.id] || ((template.metadata && template.metadata.review_modules) || []),
      supportedDocumentTypes: template.supported_document_types || []
    }));

  const contextPreview = String(reviewContext.docTextPreview || '').slice(0, 12000);
  const facts = reviewContext.facts || {};
  const basisSummary = (((reviewContext.resolvedBasisProfile || {}).basis_documents) || []).map((item) => item.title).slice(0, 20);
  const reviewPrompt = [
    '你是 Hermes 正式审查主审执行器。请对每个 reviewer 单独输出结构化结论。',
    '严格要求：',
    '1. 只输出 JSON；',
    '2. 必须按 selectedReviewers 顺序输出 reviewerPackets；',
    '3. 每个 finding 只能基于已给出的文档内容、facts、basis_summary 与 reviewer prompt；',
    '4. 若证据不足，使用 evidence_status=evidence_gap 或 visibility_gap，并保守表达；',
    '5. 不得输出正式总裁决，只输出 reviewerPackets。',
    '',
    'selectedReviewers:',
    JSON.stringify(selectedReviewers, null, 2),
    '',
    'reviewContextSummary:',
    JSON.stringify({
      reviewId,
      query,
      documentType,
      enabledModules: modules,
      focusRequirements,
      strictMode,
      basisSummary,
      facts,
      docTextPreview: contextPreview
    }, null, 2),
    '',
    'JSON 结构示例：',
    JSON.stringify({
      reviewerPackets: [
        {
          reviewerId: 'example_reviewer',
          reviewModules: ['structure_completeness'],
          degraded: false,
          overallAssessment: '字符串',
          findings: [
            {
              id: 'TMP-001',
              title: '字符串',
              severity: 'high',
              summary: '字符串',
              suggestion: '字符串',
              evidenceStatus: 'grounded',
              findingType: 'hard_evidence',
              moduleName: 'structure_completeness'
            }
          ]
        }
      ]
    }, null, 2)
  ].join('\n');

  return {
    selectedReviewers,
    aiModel: aiModel || '__FASTGPT_AI_MODEL__',
    aiSystemPrompt: '你必须返回严格 JSON，不要输出 markdown、解释或多余文本。',
    aiUserPrompt: reviewPrompt,
    targetFileUrls: Array.isArray(targetFileUrls) ? targetFileUrls : [],
    hasAiReviewers: selectedReviewers.length > 0
  };
}`;
}

function aiReviewNormalizeCode() {
  return String.raw`function main(input) {
  const {
    reviewId = '',
    aiAnswer = '',
    selectedReviewers = [],
    fallbackModuleMap = {}
  } = input || {};

  const parseJson = (text) => {
    const raw = String(text || '').trim();
    if (!raw) return {};
    const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
    const candidate = fenced ? fenced[1].trim() : raw;
    try {
      return JSON.parse(candidate);
    } catch (error) {
      return { error: 'JSON_PARSE_FAILED', raw: candidate };
    }
  };
  const severitySet = new Set(['high', 'medium', 'low', 'info']);
  const evidenceStatusSet = new Set(['grounded', 'inferred', 'evidence_gap', 'visibility_gap']);
  const payload = parseJson(aiAnswer);
  const rawPackets = Array.isArray(payload) ? payload : (Array.isArray(payload.reviewerPackets) ? payload.reviewerPackets : []);
  const packetMap = new Map();

  rawPackets.forEach((packet, packetIndex) => {
    if (!packet || !packet.reviewerId) return;
    packetMap.set(packet.reviewerId, {
      review_id: reviewId,
      engine: 'hermes',
      findings: Array.isArray(packet.findings) ? packet.findings.map((finding, findingIndex) => ({
        id: finding.id || ('H-AI-' + String(packetIndex + 1).padStart(2, '0') + '-' + String(findingIndex + 1).padStart(3, '0')),
        title: finding.title || '未命名问题',
        severity: severitySet.has(finding.severity) ? finding.severity : 'medium',
        category: finding.moduleName || ((packet.reviewModules && packet.reviewModules[0]) || 'legality_compliance'),
        summary: finding.summary || '未给出详细说明。',
        suggestion: finding.suggestion || '请人工复核并补充明确的整改措施。',
        evidence_status: evidenceStatusSet.has(finding.evidenceStatus) ? finding.evidenceStatus : 'inferred',
        source_engine: 'hermes',
        finding_type: finding.findingType || 'engineering_inference',
        raw_data: {
          module_name: finding.moduleName || ((packet.reviewModules && packet.reviewModules[0]) || 'legality_compliance'),
          template_id: packet.reviewerId,
          reviewer_id: packet.reviewerId
        }
      })) : [],
      overall_assessment: packet.overallAssessment || 'AI reviewer 已完成专项审查。',
      degraded: packet.degraded === true,
      error: packet.degraded ? (packet.error || (packet.reviewerId + ' 审查组件降级，未返回有效结果')) : undefined,
      metadata: {
        template_id: packet.reviewerId,
        agent_id: packet.reviewerId,
        review_modules: Array.isArray(packet.reviewModules) && packet.reviewModules.length ? packet.reviewModules : (fallbackModuleMap[packet.reviewerId] || [])
      }
    });
  });

  (Array.isArray(selectedReviewers) ? selectedReviewers : []).forEach((reviewer) => {
    if (packetMap.has(reviewer.reviewerId)) return;
    packetMap.set(reviewer.reviewerId, {
      review_id: reviewId,
      engine: 'hermes',
      findings: [],
      overall_assessment: reviewer.reviewerId + ' 未返回有效结果。',
      degraded: true,
      error: reviewer.reviewerId + ' 审查组件降级，未返回有效结果',
      metadata: {
        template_id: reviewer.reviewerId,
        agent_id: reviewer.reviewerId,
        review_modules: Array.isArray(reviewer.reviewModules) ? reviewer.reviewModules : (fallbackModuleMap[reviewer.reviewerId] || [])
      }
    });
  });

  const reviewerPackets = Array.from(packetMap.values());
  return {
    aiReview: {
      reviewerPackets,
      selectedReviewerIds: (Array.isArray(selectedReviewers) ? selectedReviewers : []).map((item) => item.reviewerId),
      degradedReviewerIds: reviewerPackets.filter((packet) => packet.degraded).map((packet) => packet.metadata.template_id)
    },
    reviewerPackets
  };
}`;
}

function deterministicReviewCode() {
  return String.raw`function main(input) {
  const {
    reviewId = '',
    reviewContext = {},
    enabledModules = [],
    aiReview = {}
  } = input || {};

  const DEFAULT_MODULES = ['structure_completeness', 'parameter_consistency', 'legality_compliance', 'execution_continuity', 'evidence_validation'];
  const modules = Array.isArray(enabledModules) && enabledModules.length ? enabledModules : DEFAULT_MODULES;
  const parseResult = reviewContext.parseResult || {};
  const candidates = Array.isArray(reviewContext.candidates) ? reviewContext.candidates : [];
  const text = String(parseResult.normalizedText || '');
  const reviewerPackets = [];

  const pushPacket = (packet) => reviewerPackets.push(packet);
  const makePacket = (reviewerId, reviewModules, findings, overall, degraded, error) => ({
    review_id: reviewId,
    engine: 'hermes',
    findings,
    overall_assessment: overall,
    degraded: !!degraded,
    error,
    metadata: {
      template_id: reviewerId,
      agent_id: reviewerId,
      review_modules: reviewModules
    }
  });

  if (modules.includes('evidence_validation')) {
    const visibilityNeeded = !!(parseResult.visibility && parseResult.visibility.manualReviewNeeded);
    pushPacket(makePacket(
      'visibility_gap_reviewer',
      ['evidence_validation'],
      visibilityNeeded ? [{
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
      }] : [],
      visibilityNeeded ? '可视域检查已完成。' : '未发现需要单列的可视域问题。'
    ));
  }

  if (modules.includes('legality_compliance')) {
    const findings = candidates.map((candidate, index) => ({
      id: 'H-POL-' + String(index + 1).padStart(3, '0'),
      title: candidate.title,
      severity: candidate.severityHint || 'medium',
      category: 'legality_compliance',
      summary: ((candidate.ruleHits || []).map((hit) => hit.rationale).filter(Boolean).join('；')) || (candidate.title + ' 已命中受治理审查规则。'),
      suggestion: candidate.manualReviewNeeded ? '请结合原件人工复核。' : '请依据规范条文完成补齐或修正。',
      evidence_status: candidate.manualReviewNeeded ? 'visibility_gap' : (candidate.evidenceMissing ? 'evidence_gap' : 'grounded'),
      source_engine: 'hermes',
      finding_type: candidate.findingType || 'hard_evidence',
      raw_data: { module_name: 'legality_compliance' }
    }));
    pushPacket(makePacket(
      'policy_compliance_reviewer',
      ['legality_compliance'],
      findings,
      findings.length ? '规范命中与证据线索已整理。' : '未发现需要单列的规范命中问题。'
    ));
  }

  if (modules.includes('evidence_validation')) {
    const NEGATIVE_HINTS = ['废止', '作废', '失效', '替代', '代替', '废除'];
    const EXCLUDED_DOCUMENT_KEYWORDS = ['条例', '办法', '规定', '实施细则', '通知', '通告', '意见', '决定', '命令', '管理制度', '规章', '管理办法', '管理规定', '暂行规定', '暂行办法'];
    const NON_NORMATIVE_HINTS = ['合同', '委托函', '中标通知书', '技术资料', '施工图', '设计图', '审批资料', '交底记录', '现场查勘', '查勘记录'];
    const CODE_PATTERN = /(?:(?:GB|GB\/T|GBJ|DL\/T|DL|NB\/T|NB|AQ|DB|DBJ|DGJ|JGJ|YD\/T|SL|GA|CECS|TSG|HG|CJJ|SH\/T|YB|JB|CJ|YS|SY|HJ|TB|LB|MZ|Q\/CSG|Q\/GDW|Q\/SH|Q\/BGJ)\s*[-/A-Z]*\s*\d{2,}(?:\.\d+)?(?:[-—]\d{2,4})?)/ig;
    const VERSION_YEAR_PATTERN = /[-—]\d{4}(?:\b|$)/;
    const normalizeText = (value) => String(value || '').replace(/\r\n/g, '\n').replace(/\u00a0/g, ' ').trim();
    const splitReferenceCandidates = (value) => {
      const text = normalizeText(value);
      if (!text) return [];
      if (text.trim().startsWith('|') || text.split('|').length >= 3) {
        return text
          .split('|')
          .map((cell) => normalizeText(cell))
          .filter(Boolean)
          .filter((cell) => !['序号', '名称', '名 称', '编号', '编 号', '标准号', '规范名称', '备注'].includes(cell))
          .filter((cell) => CODE_PATTERN.test(cell) || cell.includes('《'));
      }
      return text
        .replace(/^[（(]?\d+[)）.、]\s*/, '')
        .split(/[；;]/)
        .map((part) => part.trim().replace(/[。;；]+$/g, ''))
        .filter(Boolean);
    };
    const extractNormativeTitle = (value) => {
      let text = normalizeText(value);
      if (!text) return '';
      if (NON_NORMATIVE_HINTS.some((hint) => text.includes(hint))) return '';
      if (!text.includes('《') && !CODE_PATTERN.test(text)) return '';
      if (text.includes('《')) text = text.slice(text.indexOf('《'));
      text = text.replace(/^[（(]?\d+[)）.、]\s*/, '').replace(/\s+/g, ' ').trim();
      return NON_NORMATIVE_HINTS.some((hint) => text.includes(hint)) ? '' : text;
    };
    const isStandardNormative = (title) => {
      if (CODE_PATTERN.test(title)) return true;
      if (EXCLUDED_DOCUMENT_KEYWORDS.some((keyword) => title.includes(keyword))) return false;
      if (/[^办]法》/.test(title)) return false;
      return true;
    };
    const sectionIds = new Set((parseResult.sections || []).filter((section) => ['编制依据', '编制说明'].some((keyword) => String(section.title || '').includes(keyword))).map((section) => section.id));
    const candidatesRaw = (parseResult.blocks || [])
      .filter((block) => block.type !== 'heading')
      .filter((block) => block.sectionId && sectionIds.has(block.sectionId))
      .flatMap((block) => splitReferenceCandidates(block.text))
      .map(extractNormativeTitle)
      .filter(Boolean)
      .filter(isStandardNormative);
    const seen = new Set();
    const sources = candidatesRaw.filter((title) => {
      if (seen.has(title)) return false;
      seen.add(title);
      return true;
    });
    const checks = sources.map((title) => {
      const codeMatch = title.match(CODE_PATTERN);
      const precise = !!(codeMatch && VERSION_YEAR_PATTERN.test(codeMatch[0]));
      if (!precise) {
        return {
          sourceId: title,
          title,
          status: 'unknown',
          resolvedBy: 'heuristic',
          summary: '标准号缺少年份或分册锚点，不能直接判定为现行有效，需人工核验。',
          resolvedTitle: null,
          note: '裸标准号不得直接判定 current。'
        };
      }
      if (NEGATIVE_HINTS.some((token) => title.includes(token))) {
        return {
          sourceId: title,
          title,
          status: 'superseded',
          resolvedBy: 'heuristic',
          summary: '标题中包含废止或替代信号，需按最新版本复核。',
          resolvedTitle: title,
          note: '需结合权威来源进一步人工核验。'
        };
      }
      return {
        sourceId: title,
        title,
        status: 'current',
        resolvedBy: 'heuristic',
        summary: '已识别到带年份锚点的标准标题，但仍建议结合权威来源复核。',
        resolvedTitle: title,
        note: '已匹配到带年份版本锚点的标准标题。'
      };
    });
    const findings = [];
    if (checks.length) {
      findings.push({
        id: 'H-NORM-SUM-001',
        title: '编制依据现行有效性核验',
        severity: 'info',
        category: 'evidence_validation',
        summary: '共核验 ' + checks.length + ' 项编制依据，其中现行有效 ' + checks.filter((item) => item.status === 'current').length + ' 项，疑似废止/替代 ' + checks.filter((item) => item.status === 'superseded').length + ' 项，待人工核验 ' + checks.filter((item) => item.status === 'unknown').length + ' 项。',
        suggestion: '对状态不明或疑似替代的标准，请补做联网或人工复核。',
        evidence_status: 'inferred',
        source_engine: 'hermes',
        finding_type: 'normative_validity_summary',
        raw_data: { module_name: 'evidence_validation', normativeValidityChecks: checks }
      });
      checks.filter((item) => item.status !== 'current').forEach((check, index) => {
        findings.push({
          id: 'H-NORM-' + String(index + 1).padStart(3, '0'),
          title: '编制依据现行有效性存在疑点：' + check.title,
          severity: check.status === 'superseded' ? 'medium' : 'info',
          category: 'evidence_validation',
          summary: check.summary,
          suggestion: '如该编制依据已废止、被替代或状态不明，请改用现行版本并同步修正文内引用。',
          evidence_status: 'inferred',
          source_engine: 'hermes',
          finding_type: 'normative_validity_issue',
          raw_data: { module_name: 'evidence_validation', normativeValidityCheck: check }
        });
      });
    }
    pushPacket(makePacket(
      'normative_validity_reviewer',
      ['evidence_validation'],
      findings,
      checks.length ? '被审方案“编制依据”现行有效性核验已完成。' : '未识别到被审方案“编制依据”章节中可执行现行有效性核验的规范。'
    ));
  }

  if (modules.includes('evidence_validation')) {
    const aiPackets = Array.isArray(aiReview.reviewerPackets) ? aiReview.reviewerPackets : [];
    const calcPacket = aiPackets.find((packet) => packet && packet.metadata && packet.metadata.template_id === 'calculation_review_reviewer');
    if (!calcPacket || !Array.isArray(calcPacket.findings) || calcPacket.findings.length === 0) {
      pushPacket(makePacket(
        'calculation_review_reviewer',
        ['evidence_validation'],
        [{
          id: 'H-CALC-FALLBACK-001',
          title: '未见计算书或验算过程，需人工补充复核',
          severity: 'info',
          category: 'evidence_validation',
          summary: '当前材料未稳定识别出计算书或完整验算过程，禁止臆造计算错误。',
          suggestion: '请补充计算书、公式来源及关键参数验算过程后再复核。',
          evidence_status: 'evidence_gap',
          source_engine: 'hermes',
          finding_type: 'suggestion_enhancement',
          raw_data: { module_name: 'evidence_validation', fallback: true }
        }],
        '计算式与验算依据审查未获取到稳定证据，已按保守策略返回人工复核提示。'
      ));
    }
  }

  return {
    deterministicReview: {
      reviewerPackets
    },
    reviewerPackets
  };
}`;
}

function supportReviewCode() {
  return String.raw`function main(input) {
  const {
    reviewId = '',
    documentType = '',
    reviewContext = {}
  } = input || {};
  const inferModuleName = (value) => {
    const lower = String(value || '').toLowerCase();
    if (lower.includes('visibility') || lower.includes('evidence') || lower.includes('normative') || lower.includes('calculation')) return 'evidence_validation';
    if (lower.includes('structure') || lower.includes('完整')) return 'structure_completeness';
    if (lower.includes('consistency') || lower.includes('parameter') || lower.includes('resource')) return 'parameter_consistency';
    if (lower.includes('operation_chain') || lower.includes('execution') || lower.includes('ticket') || lower.includes('power_outage')) return 'execution_continuity';
    return 'legality_compliance';
  };
  const findings = (Array.isArray(reviewContext.candidates) ? reviewContext.candidates : []).map((candidate, index) => ({
    id: 'S-' + String(index + 1).padStart(3, '0'),
    title: candidate.title,
    severity: candidate.severityHint || 'medium',
    category: inferModuleName(candidate.candidateId),
    summary: ((candidate.ruleHits || []).map((hit) => hit.rationale).filter(Boolean).join('；')) || (candidate.title + ' 已命中受治理审查规则。'),
    suggestion: candidate.manualReviewNeeded ? '当前证据存在可视域缺口，请结合原件或附件人工复核。' : '请根据命中规则补齐正文、附件或规范依据。',
    evidence_status: candidate.manualReviewNeeded ? 'visibility_gap' : (candidate.evidenceMissing ? 'evidence_gap' : 'grounded'),
    source_engine: '008',
    finding_type: candidate.findingType || 'hard_evidence',
    manual_review_needed: !!candidate.manualReviewNeeded,
    raw_data: {
      candidateId: candidate.candidateId,
      module_name: inferModuleName(candidate.candidateId),
      blocking_reasons: candidate.blockingReasons || []
    }
  }));
  const reportMarkdown = [
    '# ' + documentType + ' — 008 支撑层结果',
    '',
    ...(findings.length ? findings.map((item) => '- [' + item.severity + '] ' + item.title + '：' + item.summary) : ['- 未识别到需输出的问题'])
  ].join('\n');
  const supportPacket008 = {
    review_id: reviewId,
    engine: '008',
    findings,
    overall_assessment: findings.length ? '008 支撑层已形成结构化问题线索。' : '008 支撑层未识别到需输出的问题。',
    metadata: {
      template_id: 'structured_review_primary_worker',
      agent_id: 'structured_review_primary_worker',
      review_modules: [...new Set(findings.map((item) => item.raw_data.module_name).filter(Boolean))]
    }
  };
  return {
    supportReview: {
      supportResult008: {
        summary: { issueCount: findings.length, documentType },
        issues: findings,
        reportMarkdown,
        ownership: 'support_material'
      },
      supportPacket008,
      artifactIndex: [],
      supportLayerContext: {
        reportMarkdown,
        issueCount: findings.length,
        resolvedBasisProfile: reviewContext.resolvedBasisProfile || {}
      }
    },
    supportPacket008
  };
}`;
}

function finalAssemblerCode() {
  return String.raw`function main(input) {
  const {
    reviewId = '',
    documentType = '',
    enabledModules = [],
    supportReview = {},
    aiReview = {},
    deterministicReview = {},
    docTypeLabels = {}
  } = input || {};

  const DEFAULT_MODULES = ['structure_completeness', 'parameter_consistency', 'legality_compliance', 'execution_continuity', 'evidence_validation'];
  const modules = Array.isArray(enabledModules) && enabledModules.length ? enabledModules : DEFAULT_MODULES;
  const reviewerPackets = [
    ...(Array.isArray(aiReview.reviewerPackets) ? aiReview.reviewerPackets : []),
    ...(Array.isArray(deterministicReview.reviewerPackets) ? deterministicReview.reviewerPackets : [])
  ];
  const docLabel = docTypeLabels[documentType] || documentType;
  const renderDegradedMarkdown = (reason) => [
    '# ' + docLabel + ' — 预检结果与支撑层数据（非正式审查报告）',
    '',
    '> 审查主控链路未能形成正式裁决，系统已按 fail-closed 返回降级结果。原因：' + reason,
    '',
    '本结果仅供人工复核，不构成正式审查结论。'
  ].join('\n');
  const severityScore = (severity) => ({ high: 3, medium: 2, low: 1, info: 0 })[severity] || 0;

  const hermesOk = reviewerPackets.some((packet) => !packet.degraded);
  if (!hermesOk) {
    const degradedReason = (reviewerPackets.find((packet) => packet.error) || {}).error || 'Hermes 主审 reviewer 未返回有效结果';
    return {
      finalDecision: {
        degraded: true,
        degradedReason,
        finalReportPacket: null,
        finalAnswer: renderDegradedMarkdown(degradedReason),
        traceability: [],
        hermesController: {
          enabled: true,
          finalReportReady: false,
          degraded: true,
          degradedReason
        }
      },
      finalAnswer: renderDegradedMarkdown(degradedReason),
      degraded: true,
      degradedReason,
      traceability: [],
      finalReportMarkdown: renderDegradedMarkdown(degradedReason),
      reportHtml: '<html lang="zh-CN"><body><pre>' + renderDegradedMarkdown(degradedReason) + '</pre></body></html>',
      reportPrintCss: 'body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }',
      finalReportViewModel: {
        title: docLabel + '降级结果',
        degraded: true,
        verdict: null,
        executiveSummary: '主审链路不可用，已按 fail-closed 返回降级结果：' + degradedReason,
        topRisks: [],
        keyFindings: [],
        supplementalFindings: [],
        traceabilityCount: 0
      }
    };
  }

  const blockedModules = modules.filter((moduleName) => {
    const packets = reviewerPackets.filter((packet) => Array.isArray(packet.metadata && packet.metadata.review_modules) ? packet.metadata.review_modules.includes(moduleName) : false);
    return packets.length === 0 || packets.every((packet) => packet.degraded);
  });
  if (blockedModules.length) {
    const degradedReason = '以下模块未形成有效主审结论：' + blockedModules.join('、');
    return {
      finalDecision: {
        degraded: true,
        degradedReason,
        finalReportPacket: null,
        finalAnswer: renderDegradedMarkdown(degradedReason),
        traceability: [],
        hermesController: {
          enabled: true,
          finalReportReady: false,
          degraded: true,
          degradedReason,
          blockedModules
        }
      },
      finalAnswer: renderDegradedMarkdown(degradedReason),
      degraded: true,
      degradedReason,
      traceability: [],
      finalReportMarkdown: renderDegradedMarkdown(degradedReason),
      reportHtml: '<html lang="zh-CN"><body><pre>' + renderDegradedMarkdown(degradedReason) + '</pre></body></html>',
      reportPrintCss: 'body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }',
      finalReportViewModel: {
        title: docLabel + '降级结果',
        degraded: true,
        verdict: null,
        executiveSummary: '主审链路不可用，已按 fail-closed 返回降级结果：' + degradedReason,
        topRisks: [],
        keyFindings: [],
        supplementalFindings: [],
        traceabilityCount: 0
      }
    };
  }

  const supportFindings = ((supportReview.supportPacket008 || {}).findings) || [];
  const hermesFindings = reviewerPackets.flatMap((packet) => Array.isArray(packet.findings) ? packet.findings : []);
  const supportTitles = new Set(supportFindings.map((item) => item.title));
  const supplementalFindings = hermesFindings.filter((item) => !supportTitles.has(item.title));
  const allFindings = [...supportFindings, ...supplementalFindings];
  const verdict = allFindings.some((item) => item.severity === 'high')
    ? 'fail'
    : allFindings.some((item) => item.severity === 'medium' || item.evidence_status === 'evidence_gap' || item.manual_review_needed)
      ? 'needs_revision'
      : 'conditional_pass';

  const verdictLabelMap = {
    conditional_pass: '有条件通过',
    needs_revision: '需要修改',
    fail: '不通过'
  };
  const topRisks = allFindings
    .slice()
    .sort((left, right) => severityScore(right.severity) - severityScore(left.severity))
    .map((item) => item.title)
    .filter(Boolean)
    .slice(0, 5);
  const traceability = allFindings.map((finding) => ({
    finding_id: finding.id,
    title: finding.title,
    source_engine: finding.source_engine || 'unknown',
    module_name: finding.raw_data && finding.raw_data.module_name || null,
    template_id: finding.raw_data && finding.raw_data.template_id || null
  }));
  const finalReportPacket = {
    title: docLabel + '正式审查报告',
    verdict,
    summary: '本次审查已由专业主审组件裁决完成，总体评级结论为：**' + verdictLabelMap[verdict] + '**。',
    top_risks: topRisks,
    key_findings: supportFindings,
    supplemental_findings: supplementalFindings,
    traceability,
    report_markdown: '',
    metadata: {
      documentType,
      selected_review_modules: modules
    }
  };
  finalReportPacket.report_markdown = [
    '# ' + finalReportPacket.title,
    '',
    finalReportPacket.summary,
    '',
    '## 重点风险',
    ...(topRisks.length ? topRisks.map((item) => '- ' + item) : ['- 未识别到需要单列的高风险事项']),
    '',
    '## 关键问题',
    ...(supportFindings.length ? supportFindings.map((item) => '- [' + item.severity + '] ' + item.title + '：' + item.summary) : ['- 无']),
    '',
    '## 补充问题',
    ...(supplementalFindings.length ? supplementalFindings.map((item) => '- [' + item.severity + '] ' + item.title + '：' + item.summary) : ['- 无'])
  ].join('\n');

  const markdown = finalReportPacket.report_markdown;
  const reportHtml = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" /><title>' + finalReportPacket.title + '</title><style>body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px; color: #0f172a; } h1 { font-size: 28px; margin-bottom: 16px; } h2 { font-size: 18px; margin-top: 24px; border-left: 4px solid #2563eb; padding-left: 8px; } li { margin: 8px 0; } </style></head><body>' + markdown.split('\n').map((line) => {
    if (line.startsWith('# ')) return '<h1>' + line.slice(2) + '</h1>';
    if (line.startsWith('## ')) return '<h2>' + line.slice(3) + '</h2>';
    if (line.startsWith('- ')) return '<li>' + line.slice(2) + '</li>';
    if (!line.trim()) return '';
    return '<p>' + line + '</p>';
  }).join('\n') + '</body></html>';
  const reportPrintCss = 'body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; color: #0f172a; }\nh1, h2 { break-after: avoid; }\nul, ol { padding-left: 20px; }\n';
  const finalDecision = {
    degraded: false,
    degradedReason: '',
    finalReportPacket,
    finalAnswer: markdown,
    traceability,
    hermesController: {
      enabled: true,
      finalReportReady: true,
      degraded: false
    }
  };
  return {
    finalDecision,
    finalAnswer: markdown,
    degraded: false,
    degradedReason: '',
    traceability,
    finalReportMarkdown: markdown,
    reportHtml,
    reportPrintCss,
    finalReportViewModel: {
      title: finalReportPacket.title,
      degraded: false,
      verdict,
      executiveSummary: finalReportPacket.summary,
      topRisks,
      keyFindings: supportFindings,
      supplementalFindings,
      traceabilityCount: traceability.length
    }
  };
}`;
}

function buildReviewContextTool(assets) {
  const snapshot = {
    profileMapping: assets.profileMapping,
    packRegistry: assets.packRegistry,
    rulePackRegistry: assets.rulePackRegistry,
    basisRegistry: assets.basisRegistry,
    evidenceTitles: assets.evidenceTitles,
    evidenceFindingTypes: assets.evidenceFindingTypes,
    evidenceManualReviewReasons: assets.evidenceManualReviewReasons,
    datasetManifest: assets.datasetManifest
  };
  const nodes = [
    pluginConfigNode(-280, -220),
    pluginInputNode(
      [
        inputField({ key: 'query', label: '审查指令', valueType: 'string', required: true, toolDescription: '审查目标与重点要求' }),
        inputField({ key: 'documentType', label: '文档类型', valueType: 'string', required: true, toolDescription: '被审文档类型枚举值' }),
        inputField({ key: 'disciplineTags', label: '专业标签', valueType: 'arrayString', toolDescription: '审查专业标签数组' }),
        inputField({ key: 'enabledModules', label: '启用模块', valueType: 'arrayString', toolDescription: '启用的正式审查模块' }),
        inputField({ key: 'disabledModules', label: '禁用模块', valueType: 'arrayString', toolDescription: '显式禁用的审查模块' }),
        inputField({ key: 'focusRequirements', label: '重点要求', valueType: 'arrayString', toolDescription: '用户指定的重点问题或 pack/rule_pack 提示' }),
        inputField({ key: 'strictMode', label: '严格模式', valueType: 'boolean', toolDescription: '是否按严格模式执行' }),
        inputField({ key: 'targetFileUrls', label: '目标文件 URL', valueType: 'arrayString', required: true, toolDescription: '被审文件链接数组' }),
        inputField({ key: 'basisFileUrls', label: 'basis 文件 URL', valueType: 'arrayString', toolDescription: '额外 basis 文件链接数组' }),
        inputField({ key: 'contextFileUrls', label: '上下文文件 URL', valueType: 'arrayString', toolDescription: '额外上下文文件链接数组' })
      ],
      0,
      0
    ),
    readFilesNode({ nodeId: 'readTargetFiles', name: '读取目标文件', x: 360, y: -160, fileUrlRef: ref('pluginInput', 'targetFileUrls') }),
    readFilesNode({ nodeId: 'readBasisFiles', name: '读取 basis 文件', x: 360, y: 20, fileUrlRef: ref('pluginInput', 'basisFileUrls') }),
    readFilesNode({ nodeId: 'readContextFiles', name: '读取上下文文件', x: 360, y: 200, fileUrlRef: ref('pluginInput', 'contextFileUrls') }),
    codeNode({
      nodeId: 'buildReviewContext',
      name: '构建审查上下文',
      intro: '解析文件正文、facts、profile、basis 与 governed context',
      x: 780,
      y: 0,
      inputs: [
        inputField({ key: 'query', label: 'query', valueType: 'string', value: ref('pluginInput', 'query'), renderTypeList: ['reference'] }),
        inputField({ key: 'documentType', label: 'documentType', valueType: 'string', value: ref('pluginInput', 'documentType'), renderTypeList: ['reference'] }),
        inputField({ key: 'disciplineTags', label: 'disciplineTags', valueType: 'arrayString', value: ref('pluginInput', 'disciplineTags'), renderTypeList: ['reference'] }),
        inputField({ key: 'enabledModules', label: 'enabledModules', valueType: 'arrayString', value: ref('pluginInput', 'enabledModules'), renderTypeList: ['reference'] }),
        inputField({ key: 'disabledModules', label: 'disabledModules', valueType: 'arrayString', value: ref('pluginInput', 'disabledModules'), renderTypeList: ['reference'] }),
        inputField({ key: 'focusRequirements', label: 'focusRequirements', valueType: 'arrayString', value: ref('pluginInput', 'focusRequirements'), renderTypeList: ['reference'] }),
        inputField({ key: 'strictMode', label: 'strictMode', valueType: 'boolean', value: ref('pluginInput', 'strictMode'), renderTypeList: ['reference'] }),
        inputField({ key: 'targetFilesText', label: 'targetFilesText', valueType: 'string', value: ref('readTargetFiles', 'text'), renderTypeList: ['reference'] }),
        inputField({ key: 'targetFilesRaw', label: 'targetFilesRaw', valueType: 'arrayObject', value: ref('readTargetFiles', 'system_rawResponse'), renderTypeList: ['reference'] }),
        inputField({ key: 'basisFilesRaw', label: 'basisFilesRaw', valueType: 'arrayObject', value: ref('readBasisFiles', 'system_rawResponse'), renderTypeList: ['reference'] }),
        inputField({ key: 'contextFilesRaw', label: 'contextFilesRaw', valueType: 'arrayObject', value: ref('readContextFiles', 'system_rawResponse'), renderTypeList: ['reference'] }),
        inputField({ key: 'snapshot', label: 'snapshot', valueType: 'object', renderTypeList: ['hidden'], value: snapshot })
      ],
      outputs: [
        dynamicOutput('reviewContext', '审查上下文', 'object'),
        dynamicOutput('parseResult', '解析结果', 'object'),
        dynamicOutput('docTextPreview', '文档预览', 'string'),
        dynamicOutput('resolvedProfile', 'resolvedProfile', 'object'),
        dynamicOutput('resolvedBasisProfile', 'resolvedBasisProfile', 'object'),
        dynamicOutput('governedDatasetScope', 'governedDatasetScope', 'object'),
        dynamicOutput('supportPacketBase', 'supportPacketBase', 'object')
      ],
      code: reviewContextCode()
    }),
    pluginOutputNode(
      [
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', renderTypeList: ['reference'], value: ref('buildReviewContext', 'reviewContext') }),
        inputField({ key: 'parseResult', label: 'parseResult', valueType: 'object', renderTypeList: ['reference'], value: ref('buildReviewContext', 'parseResult') }),
        inputField({ key: 'docTextPreview', label: 'docTextPreview', valueType: 'string', renderTypeList: ['reference'], value: ref('buildReviewContext', 'docTextPreview') }),
        inputField({ key: 'resolvedProfile', label: 'resolvedProfile', valueType: 'object', renderTypeList: ['reference'], value: ref('buildReviewContext', 'resolvedProfile') }),
        inputField({ key: 'resolvedBasisProfile', label: 'resolvedBasisProfile', valueType: 'object', renderTypeList: ['reference'], value: ref('buildReviewContext', 'resolvedBasisProfile') }),
        inputField({ key: 'governedDatasetScope', label: 'governedDatasetScope', valueType: 'object', renderTypeList: ['reference'], value: ref('buildReviewContext', 'governedDatasetScope') }),
        inputField({ key: 'supportPacketBase', label: 'supportPacketBase', valueType: 'object', renderTypeList: ['reference'], value: ref('buildReviewContext', 'supportPacketBase') })
      ],
      1220,
      0
    )
  ];
  const edges = [
    { source: 'pluginInput', target: 'readTargetFiles' },
    { source: 'pluginInput', target: 'readBasisFiles' },
    { source: 'pluginInput', target: 'readContextFiles' },
    { source: 'readTargetFiles', target: 'buildReviewContext' },
    { source: 'readBasisFiles', target: 'buildReviewContext' },
    { source: 'readContextFiles', target: 'buildReviewContext' },
    { source: 'buildReviewContext', target: 'pluginOutput' }
  ];
  return { nodes, edges, chatConfig: {} };
}

function buildAiReviewTool(assets) {
  const snapshot = {
    moduleBindings: assets.moduleBindings,
    templateManifest: assets.templateManifest,
    templateModuleMap: assets.templateModuleMap
  };
  const nodes = [
    pluginConfigNode(-220, -220),
    pluginInputNode(
      [
        inputField({ key: 'reviewId', label: '审查ID', valueType: 'string', required: true, toolDescription: '本次审查任务 ID' }),
        inputField({ key: 'query', label: '审查指令', valueType: 'string', required: true, toolDescription: '用户审查指令' }),
        inputField({ key: 'documentType', label: '文档类型', valueType: 'string', required: true, toolDescription: '被审文档类型枚举值' }),
        inputField({ key: 'enabledModules', label: '启用模块', valueType: 'arrayString', toolDescription: '启用的正式审查模块' }),
        inputField({ key: 'focusRequirements', label: '重点要求', valueType: 'arrayString', toolDescription: '用户指定重点问题' }),
        inputField({ key: 'strictMode', label: '严格模式', valueType: 'boolean', toolDescription: '是否按严格模式执行' }),
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', required: true, toolDescription: '由 hermes_review_context_wft 生成的 governed review context' }),
        inputField({ key: 'targetFileUrls', label: '目标文件 URL', valueType: 'arrayString', toolDescription: '被审文件链接数组' }),
        inputField({ key: 'aiModel', label: 'AI 模型', valueType: 'string', toolDescription: 'AI reviewer 使用的模型名称' })
      ],
      0,
      0
    ),
    codeNode({
      nodeId: 'selectAiReviewers',
      name: '选择 AI reviewer',
      intro: '按模块绑定、文档类型门禁与模板清单选择 reviewer',
      x: 360,
      y: 0,
      inputs: [
        inputField({ key: 'reviewId', label: 'reviewId', valueType: 'string', value: ref('pluginInput', 'reviewId'), renderTypeList: ['reference'] }),
        inputField({ key: 'query', label: 'query', valueType: 'string', value: ref('pluginInput', 'query'), renderTypeList: ['reference'] }),
        inputField({ key: 'documentType', label: 'documentType', valueType: 'string', value: ref('pluginInput', 'documentType'), renderTypeList: ['reference'] }),
        inputField({ key: 'enabledModules', label: 'enabledModules', valueType: 'arrayString', value: ref('pluginInput', 'enabledModules'), renderTypeList: ['reference'] }),
        inputField({ key: 'focusRequirements', label: 'focusRequirements', valueType: 'arrayString', value: ref('pluginInput', 'focusRequirements'), renderTypeList: ['reference'] }),
        inputField({ key: 'strictMode', label: 'strictMode', valueType: 'boolean', value: ref('pluginInput', 'strictMode'), renderTypeList: ['reference'] }),
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', value: ref('pluginInput', 'reviewContext'), renderTypeList: ['reference'] }),
        inputField({ key: 'targetFileUrls', label: 'targetFileUrls', valueType: 'arrayString', value: ref('pluginInput', 'targetFileUrls'), renderTypeList: ['reference'] }),
        inputField({ key: 'aiModel', label: 'aiModel', valueType: 'string', value: ref('pluginInput', 'aiModel'), renderTypeList: ['reference'] }),
        inputField({ key: 'snapshot', label: 'snapshot', valueType: 'object', renderTypeList: ['hidden'], value: snapshot })
      ],
      outputs: [
        dynamicOutput('selectedReviewers', 'selectedReviewers', 'arrayObject'),
        dynamicOutput('aiSystemPrompt', 'aiSystemPrompt', 'string'),
        dynamicOutput('aiUserPrompt', 'aiUserPrompt', 'string'),
        dynamicOutput('targetFileUrls', 'targetFileUrls', 'arrayString'),
        dynamicOutput('aiModel', 'aiModel', 'string'),
        dynamicOutput('hasAiReviewers', 'hasAiReviewers', 'boolean')
      ],
      code: aiReviewPlannerCode()
    }),
    chatNode({
      nodeId: 'runAiReview',
      name: '执行 AI 主审',
      intro: '执行 Hermes AI reviewer 汇总审查',
      x: 800,
      y: 0,
      modelValue: ref('selectAiReviewers', 'aiModel'),
      systemPromptRef: ref('selectAiReviewers', 'aiSystemPrompt'),
      userPromptRef: ref('selectAiReviewers', 'aiUserPrompt'),
      fileUrlRef: ref('selectAiReviewers', 'targetFileUrls')
    }),
    codeNode({
      nodeId: 'normalizeAiReview',
      name: '归一化 AI reviewer 输出',
      intro: '解析 JSON、补齐缺失 reviewer、生成 reviewer packets',
      x: 1240,
      y: 0,
      inputs: [
        inputField({ key: 'reviewId', label: 'reviewId', valueType: 'string', value: ref('pluginInput', 'reviewId'), renderTypeList: ['reference'] }),
        inputField({ key: 'aiAnswer', label: 'aiAnswer', valueType: 'string', value: ref('runAiReview', 'text'), renderTypeList: ['reference'] }),
        inputField({ key: 'selectedReviewers', label: 'selectedReviewers', valueType: 'arrayObject', value: ref('selectAiReviewers', 'selectedReviewers'), renderTypeList: ['reference'] }),
        inputField({ key: 'fallbackModuleMap', label: 'fallbackModuleMap', valueType: 'object', renderTypeList: ['hidden'], value: assets.templateModuleMap })
      ],
      outputs: [
        dynamicOutput('aiReview', 'aiReview', 'object'),
        dynamicOutput('reviewerPackets', 'reviewerPackets', 'arrayObject')
      ],
      code: aiReviewNormalizeCode()
    }),
    pluginOutputNode(
      [
        inputField({ key: 'aiReview', label: 'aiReview', valueType: 'object', renderTypeList: ['reference'], value: ref('normalizeAiReview', 'aiReview') }),
        inputField({ key: 'reviewerPackets', label: 'reviewerPackets', valueType: 'arrayObject', renderTypeList: ['reference'], value: ref('normalizeAiReview', 'reviewerPackets') })
      ],
      1660,
      0
    )
  ];
  const edges = [
    { source: 'pluginInput', target: 'selectAiReviewers' },
    { source: 'selectAiReviewers', target: 'runAiReview' },
    { source: 'runAiReview', target: 'normalizeAiReview' },
    { source: 'normalizeAiReview', target: 'pluginOutput' }
  ];
  return { nodes, edges, chatConfig: {} };
}

function buildDeterministicTool() {
  const nodes = [
    pluginConfigNode(-220, -220),
    pluginInputNode(
      [
        inputField({ key: 'reviewId', label: '审查ID', valueType: 'string', required: true, toolDescription: '本次审查任务 ID' }),
        inputField({ key: 'enabledModules', label: '启用模块', valueType: 'arrayString', toolDescription: '启用的正式审查模块' }),
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', required: true, toolDescription: '由 hermes_review_context_wft 生成的 governed review context' }),
        inputField({ key: 'aiReview', label: 'aiReview', valueType: 'object', toolDescription: '由 hermes_ai_review_wft 生成的 AI reviewer packets' })
      ],
      0,
      0
    ),
    codeNode({
      nodeId: 'runDeterministicReview',
      name: '执行确定性审查',
      intro: '执行可视域、合规、规范有效性与计算 fallback 审查',
      x: 420,
      y: 0,
      inputs: [
        inputField({ key: 'reviewId', label: 'reviewId', valueType: 'string', value: ref('pluginInput', 'reviewId'), renderTypeList: ['reference'] }),
        inputField({ key: 'enabledModules', label: 'enabledModules', valueType: 'arrayString', value: ref('pluginInput', 'enabledModules'), renderTypeList: ['reference'] }),
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', value: ref('pluginInput', 'reviewContext'), renderTypeList: ['reference'] }),
        inputField({ key: 'aiReview', label: 'aiReview', valueType: 'object', value: ref('pluginInput', 'aiReview'), renderTypeList: ['reference'] })
      ],
      outputs: [
        dynamicOutput('deterministicReview', 'deterministicReview', 'object'),
        dynamicOutput('reviewerPackets', 'reviewerPackets', 'arrayObject')
      ],
      code: deterministicReviewCode()
    }),
    pluginOutputNode(
      [
        inputField({ key: 'deterministicReview', label: 'deterministicReview', valueType: 'object', renderTypeList: ['reference'], value: ref('runDeterministicReview', 'deterministicReview') }),
        inputField({ key: 'reviewerPackets', label: 'reviewerPackets', valueType: 'arrayObject', renderTypeList: ['reference'], value: ref('runDeterministicReview', 'reviewerPackets') })
      ],
      860,
      0
    )
  ];
  const edges = [
    { source: 'pluginInput', target: 'runDeterministicReview' },
    { source: 'runDeterministicReview', target: 'pluginOutput' }
  ];
  return { nodes, edges, chatConfig: {} };
}

function buildSupportTool() {
  const nodes = [
    pluginConfigNode(-220, -220),
    pluginInputNode(
      [
        inputField({ key: 'reviewId', label: '审查ID', valueType: 'string', required: true, toolDescription: '本次审查任务 ID' }),
        inputField({ key: 'documentType', label: '文档类型', valueType: 'string', required: true, toolDescription: '被审文档类型枚举值' }),
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', required: true, toolDescription: '由 hermes_review_context_wft 生成的 governed review context' })
      ],
      0,
      0
    ),
    codeNode({
      nodeId: 'buildSupport008',
      name: '生成 008 支撑层结果',
      intro: '生成 supportResult008 / supportPacket008 / supportLayerContext',
      x: 420,
      y: 0,
      inputs: [
        inputField({ key: 'reviewId', label: 'reviewId', valueType: 'string', value: ref('pluginInput', 'reviewId'), renderTypeList: ['reference'] }),
        inputField({ key: 'documentType', label: 'documentType', valueType: 'string', value: ref('pluginInput', 'documentType'), renderTypeList: ['reference'] }),
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', value: ref('pluginInput', 'reviewContext'), renderTypeList: ['reference'] })
      ],
      outputs: [
        dynamicOutput('supportReview', 'supportReview', 'object'),
        dynamicOutput('supportPacket008', 'supportPacket008', 'object')
      ],
      code: supportReviewCode()
    }),
    pluginOutputNode(
      [
        inputField({ key: 'supportReview', label: 'supportReview', valueType: 'object', renderTypeList: ['reference'], value: ref('buildSupport008', 'supportReview') }),
        inputField({ key: 'supportPacket008', label: 'supportPacket008', valueType: 'object', renderTypeList: ['reference'], value: ref('buildSupport008', 'supportPacket008') })
      ],
      860,
      0
    )
  ];
  const edges = [
    { source: 'pluginInput', target: 'buildSupport008' },
    { source: 'buildSupport008', target: 'pluginOutput' }
  ];
  return { nodes, edges, chatConfig: {} };
}

function buildFinalAssemblerTool(assets) {
  const nodes = [
    pluginConfigNode(-220, -220),
    pluginInputNode(
      [
        inputField({ key: 'reviewId', label: '审查ID', valueType: 'string', required: true, toolDescription: '本次审查任务 ID' }),
        inputField({ key: 'documentType', label: '文档类型', valueType: 'string', required: true, toolDescription: '被审文档类型枚举值' }),
        inputField({ key: 'enabledModules', label: '启用模块', valueType: 'arrayString', toolDescription: '启用的正式审查模块' }),
        inputField({ key: 'supportReview', label: 'supportReview', valueType: 'object', required: true, toolDescription: '由 hermes_support_008_wft 生成的支撑层结果' }),
        inputField({ key: 'aiReview', label: 'aiReview', valueType: 'object', toolDescription: '由 hermes_ai_review_wft 生成的 AI reviewer packets' }),
        inputField({ key: 'deterministicReview', label: 'deterministicReview', valueType: 'object', toolDescription: '由 hermes_deterministic_review_wft 生成的确定性 reviewer packets' })
      ],
      0,
      0
    ),
    codeNode({
      nodeId: 'assembleFinalDecision',
      name: '组装最终裁决',
      intro: '执行 fail-closed、模块门禁、最终报告与降级出口组装',
      x: 480,
      y: 0,
      inputs: [
        inputField({ key: 'reviewId', label: 'reviewId', valueType: 'string', value: ref('pluginInput', 'reviewId'), renderTypeList: ['reference'] }),
        inputField({ key: 'documentType', label: 'documentType', valueType: 'string', value: ref('pluginInput', 'documentType'), renderTypeList: ['reference'] }),
        inputField({ key: 'enabledModules', label: 'enabledModules', valueType: 'arrayString', value: ref('pluginInput', 'enabledModules'), renderTypeList: ['reference'] }),
        inputField({ key: 'supportReview', label: 'supportReview', valueType: 'object', value: ref('pluginInput', 'supportReview'), renderTypeList: ['reference'] }),
        inputField({ key: 'aiReview', label: 'aiReview', valueType: 'object', value: ref('pluginInput', 'aiReview'), renderTypeList: ['reference'] }),
        inputField({ key: 'deterministicReview', label: 'deterministicReview', valueType: 'object', value: ref('pluginInput', 'deterministicReview'), renderTypeList: ['reference'] }),
        inputField({ key: 'docTypeLabels', label: 'docTypeLabels', valueType: 'object', renderTypeList: ['hidden'], value: assets.docTypeLabels })
      ],
      outputs: [
        dynamicOutput('finalDecision', 'finalDecision', 'object'),
        dynamicOutput('finalAnswer', 'finalAnswer', 'string'),
        dynamicOutput('degraded', 'degraded', 'boolean'),
        dynamicOutput('degradedReason', 'degradedReason', 'string'),
        dynamicOutput('traceability', 'traceability', 'arrayObject'),
        dynamicOutput('finalReportMarkdown', 'finalReportMarkdown', 'string'),
        dynamicOutput('reportHtml', 'reportHtml', 'string'),
        dynamicOutput('reportPrintCss', 'reportPrintCss', 'string'),
        dynamicOutput('finalReportViewModel', 'finalReportViewModel', 'object')
      ],
      code: finalAssemblerCode()
    }),
    pluginOutputNode(
      [
        inputField({ key: 'finalDecision', label: 'finalDecision', valueType: 'object', renderTypeList: ['reference'], value: ref('assembleFinalDecision', 'finalDecision') }),
        inputField({ key: 'finalAnswer', label: 'finalAnswer', valueType: 'string', renderTypeList: ['reference'], value: ref('assembleFinalDecision', 'finalAnswer') }),
        inputField({ key: 'degraded', label: 'degraded', valueType: 'boolean', renderTypeList: ['reference'], value: ref('assembleFinalDecision', 'degraded') }),
        inputField({ key: 'degradedReason', label: 'degradedReason', valueType: 'string', renderTypeList: ['reference'], value: ref('assembleFinalDecision', 'degradedReason') }),
        inputField({ key: 'traceability', label: 'traceability', valueType: 'arrayObject', renderTypeList: ['reference'], value: ref('assembleFinalDecision', 'traceability') }),
        inputField({ key: 'finalReportMarkdown', label: 'finalReportMarkdown', valueType: 'string', renderTypeList: ['reference'], value: ref('assembleFinalDecision', 'finalReportMarkdown') }),
        inputField({ key: 'reportHtml', label: 'reportHtml', valueType: 'string', renderTypeList: ['reference'], value: ref('assembleFinalDecision', 'reportHtml') }),
        inputField({ key: 'reportPrintCss', label: 'reportPrintCss', valueType: 'string', renderTypeList: ['reference'], value: ref('assembleFinalDecision', 'reportPrintCss') }),
        inputField({ key: 'finalReportViewModel', label: 'finalReportViewModel', valueType: 'object', renderTypeList: ['reference'], value: ref('assembleFinalDecision', 'finalReportViewModel') })
      ],
      980,
      0
    )
  ];
  const edges = [
    { source: 'pluginInput', target: 'assembleFinalDecision' },
    { source: 'assembleFinalDecision', target: 'pluginOutput' }
  ];
  return { nodes, edges, chatConfig: {} };
}

export function buildWorkflowToolBundles(assets) {
  const workflows = {
    hermes_review_context_wft: buildReviewContextTool(assets),
    hermes_ai_review_wft: buildAiReviewTool(assets),
    hermes_deterministic_review_wft: buildDeterministicTool(assets),
    hermes_support_008_wft: buildSupportTool(assets),
    hermes_final_assembler_wft: buildFinalAssemblerTool(assets)
  };

  return WORKFLOW_TOOL_SPECS.map((spec) => {
    const workflow = workflows[spec.key];
    return {
      key: spec.key,
      workflow,
      templateJson: {
        name: spec.name,
        intro: spec.intro,
        author: 'OpenAI Codex',
        avatar: spec.avatar,
        tags: spec.tags,
        type: 'plugin',
        workflow
      },
      createJson: {
        name: spec.name,
        avatar: spec.avatar,
        intro: spec.intro,
        type: 'plugin',
        modules: workflow.nodes,
        edges: workflow.edges,
        chatConfig: workflow.chatConfig
      }
    };
  });
}

export function buildMainWorkflow(assets) {
  const variables = [
    { key: 'documentType', label: 'documentType', type: 'input', required: true },
    { key: 'disciplineTags', label: 'disciplineTags', type: 'textarea', required: false },
    { key: 'enabledModules', label: 'enabledModules', type: 'textarea', required: false },
    { key: 'disabledModules', label: 'disabledModules', type: 'textarea', required: false },
    { key: 'focusRequirements', label: 'focusRequirements', type: 'textarea', required: false },
    { key: 'strictMode', label: 'strictMode', type: 'switch', required: false },
    { key: 'basisFileUrls', label: 'basisFileUrls', type: 'textarea', required: false },
    { key: 'contextFileUrls', label: 'contextFileUrls', type: 'textarea', required: false }
  ];

  const normalizeCode = String.raw`function main(input) {
  const {
    userChatInput = '',
    userFiles = [],
    documentType = '',
    disciplineTags = [],
    enabledModules = [],
    disabledModules = [],
    focusRequirements = [],
    strictMode = true
  } = input || {};
  const DEFAULT_MODULES = ['structure_completeness', 'parameter_consistency', 'legality_compliance', 'execution_continuity', 'evidence_validation'];
  const toArray = (value) => {
    if (Array.isArray(value)) return value;
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (!trimmed) return [];
      try {
        const parsed = JSON.parse(trimmed);
        return Array.isArray(parsed) ? parsed : trimmed.split(/[,\n]/).map((item) => item.trim()).filter(Boolean);
      } catch {
        return trimmed.split(/[,\n]/).map((item) => item.trim()).filter(Boolean);
      }
    }
    return [];
  };
  const disabled = new Set(toArray(disabledModules));
  const enabled = toArray(enabledModules).length ? toArray(enabledModules) : DEFAULT_MODULES;
  return {
    reviewId: 'fgpt-' + Date.now(),
    query: String(userChatInput || '').trim() || '请执行结构化正式审查',
    documentType,
    disciplineTags: toArray(disciplineTags),
    enabledModules: [...new Set(enabled.filter((item) => !disabled.has(item)))],
    disabledModules: [...disabled],
    focusRequirements: toArray(focusRequirements),
    strictMode: strictMode !== false && strictMode !== 'false',
    targetFileUrls: Array.isArray(userFiles) ? userFiles : [],
    basisFileUrls: [],
    contextFileUrls: []
  };
}`;

  const nodes = [
    systemConfigNode(-260, -220),
    workflowStartNode(0, 0),
    codeNode({
      nodeId: 'normalizeInput',
      name: '归一化输入',
      intro: '归一化变量、生成 reviewId，并显式透传 target 文件链接',
      x: 360,
      y: 0,
      inputs: [
        inputField({ key: 'userChatInput', label: 'userChatInput', valueType: 'string', value: ref('workflowStart', 'userChatInput'), renderTypeList: ['reference'] }),
        inputField({ key: 'userFiles', label: 'userFiles', valueType: 'arrayString', value: ref('workflowStart', 'userFiles'), renderTypeList: ['reference'] }),
        inputField({ key: 'documentType', label: 'documentType', valueType: 'string', renderTypeList: ['reference'], value: '__VAR__documentType' }),
        inputField({ key: 'disciplineTags', label: 'disciplineTags', valueType: 'any', renderTypeList: ['reference'], value: '__VAR__disciplineTags' }),
        inputField({ key: 'enabledModules', label: 'enabledModules', valueType: 'any', renderTypeList: ['reference'], value: '__VAR__enabledModules' }),
        inputField({ key: 'disabledModules', label: 'disabledModules', valueType: 'any', renderTypeList: ['reference'], value: '__VAR__disabledModules' }),
        inputField({ key: 'focusRequirements', label: 'focusRequirements', valueType: 'any', renderTypeList: ['reference'], value: '__VAR__focusRequirements' }),
        inputField({ key: 'strictMode', label: 'strictMode', valueType: 'any', renderTypeList: ['reference'], value: '__VAR__strictMode' })
      ],
      outputs: [
        dynamicOutput('reviewId', 'reviewId', 'string'),
        dynamicOutput('query', 'query', 'string'),
        dynamicOutput('documentType', 'documentType', 'string'),
        dynamicOutput('disciplineTags', 'disciplineTags', 'arrayString'),
        dynamicOutput('enabledModules', 'enabledModules', 'arrayString'),
        dynamicOutput('disabledModules', 'disabledModules', 'arrayString'),
        dynamicOutput('focusRequirements', 'focusRequirements', 'arrayString'),
        dynamicOutput('strictMode', 'strictMode', 'boolean'),
        dynamicOutput('targetFileUrls', 'targetFileUrls', 'arrayString'),
        dynamicOutput('basisFileUrls', 'basisFileUrls', 'arrayString'),
        dynamicOutput('contextFileUrls', 'contextFileUrls', 'arrayString')
      ],
      code: normalizeCode
    }),
    pluginModuleNode({
      nodeId: 'reviewContextTool',
      name: '调用 hermes_review_context_wft',
      intro: '构建 governed review context',
      key: 'hermes_review_context_wft',
      x: 820,
      y: 0,
      inputs: [
        inputField({ key: 'query', label: 'query', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'query') }),
        inputField({ key: 'documentType', label: 'documentType', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'documentType') }),
        inputField({ key: 'disciplineTags', label: 'disciplineTags', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'disciplineTags') }),
        inputField({ key: 'enabledModules', label: 'enabledModules', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'enabledModules') }),
        inputField({ key: 'disabledModules', label: 'disabledModules', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'disabledModules') }),
        inputField({ key: 'focusRequirements', label: 'focusRequirements', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'focusRequirements') }),
        inputField({ key: 'strictMode', label: 'strictMode', valueType: 'boolean', renderTypeList: ['reference'], value: ref('normalizeInput', 'strictMode') }),
        inputField({ key: 'targetFileUrls', label: 'targetFileUrls', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'targetFileUrls') }),
        inputField({ key: 'basisFileUrls', label: 'basisFileUrls', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'basisFileUrls') }),
        inputField({ key: 'contextFileUrls', label: 'contextFileUrls', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'contextFileUrls') })
      ],
      outputs: [
        staticOutput('reviewContext', 'reviewContext', 'object'),
        staticOutput('parseResult', 'parseResult', 'object'),
        staticOutput('docTextPreview', 'docTextPreview', 'string'),
        staticOutput('resolvedProfile', 'resolvedProfile', 'object'),
        staticOutput('resolvedBasisProfile', 'resolvedBasisProfile', 'object'),
        staticOutput('governedDatasetScope', 'governedDatasetScope', 'object'),
        staticOutput('supportPacketBase', 'supportPacketBase', 'object')
      ]
    }),
    pluginModuleNode({
      nodeId: 'aiReviewTool',
      name: '调用 hermes_ai_review_wft',
      intro: '执行 AI reviewer',
      key: 'hermes_ai_review_wft',
      x: 1280,
      y: 0,
      inputs: [
        inputField({ key: 'reviewId', label: 'reviewId', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'reviewId') }),
        inputField({ key: 'query', label: 'query', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'query') }),
        inputField({ key: 'documentType', label: 'documentType', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'documentType') }),
        inputField({ key: 'enabledModules', label: 'enabledModules', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'enabledModules') }),
        inputField({ key: 'focusRequirements', label: 'focusRequirements', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'focusRequirements') }),
        inputField({ key: 'strictMode', label: 'strictMode', valueType: 'boolean', renderTypeList: ['reference'], value: ref('normalizeInput', 'strictMode') }),
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', renderTypeList: ['reference'], value: ref('reviewContextTool', 'reviewContext') }),
        inputField({ key: 'targetFileUrls', label: 'targetFileUrls', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'targetFileUrls') }),
        inputField({ key: 'aiModel', label: 'aiModel', valueType: 'string', renderTypeList: ['reference'], value: PLACEHOLDER_AI_MODEL })
      ],
      outputs: [
        staticOutput('aiReview', 'aiReview', 'object'),
        staticOutput('reviewerPackets', 'reviewerPackets', 'arrayObject')
      ]
    }),
    pluginModuleNode({
      nodeId: 'deterministicReviewTool',
      name: '调用 hermes_deterministic_review_wft',
      intro: '执行确定性 reviewer',
      key: 'hermes_deterministic_review_wft',
      x: 1740,
      y: 0,
      inputs: [
        inputField({ key: 'reviewId', label: 'reviewId', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'reviewId') }),
        inputField({ key: 'enabledModules', label: 'enabledModules', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'enabledModules') }),
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', renderTypeList: ['reference'], value: ref('reviewContextTool', 'reviewContext') }),
        inputField({ key: 'aiReview', label: 'aiReview', valueType: 'object', renderTypeList: ['reference'], value: ref('aiReviewTool', 'aiReview') })
      ],
      outputs: [
        staticOutput('deterministicReview', 'deterministicReview', 'object'),
        staticOutput('reviewerPackets', 'reviewerPackets', 'arrayObject')
      ]
    }),
    pluginModuleNode({
      nodeId: 'support008Tool',
      name: '调用 hermes_support_008_wft',
      intro: '生成 008 支撑层结果',
      key: 'hermes_support_008_wft',
      x: 2200,
      y: 0,
      inputs: [
        inputField({ key: 'reviewId', label: 'reviewId', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'reviewId') }),
        inputField({ key: 'documentType', label: 'documentType', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'documentType') }),
        inputField({ key: 'reviewContext', label: 'reviewContext', valueType: 'object', renderTypeList: ['reference'], value: ref('reviewContextTool', 'reviewContext') })
      ],
      outputs: [
        staticOutput('supportReview', 'supportReview', 'object'),
        staticOutput('supportPacket008', 'supportPacket008', 'object')
      ]
    }),
    pluginModuleNode({
      nodeId: 'finalAssemblerTool',
      name: '调用 hermes_final_assembler_wft',
      intro: '组装正式/降级结果',
      key: 'hermes_final_assembler_wft',
      x: 2660,
      y: 0,
      inputs: [
        inputField({ key: 'reviewId', label: 'reviewId', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'reviewId') }),
        inputField({ key: 'documentType', label: 'documentType', valueType: 'string', renderTypeList: ['reference'], value: ref('normalizeInput', 'documentType') }),
        inputField({ key: 'enabledModules', label: 'enabledModules', valueType: 'arrayString', renderTypeList: ['reference'], value: ref('normalizeInput', 'enabledModules') }),
        inputField({ key: 'supportReview', label: 'supportReview', valueType: 'object', renderTypeList: ['reference'], value: ref('support008Tool', 'supportReview') }),
        inputField({ key: 'aiReview', label: 'aiReview', valueType: 'object', renderTypeList: ['reference'], value: ref('aiReviewTool', 'aiReview') }),
        inputField({ key: 'deterministicReview', label: 'deterministicReview', valueType: 'object', renderTypeList: ['reference'], value: ref('deterministicReviewTool', 'deterministicReview') })
      ],
      outputs: [
        staticOutput('finalDecision', 'finalDecision', 'object'),
        staticOutput('finalAnswer', 'finalAnswer', 'string'),
        staticOutput('degraded', 'degraded', 'boolean'),
        staticOutput('degradedReason', 'degradedReason', 'string'),
        staticOutput('traceability', 'traceability', 'arrayObject'),
        staticOutput('finalReportMarkdown', 'finalReportMarkdown', 'string'),
        staticOutput('reportHtml', 'reportHtml', 'string'),
        staticOutput('reportPrintCss', 'reportPrintCss', 'string'),
        staticOutput('finalReportViewModel', 'finalReportViewModel', 'object')
      ]
    }),
    answerNode('finalAnswerNode', 3120, 0, ref('finalAssemblerTool', 'finalAnswer'))
  ];

  const edges = [
    { source: 'workflowStart', target: 'normalizeInput' },
    { source: 'normalizeInput', target: 'reviewContextTool' },
    { source: 'reviewContextTool', target: 'aiReviewTool' },
    { source: 'aiReviewTool', target: 'deterministicReviewTool' },
    { source: 'deterministicReviewTool', target: 'support008Tool' },
    { source: 'support008Tool', target: 'finalAssemblerTool' },
    { source: 'finalAssemblerTool', target: 'finalAnswerNode' }
  ];

  return {
    nodes,
    edges,
    chatConfig: {
      welcomeText: '上传被审文件后，我将按 Hermes 固定编排执行正式审查。',
      variables,
      autoExecute: false,
      questionGuide: { open: false },
      ttsConfig: { type: 'web' },
      whisperConfig: { open: false, autoSend: false, autoTTSResponse: false },
      chatInputGuide: { open: true, customUrl: '' },
      fileSelectConfig: {
        maxFiles: 10,
        canSelectFile: true,
        canSelectImg: false,
        canSelectVideo: false,
        canSelectAudio: false,
        canSelectCustomFileExtension: false,
        customFileExtensionList: []
      },
      instruction: [
        'migrationMode: workflow+workflow-tools',
        '按固定编排调用 5 个工作流工具完成 Hermes 结构化正式审查。',
        '必须显式透传 target 文件链接；若主审结果不可用，必须 fail-closed。',
        '工作流工具 appId 通过运行时 registry 注入，不得留空。'
      ].join('\n')
    }
  };
}

export function buildRuntimeTemplate() {
  return {
    defaultAiModel: PLACEHOLDER_AI_MODEL,
    workflowToolAppIds: Object.fromEntries(
      WORKFLOW_TOOL_SPECS.map((spec) => [spec.key, `__FASTGPT_APP_ID__${spec.key}`])
    )
  };
}

export function buildBundle(repoRoot) {
  const assets = loadGeneratedAssets(repoRoot);
  return {
    assets,
    runtimeTemplate: buildRuntimeTemplate(),
    workflowTools: buildWorkflowToolBundles(assets),
    mainWorkflow: buildMainWorkflow(assets),
    mainWorkflowCreate: {
      name: 'Hermes 结构化正式审查主工作流',
      avatar: 'core/app/type/workflowFill',
      intro: '按固定编排调用 5 个工作流工具完成 Hermes 结构化正式审查。',
      type: 'advanced',
      modules: buildMainWorkflow(assets).nodes,
      edges: buildMainWorkflow(assets).edges,
      chatConfig: buildMainWorkflow(assets).chatConfig
    }
  };
}

export function writeBundleArtifacts(repoRoot, bundle) {
  const artifactsDir = path.join(repoRoot, 'artifacts', 'fastgpt');
  const workflowToolsDir = path.join(artifactsDir, 'workflow_tools');
  const governedSnapshotsDir = path.join(artifactsDir, 'governed_snapshots');
  ensureDir(artifactsDir);
  ensureDir(workflowToolsDir);
  ensureDir(governedSnapshotsDir);

  fs.writeFileSync(
    path.join(artifactsDir, 'hermes-structured-review.workflow.json'),
    JSON.stringify(bundle.mainWorkflow, null, 2)
  );
  fs.writeFileSync(
    path.join(artifactsDir, 'hermes-structured-review.app.create.json'),
    JSON.stringify(bundle.mainWorkflowCreate, null, 2)
  );
  fs.writeFileSync(
    path.join(artifactsDir, 'workflow_runtime.template.json'),
    JSON.stringify(bundle.runtimeTemplate, null, 2)
  );

  for (const item of bundle.workflowTools) {
    fs.writeFileSync(
      path.join(workflowToolsDir, `${item.key}.template.json`),
      JSON.stringify(item.templateJson, null, 2)
    );
    fs.writeFileSync(
      path.join(workflowToolsDir, `${item.key}.create.json`),
      JSON.stringify(item.createJson, null, 2)
    );
  }

  const generatedDir = bundle.assets.generatedDir;
  for (const fileName of fs.readdirSync(generatedDir)) {
    fs.copyFileSync(
      path.join(generatedDir, fileName),
      path.join(governedSnapshotsDir, fileName)
    );
  }
  fs.writeFileSync(
    path.join(governedSnapshotsDir, 'dataset_manifest.json'),
    JSON.stringify(bundle.assets.datasetManifest, null, 2)
  );
}
