# GitOps Delivery Platform on Kubernetes

[![ci](https://github.com/VirenSawant07/gitops-delivery-app/actions/workflows/ci.yaml/badge.svg)](https://github.com/VirenSawant07/gitops-delivery-app/actions/workflows/ci.yaml)

A pull-based delivery platform for two Python microservices on Kubernetes.
A developer only pushes code. From there, every change is tested, scanned, built, recorded in Git, deployed by ArgoCD, and watched by Prometheus, with alerts sent to Discord.

This repo holds the **application code, CI and docs**.
The cluster's desired state lives in **[gitops-delivery-config](https://github.com/VirenSawant07/gitops-delivery-config)**.

## How it works

```mermaid
flowchart LR
    dev([Developer]) -->|PR / merge| ci

    subgraph app[gitops-delivery-app]
      ci[GitHub Actions<br/>lint · test · build<br/>Trivy gate · push]
    end

    ci -->|image :git-sha| ghcr[(GHCR)]
    ci -->|bump staging tag<br/>deploy key| cfg

    subgraph config[gitops-delivery-config]
      cfg[apps/staging<br/>apps/prod<br/>Helm chart]
      promote[promote workflow<br/>opens PR to prod]
    end

    promote --> cfg

    subgraph kind[Kind cluster]
      argo[ArgoCD<br/>app-of-apps] --> staging[staging<br/>api → inventory]
      argo --> prod[prod<br/>api → inventory]
      prom[Prometheus] --> am[Alertmanager]
      graf[Grafana]
    end

    cfg -.->|pulled every 60s| argo
    ghcr -.-> staging & prod
    staging & prod -.->|/metrics| prom
    am -->|alerts| discord([Discord])
```

| Flow | What happens |
|---|---|
| **Deploy** | Merge to `main` → CI pushes `ghcr.io/virensawant07/gitops-<svc>:<sha>` and commits the new tag to `apps/staging/` → ArgoCD syncs staging |
| **Promote** | Run the `promote` workflow in the config repo → a PR copies staging tags to `apps/prod/` → merging it deploys prod |
| **Rollback** | `git revert` the deploy commit in the config repo → ArgoCD syncs the previous version |
| **Self-heal** | Manual changes to the cluster (`kubectl scale`, `edit`) are reverted to what Git says |
| **Alert** | Error rate, availability, restarts, CPU and memory rules → Alertmanager → Discord, each linked to a runbook |

**One version for both services (deliberate trade-off).** Every change to `main` builds, scans and deploys *both* services, tagged with the same commit SHA. A change to one service also redeploys the other. In return, the whole system has a single version number, there is no path-filter logic to get wrong, and staging always runs a pair that was tested together. With more services, per-service builds (path filters) would be worth the extra complexity.

## The services

| Service | Endpoint | Purpose |
|---|---|---|
| `inventory` | `GET /items` | Stock levels (in memory) |
| `api` | `GET /products` | Calls `inventory` over cluster DNS and returns products with `in_stock`. Returns `502` if inventory is unavailable. |
| `api` | `GET /` | **Inkling**, a small stationery shop page: live stock, plus a "behind the counter" panel showing the running commit, environment, answering pod, latency and a request log (failed requests appear in red during incidents) |

Both expose `/healthz` (liveness), `/readyz` (readiness), `/metrics` (Prometheus) and the running `version` (the git SHA).
Each request is logged as one JSON line on stdout (`time`, `level`, `method`, `path`, `status`, `duration_ms`, `version`, `pod`).
For drills and demos they support fault injection via environment variables: `FAULT_ERROR_RATE`, `FAULT_LATENCY_MS`, and `ALLOW_CRASH` (which enables `POST /crash`).

## Tech stack

| Area | Tools |
|---|---|
| App | Python 3.14, FastAPI, pytest, ruff |
| Containers | Docker multi-stage build, non-root (UID 10001), no pip at runtime |
| CI | GitHub Actions (SHA-pinned), Trivy (digest-pinned), GHCR, Dependabot |
| Kubernetes | Kind (1 control plane + 2 workers), one reusable Helm chart |
| CD | ArgoCD: app-of-apps, git-files ApplicationSet, automated sync + prune + self-heal |
| Secrets | Sealed Secrets (encrypted secrets committed to Git) |
| Observability | kube-prometheus-stack: Prometheus, Alertmanager, Grafana dashboards as code |

## Security

- **Supply chain:** Actions are pinned to commit SHAs; Trivy, Prometheus (`promtool`) and the base images (`python:3.14-slim`, `busybox:1.37`) to image digests, after the March 2026 attack that re-pointed Trivy's mutable tags. kubeconform downloads are checksum-verified, and its CRD schemas come from a pinned commit. Python dependencies are fully locked with `pip-compile`.
- **Image tags:** each image is tagged with its commit SHA, which is *unique per commit but not immutable* (GHCR tags can be overwritten). Deploying by digest is the next step; see [decision 4](docs/decisions/04-image-tags-and-pinning.md).
- **Blocking scan:** the build fails on fixable CRITICAL CVEs, and PR builds never push or deploy.
- **Minimal images:** removing pip from the runtime image took Trivy's HIGH/CRITICAL findings from **4 to 0**.
- **Pods:** non-root, read-only root filesystem, all capabilities dropped, no privilege escalation, seccomp `RuntimeDefault`, no service-account token.
- **Network:** a NetworkPolicy lets only `api` (and Prometheus) reach `inventory`. An unrelated pod was verified to be blocked.
- **Least privilege:** CI writes to the config repo with a deploy key scoped to that single repo, and never gets cluster credentials. Within that repo the key can write any path, including `apps/prod/`; see [decision 6](docs/decisions/06-protecting-prod.md) for the branch rules and this residual risk.

## Measured results

All numbers were measured on the running system (Kind on a laptop: Ryzen 5 5600H, 16 GB RAM).

| Measure | Result |
|---|---|
| Image size on disk (`docker image ls`), naive `python:3.14` vs multi-stage slim without pip | 1.67 GB → 207 MB (−88%) |
| Trivy HIGH/CRITICAL fixable findings, before → after removing pip | 4 → 0 |
| CI run (lint, test, scan, build, push, deploy commit) | ~66 s |
| Merge to `main` → new version running in staging | ~3 min |
| Promote PR merged → prod fully rolled out (6 pods) | ~65 s |
| Manual drift (`kubectl scale`) reverted by ArgoCD | 2 s |
| Worker node drained → pods rescheduled, PDB respected | ~9 s |
| Empty laptop → whole platform rebuilt from Git, all ArgoCD apps healthy (`setup.sh`) | ~6 min (measured with 8 apps, before metrics-server was added) |

## Run it yourself

Requirements: Docker, kind, kubectl, helm, and bash (Git Bash on Windows).

```bash
git clone https://github.com/VirenSawant07/gitops-delivery-config.git
cd gitops-delivery-config
bash bootstrap/setup.sh             # Kind cluster → ArgoCD → everything else from Git
```

Then:

```bash
kubectl -n staging port-forward svc/api 18080:80          # shop: http://localhost:18080/
kubectl -n argocd port-forward svc/argocd-server 8443:443  # ArgoCD UI
kubectl -n monitoring port-forward svc/monitoring-grafana 13000:80   # Grafana
```

> The SealedSecrets in the config repo are encrypted for the original cluster's key. To rebuild that cluster, pass the key backup, kept outside the repo: `SEALED_SECRETS_KEY=~/sealed-secrets-key-backup.yaml bash bootstrap/setup.sh`. On a different cluster, re-seal your own Discord webhook and Grafana password with `kubeseal`. See [decision 5](docs/decisions/05-sealed-secrets.md).

Local development:

```bash
pip install -r requirements-dev.txt -r services/api/requirements.txt
cd services/api && python -m pytest
```

## Repository layout

```
services/
  api/          FastAPI app, Dockerfile, tests (inventory is mocked)
  inventory/    FastAPI app, Dockerfile, tests
  */requirements.in    direct dependencies; requirements.txt is the pip-compile lock
.github/
  workflows/ci.yaml     lint → test → build → Trivy gate → push → bump staging
  dependabot.yml
docs/
  decisions/    why things are built this way
  runbooks/     one per alert
```

## Design decisions

1. [Separate app and config repositories](docs/decisions/01-two-repos.md)
2. [Pull-based delivery with ArgoCD](docs/decisions/02-argocd-pull-model.md)
3. [One reusable Helm chart](docs/decisions/03-one-helm-chart.md)
4. [Commit-SHA image tags and a pinned supply chain](docs/decisions/04-image-tags-and-pinning.md)
5. [Sealed Secrets for secrets in Git](docs/decisions/05-sealed-secrets.md)
6. [Protecting prod with branch rules](docs/decisions/06-protecting-prod.md)

## Roadmap

- Canary releases with Argo Rollouts and automatic rollback driven by Prometheus analysis
- Kyverno admission policies and cosign-signed images
- SLOs with error-budget burn-rate alerts
- Horizontal Pod Autoscaling with k6 load tests
