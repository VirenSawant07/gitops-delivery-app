# 3. One reusable Helm chart for every service

**Status:** accepted

## Context
Both services need the same Kubernetes objects: Deployment, Service, PDB, NetworkPolicy and ServiceMonitor, with the same probes and security settings. Copying YAML per service leads to drift between them.

## Decision
A single chart, `charts/service`. Each service × environment gets a small values file (image, replicas, env vars, NetworkPolicy peers). The Helm release name becomes the service name.

## Consequences
- Hardening (non-root, read-only filesystem, dropped capabilities, probes, limits) is written once and applied everywhere.
- A new service is just a new values file. The ApplicationSet picks it up automatically.
- Cost: the chart must stay generic. A service needing something unusual means adding an opt-in toggle.
- Considered: Kustomize (plain YAML + patches). We chose Helm because one parameterised template serves many services more simply than overlays.
