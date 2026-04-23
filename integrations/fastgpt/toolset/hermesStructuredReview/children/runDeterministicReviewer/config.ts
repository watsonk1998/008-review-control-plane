import { defineTool } from '@tool/type';
import { FlowNodeInputTypeEnum, WorkflowIOValueTypeEnum } from '@tool/type/fastgpt';

export default defineTool({
  name: {
    'zh-CN': '运行确定性 reviewer',
    en: 'Run deterministic reviewer'
  },
  description: {
    'zh-CN': '处理 visibility_gap_reviewer / policy_compliance_reviewer / normative_validity_reviewer。',
    en: 'Run deterministic reviewers: visibility gap, policy compliance and normative validity.'
  },
  toolDescription: 'Run a deterministic governed reviewer and return its packet.',
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
          key: 'reviewerId',
          label: 'reviewerId',
          valueType: WorkflowIOValueTypeEnum.string,
          renderTypeList: [FlowNodeInputTypeEnum.select, FlowNodeInputTypeEnum.reference],
          required: true
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
          key: 'packet',
          label: 'packet',
          valueType: WorkflowIOValueTypeEnum.object
        },
        {
          key: 'reviewerId',
          label: 'reviewerId',
          valueType: WorkflowIOValueTypeEnum.string
        }
      ]
    }
  ]
});
