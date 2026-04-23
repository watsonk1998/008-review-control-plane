import { z } from 'zod';
import { buildReviewContext } from '../../../lib/context.js';

const ReviewFileRef = z.object({
  fileName: z.string().optional(),
  fileType: z.string().optional(),
  path: z.string().optional(),
  url: z.string().optional(),
  content: z.string().optional()
});

export const InputType = z.object({
  query: z.string(),
  documentType: z.enum([
    'construction_org',
    'construction_scheme',
    'hazardous_special_scheme',
    'distribution_network_special_scheme',
    'supervision_plan',
    'review_support_material'
  ]),
  disciplineTags: z.array(z.string()).optional().default([]),
  enabledModules: z.array(z.string()).optional().default([]),
  disabledModules: z.array(z.string()).optional().default([]),
  focusRequirements: z.array(z.string()).optional().default([]),
  strictMode: z.boolean().optional().default(true),
  targetFiles: z.array(ReviewFileRef).min(1),
  basisFiles: z.array(ReviewFileRef).optional().default([]),
  contextFiles: z.array(ReviewFileRef).optional().default([])
});

export const OutputType = z.object({
  reviewContext: z.record(z.string(), z.any()),
  parseResult: z.record(z.string(), z.any()),
  docTextPreview: z.string()
});

export async function tool(input: z.infer<typeof InputType>): Promise<z.infer<typeof OutputType>> {
  const reviewContext = await buildReviewContext(input);
  return {
    reviewContext: reviewContext as Record<string, unknown>,
    parseResult: reviewContext.parseResult as Record<string, unknown>,
    docTextPreview: reviewContext.docTextPreview
  };
}
