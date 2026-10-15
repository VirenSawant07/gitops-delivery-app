# 4. Immutable image tags and a pinned supply chain

**Status:** accepted

## Context
A tag like `latest` can point to different images over time, so "what's running?" has no exact answer. The same goes for CI tooling: in March 2026, attackers re-pointed most of Trivy's GitHub Action version tags to credential-stealing code.

## Decision
- Images are tagged with the **full git commit SHA**. The running version is exposed in every API response and in metrics (`version` label).
- GitHub Actions are pinned to **commit SHAs**. Trivy runs as a container image pinned by **digest**. kubeconform is downloaded with a **checksum check**.
- The Trivy scan **fails the build** on fixable CRITICAL vulnerabilities, and nothing is pushed.
- pip is removed from the runtime image (it found 4 HIGH CVEs in pip's bundled libraries, now 0).
- Dependabot opens PRs to move pins forward deliberately.

## Consequences
- Every pod traces back to an exact commit, and rollbacks are deterministic.
- A compromised upstream tag can't silently change what CI runs.
- Cost: pins must be bumped. Dependabot automates the PRs.
