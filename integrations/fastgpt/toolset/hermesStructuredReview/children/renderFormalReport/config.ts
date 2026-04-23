import { defineTool } from '@tool/type';
import { FlowNodeInputTypeEnum, WorkflowIOValueTypeEnum } from '@tool/type/fastgpt';

export default defineTool({
  name: {
    'zh-CN': '渲染正式报告',
    en: 'Render formal report'
  },
  description: {
    'zh-CN': '将最终裁决渲染为 Markdown / HTML / print CSS / ViewModel。',
    en: 'Render the final decision into markdown, html, print css and a view model.'
  },
  toolDescription: 'Render Hermes structured-review final output for FastGPT.',
  versionList: [
    {
      value: '0.1.1',
      description: 'Default version',
      inputs: [
        {
          key: 'documentType',
          label: '文档类型',
          valueType: WorkflowIOValueTypeEnum.string,
          renderTypeList: [FlowNodeInputTypeEnum.select, FlowNodeInputTypeEnum.reference],
          required: true
        },
        {
          key: 'finalDecision',
          label: 'finalDecision',
          valueType: WorkflowIOValueTypeEnum.object,
          renderTypeList: [FlowNodeInputTypeEnum.JSONEditor, FlowNodeInputTypeEnum.reference],
          required: true
        }
      ],
      outputs: [
        {
          key: 'finalReportMarkdown',
          label: 'Markdown',
          valueType: WorkflowIOValueTypeEnum.string
        },
        {
          key: 'reportHtml',
          label: 'HTML',
          valueType: WorkflowIOValueTypeEnum.string
        },
        {
          key: 'reportPrintCss',
          label: 'printCss',
          valueType: WorkflowIOValueTypeEnum.string
        },
        {
          key: 'finalReportViewModel',
          label: 'ViewModel',
          valueType: WorkflowIOValueTypeEnum.object
        }
      ]
    }
  ]
});
