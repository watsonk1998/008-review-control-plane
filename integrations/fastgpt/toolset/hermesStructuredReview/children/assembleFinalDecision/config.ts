import { defineTool } from '@tool/type';
import { FlowNodeInputTypeEnum, WorkflowIOValueTypeEnum } from '@tool/type/fastgpt';

export default defineTool({
  name: {
    'zh-CN': '组装最终裁决',
    en: 'Assemble final decision'
  },
  description: {
    'zh-CN': '执行 fail-closed、模块级门禁、traceability 和 finalReportPacket 组装。',
    en: 'Apply fail-closed rules, module gate checks, traceability and final report assembly.'
  },
  toolDescription: 'Assemble the final Hermes structured-review decision packet.',
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
          key: 'supportReview',
          label: '支撑层结果',
          valueType: WorkflowIOValueTypeEnum.object,
          renderTypeList: [FlowNodeInputTypeEnum.JSONEditor, FlowNodeInputTypeEnum.reference],
          required: true
        },
        {
          key: 'reviewerPackets',
          label: 'reviewerPackets',
          valueType: WorkflowIOValueTypeEnum.object,
          renderTypeList: [FlowNodeInputTypeEnum.JSONEditor, FlowNodeInputTypeEnum.reference]
        }
      ],
      outputs: [
        {
          key: 'finalDecision',
          label: 'finalDecision',
          valueType: WorkflowIOValueTypeEnum.object
        },
        {
          key: 'finalAnswer',
          label: 'finalAnswer',
          valueType: WorkflowIOValueTypeEnum.string
        },
        {
          key: 'degraded',
          label: 'degraded',
          valueType: WorkflowIOValueTypeEnum.boolean
        }
      ]
    }
  ]
});
