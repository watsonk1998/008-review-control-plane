import { defineTool } from '@tool/type';
import { FlowNodeInputTypeEnum, WorkflowIOValueTypeEnum } from '@tool/type/fastgpt';

export default defineTool({
  name: {
    'zh-CN': '生成 008 支撑层结果',
    en: 'Run support review 008'
  },
  description: {
    'zh-CN': '将 governed context 转为 008 支撑层结果与 supportPacket008。',
    en: 'Generate supportResult008 and supportPacket008 from governed review context.'
  },
  toolDescription: 'Generate the 008 support-layer result and support packet from review context.',
  versionList: [
    {
      value: '0.1.1',
      description: 'Default version',
      inputs: [
        {
          key: 'reviewId',
          label: '审查ID',
          valueType: WorkflowIOValueTypeEnum.string,
          renderTypeList: [FlowNodeInputTypeEnum.input, FlowNodeInputTypeEnum.reference],
          required: true
        },
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
          key: 'enabledModules',
          label: '启用模块',
          valueType: WorkflowIOValueTypeEnum.arrayString,
          renderTypeList: [FlowNodeInputTypeEnum.JSONEditor, FlowNodeInputTypeEnum.reference]
        },
        {
          key: 'reviewContext',
          label: '审查上下文',
          valueType: WorkflowIOValueTypeEnum.object,
          renderTypeList: [FlowNodeInputTypeEnum.JSONEditor, FlowNodeInputTypeEnum.reference],
          required: true
        }
      ],
      outputs: [
        {
          key: 'supportReview',
          label: '支撑层结果',
          valueType: WorkflowIOValueTypeEnum.object
        },
        {
          key: 'supportPacket008',
          label: 'supportPacket008',
          valueType: WorkflowIOValueTypeEnum.object
        }
      ]
    }
  ]
});
