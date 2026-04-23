import { z } from 'zod';
import { runDeterministicReviewerTool } from '../../../lib/reviewCore.js';

export const InputType = z.object({
  reviewId: z.string(),
  reviewerId: z.enum([
    'visibility_gap_reviewer',
    'policy_compliance_reviewer',
    'normative_validity_reviewer'
  ]),
  reviewContext: z.record(z.string(), z.any())
});

export const OutputType = z.object({
  packet: z.record(z.string(), z.any()),
  reviewerId: z.string()
});

export async function tool(input: z.infer<typeof InputType>): Promise<z.infer<typeof OutputType>> {
  const result = await runDeterministicReviewerTool({
    reviewId: input.reviewId,
    reviewerId: input.reviewerId,
    reviewContext: input.reviewContext as any
  });
  return {
    packet: result.packet as Record<string, unknown>,
    reviewerId: result.reviewerId
  };
}
