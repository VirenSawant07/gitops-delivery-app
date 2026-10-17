# Runbook: ServiceDown

**Severity:** critical
**Fires when:** any Deployment in `staging` or `prod` (except `traffic-generator`) has 0 available pods for 1 minute (from kube-state-metrics, so it still fires when every pod is gone).

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

## Fix
Revert the last change to `apps/<env>/<service>.yaml` if it caused this. Otherwise fix the root cause and redeploy through Git.

## Verify
`kubectl get pods` shows all pods `1/1 Running`, and the alert resolves.
