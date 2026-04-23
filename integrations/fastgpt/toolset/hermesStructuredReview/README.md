# hermesStructuredReview

FastGPT Toolset package source for the Hermes structured-review migration.

Included tools:

- `buildReviewContext`
- `runSupportReview008`
- `runDeterministicReviewer`
- `assembleFinalDecision`
- `renderFormalReport`

Implementation note:

- child tools live under `children/*`
- shared governed logic lives under `lib/*`
- governed YAML / template / basis assets are exported into `assets/generated/*`
