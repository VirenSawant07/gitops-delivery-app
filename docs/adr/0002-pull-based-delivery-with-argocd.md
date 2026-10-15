# 2. Pull-based delivery with ArgoCD

**Status:** accepted

## Context
In push-based CD, the CI system runs `kubectl apply` and must hold cluster credentials. Nothing notices if someone later changes the cluster by hand.

## Decision
Use ArgoCD inside the cluster to **pull** the desired state from the config repo, with automated sync, prune and self-heal. An app-of-apps root and a git-files ApplicationSet create one Application per `apps/<env>/<service>.yaml`.

## Consequences
- CI never holds cluster credentials.
- Drift is corrected automatically (a manual `kubectl scale` was reverted in 2 s).
- Rollback is `git revert` on the config repo.
- Cost: changes arrive on the next poll (60 s here), because GitHub webhooks can't reach a cluster on a laptop. In a hosted cluster, a webhook would remove that delay.
