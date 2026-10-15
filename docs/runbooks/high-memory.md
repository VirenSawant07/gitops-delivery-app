# Runbook: HighMemoryUsage

**Severity:** warning
**Fires when:** a pod uses more than 85% of its memory limit for 5 minutes.

## Impact
At 100% of the limit the container is **OOMKilled** (killed and restarted). This alert is the early warning.

## Check
- Grafana: **Memory used / limit**. Is it a steady climb (a leak) or a jump after a deploy?
```bash
kubectl top pods -n <env>
kubectl describe pod -n <env> <pod>    # look for previous OOMKilled terminations
```

## Fix
- **A jump after a deploy:** revert the deploy commit.
- **A steady climb:** likely a leak. Restarting buys time (`kubectl rollout restart` is safe, and ArgoCD won't fight it), but fix the code.
- **The limit is genuinely too low:** raise `resources.limits.memory` in `apps/<env>/<service>.yaml`.

## Verify
Memory settles below 85% of the limit and the alert resolves.
