# Runbook: PodRestartingFrequently

**Severity:** warning
**Fires when:** a container restarts 2 or more times within 10 minutes.

## Impact
Reduced capacity, and possibly dropped requests while the pod restarts. Kubernetes keeps healing it, but something is wrong.

## Check
```bash
kubectl get pods -n <env>                       # RESTARTS column, status
kubectl describe pod -n <env> <pod>             # "Last State: Terminated" -> Reason / Exit Code
kubectl logs -n <env> <pod> --previous          # logs from the crashed container
```
| Last state reason | Usual cause |
|---|---|
| `OOMKilled` | Memory limit too low or a leak. See [high-memory.md](high-memory.md). |
| `Error`, exit code 1 | The app crashed. Read the `--previous` logs. |
| Liveness probe failed (in Events) | The app hung, or the probe is too strict for slow starts |

## Fix
Fix the cause in code or in `apps/<env>/<service>.yaml` (resources, probes) and deploy through Git. If a recent release caused it, revert that deploy commit.

## Verify
The RESTARTS count stops increasing for 10 minutes and the alert resolves.
