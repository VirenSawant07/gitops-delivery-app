# Runbook: HighErrorRate

**Severity:** critical
**Fires when:** more than 5% of real requests to a service (probes and `/metrics` excluded) return 5xx for 1 minute.

## Impact
Users are getting errors. In `prod` this is customer-facing.

## Check
1. Which version is failing? Open the Grafana dashboard **GitOps Delivery Platform** and look at **Traffic by running version** and **Error rate**.
2. Did something just deploy? Check the config repo history:
   ```bash
   git log --oneline -5 -- apps/<env>/
   ```
3. Look at the app's errors:
   ```bash
   kubectl logs -n <env> deploy/<service> --tail=50
   ```
4. If `api` returns `502`, the problem is downstream. Check `inventory` (see [service-down.md](service-down.md)).

## Fix
- **A recent deploy caused it:** roll back by reverting the deploy commit in the config repo. ArgoCD syncs the previous version within about a minute.
  ```bash
  git revert <deploy-commit-sha> && git push
  ```
- **Not deploy-related:** check `inventory` health and pod restarts, then escalate.

## Verify
The alert resolves (Discord shows `RESOLVED`) and the error-rate panel returns to ~0%.
