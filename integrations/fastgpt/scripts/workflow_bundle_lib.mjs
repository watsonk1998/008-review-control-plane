import fs from 'node:fs';
import path from 'node:path';

const TOOL_DEFS = [
  {
    key: 'hermes_review_context_wft',
    title: 'Hermes 审查上下文工具',
    intro: '归一化输入、解析文档、解析治理快照，并输出受治理的审查上下文。',
    placeholder: '__WFT_HERMES_REVIEW_CONTEXT_ID__'
  },
  {
    key: 'hermes_ai_review_wft',
    title: 'Hermes AI 审查工具',
    intro: '按模块与文档类型选择 AI reviewer，执行结构化主审并输出 reviewer 分包。',
    placeholder: '__WFT_HERMES_AI_REVIEW_ID__'
  },
  {
    key: 'hermes_deterministic_review_wft',
    title: 'Hermes 确定性审查工具',
    intro: '执行可视域缺口、规范有效性、政策符合性与计算核验 fallback。',
    placeholder: '__WFT_HERMES_DETERMINISTIC_REVIEW_ID__'
  },
  {
    key: 'hermes_support_008_wft',
    title: 'Hermes 008 支撑层工具',
    intro: '整理 008 支撑层结果、证据索引与 supportPacket008。',
    placeholder: '__WFT_HERMES_SUPPORT_008_ID__'
  },
  {
    key: 'hermes_final_assembler_wft',
    title: 'Hermes 最终组装工具',
    intro: '执行 fail-closed、模块门禁、最终评级与正式/降级报告输出。',
    placeholder: '__WFT_HERMES_FINAL_ASSEMBLER_ID__'
  }
];

const AI_MODEL_PLACEHOLDER = '__FASTGPT_AI_MODEL__';

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeJson(file, payload) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, `${JSON.stringify(payload, null, 2)}\n`);
}

function pos(x, y) {
  return { x, y };
}

function makeEdge(source, target, sourceHandle = `${source}-source-right`, targetHandle = `${target}-target-left`) {
  return { source, target, sourceHandle, targetHandle };
}

function baseNode({ nodeId, name, intro, avatar, flowNodeType, position, version = '489', showStatus = true, inputs = [], outputs = [] }) {
  return {
    nodeId,
    name,
    intro,
    avatar,
    flowNodeType,
    showStatus,
    position,
    version,
    inputs,
    outputs
  };
}

function pluginConfigNode(position = pos(0, 0)) {
  return baseNode({
    nodeId: 'pluginConfig',
    name: '系统配置',
    intro: '',
    avatar: 'core/workflow/template/systemConfig',
    flowNodeType: 'pluginConfig',
    showStatus: false,
    position,
    version: '4811'
  });
}

function pluginInputNode(inputs, outputs, position = pos(420, 0)) {
  return baseNode({
    nodeId: 'pluginInput',
    name: '工具开始',
    intro: '配置工作流工具输入参数。',
    avatar: 'core/workflow/template/workflowStart',
    flowNodeType: 'pluginInput',
    showStatus: false,
    position,
    version: '481',
    inputs,
    outputs
  });
}

function pluginOutputNode(inputs, position = pos(1980, 0)) {
  return baseNode({
    nodeId: 'pluginOutput',
    name: '工具输出',
    intro: '配置工作流工具对外暴露的输出。',
    avatar: 'core/workflow/template/pluginOutput',
    flowNodeType: 'pluginOutput',
    showStatus: false,
    position,
    version: '481',
    inputs,
    outputs: []
  });
}

function workflowStartNode(position = pos(0, 0)) {
  return baseNode({
    nodeId: 'workflowStart',
    name: '流程开始',
    intro: '接收用户问题、上传文件和工作流变量。',
    avatar: 'core/workflow/template/workflowStart',
    flowNodeType: 'workflowStart',
    showStatus: false,
    position,
    version: '481',
    inputs: [
      {
        key: 'userChatInput',
        renderTypeList: ['reference', 'textarea'],
        valueType: 'string',
        label: '用户问题',
        required: true,
        toolDescription: '用户问题',
        debugLabel: ''
      }
    ],
    outputs: [
      {
        id: 'userChatInput',
        key: 'userChatInput',
        label: '用户问题',
        type: 'static',
        valueType: 'string',
        description: ''
      },
      {
        id: 'userFiles',
        key: 'userFiles',
        label: '用户文件',
        description: '用户上传文件 URL 数组。',
        type: 'static',
        valueType: 'arrayString'
      }
    ]
  });
}

function userGuideNode(position = pos(-380, -180)) {
  return baseNode({
    nodeId: 'userGuide',
    name: '系统配置',
    intro: 'Hermes 审查主工作流（migrationMode=workflow+workflow-tools）。',
    avatar: 'core/workflow/template/systemConfig',
    flowNodeType: 'userGuide',
    showStatus: false,
    position,
    version: '481'
  });
}

function readFilesNode({ nodeId, position, fileSource }) {
  return baseNode({
    nodeId,
    name: '文档解析',
    intro: '解析文档内容并返回拼接后的正文文本。',
    avatar: 'core/workflow/template/readFiles',
    flowNodeType: 'readFiles',
    showStatus: true,
    position,
    version: '489',
    inputs: [
      {
        key: 'fileUrlList',
        renderTypeList: ['reference'],
        valueType: 'arrayString',
        label: '文档链接',
        required: true,
        value: fileSource,
        valueDesc: '',
        description: '',
        debugLabel: '',
        toolDescription: ''
      }
    ],
    outputs: [
      {
        id: 'system_text',
        key: 'system_text',
        label: '文档文本',
        description: '文档原文，由文件名和文档内容组成。',
        valueType: 'string',
        type: 'static'
      }
    ]
  });
}

function codeNode({ nodeId, name, intro, position, code, inputs = [], outputs = [] }) {
  return baseNode({
    nodeId,
    name,
    intro,
    avatar: 'core/workflow/template/codeRun',
    flowNodeType: 'code',
    showStatus: true,
    position,
    version: '482',
    inputs: [
      {
        key: 'system_addInputParam',
        renderTypeList: ['addInputParam'],
        valueType: 'dynamic',
        label: '',
        required: false,
        description: '代码节点输入参数。',
        customInputConfig: {
          selectValueTypeList: [
            'string',
            'number',
            'boolean',
            'object',
            'arrayString',
            'arrayNumber',
            'arrayBoolean',
            'arrayObject',
            'arrayAny',
            'any',
            'chatHistory',
            'datasetQuote',
            'dynamic',
            'selectApp',
            'selectDataset'
          ],
          showDescription: false,
          showDefaultValue: true
        },
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'codeType',
        renderTypeList: ['hidden'],
        label: '',
        value: 'js',
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'code',
        renderTypeList: ['custom'],
        label: '',
        value: code,
        debugLabel: '',
        toolDescription: ''
      },
      ...inputs
    ],
    outputs: [
      {
        id: 'system_rawResponse',
        key: 'system_rawResponse',
        label: '完整结果',
        valueType: 'object',
        type: 'static',
        description: ''
      },
      {
        id: 'error',
        key: 'error',
        label: '错误信息',
        description: '代码运行错误信息。',
        valueType: 'object',
        type: 'static'
      },
      {
        id: 'system_addOutputParam',
        key: 'system_addOutputParam',
        type: 'dynamic',
        valueType: 'dynamic',
        label: '',
        customFieldConfig: {
          selectValueTypeList: [
            'string',
            'number',
            'boolean',
            'object',
            'arrayString',
            'arrayNumber',
            'arrayBoolean',
            'arrayObject',
            'any',
            'chatHistory',
            'datasetQuote',
            'dynamic',
            'selectApp',
            'selectDataset'
          ],
          showDescription: false,
          showDefaultValue: false
        },
        description: 'return 对象会按 key 作为输出。'
      },
      ...outputs
    ]
  });
}

function chatNode({ nodeId, name, intro, position, modelValue, systemPrompt, userChatInputRef, outputs = [], extraInputs = [] }) {
  return baseNode({
    nodeId,
    name,
    intro,
    avatar: 'core/workflow/template/aiChat',
    flowNodeType: 'chatNode',
    showStatus: true,
    position,
    version: '481',
    inputs: [
      {
        key: 'model',
        renderTypeList: ['settingLLMModel', 'reference'],
        label: '模型',
        valueType: 'string',
        selectedTypeIndex: 0,
        value: modelValue,
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'temperature',
        renderTypeList: ['hidden'],
        label: '',
        value: 2,
        valueType: 'number',
        min: 0,
        max: 10,
        step: 1,
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'maxToken',
        renderTypeList: ['hidden'],
        label: '',
        value: 4000,
        valueType: 'number',
        min: 100,
        max: 4000,
        step: 50,
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'isResponseAnswerText',
        renderTypeList: ['hidden'],
        label: '',
        value: false,
        valueType: 'boolean',
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'aiChatQuoteRole',
        renderTypeList: ['hidden'],
        label: '',
        valueType: 'string',
        value: 'system',
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'quoteTemplate',
        renderTypeList: ['hidden'],
        label: '',
        valueType: 'string',
        value: '{{q}}\n{{a}}',
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'quotePrompt',
        renderTypeList: ['hidden'],
        label: '',
        valueType: 'string',
        value: '',
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'aiChatVision',
        renderTypeList: ['hidden'],
        label: '',
        valueType: 'boolean',
        value: false,
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'systemPrompt',
        renderTypeList: ['textarea', 'reference'],
        max: 3000,
        valueType: 'string',
        label: '系统提示词',
        description: '控制结构化输出。',
        placeholder: '',
        value: systemPrompt,
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'history',
        renderTypeList: ['numberInput', 'reference'],
        valueType: 'chatHistory',
        label: '历史轮次',
        description: '限制历史轮次。',
        required: true,
        min: 0,
        max: 50,
        value: 2,
        debugLabel: '',
        toolDescription: ''
      },
      {
        key: 'stringQuoteText',
        renderTypeList: ['reference', 'textarea'],
        label: '文档引用',
        debugLabel: '文档引用',
        description: '可选的补充上下文。',
        valueType: 'string',
        toolDescription: ''
      },
      {
        key: 'userChatInput',
        renderTypeList: ['reference', 'textarea'],
        valueType: 'string',
        label: '用户问题',
        required: true,
        toolDescription: '用户问题',
        selectedTypeIndex: 0,
        value: userChatInputRef,
        debugLabel: ''
      },
      ...extraInputs
    ],
    outputs: [
      {
        id: 'history',
        key: 'history',
        required: true,
        label: '新上下文',
        description: '新的上下文',
        valueType: 'chatHistory',
        valueDesc: '{ obj: System | Human | AI; value: string; }[]',
        type: 'static'
      },
      {
        id: 'answerText',
        key: 'answerText',
        required: true,
        label: '回答文本',
        description: '模型回复文本。',
        valueType: 'string',
        type: 'static'
      },
      ...outputs
    ]
  });
}

function answerNode({ nodeId, name, intro, position, textValue }) {
  return baseNode({
    nodeId,
    name,
    intro,
    avatar: 'core/workflow/template/reply',
    flowNodeType: 'answerNode',
    showStatus: false,
    position,
    version: '481',
    inputs: [
      {
        key: 'text',
        renderTypeList: ['textarea', 'reference'],
        valueType: 'any',
        required: true,
        label: '回复内容',
        description: '输出给用户的文本。',
        placeholder: '',
        selectedTypeIndex: Array.isArray(textValue) ? 1 : 0,
        value: textValue,
        debugLabel: '',
        toolDescription: ''
      }
    ],
    outputs: []
  });
}

function ifElseNode({ nodeId, name, intro, position, variableRef }) {
  return baseNode({
    nodeId,
    name,
    intro,
    avatar: 'core/workflow/template/ifelse',
    flowNodeType: 'ifElseNode',
    showStatus: true,
    position,
    version: '481',
    inputs: [
      {
        key: 'ifElseList',
        renderTypeList: ['hidden'],
        valueType: 'any',
        label: '',
        value: [
          {
            condition: 'AND',
            list: [
              {
                variable: variableRef,
                condition: 'equalTo',
                value: 'true'
              }
            ]
          }
        ],
        debugLabel: '',
        toolDescription: ''
      }
    ],
    outputs: [
      {
        id: 'ifElseResult',
        key: 'ifElseResult',
        label: '判断结果',
        valueType: 'string',
        type: 'static',
        description: ''
      }
    ]
  });
}

function pluginModuleNode({ nodeId, name, intro, position, pluginId, inputs, outputs }) {
  return baseNode({
    nodeId,
    name,
    intro,
    avatar: '/imgs/workflow/tool.svg',
    flowNodeType: 'pluginModule',
    showStatus: false,
    position,
    version: '488',
    inputs: [
      {
        key: 'system_forbid_stream',
        renderTypeList: ['switch'],
        valueType: 'boolean',
        label: '禁用流输出',
        description: '嵌套工具一律使用非流式。',
        value: true,
        valueDesc: '',
        debugLabel: '',
        toolDescription: ''
      },
      ...inputs
    ],
    outputs,
    pluginId
  });
}

function variableEntry({ key, type = 'input', required = false }) {
  return { key, label: key, type, required };
}

function inputVar(key, label, valueType, value, description = '', required = true) {
  return {
    renderTypeList: ['input'],
    selectedTypeIndex: 0,
    valueType,
    canEdit: true,
    key,
    label,
    description,
    required,
    value,
    valueDesc: '',
    debugLabel: '',
    toolDescription: description || label
  };
}

function inputRef(key, label, valueType, value, description = '', required = true) {
  return {
    renderTypeList: ['reference'],
    selectedTypeIndex: 0,
    valueType,
    canEdit: true,
    key,
    label,
    description,
    required,
    value,
    valueDesc: '',
    debugLabel: '',
    toolDescription: description || label
  };
}

function inputHidden(key, valueType, value, description = '') {
  return {
    key,
    renderTypeList: ['hidden'],
    valueType,
    label: '',
    value,
    required: false,
    description,
    debugLabel: '',
    toolDescription: ''
  };
}

function outputHidden(key, valueType, label = key) {
  return {
    id: key,
    valueType,
    key,
    label,
    type: 'hidden'
  };
}

function outputDynamic(key, valueType, label = key, description = '') {
  return {
    id: key,
    valueType,
    type: 'dynamic',
    key,
    label,
    description
  };
}

function pluginOutputRef(key, label, valueType, value, description = '') {
  return {
    renderTypeList: ['reference'],
    valueType,
    canEdit: true,
    key,
    label,
    description,
    value
  };
}

function normalizeMultilineCode(code) {
  return code.trim().replace(/^\n+/, '');
}

function mainNormalizeCode(docTypeLabels) {
  return normalizeMultilineCode(`
function main({ userChatInput, userFiles, documentTypeRaw, disciplineTagsRaw, enabledModulesRaw, disabledModulesRaw, focusRequirementsRaw, strictModeRaw }) {
  function toArray(value) {
    if (Array.isArray(value)) return value.filter(Boolean);
    if (value == null || value === '') return [];
    if (typeof value === 'object') return [value];
    if (typeof value === 'string') {
      const text = value.trim();
      if (!text) return [];
      try {
        const parsed = JSON.parse(text);
        if (Array.isArray(parsed)) return parsed.filter(Boolean);
      } catch (error) {}
      return text.split(/[\n,，;；]/).map((item) => item.trim()).filter(Boolean);
    }
    return [value];
  }
  function toBoolean(value, defaultValue) {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'number') return value !== 0;
    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase();
      if (!normalized) return defaultValue;
      if (['true', '1', 'yes', 'y', 'on'].includes(normalized)) return true;
      if (['false', '0', 'no', 'n', 'off'].includes(normalized)) return false;
    }
    return defaultValue;
  }
  const defaultModules = ['structure_completeness', 'parameter_consistency', 'legality_compliance', 'execution_continuity', 'evidence_validation'];
  const disabledModules = new Set(toArray(disabledModulesRaw));
  let enabledModules = toArray(enabledModulesRaw);
  if (!enabledModules.length) enabledModules = defaultModules.slice();
  enabledModules = enabledModules.filter((item) => !disabledModules.has(item));
  const targetFileUrls = Array.isArray(userFiles) ? userFiles.filter(Boolean) : [];
  const documentType = (documentTypeRaw || '').trim() || 'construction_org';
  const reviewId = 'fastgpt-hermes-' + Date.now();
  const documentTypeLabelMap = ${JSON.stringify(docTypeLabels)};
  return {
    reviewId,
    query: typeof userChatInput === 'string' && userChatInput.trim() ? userChatInput.trim() : '请执行 Hermes 正式审查。',
    documentType,
    documentTypeLabel: documentTypeLabelMap[documentType] || documentType,
    disciplineTags: toArray(disciplineTagsRaw),
    enabledModules,
    disabledModules: Array.from(disabledModules),
    focusRequirements: toArray(focusRequirementsRaw),
    strictMode: toBoolean(strictModeRaw, true),
    targetFileUrls,
    basisFileUrls: [],
    contextFileUrls: []
  };
}
`);
}

function reviewContextCode() {
  return normalizeMultilineCode(`
function main({ reviewId, query, documentType, disciplineTags, enabledModules, disabledModules, focusRequirements, strictMode, targetFileUrls, basisFileUrls, contextFileUrls, documentText, governanceSnapshot, datasetManifest }) {
  function toArray(value) {
    if (Array.isArray(value)) return value.filter(Boolean);
    if (value == null || value === '') return [];
    if (typeof value === 'object') return [value];
    if (typeof value === 'string') {
      const text = value.trim();
      if (!text) return [];
      try {
        const parsed = JSON.parse(text);
        if (Array.isArray(parsed)) return parsed.filter(Boolean);
      } catch (error) {}
      return text.split(/[\n,，;；]/).map((item) => item.trim()).filter(Boolean);
    }
    return [value];
  }
  function unique(list) {
    return Array.from(new Set((list || []).filter(Boolean)));
  }
  function normalizeText(value) {
    return String(value || '').replace(/\r/g, '\n').replace(/\u0000/g, '').replace(/\n{3,}/g, '\n\n').trim();
  }
  function slugify(value) {
    return String(value || '').toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-').replace(/^-+|-+$/g, '') || 'block';
  }
  function isHeading(line) {
    return /^#{1,6}\s+/.test(line) || /^第[一二三四五六七八九十0-9]+[章节篇部分]/.test(line) || /^(一|二|三|四|五|六|七|八|九|十)[、.]/.test(line);
  }
  function headingLevel(line) {
    const hashMatch = line.match(/^(#{1,6})\s+/);
    if (hashMatch) return hashMatch[1].length;
    if (/^第[一二三四五六七八九十0-9]+篇/.test(line)) return 1;
    if (/^第[一二三四五六七八九十0-9]+章/.test(line)) return 2;
    if (/^第[一二三四五六七八九十0-9]+节/.test(line)) return 3;
    return 2;
  }
  function cleanHeading(line) {
    return line.replace(/^#{1,6}\s+/, '').trim();
  }
  function parseDocument(text) {
    const normalized = normalizeText(text);
    const lines = normalized.split(/\n/);
    const sections = [];
    const blocks = [];
    let currentSectionId = null;
    let currentTitle = '正文';
    let currentLevel = 1;
    let buffer = [];
    let position = 0;
    function flushBuffer() {
      const value = normalizeText(buffer.join('\n'));
      if (!value) return;
      position += 1;
      blocks.push({
        id: 'block-' + position,
        type: 'paragraph',
        text: value,
        sectionId: currentSectionId,
        headingLevel: null,
        position
      });
      buffer = [];
    }
    lines.forEach((rawLine) => {
      const line = String(rawLine || '').trim();
      if (!line) {
        if (buffer.length) buffer.push('');
        return;
      }
      if (isHeading(line)) {
        flushBuffer();
        currentTitle = cleanHeading(line);
        currentLevel = headingLevel(line);
        currentSectionId = 'section-' + slugify(currentTitle) + '-' + (sections.length + 1);
        sections.push({
          id: currentSectionId,
          title: currentTitle,
          key: slugify(currentTitle),
          level: currentLevel,
          parentId: null,
          blockId: 'block-heading-' + (sections.length + 1),
          position: sections.length + 1
        });
        position += 1;
        blocks.push({
          id: 'block-heading-' + sections.length,
          type: 'heading',
          text: currentTitle,
          sectionId: currentSectionId,
          headingLevel: currentLevel,
          position
        });
        return;
      }
      buffer.push(line);
    });
    flushBuffer();
    return { sections, blocks, normalizedText: normalized };
  }
  function targetSectionIds(sections) {
    return new Set((sections || []).filter((section) => /编制依据|编制说明/.test(section.title)).map((section) => section.id));
  }
  function splitReferenceCandidates(text) {
    const value = normalizeText(text);
    if (!value) return [];
    if (value.trim().startsWith('|') || value.split('|').length >= 3) {
      return value.split('|').map((cell) => normalizeText(cell)).filter(Boolean).filter((cell) => !['序号', '名称', '规范名称', '标准号', '备注', '编号'].includes(cell));
    }
    return value.replace(/^[（(]?\d+[)）.、]\s*/, '').split(/[；;]/).map((part) => part.trim().replace(/[。;；]+$/g, '')).filter(Boolean);
  }
  const normativeCodePattern = /(?:(?:GB|GB\/T|GBJ|DL\/T|DL|Q\/CSG|Q\/GDW|Q\/SH|Q\/BGJ|JGJ|NB\/T|NB|AQ|DB|DBJ|DGJ|YD\/T|SL|GA|CECS|TSG|HG|CJJ|SH\/T|YB|JB|CJ|YS|SY|HJ|TB|LB|MZ)\s*[-/A-Z]*\s*\d{2,}(?:\.\d+)?(?:[-—]\d{2,4})?)/i;
  function extractNormativeTitle(text) {
    let value = normalizeText(text);
    if (!value) return '';
    if (!value.includes('《') && !normativeCodePattern.test(value)) return '';
    if (value.includes('《')) value = value.slice(value.indexOf('《'));
    return value.replace(/^[(（]?\d+[)）.、]\s*/, '').trim();
  }
  function parseVisibility(text) {
    const attachmentMatches = text.match(/附件|附图|见图|详见|附表/g) || [];
    const duplicateSectionTitles = [];
    return {
      attachmentCount: attachmentMatches.length,
      counts: { sectionCount: 0, blockCount: 0 },
      reasonCounts: attachmentMatches.length ? { title_detected_without_attachment_body: attachmentMatches.length } : {},
      duplicateSectionTitles,
      parseWarnings: attachmentMatches.length ? ['正文多处引用附件或附图，当前仅获得正文文本。'] : [],
      manualReviewNeeded: attachmentMatches.length > 0,
      manualReviewReason: attachmentMatches.length ? '正文引用了附件、附图或外部材料，需人工结合原件复核。' : null
    };
  }
  const snapshot = governanceSnapshot || {};
  const parsed = parseDocument(documentText || '');
  const visibility = parseVisibility(parsed.normalizedText);
  visibility.counts.sectionCount = parsed.sections.length;
  visibility.counts.blockCount = parsed.blocks.length;
  const basisSectionIds = targetSectionIds(parsed.sections);
  const normativeRefs = unique(parsed.blocks
    .filter((block) => block.type !== 'heading')
    .filter((block) => basisSectionIds.size ? basisSectionIds.has(block.sectionId) : true)
    .flatMap((block) => splitReferenceCandidates(block.text))
    .map(extractNormativeTitle)
    .filter(Boolean));
  const facts = {
    section_count: parsed.sections.length,
    block_count: parsed.blocks.length,
    attachment_mentions: visibility.attachmentCount,
    has_emergency_plan: /应急|抢修|事故/.test(parsed.normalizedText),
    has_calculation_basis: /计算|验算|公式|荷载|安全系数/.test(parsed.normalizedText),
    has_operation_chain: /停电|验电|接地|挂牌|遮栏|复电|送电/.test(parsed.normalizedText),
    normative_refs: normativeRefs,
    focus_requirements: toArray(focusRequirements),
    discipline_tags: toArray(disciplineTags)
  };
  const profileMapping = snapshot.profileMapping || {};
  const resolvedProfile = profileMapping[documentType] || {
    profile_id: documentType,
    classification: { level1: '审查任务', level2: documentType },
    default_pack_ids: [],
    required_pack_ids: [],
    optional_pack_ids: [],
    enterprise_pack_ids: [],
    rule_pack_ids: []
  };
  const packRegistry = snapshot.packRegistry || {};
  const packsMap = packRegistry.packs || {};
  const basisRegistry = snapshot.basisRegistry || {};
  const packIds = unique([].concat(resolvedProfile.default_pack_ids || [], resolvedProfile.required_pack_ids || [], resolvedProfile.enterprise_pack_ids || []));
  const packs = packIds.map((packId) => packsMap[packId]).filter(Boolean);
  const basisIds = unique(packs.flatMap((pack) => pack.basis_ids || []));
  const basisDocuments = basisIds.map((basisId) => {
    const item = basisRegistry[basisId] || { basis_id: basisId, title: basisId, file_refs: [] };
    return {
      basis_id: basisId,
      title: item.title || basisId,
      version: item.version || '',
      file_refs: item.file_refs || [],
      applicability_tags: item.applicability_tags || []
    };
  });
  const resolvedBasisProfile = {
    profile_id: resolvedProfile.profile_id || documentType,
    level1_classification: (resolvedProfile.classification || {}).level1 || '审查任务',
    level2_classification: (resolvedProfile.classification || {}).level2 || documentType,
    level3_classification: (resolvedProfile.classification || {}).level3 || null,
    packs,
    rule_packs: (snapshot.rulePackRegistry && (resolvedProfile.rule_pack_ids || []).map((rulePackId) => snapshot.rulePackRegistry.rule_packs ? snapshot.rulePackRegistry.rule_packs[rulePackId] : null).filter(Boolean)) || [],
    basis_documents: basisDocuments,
    degraded: false,
    degradation_reasons: []
  };
  const governedDatasetScope = {
    documentType,
    profileId: resolvedBasisProfile.profile_id,
    datasetKeys: ((datasetManifest || {}).entries || []).filter((entry) => entry.profileId === resolvedBasisProfile.profile_id || (entry.documentTypes || []).includes(documentType)).map((entry) => entry.datasetKey),
    datasetIdPlaceholders: ((datasetManifest || {}).entries || []).filter((entry) => entry.profileId === resolvedBasisProfile.profile_id || (entry.documentTypes || []).includes(documentType)).map((entry) => entry.datasetIdPlaceholder),
    basisIds,
    basisTitles: basisDocuments.map((item) => item.title),
    basisFileRefs: unique(basisDocuments.flatMap((item) => item.file_refs || []))
  };
  const moduleBindings = snapshot.moduleBindings || {};
  const ruleHits = basisDocuments.slice(0, Math.max(3, Math.min(basisDocuments.length, 8))).map((doc, index) => ({
    ruleId: 'FG-RULE-' + String(index + 1).padStart(3, '0'),
    packId: packs[index % Math.max(packs.length, 1)] ? packs[index % packs.length].pack_id : 'governed.base',
    packReadiness: 'ready',
    matchType: 'basis_profile_projection',
    status: 'candidate',
    layerHint: 'support',
    severityHint: index === 0 ? 'medium' : 'low',
    factRefs: ['normative_refs'],
    evidenceRefs: doc.file_refs || [],
    rationale: '已将受治理依据纳入本次 FastGPT 审查上下文。',
    applicabilityState: 'matched',
    blockingReasons: [],
    missingFactKeys: []
  }));
  const enabled = toArray(enabledModules).length ? toArray(enabledModules) : Object.keys(moduleBindings);
  const candidates = enabled.map((moduleName, index) => ({
    candidateId: moduleName + '-candidate-' + (index + 1),
    title: ((moduleBindings[moduleName] || {}).title || moduleName) + '：待主审复核',
    layerHint: 'review',
    severityHint: moduleName === 'evidence_validation' && visibility.manualReviewNeeded ? 'medium' : 'low',
    findingType: visibility.manualReviewNeeded && moduleName === 'evidence_validation' ? 'visibility_gap' : 'engineering_inference',
    ruleHits: ruleHits.slice(0, 2),
    evidenceMissing: visibility.manualReviewNeeded && moduleName === 'evidence_validation',
    manualReviewNeeded: visibility.manualReviewNeeded && moduleName === 'evidence_validation',
    manualReviewReason: visibility.manualReviewReason,
    blockingReasons: visibility.manualReviewNeeded && moduleName === 'evidence_validation' ? ['attachment_visibility_gap'] : []
  }));
  const parseResult = {
    documentId: reviewId,
    filePath: (targetFileUrls || [])[0] || '',
    fileType: 'mixed',
    parseMode: 'fastgpt_read_files',
    parserLimited: visibility.manualReviewNeeded,
    sections: parsed.sections,
    blocks: parsed.blocks,
    attachments: [],
    normalizedText: parsed.normalizedText,
    preview: parsed.normalizedText.slice(0, 1000),
    visibility,
    parseWarnings: visibility.parseWarnings
  };
  const supportPacketBase = {
    review_id: reviewId,
    document_type: documentType,
    document_preview: parseResult.preview,
    basis_summary: {
      profile_id: resolvedBasisProfile.profile_id,
      pack_ids: packs.map((item) => item.pack_id),
      basis_ids: basisDocuments.map((item) => item.basis_id),
      dataset_scope: governedDatasetScope
    },
    parse_visibility: visibility,
    facts,
    focus_requirements: toArray(focusRequirements),
    discipline_tags: toArray(disciplineTags),
    strict_mode: strictMode !== false
  };
  const reviewContext = {
    reviewId,
    query,
    documentType,
    enabledModules: enabled,
    disabledModules: toArray(disabledModules),
    focusRequirements: toArray(focusRequirements),
    strictMode: strictMode !== false,
    targetFileUrls: toArray(targetFileUrls),
    basisFileUrls: toArray(basisFileUrls),
    contextFileUrls: toArray(contextFileUrls),
    parseResult,
    docTextPreview: parseResult.preview,
    facts,
    ruleHits,
    candidates,
    resolvedProfile,
    resolvedBasisProfile,
    governedDatasetScope,
    supportPacketBase
  };
  return {
    reviewContext,
    parseResult,
    docTextPreview: reviewContext.docTextPreview,
    facts,
    ruleHits,
    candidates,
    resolvedProfile,
    resolvedBasisProfile,
    governedDatasetScope,
    supportPacketBase
  };
}
`);
}

function aiReviewPrepareCode() {
  return normalizeMultilineCode(`
function main({ reviewContext, governanceSnapshot, aiModel }) {
  function unique(list) { return Array.from(new Set((list || []).filter(Boolean))); }
  function lower(value) { return String(value || '').toLowerCase(); }
  const snapshot = governanceSnapshot || {};
  const moduleBindings = snapshot.moduleBindings || {};
  const templateManifest = snapshot.templateManifest || [];
  const enabledModules = Array.isArray(reviewContext && reviewContext.enabledModules) ? reviewContext.enabledModules : [];
  const documentType = reviewContext && reviewContext.documentType;
  const templateIdToModules = {};
  Object.keys(moduleBindings).forEach((moduleName) => {
    const templates = ((moduleBindings[moduleName] || {}).hermes_templates || []);
    templates.forEach((templateId) => {
      templateIdToModules[templateId] = templateIdToModules[templateId] || [];
      templateIdToModules[templateId].push(moduleName);
    });
  });
  const selectedAiTemplates = unique(enabledModules.flatMap((moduleName) => ((moduleBindings[moduleName] || {}).hermes_templates || [])))
    .map((templateId) => templateManifest.find((item) => item.id === templateId))
    .filter(Boolean)
    .filter((template) => template.execution_mode === 'hermes_router')
    .filter((template) => !Array.isArray(template.supported_document_types) || template.supported_document_types.length === 0 || template.supported_document_types.includes(documentType))
    .map((template) => ({
      reviewerId: template.id,
      name: template.agent_name,
      purpose: template.agent_purpose,
      focusKeywords: template.focus_keywords || [],
      modules: unique(templateIdToModules[template.id] || [])
    }));
  const prompt = [
    '你是 Hermes 结构化审查主审执行器。',
    '必须严格依据给定的 reviewContext 输出 JSON，不得输出 JSON 之外的文字。',
    '如无问题，可返回空 findings，但不得臆造计算错误。',
    '若 reviewer 属于计算类且证据不足，不得编造错误，交由后续确定性 fallback 处理。',
    '',
    '返回 JSON 结构：',
    '{',
    '  "packets": [',
    '    {',
    '      "reviewerId": "string",',
    '      "degraded": false,',
    '      "overall": "string",',
    '      "findings": [',
    '        {',
    '          "title": "string",',
    '          "severity": "high|medium|low|info",',
    '          "summary": "string",',
    '          "suggestion": "string",',
    '          "evidence_status": "grounded|inferred|evidence_gap|visibility_gap"',
    '        }',
    '      ]',
    '    }',
    '  ]',
    '}',
    '',
    'selectedAiTemplates=' + JSON.stringify(selectedAiTemplates),
    'reviewContext=' + JSON.stringify(reviewContext)
  ].join('\n');
  return {
    selectedAiTemplates,
    selectedReviewerIds: selectedAiTemplates.map((item) => item.reviewerId),
    aiPrompt: prompt,
    aiModel: aiModel || '${AI_MODEL_PLACEHOLDER}'
  };
}
`);
}

function aiReviewNormalizeCode() {
  return normalizeMultilineCode(`
function main({ reviewContext, governanceSnapshot, selectedAiTemplates, aiAnswerText }) {
  function unique(list) { return Array.from(new Set((list || []).filter(Boolean))); }
  function parseJson(text) {
    const raw = String(text || '').trim();
    if (!raw) return null;
    const stripped = raw
      .replace(new RegExp('^' + String.fromCharCode(96, 96, 96) + 'json\\s*', 'i'), '')
      .replace(new RegExp('^' + String.fromCharCode(96, 96, 96)), '')
      .replace(new RegExp(String.fromCharCode(96, 96, 96) + '$'), '')
      .trim();
    try { return JSON.parse(stripped); } catch (error) {}
    const start = stripped.indexOf('{');
    const end = stripped.lastIndexOf('}');
    if (start >= 0 && end > start) {
      try { return JSON.parse(stripped.slice(start, end + 1)); } catch (error) {}
    }
    return null;
  }
  function severity(value) {
    const normalized = String(value || 'low').toLowerCase();
    return ['high', 'medium', 'low', 'info'].includes(normalized) ? normalized : 'low';
  }
  const snapshot = governanceSnapshot || {};
  const moduleBindings = snapshot.moduleBindings || {};
  const templateIdToModules = {};
  Object.keys(moduleBindings).forEach((moduleName) => {
    ((moduleBindings[moduleName] || {}).hermes_templates || []).forEach((templateId) => {
      templateIdToModules[templateId] = templateIdToModules[templateId] || [];
      templateIdToModules[templateId].push(moduleName);
    });
  });
  const parsed = parseJson(aiAnswerText) || { packets: [] };
  const packetMap = {};
  (Array.isArray(parsed.packets) ? parsed.packets : []).forEach((packet) => {
    if (packet && packet.reviewerId) packetMap[packet.reviewerId] = packet;
  });
  const reviewerPackets = (selectedAiTemplates || []).map((template, index) => {
    const packet = packetMap[template.reviewerId];
    if (!packet) {
      return {
        review_id: reviewContext.reviewId,
        engine: 'hermes',
        findings: [],
        overall_assessment: 'AI reviewer 未返回结构化结果。',
        degraded: true,
        error: template.reviewerId + ' 审查组件降级，未返回有效结果',
        metadata: {
          template_id: template.reviewerId,
          agent_id: template.reviewerId,
          review_modules: unique(template.modules || templateIdToModules[template.reviewerId] || []),
          agent_name: template.name
        },
        raw_result: { parseError: true, answerText: aiAnswerText }
      };
    }
    const findings = Array.isArray(packet.findings) ? packet.findings : [];
    return {
      review_id: reviewContext.reviewId,
      engine: 'hermes',
      findings: findings.map((finding, findingIndex) => ({
        id: 'H-AI-' + String(index + 1).padStart(2, '0') + '-' + String(findingIndex + 1).padStart(3, '0'),
        title: finding.title || (template.name + '发现'),
        severity: severity(finding.severity),
        category: (template.modules || templateIdToModules[template.reviewerId] || [])[0] || 'legality_compliance',
        summary: finding.summary || '主审组件已识别到需要人工处置的问题。',
        suggestion: finding.suggestion || '请根据依据文件和原文证据补正。',
        evidence_status: finding.evidence_status || 'grounded',
        source_engine: 'hermes',
        finding_type: 'hard_evidence',
        raw_data: {
          module_name: (template.modules || templateIdToModules[template.reviewerId] || [])[0] || 'legality_compliance',
          review_modules: unique(template.modules || templateIdToModules[template.reviewerId] || []),
          reviewer_id: template.reviewerId,
          reviewer_name: template.name
        }
      })),
      overall_assessment: packet.overall || (findings.length ? 'AI reviewer 已形成结构化问题。' : 'AI reviewer 未识别到需输出的问题。'),
      degraded: Boolean(packet.degraded),
      error: packet.degraded ? (packet.error || (template.reviewerId + ' 审查组件降级，未返回有效结果')) : '',
      metadata: {
        template_id: template.reviewerId,
        agent_id: template.reviewerId,
        review_modules: unique(template.modules || templateIdToModules[template.reviewerId] || []),
        agent_name: template.name
      },
      raw_result: packet
    };
  });
  const traceability = reviewerPackets.flatMap((packet) => (packet.findings || []).map((finding) => ({
    reviewerId: packet.metadata.agent_id,
    findingId: finding.id,
    moduleName: finding.raw_data && finding.raw_data.module_name,
    basisIds: ((reviewContext.resolvedBasisProfile || {}).basis_documents || []).map((item) => item.basis_id),
    evidenceRefs: ((reviewContext.governedDatasetScope || {}).basisFileRefs || []).slice(0, 5)
  })));
  return {
    aiReviewResult: {
      selectedAiTemplates,
      reviewerPackets,
      traceability,
      degradedCount: reviewerPackets.filter((packet) => packet.degraded).length
    },
    reviewerPackets,
    traceability
  };
}
`);
}

function deterministicCode() {
  return normalizeMultilineCode(`
function main({ reviewContext, governanceSnapshot, aiReviewResult }) {
  function unique(list) { return Array.from(new Set((list || []).filter(Boolean))); }
  function severity(value) {
    const normalized = String(value || 'low').toLowerCase();
    return ['high', 'medium', 'low', 'info'].includes(normalized) ? normalized : 'low';
  }
  const normativeCodePattern = /(?:(?:GB|GB\/T|GBJ|DL\/T|DL|Q\/CSG|Q\/GDW|Q\/SH|Q\/BGJ|JGJ|NB\/T|NB|AQ|DB|DBJ|DGJ|YD\/T|SL|GA|CECS|TSG|HG|CJJ|SH\/T|YB|JB|CJ|YS|SY|HJ|TB|LB|MZ)\s*[-/A-Z]*\s*\d{2,}(?:\.\d+)?(?:[-—]\d{2,4})?)/i;
  const versionYearPattern = /[-—]\d{4}(?:\b|$)/;
  function makePacket(reviewerId, findings, overall, degraded, error, modules) {
    return {
      review_id: reviewContext.reviewId,
      engine: 'hermes',
      findings,
      overall_assessment: overall,
      degraded: Boolean(degraded),
      error: degraded ? (error || (reviewerId + ' 审查组件降级，未返回有效结果')) : '',
      metadata: {
        template_id: reviewerId,
        agent_id: reviewerId,
        review_modules: unique(modules || [])
      }
    };
  }
  const packets = [];
  const visibility = reviewContext.parseResult && reviewContext.parseResult.visibility;
  const enabledModules = reviewContext.enabledModules || [];
  if (enabledModules.includes('evidence_validation') && visibility && visibility.manualReviewNeeded) {
    packets.push(makePacket('visibility_gap_reviewer', [{
      id: 'H-VIS-001',
      title: '附件及图纸解析受限，请结合原件复核',
      severity: 'medium',
      category: 'evidence_validation',
      summary: visibility.manualReviewReason || '正文引用了附件或图纸，但当前可视域无法稳定获取其实质内容。',
      suggestion: '请补充附件原件或结合原件人工复核。',
      evidence_status: 'visibility_gap',
      source_engine: 'hermes',
      finding_type: 'visibility_gap',
      manual_review_needed: true,
      raw_data: { module_name: 'evidence_validation', review_modules: ['evidence_validation'] }
    }], '可视域检查已完成。', false, '', ['evidence_validation']));
  }
  if (enabledModules.includes('legality_compliance')) {
    const findings = (reviewContext.candidates || []).filter((candidate) => String(candidate.candidateId || '').includes('legality') || String(candidate.title || '').includes('合法') || String(candidate.title || '').includes('合规'))
      .slice(0, 3)
      .map((candidate, index) => ({
        id: 'H-POL-' + String(index + 1).padStart(3, '0'),
        title: candidate.title || '规范符合性提示',
        severity: severity(candidate.severityHint || 'low'),
        category: 'legality_compliance',
        summary: (candidate.ruleHits || []).map((hit) => hit.rationale).filter(Boolean).join('；') || '已命中规范符合性线索，请结合正式依据复核。',
        suggestion: '请结合正式依据和原文段落补充合规性说明。',
        evidence_status: candidate.evidenceMissing ? 'evidence_gap' : 'grounded',
        source_engine: 'hermes',
        finding_type: 'engineering_inference',
        raw_data: { module_name: 'legality_compliance', review_modules: ['legality_compliance'] }
      }));
    packets.push(makePacket('policy_compliance_reviewer', findings, findings.length ? '规范命中与合规线索已整理。' : '未发现需要单列的规范符合性问题。', false, '', ['legality_compliance']));
  }
  if (enabledModules.includes('evidence_validation')) {
    const refs = (((reviewContext.facts || {}).normative_refs) || []).slice(0, 12);
    const checks = refs.map((title) => {
      const codeMatch = String(title).match(normativeCodePattern);
      const precise = Boolean(codeMatch && versionYearPattern.test(codeMatch[0]));
      if (!precise) {
        return {
          sourceId: title,
          title,
          status: 'unknown',
          resolvedBy: 'heuristic',
          summary: '标准号缺少年份或分册锚点，不能直接判定为现行有效。',
          resolvedTitle: '',
          note: '裸标准号不得直接判定 current。'
        };
      }
      return {
        sourceId: title,
        title,
        status: 'current',
        resolvedBy: 'heuristic',
        summary: '当前仅根据标准标题与年份锚点作保守确认，仍建议人工复核。',
        resolvedTitle: title,
        note: '已匹配到带年份版本锚点的标准标题。'
      };
    });
    packets.push(makePacket('normative_validity_reviewer', checks.length ? [{
      id: 'H-NORM-001',
      title: '编制依据现行有效性核验',
      severity: checks.some((item) => item.status === 'unknown') ? 'medium' : 'info',
      category: 'evidence_validation',
      summary: checks.some((item) => item.status === 'unknown') ? '存在待人工核验的标准编号或版本锚点。' : '当前标准标题均带有版本锚点。',
      suggestion: '请对 unknown 项结合权威来源补充核验。',
      evidence_status: checks.some((item) => item.status === 'unknown') ? 'evidence_gap' : 'grounded',
      source_engine: 'hermes',
      finding_type: 'engineering_inference',
      raw_data: {
        module_name: 'evidence_validation',
        review_modules: ['evidence_validation'],
        normativeValidityChecks: checks
      }
    }] : [], checks.length ? '规范有效性核验已完成。' : '未识别到需核验的标准规范。', false, '', ['evidence_validation']));
    const aiCalcPacket = Array.isArray(aiReviewResult && aiReviewResult.reviewerPackets)
      ? aiReviewResult.reviewerPackets.find((packet) => packet && packet.metadata && packet.metadata.agent_id === 'calculation_review_reviewer')
      : null;
    if (!aiCalcPacket || !Array.isArray(aiCalcPacket.findings) || aiCalcPacket.findings.length === 0) {
      packets.push(makePacket('calculation_review_reviewer', [{
        id: 'H-CALC-FALLBACK-001',
        title: '未见计算书或验算过程，需人工补充复核',
        severity: 'info',
        category: 'evidence_validation',
        summary: '当前材料未稳定呈现计算书、验算过程或参数取值依据，系统按保守策略输出提示。',
        suggestion: '请补充计算书、验算过程或关键参数来源后再复核。',
        evidence_status: 'evidence_gap',
        source_engine: 'hermes',
        finding_type: 'suggestion_enhancement',
        raw_data: { module_name: 'evidence_validation', review_modules: ['evidence_validation'], fallback: true }
      }], '计算核验 reviewer 未形成有效结果，已注入保守型 fallback。', false, '', ['evidence_validation']));
    }
  }
  return {
    deterministicReviewResult: {
      reviewerPackets: packets,
      degradedCount: packets.filter((packet) => packet.degraded).length
    },
    reviewerPackets: packets
  };
}
`);
}

function support008Code() {
  return normalizeMultilineCode(`
function main({ reviewContext }) {
  function severity(value) {
    const normalized = String(value || 'low').toLowerCase();
    return ['high', 'medium', 'low', 'info'].includes(normalized) ? normalized : 'low';
  }
  const findings = (reviewContext.candidates || []).map((candidate, index) => ({
    id: 'S-' + String(index + 1).padStart(3, '0'),
    title: candidate.title,
    severity: severity(candidate.severityHint),
    category: String(candidate.candidateId || '').split('-candidate-')[0] || 'support_material',
    summary: (candidate.ruleHits || []).map((hit) => hit.rationale).filter(Boolean).join('；') || '已命中治理快照中的审查线索。',
    suggestion: candidate.manualReviewNeeded ? '请结合原件人工补充复核。' : '请结合正式审查结论闭环处置。',
    evidence_status: candidate.manualReviewNeeded ? 'visibility_gap' : (candidate.evidenceMissing ? 'evidence_gap' : 'grounded'),
    source_engine: '008',
    finding_type: candidate.findingType || 'engineering_inference',
    raw_data: {
      candidateId: candidate.candidateId,
      review_modules: [String(candidate.candidateId || '').split('-candidate-')[0]],
      module_name: String(candidate.candidateId || '').split('-candidate-')[0]
    }
  }));
  const reportMarkdown = ['# 008 支撑层结果', '', ...(findings.length ? findings.map((item) => '- [' + item.severity + '] ' + item.title + '：' + item.summary) : ['- 未识别到需输出的问题'])].join('\n');
  const supportPacket008 = {
    review_id: reviewContext.reviewId,
    engine: '008',
    findings,
    overall_assessment: findings.length ? '008 支撑层已形成结构化问题线索。' : '008 支撑层未识别到需输出的问题。',
    degraded: false,
    error: '',
    metadata: {
      template_id: 'structured_review_primary_worker',
      agent_id: 'structured_review_primary_worker',
      review_modules: ['support_material']
    }
  };
  return {
    supportReviewResult: {
      supportResult008: {
        summary: { issueCount: findings.length, documentType: reviewContext.documentType },
        issues: findings,
        reportMarkdown,
        ownership: 'support_material'
      },
      supportPacket008,
      artifactIndex: [],
      supportLayerContext: {
        reportMarkdown,
        issueCount: findings.length,
        governedDatasetScope: reviewContext.governedDatasetScope
      }
    },
    supportResult008: {
      summary: { issueCount: findings.length, documentType: reviewContext.documentType },
      issues: findings,
      reportMarkdown,
      ownership: 'support_material'
    },
    supportPacket008,
    artifactIndex: [],
    supportLayerContext: {
      reportMarkdown,
      issueCount: findings.length,
      governedDatasetScope: reviewContext.governedDatasetScope
    }
  };
}
`);
}

function finalAssemblerCode(docTypeLabels, moduleTitles) {
  return normalizeMultilineCode(`
function main({ reviewContext, aiReviewResult, deterministicReviewResult, supportReviewResult }) {
  const DOC_LABELS = ${JSON.stringify(docTypeLabels)};
  const MODULE_TITLES = ${JSON.stringify(moduleTitles)};
  function severityRank(value) {
    return { high: 4, medium: 3, low: 2, info: 1 }[String(value || 'low').toLowerCase()] || 2;
  }
  function unique(list) { return Array.from(new Set((list || []).filter(Boolean))); }
  function docLabel(documentType) { return DOC_LABELS[documentType] || documentType; }
  function moduleLabel(moduleName) { return MODULE_TITLES[moduleName] || moduleName; }
  function nonEmpty(value, fallback) {
    return String(value || '').trim() || fallback;
  }
  function flatten(list) { return [].concat(...(list || []).map((item) => Array.isArray(item) ? item : [item])); }
  const aiPackets = Array.isArray(aiReviewResult && aiReviewResult.reviewerPackets) ? aiReviewResult.reviewerPackets : [];
  const deterministicPackets = Array.isArray(deterministicReviewResult && deterministicReviewResult.reviewerPackets) ? deterministicReviewResult.reviewerPackets : [];
  const reviewerPackets = aiPackets.concat(deterministicPackets);
  const hermesPackets = reviewerPackets.filter((packet) => packet && packet.engine === 'hermes');
  const enabledModules = reviewContext.enabledModules || [];
  let degradedReason = '';
  if (!hermesPackets.length) {
    degradedReason = 'Hermes 主审链路未形成任何实际审查结果。';
  } else if (hermesPackets.every((packet) => packet.degraded)) {
    degradedReason = 'Hermes 主审链路全部降级，系统按 fail-closed 返回非正式结果。';
  }
  if (!degradedReason) {
    for (const moduleName of enabledModules) {
      const actualPackets = hermesPackets.filter((packet) => Array.isArray(packet.metadata && packet.metadata.review_modules) && packet.metadata.review_modules.includes(moduleName));
      if (!actualPackets.length) {
        degradedReason = moduleLabel(moduleName) + ' 模块未形成实际审查结果，系统按 fail-closed 返回。';
        break;
      }
      if (actualPackets.every((packet) => packet.degraded)) {
        degradedReason = moduleLabel(moduleName) + ' 模块的实际运行 reviewer 全部降级，系统按 fail-closed 返回。';
        break;
      }
    }
  }
  const allFindings = reviewerPackets.flatMap((packet) => Array.isArray(packet.findings) ? packet.findings : []);
  const keyFindings = allFindings.filter((item) => severityRank(item.severity) >= 3).sort((a, b) => severityRank(b.severity) - severityRank(a.severity));
  const supplementalFindings = allFindings.filter((item) => !keyFindings.includes(item));
  const verdict = keyFindings.some((item) => String(item.severity).toLowerCase() === 'high') ? 'fail' : keyFindings.length ? 'needs_revision' : 'conditional_pass';
  const verdictLabel = { conditional_pass: '有条件通过', needs_revision: '需要修改', fail: '不通过' }[verdict];
  const topRisks = unique(keyFindings.slice(0, 5).map((item) => item.title));
  const traceability = flatten([
    Array.isArray(aiReviewResult && aiReviewResult.traceability) ? aiReviewResult.traceability : [],
    allFindings.map((finding) => ({
      findingId: finding.id,
      title: finding.title,
      moduleName: finding.raw_data && finding.raw_data.module_name,
      basisIds: ((reviewContext.resolvedBasisProfile || {}).basis_documents || []).map((item) => item.basis_id),
      evidenceRefs: ((reviewContext.governedDatasetScope || {}).basisFileRefs || []).slice(0, 5)
    }))
  ]);
  const title = docLabel(reviewContext.documentType) + '正式审查报告';
  const summary = '本次审查已由专业主审组件裁决完成，总体评级结论为：**' + verdictLabel + '**。';
  const finalReportPacket = degradedReason ? null : {
    title,
    verdict,
    summary,
    top_risks: topRisks,
    key_findings: keyFindings,
    supplemental_findings: supplementalFindings,
    traceability,
    report_markdown: '',
    metadata: {
      reviewId: reviewContext.reviewId,
      documentType: reviewContext.documentType,
      enabledModules,
      basisProfileId: reviewContext.resolvedBasisProfile && reviewContext.resolvedBasisProfile.profile_id
    }
  };
  let finalReportMarkdown = '';
  let reportHtml = '';
  let reportPrintCss = '';
  let finalReportViewModel = {};
  let finalAnswer = '';
  if (degradedReason) {
    finalAnswer = [
      '# ' + docLabel(reviewContext.documentType) + ' — 预检结果与支撑层数据（非正式审查报告）',
      '',
      '> 审查主控链路未能形成正式裁决，系统已按 fail-closed 返回降级结果。原因：' + nonEmpty(degradedReason, 'Hermes 审查组件降级，未返回有效结果'),
      '',
      '本结果仅供人工复核，不构成正式审查结论。'
    ].join('\n');
  } else {
    finalReportMarkdown = [
      '# ' + title,
      '',
      summary,
      '',
      '## 重点风险',
      ...(topRisks.length ? topRisks.map((item) => '- ' + item) : ['- 未识别到需要单列的高风险事项']),
      '',
      '## 关键问题',
      ...(keyFindings.length ? keyFindings.map((item) => '- [' + item.severity + '] ' + item.title + '：' + item.summary) : ['- 无']),
      '',
      '## 补充问题',
      ...(supplementalFindings.length ? supplementalFindings.slice(0, 10).map((item) => '- [' + item.severity + '] ' + item.title + '：' + item.summary) : ['- 无'])
    ].join('\n');
    reportPrintCss = ['body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; color: #111827; line-height: 1.7; }', '.structured-report__section { margin-bottom: 24px; }', '.structured-report__muted { color: #6b7280; font-size: 12px; }', '.structured-report__table-wrap { overflow-x: auto; overscroll-behavior-x: contain; }', '@media print { .structured-report__table-wrap { overflow: visible; } }'].join('\n');
    reportHtml = '<html><head><meta charset="utf-8" /><style>' + reportPrintCss + '</style></head><body>' +
      '<h1>' + title + '</h1>' +
      '<p>' + summary + '</p>' +
      '<div class="structured-report__section"><h2>重点风险</h2><ul>' + (topRisks.length ? topRisks.map((item) => '<li>' + item + '</li>').join('') : '<li>未识别到需要单列的高风险事项</li>') + '</ul></div>' +
      '<div class="structured-report__section"><h2>关键问题</h2><ul>' + (keyFindings.length ? keyFindings.map((item) => '<li>[' + item.severity + '] ' + item.title + '：' + item.summary + '</li>').join('') : '<li>无</li>') + '</ul></div>' +
      '</body></html>';
    finalReportViewModel = {
      reviewId: reviewContext.reviewId,
      title,
      verdict,
      verdictLabel,
      executiveSummary: summary,
      executiveSummaryView: {
        verdictLabel,
        metrics: {
          enabledModuleCount: enabledModules.length,
          findingCount: allFindings.length,
          keyFindingCount: keyFindings.length
        }
      },
      sections: enabledModules.map((moduleName) => ({
        moduleName,
        title: moduleLabel(moduleName),
        findings: allFindings.filter((item) => item.raw_data && item.raw_data.module_name === moduleName)
      })),
      normativeValidityChecks: allFindings.flatMap((item) => item.raw_data && Array.isArray(item.raw_data.normativeValidityChecks) ? item.raw_data.normativeValidityChecks : [])
    };
    finalAnswer = finalReportMarkdown;
    finalReportPacket.report_markdown = finalReportMarkdown;
  }
  return {
    degraded: Boolean(degradedReason),
    degradedReason: nonEmpty(degradedReason, 'Hermes 审查组件降级，未返回有效结果'),
    finalReportPacket,
    finalReportMarkdown,
    reportHtml,
    reportPrintCss,
    finalReportViewModel,
    traceability,
    finalAnswer,
    artifactLinks: {
      html: '',
      markdown: '',
      json: ''
    }
  };
}
`);
}

function reviewContextWorkflow(governanceSnapshot, datasetManifest) {
  const inputKeys = [
    ['reviewId', '审查任务 ID', 'string'],
    ['query', '审查指令', 'string'],
    ['documentType', '文档类型', 'string'],
    ['disciplineTags', '专业标签', 'arrayString'],
    ['enabledModules', '启用模块', 'arrayString'],
    ['disabledModules', '禁用模块', 'arrayString'],
    ['focusRequirements', '关注点', 'arrayString'],
    ['strictMode', '严格模式', 'boolean'],
    ['targetFileUrls', '目标文件 URL', 'arrayString'],
    ['basisFileUrls', '依据文件 URL', 'arrayString'],
    ['contextFileUrls', '补充上下文 URL', 'arrayString']
  ];
  const nodes = [
    pluginConfigNode(pos(0, 0)),
    pluginInputNode(
      inputKeys.map(([key, label, valueType]) => inputRef(key, label, valueType, undefined, label)),
      inputKeys.map(([key, label, valueType]) => outputHidden(key, valueType, label)),
      pos(420, 0)
    ),
    readFilesNode({ nodeId: 'readTargetFiles', position: pos(820, -180), fileSource: ['pluginInput', 'targetFileUrls'] }),
    codeNode({
      nodeId: 'buildReviewContext',
      name: '构建审查上下文',
      intro: '解析文档、治理快照与数据集清单。',
      position: pos(1260, 0),
      code: reviewContextCode(),
      inputs: [
        inputRef('reviewId', 'reviewId', 'string', ['pluginInput', 'reviewId']),
        inputRef('query', 'query', 'string', ['pluginInput', 'query']),
        inputRef('documentType', 'documentType', 'string', ['pluginInput', 'documentType']),
        inputRef('disciplineTags', 'disciplineTags', 'arrayString', ['pluginInput', 'disciplineTags']),
        inputRef('enabledModules', 'enabledModules', 'arrayString', ['pluginInput', 'enabledModules']),
        inputRef('disabledModules', 'disabledModules', 'arrayString', ['pluginInput', 'disabledModules']),
        inputRef('focusRequirements', 'focusRequirements', 'arrayString', ['pluginInput', 'focusRequirements']),
        inputRef('strictMode', 'strictMode', 'boolean', ['pluginInput', 'strictMode']),
        inputRef('targetFileUrls', 'targetFileUrls', 'arrayString', ['pluginInput', 'targetFileUrls']),
        inputRef('basisFileUrls', 'basisFileUrls', 'arrayString', ['pluginInput', 'basisFileUrls']),
        inputRef('contextFileUrls', 'contextFileUrls', 'arrayString', ['pluginInput', 'contextFileUrls']),
        inputRef('documentText', 'documentText', 'string', ['readTargetFiles', 'system_text']),
        inputHidden('governanceSnapshot', 'object', governanceSnapshot),
        inputHidden('datasetManifest', 'object', datasetManifest)
      ],
      outputs: [
        outputDynamic('reviewContext', 'object'),
        outputDynamic('parseResult', 'object'),
        outputDynamic('docTextPreview', 'string'),
        outputDynamic('facts', 'object'),
        outputDynamic('ruleHits', 'arrayObject'),
        outputDynamic('candidates', 'arrayObject'),
        outputDynamic('resolvedProfile', 'object'),
        outputDynamic('resolvedBasisProfile', 'object'),
        outputDynamic('governedDatasetScope', 'object'),
        outputDynamic('supportPacketBase', 'object')
      ]
    }),
    pluginOutputNode([
      pluginOutputRef('reviewContext', 'reviewContext', 'object', ['buildReviewContext', 'reviewContext']),
      pluginOutputRef('parseResult', 'parseResult', 'object', ['buildReviewContext', 'parseResult']),
      pluginOutputRef('docTextPreview', 'docTextPreview', 'string', ['buildReviewContext', 'docTextPreview']),
      pluginOutputRef('facts', 'facts', 'object', ['buildReviewContext', 'facts']),
      pluginOutputRef('ruleHits', 'ruleHits', 'arrayObject', ['buildReviewContext', 'ruleHits']),
      pluginOutputRef('candidates', 'candidates', 'arrayObject', ['buildReviewContext', 'candidates']),
      pluginOutputRef('resolvedProfile', 'resolvedProfile', 'object', ['buildReviewContext', 'resolvedProfile']),
      pluginOutputRef('resolvedBasisProfile', 'resolvedBasisProfile', 'object', ['buildReviewContext', 'resolvedBasisProfile']),
      pluginOutputRef('governedDatasetScope', 'governedDatasetScope', 'object', ['buildReviewContext', 'governedDatasetScope']),
      pluginOutputRef('supportPacketBase', 'supportPacketBase', 'object', ['buildReviewContext', 'supportPacketBase'])
    ], pos(1740, 0))
  ];
  const edges = [
    makeEdge('pluginInput', 'readTargetFiles'),
    makeEdge('readTargetFiles', 'buildReviewContext'),
    makeEdge('buildReviewContext', 'pluginOutput')
  ];
  return { nodes, edges, chatConfig: {} };
}

function aiReviewWorkflow(governanceSnapshot) {
  const inputKeys = [
    ['reviewContext', '审查上下文', 'object'],
    ['reviewId', '审查任务 ID', 'string'],
    ['documentType', '文档类型', 'string'],
    ['enabledModules', '启用模块', 'arrayString'],
    ['targetFileUrls', '目标文件 URL', 'arrayString']
  ];
  const nodes = [
    pluginConfigNode(pos(0, 0)),
    pluginInputNode(
      inputKeys.map(([key, label, valueType]) => inputRef(key, label, valueType, undefined, label)),
      inputKeys.map(([key, label, valueType]) => outputHidden(key, valueType, label)),
      pos(420, 0)
    ),
    codeNode({
      nodeId: 'prepareAiReview',
      name: '选择 AI reviewer',
      intro: '根据模块绑定、文档类型与模板元数据确定实际运行 reviewer。',
      position: pos(900, 0),
      code: aiReviewPrepareCode(),
      inputs: [
        inputRef('reviewContext', 'reviewContext', 'object', ['pluginInput', 'reviewContext']),
        inputHidden('governanceSnapshot', 'object', governanceSnapshot),
        inputVar('aiModel', 'aiModel', 'string', AI_MODEL_PLACEHOLDER, 'FastGPT 模型占位符')
      ],
      outputs: [
        outputDynamic('selectedAiTemplates', 'arrayObject'),
        outputDynamic('selectedReviewerIds', 'arrayString'),
        outputDynamic('aiPrompt', 'string'),
        outputDynamic('aiModel', 'string')
      ]
    }),
    chatNode({
      nodeId: 'runAiReview',
      name: '执行 AI 主审',
      intro: '统一执行结构化 AI 审查并返回 reviewer 分包。',
      position: pos(1380, 0),
      modelValue: AI_MODEL_PLACEHOLDER,
      systemPrompt: '你是 Hermes 结构化审查主审执行器。必须严格输出 JSON，不得输出解释、代码块外文字或额外说明。',
      userChatInputRef: ['prepareAiReview', 'aiPrompt']
    }),
    codeNode({
      nodeId: 'normalizeAiReview',
      name: '归一化 AI 结果',
      intro: '将 AI 输出转换为 reviewerPackets，并对缺失 reviewer 执行 degrade。',
      position: pos(1860, 0),
      code: aiReviewNormalizeCode(),
      inputs: [
        inputRef('reviewContext', 'reviewContext', 'object', ['pluginInput', 'reviewContext']),
        inputHidden('governanceSnapshot', 'object', governanceSnapshot),
        inputRef('selectedAiTemplates', 'selectedAiTemplates', 'arrayObject', ['prepareAiReview', 'selectedAiTemplates']),
        inputRef('aiAnswerText', 'aiAnswerText', 'string', ['runAiReview', 'answerText'])
      ],
      outputs: [
        outputDynamic('aiReviewResult', 'object'),
        outputDynamic('reviewerPackets', 'arrayObject'),
        outputDynamic('traceability', 'arrayObject')
      ]
    }),
    pluginOutputNode([
      pluginOutputRef('aiReviewResult', 'aiReviewResult', 'object', ['normalizeAiReview', 'aiReviewResult']),
      pluginOutputRef('reviewerPackets', 'reviewerPackets', 'arrayObject', ['normalizeAiReview', 'reviewerPackets']),
      pluginOutputRef('traceability', 'traceability', 'arrayObject', ['normalizeAiReview', 'traceability'])
    ], pos(2320, 0))
  ];
  const edges = [
    makeEdge('pluginInput', 'prepareAiReview'),
    makeEdge('prepareAiReview', 'runAiReview'),
    makeEdge('runAiReview', 'normalizeAiReview'),
    makeEdge('normalizeAiReview', 'pluginOutput')
  ];
  return { nodes, edges, chatConfig: {} };
}

function deterministicWorkflow(governanceSnapshot) {
  const inputKeys = [
    ['reviewContext', '审查上下文', 'object'],
    ['aiReviewResult', 'AI 主审结果', 'object']
  ];
  const nodes = [
    pluginConfigNode(pos(0, 0)),
    pluginInputNode(
      inputKeys.map(([key, label, valueType]) => inputRef(key, label, valueType, undefined, label)),
      inputKeys.map(([key, label, valueType]) => outputHidden(key, valueType, label)),
      pos(420, 0)
    ),
    codeNode({
      nodeId: 'runDeterministicReview',
      name: '执行确定性审查',
      intro: '执行 visibility / policy / normative validity / calc fallback。',
      position: pos(980, 0),
      code: deterministicCode(),
      inputs: [
        inputRef('reviewContext', 'reviewContext', 'object', ['pluginInput', 'reviewContext']),
        inputHidden('governanceSnapshot', 'object', governanceSnapshot),
        inputRef('aiReviewResult', 'aiReviewResult', 'object', ['pluginInput', 'aiReviewResult'])
      ],
      outputs: [
        outputDynamic('deterministicReviewResult', 'object'),
        outputDynamic('reviewerPackets', 'arrayObject')
      ]
    }),
    pluginOutputNode([
      pluginOutputRef('deterministicReviewResult', 'deterministicReviewResult', 'object', ['runDeterministicReview', 'deterministicReviewResult']),
      pluginOutputRef('reviewerPackets', 'reviewerPackets', 'arrayObject', ['runDeterministicReview', 'reviewerPackets'])
    ], pos(1480, 0))
  ];
  const edges = [makeEdge('pluginInput', 'runDeterministicReview'), makeEdge('runDeterministicReview', 'pluginOutput')];
  return { nodes, edges, chatConfig: {} };
}

function supportWorkflow() {
  const nodes = [
    pluginConfigNode(pos(0, 0)),
    pluginInputNode(
      [inputRef('reviewContext', '审查上下文', 'object', undefined, '审查上下文')],
      [outputHidden('reviewContext', 'object', '审查上下文')],
      pos(420, 0)
    ),
    codeNode({
      nodeId: 'buildSupport008',
      name: '整理 008 支撑层结果',
      intro: '输出 supportResult008、supportPacket008 与支撑层上下文。',
      position: pos(980, 0),
      code: support008Code(),
      inputs: [inputRef('reviewContext', 'reviewContext', 'object', ['pluginInput', 'reviewContext'])],
      outputs: [
        outputDynamic('supportReviewResult', 'object'),
        outputDynamic('supportResult008', 'object'),
        outputDynamic('supportPacket008', 'object'),
        outputDynamic('artifactIndex', 'arrayObject'),
        outputDynamic('supportLayerContext', 'object')
      ]
    }),
    pluginOutputNode([
      pluginOutputRef('supportReviewResult', 'supportReviewResult', 'object', ['buildSupport008', 'supportReviewResult']),
      pluginOutputRef('supportResult008', 'supportResult008', 'object', ['buildSupport008', 'supportResult008']),
      pluginOutputRef('supportPacket008', 'supportPacket008', 'object', ['buildSupport008', 'supportPacket008']),
      pluginOutputRef('artifactIndex', 'artifactIndex', 'arrayObject', ['buildSupport008', 'artifactIndex']),
      pluginOutputRef('supportLayerContext', 'supportLayerContext', 'object', ['buildSupport008', 'supportLayerContext'])
    ], pos(1480, 0))
  ];
  const edges = [makeEdge('pluginInput', 'buildSupport008'), makeEdge('buildSupport008', 'pluginOutput')];
  return { nodes, edges, chatConfig: {} };
}

function finalAssemblerWorkflow(docTypeLabels, moduleTitles) {
  const inputKeys = [
    ['reviewContext', '审查上下文', 'object'],
    ['aiReviewResult', 'AI 主审结果', 'object'],
    ['deterministicReviewResult', '确定性审查结果', 'object'],
    ['supportReviewResult', '008 支撑层结果', 'object']
  ];
  const nodes = [
    pluginConfigNode(pos(0, 0)),
    pluginInputNode(
      inputKeys.map(([key, label, valueType]) => inputRef(key, label, valueType, undefined, label)),
      inputKeys.map(([key, label, valueType]) => outputHidden(key, valueType, label)),
      pos(420, 0)
    ),
    codeNode({
      nodeId: 'assembleFinalDecision',
      name: '组装最终结论',
      intro: '执行 fail-closed、模块门禁、最终评级与报告渲染。',
      position: pos(980, 0),
      code: finalAssemblerCode(docTypeLabels, moduleTitles),
      inputs: [
        inputRef('reviewContext', 'reviewContext', 'object', ['pluginInput', 'reviewContext']),
        inputRef('aiReviewResult', 'aiReviewResult', 'object', ['pluginInput', 'aiReviewResult']),
        inputRef('deterministicReviewResult', 'deterministicReviewResult', 'object', ['pluginInput', 'deterministicReviewResult']),
        inputRef('supportReviewResult', 'supportReviewResult', 'object', ['pluginInput', 'supportReviewResult'])
      ],
      outputs: [
        outputDynamic('degraded', 'boolean'),
        outputDynamic('degradedReason', 'string'),
        outputDynamic('finalReportPacket', 'object'),
        outputDynamic('finalReportMarkdown', 'string'),
        outputDynamic('reportHtml', 'string'),
        outputDynamic('reportPrintCss', 'string'),
        outputDynamic('finalReportViewModel', 'object'),
        outputDynamic('traceability', 'arrayObject'),
        outputDynamic('finalAnswer', 'string'),
        outputDynamic('artifactLinks', 'object')
      ]
    }),
    pluginOutputNode([
      pluginOutputRef('degraded', 'degraded', 'boolean', ['assembleFinalDecision', 'degraded']),
      pluginOutputRef('degradedReason', 'degradedReason', 'string', ['assembleFinalDecision', 'degradedReason']),
      pluginOutputRef('finalReportPacket', 'finalReportPacket', 'object', ['assembleFinalDecision', 'finalReportPacket']),
      pluginOutputRef('finalReportMarkdown', 'finalReportMarkdown', 'string', ['assembleFinalDecision', 'finalReportMarkdown']),
      pluginOutputRef('reportHtml', 'reportHtml', 'string', ['assembleFinalDecision', 'reportHtml']),
      pluginOutputRef('reportPrintCss', 'reportPrintCss', 'string', ['assembleFinalDecision', 'reportPrintCss']),
      pluginOutputRef('finalReportViewModel', 'finalReportViewModel', 'object', ['assembleFinalDecision', 'finalReportViewModel']),
      pluginOutputRef('traceability', 'traceability', 'arrayObject', ['assembleFinalDecision', 'traceability']),
      pluginOutputRef('finalAnswer', 'finalAnswer', 'string', ['assembleFinalDecision', 'finalAnswer']),
      pluginOutputRef('artifactLinks', 'artifactLinks', 'object', ['assembleFinalDecision', 'artifactLinks'])
    ], pos(1500, 0))
  ];
  const edges = [makeEdge('pluginInput', 'assembleFinalDecision'), makeEdge('assembleFinalDecision', 'pluginOutput')];
  return { nodes, edges, chatConfig: {} };
}

function mainWorkflow(docTypeLabels) {
  const nodes = [
    userGuideNode(pos(-320, -180)),
    workflowStartNode(pos(0, 0)),
    codeNode({
      nodeId: 'normalizeInput',
      name: '归一化输入',
      intro: '固定主工作流输入协议，并显式生成 targetFileUrls。',
      position: pos(420, 0),
      code: mainNormalizeCode(docTypeLabels),
      inputs: [
        inputRef('userChatInput', 'userChatInput', 'string', ['workflowStart', 'userChatInput']),
        inputRef('userFiles', 'userFiles', 'arrayString', ['workflowStart', 'userFiles']),
        inputVar('documentTypeRaw', 'documentTypeRaw', 'string', '{{$VARIABLE_NODE_ID.documentType$}}', '文档类型'),
        inputVar('disciplineTagsRaw', 'disciplineTagsRaw', 'string', '{{$VARIABLE_NODE_ID.disciplineTags$}}', '专业标签'),
        inputVar('enabledModulesRaw', 'enabledModulesRaw', 'string', '{{$VARIABLE_NODE_ID.enabledModules$}}', '启用模块'),
        inputVar('disabledModulesRaw', 'disabledModulesRaw', 'string', '{{$VARIABLE_NODE_ID.disabledModules$}}', '禁用模块'),
        inputVar('focusRequirementsRaw', 'focusRequirementsRaw', 'string', '{{$VARIABLE_NODE_ID.focusRequirements$}}', '关注点'),
        inputVar('strictModeRaw', 'strictModeRaw', 'string', '{{$VARIABLE_NODE_ID.strictMode$}}', '严格模式')
      ],
      outputs: [
        outputDynamic('reviewId', 'string'),
        outputDynamic('query', 'string'),
        outputDynamic('documentType', 'string'),
        outputDynamic('documentTypeLabel', 'string'),
        outputDynamic('disciplineTags', 'arrayString'),
        outputDynamic('enabledModules', 'arrayString'),
        outputDynamic('disabledModules', 'arrayString'),
        outputDynamic('focusRequirements', 'arrayString'),
        outputDynamic('strictMode', 'boolean'),
        outputDynamic('targetFileUrls', 'arrayString'),
        outputDynamic('basisFileUrls', 'arrayString'),
        outputDynamic('contextFileUrls', 'arrayString')
      ]
    }),
    pluginModuleNode({
      nodeId: 'callReviewContextWft',
      name: '调用 hermes_review_context_wft',
      intro: '解析文档与治理快照。',
      position: pos(900, 0),
      pluginId: TOOL_DEFS[0].placeholder,
      inputs: [
        inputRef('reviewId', 'reviewId', 'string', ['normalizeInput', 'reviewId']),
        inputRef('query', 'query', 'string', ['normalizeInput', 'query']),
        inputRef('documentType', 'documentType', 'string', ['normalizeInput', 'documentType']),
        inputRef('disciplineTags', 'disciplineTags', 'arrayString', ['normalizeInput', 'disciplineTags']),
        inputRef('enabledModules', 'enabledModules', 'arrayString', ['normalizeInput', 'enabledModules']),
        inputRef('disabledModules', 'disabledModules', 'arrayString', ['normalizeInput', 'disabledModules']),
        inputRef('focusRequirements', 'focusRequirements', 'arrayString', ['normalizeInput', 'focusRequirements']),
        inputRef('strictMode', 'strictMode', 'boolean', ['normalizeInput', 'strictMode']),
        inputRef('targetFileUrls', 'targetFileUrls', 'arrayString', ['normalizeInput', 'targetFileUrls']),
        inputRef('basisFileUrls', 'basisFileUrls', 'arrayString', ['normalizeInput', 'basisFileUrls']),
        inputRef('contextFileUrls', 'contextFileUrls', 'arrayString', ['normalizeInput', 'contextFileUrls'])
      ],
      outputs: [
        outputDynamic('reviewContext', 'object'),
        outputDynamic('parseResult', 'object'),
        outputDynamic('docTextPreview', 'string'),
        outputDynamic('facts', 'object'),
        outputDynamic('ruleHits', 'arrayObject'),
        outputDynamic('candidates', 'arrayObject'),
        outputDynamic('resolvedProfile', 'object'),
        outputDynamic('resolvedBasisProfile', 'object'),
        outputDynamic('governedDatasetScope', 'object'),
        outputDynamic('supportPacketBase', 'object')
      ]
    }),
    pluginModuleNode({
      nodeId: 'callAiReviewWft',
      name: '调用 hermes_ai_review_wft',
      intro: '执行 AI 主审 reviewer。',
      position: pos(1380, 0),
      pluginId: TOOL_DEFS[1].placeholder,
      inputs: [
        inputRef('reviewContext', 'reviewContext', 'object', ['callReviewContextWft', 'reviewContext']),
        inputRef('reviewId', 'reviewId', 'string', ['normalizeInput', 'reviewId']),
        inputRef('documentType', 'documentType', 'string', ['normalizeInput', 'documentType']),
        inputRef('enabledModules', 'enabledModules', 'arrayString', ['normalizeInput', 'enabledModules']),
        inputRef('targetFileUrls', 'targetFileUrls', 'arrayString', ['normalizeInput', 'targetFileUrls'])
      ],
      outputs: [
        outputDynamic('aiReviewResult', 'object'),
        outputDynamic('reviewerPackets', 'arrayObject'),
        outputDynamic('traceability', 'arrayObject')
      ]
    }),
    pluginModuleNode({
      nodeId: 'callDeterministicWft',
      name: '调用 hermes_deterministic_review_wft',
      intro: '执行确定性审查与 calculation fallback。',
      position: pos(1860, 0),
      pluginId: TOOL_DEFS[2].placeholder,
      inputs: [
        inputRef('reviewContext', 'reviewContext', 'object', ['callReviewContextWft', 'reviewContext']),
        inputRef('aiReviewResult', 'aiReviewResult', 'object', ['callAiReviewWft', 'aiReviewResult'])
      ],
      outputs: [
        outputDynamic('deterministicReviewResult', 'object'),
        outputDynamic('reviewerPackets', 'arrayObject')
      ]
    }),
    pluginModuleNode({
      nodeId: 'callSupportWft',
      name: '调用 hermes_support_008_wft',
      intro: '整理 008 支撑层结果。',
      position: pos(2340, 0),
      pluginId: TOOL_DEFS[3].placeholder,
      inputs: [inputRef('reviewContext', 'reviewContext', 'object', ['callReviewContextWft', 'reviewContext'])],
      outputs: [
        outputDynamic('supportReviewResult', 'object'),
        outputDynamic('supportResult008', 'object'),
        outputDynamic('supportPacket008', 'object'),
        outputDynamic('artifactIndex', 'arrayObject'),
        outputDynamic('supportLayerContext', 'object')
      ]
    }),
    pluginModuleNode({
      nodeId: 'callFinalAssemblerWft',
      name: '调用 hermes_final_assembler_wft',
      intro: '执行 fail-closed 与正式/降级输出。',
      position: pos(2820, 0),
      pluginId: TOOL_DEFS[4].placeholder,
      inputs: [
        inputRef('reviewContext', 'reviewContext', 'object', ['callReviewContextWft', 'reviewContext']),
        inputRef('aiReviewResult', 'aiReviewResult', 'object', ['callAiReviewWft', 'aiReviewResult']),
        inputRef('deterministicReviewResult', 'deterministicReviewResult', 'object', ['callDeterministicWft', 'deterministicReviewResult']),
        inputRef('supportReviewResult', 'supportReviewResult', 'object', ['callSupportWft', 'supportReviewResult'])
      ],
      outputs: [
        outputDynamic('degraded', 'boolean'),
        outputDynamic('degradedReason', 'string'),
        outputDynamic('finalReportPacket', 'object'),
        outputDynamic('finalReportMarkdown', 'string'),
        outputDynamic('reportHtml', 'string'),
        outputDynamic('reportPrintCss', 'string'),
        outputDynamic('finalReportViewModel', 'object'),
        outputDynamic('traceability', 'arrayObject'),
        outputDynamic('finalAnswer', 'string'),
        outputDynamic('artifactLinks', 'object')
      ]
    }),
    ifElseNode({
      nodeId: 'routeFinalReply',
      name: '判断是否降级',
      intro: '正式报告与降级结果二选一。',
      position: pos(3300, 0),
      variableRef: ['callFinalAssemblerWft', 'degraded']
    }),
    answerNode({
      nodeId: 'formalReply',
      name: '正式报告输出',
      intro: '输出正式 Markdown 报告。',
      position: pos(3720, -150),
      textValue: ['callFinalAssemblerWft', 'finalReportMarkdown']
    }),
    answerNode({
      nodeId: 'degradedReply',
      name: '降级结果输出',
      intro: '输出 fail-closed 说明。',
      position: pos(3720, 150),
      textValue: ['callFinalAssemblerWft', 'finalAnswer']
    })
  ];
  const edges = [
    makeEdge('workflowStart', 'normalizeInput'),
    makeEdge('normalizeInput', 'callReviewContextWft'),
    makeEdge('callReviewContextWft', 'callAiReviewWft'),
    makeEdge('callAiReviewWft', 'callDeterministicWft'),
    makeEdge('callDeterministicWft', 'callSupportWft'),
    makeEdge('callSupportWft', 'callFinalAssemblerWft'),
    makeEdge('callFinalAssemblerWft', 'routeFinalReply'),
    makeEdge('routeFinalReply', 'formalReply', 'routeFinalReply-source-ELSE', 'formalReply-target-left'),
    makeEdge('routeFinalReply', 'degradedReply', 'routeFinalReply-source-IF', 'degradedReply-target-left')
  ];
  return {
    nodes,
    edges,
    chatConfig: {
      welcomeText: '上传方案文件后，我将按固定主工作流调度 Hermes 审查上下文工具、AI 审查工具、确定性审查工具、008 支撑层工具与最终组装工具。',
      variables: [
        variableEntry({ key: 'documentType', required: true }),
        variableEntry({ key: 'disciplineTags', type: 'textarea' }),
        variableEntry({ key: 'enabledModules', type: 'textarea' }),
        variableEntry({ key: 'disabledModules', type: 'textarea' }),
        variableEntry({ key: 'focusRequirements', type: 'textarea' }),
        variableEntry({ key: 'strictMode' })
      ],
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
      instruction: 'migrationMode=workflow+workflow-tools。主工作流仅做固定编排，不允许 LLM 自主跳过关键阶段；若 Hermes 主审结果不可用，必须 fail-closed。'
    }
  };
}

function toTemplateJson({ name, intro, avatar = 'core/app/templates/workflow', tags = ['review'], type = 'plugin', workflow }) {
  return { name, intro, author: 'Codex', avatar, tags, type, workflow };
}

function toCreateJson({ name, type, workflow }) {
  return { name, type, modules: workflow.nodes, edges: workflow.edges, chatConfig: workflow.chatConfig || {} };
}

function buildDatasetManifest(governanceSnapshot) {
  const basisRegistry = governanceSnapshot.basisRegistry || {};
  const profileMapping = governanceSnapshot.profileMapping || {};
  const packRegistry = governanceSnapshot.packRegistry || {};
  const packsMap = packRegistry.packs || {};
  const docTypeLabels = governanceSnapshot.docTypeLabels || {};
  const entries = Object.keys(profileMapping).map((profileId) => {
    const profile = profileMapping[profileId] || {};
    const packIds = Array.from(new Set([].concat(profile.default_pack_ids || [], profile.required_pack_ids || [], profile.enterprise_pack_ids || [])));
    const basisIds = Array.from(new Set(packIds.flatMap((packId) => (packsMap[packId] || {}).basis_ids || [])));
    const basisFiles = Array.from(new Set(basisIds.flatMap((basisId) => (basisRegistry[basisId] || {}).file_refs || [])));
    const safeKey = profileId.toUpperCase().replace(/[^A-Z0-9]+/g, '_');
    return {
      datasetKey: `basis.${profileId}`,
      datasetIdPlaceholder: `__DATASET_${safeKey}__`,
      displayName: `${docTypeLabels[profileId] || profileId} 依据数据集`,
      profileId,
      documentTypes: Object.keys(docTypeLabels).filter((key) => key === profileId),
      packIds,
      basisIds,
      basisFiles
    };
  });
  return {
    version: 1,
    generatedAt: new Date().toISOString(),
    entries
  };
}

function loadGovernance({ repoRoot }) {
  const artifactsGovernanceDir = path.join(repoRoot, 'artifacts', 'fastgpt', 'governance');
  const legacyDir = path.join(repoRoot, 'integrations', 'fastgpt', 'toolset', 'hermesStructuredReview', 'assets', 'generated');
  const snapshotFile = path.join(artifactsGovernanceDir, 'governance_snapshot.json');
  const snapshot = fs.existsSync(snapshotFile)
    ? (() => {
        const raw = readJson(snapshotFile);
        return {
          moduleBindings: raw.moduleBindings || raw.module_bindings || {},
          moduleTitles: raw.moduleTitles || raw.module_titles || {},
          docTypeLabels: raw.docTypeLabels || raw.doc_type_labels || {},
          templateManifest: raw.templateManifest || raw.template_manifest || [],
          profileMapping: raw.profileMapping || raw.profile_mapping || {},
          packRegistry: raw.packRegistry || raw.pack_registry || {},
          rulePackRegistry: raw.rulePackRegistry || raw.rule_pack_registry || {},
          basisRegistry: raw.basisRegistry || raw.basis_registry || {},
          evidenceTitles: raw.evidenceTitles || raw.evidence_titles || {},
          evidenceFindingTypes: raw.evidenceFindingTypes || raw.evidence_finding_types || {},
          evidenceManualReviewReasons:
            raw.evidenceManualReviewReasons || raw.evidence_manual_review_reasons || {}
        };
      })()
    : {
        moduleBindings: readJson(path.join(legacyDir, 'module_bindings.json')),
        moduleTitles: readJson(path.join(legacyDir, 'module_titles.json')),
        docTypeLabels: readJson(path.join(legacyDir, 'doc_type_labels.json')),
        templateManifest: readJson(path.join(legacyDir, 'template_manifest.json')),
        profileMapping: readJson(path.join(legacyDir, 'profile_mapping.json')),
        packRegistry: readJson(path.join(legacyDir, 'pack_registry.json')),
        rulePackRegistry: readJson(path.join(legacyDir, 'rule_pack_registry.json')),
        basisRegistry: readJson(path.join(legacyDir, 'basis_registry.json')),
        evidenceTitles: readJson(path.join(legacyDir, 'evidence_titles.json')),
        evidenceFindingTypes: readJson(path.join(legacyDir, 'evidence_finding_types.json')),
        evidenceManualReviewReasons: readJson(path.join(legacyDir, 'evidence_manual_review_reasons.json'))
      };
  const datasetManifestFile = path.join(artifactsGovernanceDir, 'dataset_manifest.json');
  const datasetManifest = fs.existsSync(datasetManifestFile)
    ? readJson(datasetManifestFile)
    : buildDatasetManifest(snapshot);
  return { governanceSnapshot: snapshot, datasetManifest };
}

function registryTemplate() {
  return {
    migrationMode: 'workflow+workflow-tools',
    aiModel: AI_MODEL_PLACEHOLDER,
    workflowToolIds: Object.fromEntries(TOOL_DEFS.map((tool) => [tool.key, tool.placeholder])),
    notes: [
      '先导入 5 个工作流工具，再将导入后的工具 ID 回填到 workflowToolIds。',
      '若模型 ID 不是默认占位符，请先回填 aiModel，再生成 linked 工作流。',
      '文件不会自动透传到工作流工具；主工作流已显式传递 targetFileUrls / basisFileUrls / contextFileUrls。'
    ]
  };
}

export function generateBundle({ repoRoot }) {
  const artifactsDir = path.join(repoRoot, 'artifacts', 'fastgpt');
  const workflowToolsDir = path.join(artifactsDir, 'workflow-tools');
  ensureDir(artifactsDir);
  ensureDir(workflowToolsDir);

  const { governanceSnapshot, datasetManifest } = loadGovernance({ repoRoot });
  const toolWorkflows = {
    hermes_review_context_wft: reviewContextWorkflow(governanceSnapshot, datasetManifest),
    hermes_ai_review_wft: aiReviewWorkflow(governanceSnapshot),
    hermes_deterministic_review_wft: deterministicWorkflow(governanceSnapshot),
    hermes_support_008_wft: supportWorkflow(),
    hermes_final_assembler_wft: finalAssemblerWorkflow(governanceSnapshot.docTypeLabels || {}, governanceSnapshot.moduleTitles || {})
  };

  for (const tool of TOOL_DEFS) {
    const workflow = toolWorkflows[tool.key];
    writeJson(path.join(workflowToolsDir, `${tool.key}.workflow.json`), workflow);
    writeJson(
      path.join(workflowToolsDir, `${tool.key}.template.json`),
      toTemplateJson({ name: tool.key, intro: tool.intro, type: 'plugin', workflow })
    );
    writeJson(
      path.join(workflowToolsDir, `${tool.key}.create.json`),
      toCreateJson({ name: tool.key, type: 'plugin', workflow })
    );
  }

  const main = mainWorkflow(governanceSnapshot.docTypeLabels || {});
  writeJson(path.join(artifactsDir, 'hermes-main-review.workflow.json'), main);
  writeJson(
    path.join(artifactsDir, 'hermes-main-review.create.json'),
    toCreateJson({ name: 'hermes-main-review', type: 'advanced', workflow: main })
  );
  writeJson(path.join(artifactsDir, 'workflow_tool_registry.template.json'), registryTemplate());

  return {
    artifactsDir,
    workflowToolsDir,
    toolDefs: TOOL_DEFS,
    governanceSnapshot,
    datasetManifest,
    mainWorkflowPath: path.join(artifactsDir, 'hermes-main-review.workflow.json')
  };
}
