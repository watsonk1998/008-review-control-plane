import { defineToolSet } from '@tool/type';
import { ToolTagEnum } from '@tool/type/tags';

export default defineToolSet({
  name: {
    'zh-CN': 'Hermes 结构化审查工具集',
    en: 'Hermes Structured Review Toolset'
  },
  tags: [ToolTagEnum.enum.productivity, ToolTagEnum.enum.tools],
  description: {
    'zh-CN': '将 hermes-review-agent 的受治理结构化审查能力迁移为 FastGPT 系统工具集。',
    en: 'Governed structured-review tools migrated from hermes-review-agent for FastGPT.'
  },
  toolDescription: 'Governed structured review tools for building review context, support packets, deterministic reviewers, final decisions and report rendering.'
});
