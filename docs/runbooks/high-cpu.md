# Runbook: HighCPUUsage

**Severity:** warning
**Fires when:** a pod uses more than 80% of its CPU limit for 5 minutes.

## Impact
Above the limit, the container is **throttled** (slowed down, not killed). Latency rises before errors do.

## Check
- Grafana: **CPU used / limit** and **p95 latency** panels. Is latency rising too?
- Is it more traffic, or a slower code path? Compare with **Requests per second**.
```bash
kubectl top pods -n <env>
```

## Fix
- **More traffic:** add replicas (`replicas:` in `apps/<env>/<service>.yaml`), or enable autoscaling (roadmap).
- **The limit is too tight for normal load:** raise `resources.limits.cpu` in the values file.
- **A regression in a new release:** revert the deploy commit.

All changes go through Git; ArgoCD applies them.

## Verify
CPU drops below 80% of the limit and the alert resolves.
