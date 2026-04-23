# FastGPT integration for hermes-review-agent

This workspace contains a FastGPT-first migration bundle for `hermes-review-agent`:

- governed asset export from the Python source of truth
- a FastGPT system Toolset package source (`hermesStructuredReview`)
- workflow generators (actual `tools` workflow + baseline validator-safe workflow)
- parity / readiness report generators
- local Vitest coverage for the 5 tool functions

## Build flow

```bash
cd /Users/lucas/repos/review/hermes-review-agent/integrations/fastgpt
npm install
npm run generate:all
npm test
npm run build:pkg
```
