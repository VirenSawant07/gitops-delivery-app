# 6. Protecting prod with branch rules

**Status:** accepted (rulesets are configured in GitHub, outside these repos)

## Context
The whole point of the config repo is that prod only changes through a reviewed pull request. Without branch protection that is a convention, not a guarantee: anyone with write access, and the CI deploy key, can push straight to `main`, including `apps/prod/`.

## Decision
- **Config repo, `main`:** changes require a pull request, and the `validate` check must pass before merge. **Deploy keys are on the bypass list**, so app CI can still push the staging tag bump directly.
- **App repo, `main`:** changes require a pull request, and both `build (api)` and `build (inventory)` checks must pass.
- Force pushes and branch deletion are blocked on both.

## Residual risk
The bypass is per key, not per path. The CI deploy key can technically change **any** file in the config repo, including `apps/prod/`. Today, prod is protected by what the pipeline does (it only edits `apps/staging/`), not by what the key is allowed to do. A leaked deploy key could deploy to prod without review.

Ways to close this gap, in rough order of effort:
- **Path-restricted push rules**, so the key's bypass only applies to `apps/staging/**`.
- **A separate staging config repo**, so the CI key has no write access to prod's repo at all.
- **ArgoCD Image Updater** for staging, so CI needs no write access to Git.

## Consequences
- Prod changes are reviewed and validated by default, and the rulesets are visible in GitHub.
- The remaining risk is written down rather than hidden. It is the first thing to fix before this design is used for real.
