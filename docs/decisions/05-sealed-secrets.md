# 5. Sealed Secrets for secrets in Git

**Status:** accepted

## Context
GitOps wants everything in Git, but the Discord webhook URL and the Grafana admin password must never be committed in plain text.

## Decision
Use Bitnami Sealed Secrets. Secrets are encrypted with the cluster's public key (`kubeseal`) and committed as `SealedSecret` objects. Only the controller in the cluster can decrypt them.

## Consequences
- Every secret is versioned and reviewed like any other config. Nothing plain-text is stored in the repo.
- No dependency on an external secret store.
- Cost: the controller's private key lives in the cluster. If the cluster is rebuilt without backing up that key, the secrets must be re-sealed. Back it up **outside the repo** (it decrypts every secret in Git) and pass it to `bootstrap/setup.sh`:
  ```bash
  kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml \
    | yq 'del(.items[].metadata.uid, .items[].metadata.resourceVersion, .items[].metadata.creationTimestamp, .items[].metadata.managedFields)' \
    > ~/sealed-secrets-key-backup.yaml
  SEALED_SECRETS_KEY=~/sealed-secrets-key-backup.yaml bash bootstrap/setup.sh
  ```
- Considered: External Secrets Operator with AWS Secrets Manager. That's a better fit for a real cloud cluster, and it's on the roadmap.
