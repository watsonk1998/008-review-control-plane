import { z } from 'zod';
import { runSupportReview008Tool } from '../../../lib/reviewCore.js';

export const InputType = z.object({
  reviewId: z.string(),
  query: z.string(),
  documentType: z.enum([
    'construction_org',
    'construction_scheme',
    'hazardous_special_scheme',
    'distribution_network_special_scheme',
    'supervision_plan',
    'review_support_material'
  ]),
  enabledModules: z.array(z.string()).optional().default([]),
  reviewContext: z.record(z.string(), z.any())
});

export const OutputType = z.object({
  supportReview: z.record(z.string(), z.any()),
  supportPacket008: z.record(z.string(), z.any())
});

export async function tool(input: z.infer<typeof InputType>): Promise<z.infer<typeof OutputType>> {
  const supportReview = await runSupportReview008Tool({
    reviewId: input.reviewId,
    query: input.query,
    documentType: input.documentType,
    enabledModules: input.enabledModules,
    reviewContext: input.reviewContext as any
  });
  return {
    supportReview: supportReview as Record<string, unknown>,
    supportPacket008: supportReview.supportPacket008 as Record<string, unknown>
  };
}
