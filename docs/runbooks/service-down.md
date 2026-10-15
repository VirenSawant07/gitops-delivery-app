# Runbook: ServiceDown

**Severity:** critical
**Fires when:** Prometheus cannot scrape any healthy target of a service for 1 minute.

## Impact
The service is unreachable. If it's `inventory`, `api` will answer `502 inventory unavailable`.

## Check
```bash
kubectl get pods -n <env> -l app.kubernetes.io/name=<service>
kubectl describe pod -n <env> <pod>          # Events: image pull, probe failures, OOMKilled
kubectl get endpointslices -n <env> -l kubernetes.io/service-name=<service>
```
- `ImagePullBackOff`: the image tag in `apps/<env>/<service>.yaml` doesn't exist in GHCR, or the package isn't public.
- `CrashLoopBackOff`: see [pod-restarting.md](pod-restarting.md).
- Pods are `Running` but the target is down: check the NetworkPolicy allows the `monitoring` namespace.

## Fix
Revert the last change to `apps/<env>/<service>.yaml` if it caused this. Otherwise fix the root cause and redeploy through Git.

## Verify
`kubectl get pods` shows all pods `1/1 Running`, and the alert resolves.
