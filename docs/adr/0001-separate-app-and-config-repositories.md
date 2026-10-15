# 1. Separate app and config repositories

**Status:** accepted

## Context
Something has to record which image version runs in each environment. Keeping that in the same repo as the code means every deploy commit triggers code CI again, and code history gets mixed with deploy history.

## Decision
- `gitops-delivery-app` holds code, Dockerfiles, CI and docs.
- `gitops-delivery-config` holds the desired state of the cluster: the Helm chart, per-environment values, ArgoCD apps and monitoring.

App CI writes image tags into the config repo using a **deploy key scoped to that one repository**.

## Consequences
- No CI loops: a tag bump in the config repo never re-triggers the app pipeline.
- The config repo's history is a clean audit log of every deploy and promotion.
- Different change paths: CI may update staging, but prod only changes through a reviewed PR.
- Cost: two repos to manage, and a deploy key to rotate.
