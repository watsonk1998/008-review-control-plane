# FastGPT integration for hermes-review-agent

This workspace contains a FastGPT-first migration bundle for `hermes-review-agent`:

- governed asset export from the Python source of truth
- a FastGPT system Toolset package source (`hermesStructuredReview`) with 5 child tools
- workflow generators (actual `tools` workflow + baseline validator-safe workflow)
- parity / readiness report generators
- local Vitest coverage for parser / context / reviewer / assembler flows

## Build flow

```bash
cd /Users/lucas/repos/review/hermes-review-agent/integrations/fastgpt
npm install
npm run generate:all
npm test
npm run build:pkg
```

## Toolset layout

The Toolset package lives under:

- `/Users/lucas/repos/review/hermes-review-agent/integrations/fastgpt/toolset/hermesStructuredReview`

Child tools:

1. `buildReviewContext`
2. `runSupportReview008`
3. `runDeterministicReviewer`
4. `assembleFinalDecision`
5. `renderFormalReport`

Generated bundle outputs:

- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-structured-review.workflow.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-structured-review.workflow.baseline.json`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-fastgpt-parity-matrix.md`
- `/Users/lucas/repos/review/hermes-review-agent/artifacts/fastgpt/hermes-fastgpt-import-readiness.md`
