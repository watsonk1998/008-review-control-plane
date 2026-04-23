import { defineTool } from '@tool/type';
import { FlowNodeInputTypeEnum, WorkflowIOValueTypeEnum } from '@tool/type/fastgpt';

export default defineTool({
  name: {
    'zh-CN': '构建审查上下文',
    en: 'Build review context'
  },
  description: {
    'zh-CN': '读取文档、解析正文、生成 facts/profile/basis/rule/candidate/governed support packet。',
    en: 'Parse source document and build facts/profile/basis/rule/candidate/governed support packet.'
  },
  toolDescription:
    'Build the governed Hermes structured-review context from uploaded files and workflow variables.',
  versionList: [
    {
      value: '0.1.1',
      description: 'Default version',
      inputs: [
        {
          key: 'query',
          label: '审查指令',
          valueType: WorkflowIOValueTypeEnum.string,
          renderTypeList: [FlowNodeInputTypeEnum.input, FlowNodeInputTypeEnum.reference],
          required: true
        },
        {
          key: 'documentType',
          label: '文档类型',
          valueType: WorkflowIOValueTypeEnum.string,
          renderTypeList: [FlowNodeInputTypeEnum.select, FlowNodeInputTypeEnum.reference],
          required: true
        },
        {
          key: 'disciplineTags',
          label: '专业标签',
          valueType: WorkflowIOValueTypeEnum.arrayString,
          renderTypeList: [FlowNodeInputTypeEnum.JSONEditor, FlowNodeInputTypeEnum.reference]
        },
        {
          key: 'enabledModules',
          label: '启用模块',
          valueType: WorkflowIOValueTypeEnum.arrayString,
          renderTypeList: [FlowNodeInputTypeEnum.JSONEditor, FlowNodeInputTypeEnum.reference]
        },
        {
          key: 'focusRequirements',
          label: '重点要求',
          valueType: WorkflowIOValueTypeEnum.arrayString,
          renderTypeList: [FlowNodeInputTypeEnum.JSONEditor, FlowNodeInputTypeEnum.reference]
        },
        {
          key: 'targetFiles',
          label: '目标文件',
          valueType: WorkflowIOValueTypeEnum.object,
          renderTypeList: [FlowNodeInputTypeEnum.JSONEditor, FlowNodeInputTypeEnum.reference],
          required: true
        }
      ],
      outputs: [
        {
          key: 'reviewContext',
          label: '审查上下文',
          valueType: WorkflowIOValueTypeEnum.object
        },
        {
          key: 'parseResult',
          label: '解析结果',
          valueType: WorkflowIOValueTypeEnum.object
        },
        {
          key: 'docTextPreview',
          label: '文档预览',
          valueType: WorkflowIOValueTypeEnum.string
        }
      ]
    }
  ]
});
