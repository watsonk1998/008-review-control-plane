import { z } from 'zod';
import { renderFormalReportTool } from '../../../lib/reviewCore.js';

export const InputType = z.object({
  documentType: z.enum([
    'construction_org',
    'construction_scheme',
    'hazardous_special_scheme',
    'distribution_network_special_scheme',
    'supervision_plan',
    'review_support_material'
  ]),
  finalDecision: z.record(z.string(), z.any())
});

export const OutputType = z.object({
  finalReportMarkdown: z.string(),
  reportHtml: z.string(),
  reportPrintCss: z.string(),
  finalReportViewModel: z.record(z.string(), z.any())
});

export async function tool(input: z.infer<typeof InputType>): Promise<z.infer<typeof OutputType>> {
  const rendered = renderFormalReportTool({
    documentType: input.documentType,
    finalDecision: input.finalDecision as any
  });
  return rendered;
}
