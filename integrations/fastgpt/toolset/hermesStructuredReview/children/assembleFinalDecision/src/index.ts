import { z } from 'zod';
import { assembleFinalDecisionTool } from '../../../lib/reviewCore.js';

export const InputType = z.object({
  reviewId: z.string(),
  documentType: z.enum([
    'construction_org',
    'construction_scheme',
    'hazardous_special_scheme',
    'distribution_network_special_scheme',
    'supervision_plan',
    'review_support_material'
  ]),
  enabledModules: z.array(z.string()).optional().default([]),
  supportReview: z.record(z.string(), z.any()),
  reviewerPackets: z.array(z.record(z.string(), z.any())).optional().default([])
});

export const OutputType = z.object({
  finalDecision: z.record(z.string(), z.any()),
  finalAnswer: z.string(),
  degraded: z.boolean()
});

export async function tool(input: z.infer<typeof InputType>): Promise<z.infer<typeof OutputType>> {
  const finalDecision = assembleFinalDecisionTool({
    reviewId: input.reviewId,
    documentType: input.documentType,
    enabledModules: input.enabledModules,
    supportReview: input.supportReview as any,
    reviewerPackets: input.reviewerPackets as any[]
  });
  return {
    finalDecision: finalDecision as Record<string, unknown>,
    finalAnswer: finalDecision.finalAnswer,
    degraded: finalDecision.degraded
  };
}
