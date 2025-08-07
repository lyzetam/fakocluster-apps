---
title: "GitOps in Practice: Managing Kubernetes with FluxCD"
date: 2025-01-06
draft: false
description: "A deep dive into implementing GitOps practices with FluxCD for automated Kubernetes deployments"
tags: ["GitOps", "FluxCD", "Kubernetes", "CI/CD", "Automation"]
categories: ["Technical", "DevOps"]
author: "Landry"
---

After running the Fako Cluster for several months, I can confidently say that adopting GitOps with FluxCD has been one of the best decisions for managing my Kubernetes infrastructure. In this post, I'll share practical insights and patterns that have proven invaluable.

## What is GitOps?

GitOps is a way of implementing Continuous Deployment for cloud native applications. It focuses on:

- **Declarative Infrastructure**: Everything defined in Git
- **Automated Reconciliation**: Cluster state matches Git state
- **Version Control**: Complete history of all changes
- **Pull-based Deployment**: No direct kubectl access needed

## Why FluxCD?

Among GitOps tools like ArgoCD and Fleet, I chose FluxCD because:

1. **Lightweight**: Minimal resource footprint
2. **Native Kubernetes**: Uses standard Kubernetes controllers
3. **Multi-tenancy**: Built-in support for multiple environments
4. **Extensible**: Works with Helm, Kustomize, and raw manifests

## Real-World Implementation

### Repository Structure

Here's how I organize my GitOps repository:

```
fakocluster-apps/
├── clusters/
│   └── production/
│       ├── flux-system/
│       └── infrastructure.yaml
├── infrastructure/
│   ├── controllers/
│   ├── configs/
│   └── sources/
└── apps/
    ├── base/
    └── production/
```

### Bootstrapping FluxCD

The initial setup is straightforward:

```bash
flux bootstrap github \
  --owner=lyzetam \
  --repository=fakocluster-apps \
  --branch=main \
  --path=./clusters/production \
  --personal
```

### Managing Secrets Safely

One challenge with GitOps is handling secrets. Here's my approach:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
  namespace: myapp
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: app-secrets
  data:
    - secretKey: api-key
      remoteRef:
        key: myapp/production
        property: api_key
```

## Practical Patterns

### 1. Environment Promotion

I use Kustomize overlays for environment-specific configurations:

```yaml
# apps/base/myapp/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml

# apps/production/myapp/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: myapp
resources:
  - ../../base/myapp
patchesStrategicMerge:
  - deployment-patch.yaml
```

### 2. Automated Image Updates

FluxCD's image automation controllers handle container updates:

```yaml
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageUpdateAutomation
metadata:
  name: flux-system
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: flux-system
  git:
    commit:
      author:
        name: fluxcdbot
        email: fluxcdbot@users.noreply.github.com
      messageTemplate: |
        Automated image update
        
        [ci skip]
    push:
      branch: main
```

### 3. Health Checks and Notifications

Monitoring FluxCD reconciliation:

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta2
kind: Alert
metadata:
  name: on-call-webapp
  namespace: flux-system
spec:
  providerRef:
    name: discord
  eventSeverity: info
  eventSources:
    - kind: GitRepository
      name: '*'
    - kind: Kustomization
      name: '*'
```

## Lessons Learned

### 1. Start Simple

Don't try to automate everything at once. I started with:
- Basic deployments
- Gradually added Helm charts
- Then implemented secret management
- Finally added image automation

### 2. Namespace Organization

Keeping services in separate namespaces with FluxCD has benefits:
- Better resource isolation
- Easier RBAC management
- Cleaner GitOps structure

### 3. Rollback Strategy

Git makes rollbacks trivial:

```bash
# Revert to previous state
git revert HEAD
git push

# FluxCD automatically reconciles
```

### 4. Testing Changes

I use a staging branch for testing:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: flux-system-staging
spec:
  ref:
    branch: staging  # Test changes here first
```

## Common Pitfalls to Avoid

1. **Don't commit secrets**: Use External Secrets or Sealed Secrets
2. **Watch resource limits**: FluxCD controllers need adequate resources
3. **Plan for Git outages**: Consider local caching strategies
4. **Version your CRDs**: Include them in your GitOps flow

## Performance Optimization

For larger clusters:

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
spec:
  interval: 10m  # Adjust based on change frequency
  retryInterval: 2m
  timeout: 5m
  prune: true
  wait: true
  force: false  # Avoid unless necessary
```

## Debugging FluxCD

Useful commands for troubleshooting:

```bash
# Check FluxCD status
flux get all

# View reconciliation errors
flux logs --follow

# Suspend reconciliation for debugging
flux suspend kustomization apps

# Force reconciliation
flux reconcile kustomization apps --with-source
```

## The GitOps Advantage

After months of using GitOps:

- **Zero manual deployments**: Everything through Git
- **Complete audit trail**: Every change tracked
- **Disaster recovery**: Rebuild cluster from Git
- **Team collaboration**: PR reviews for infrastructure

## What's Next?

GitOps with FluxCD has transformed how I manage the Fako Cluster. Future posts will cover:

- Multi-cluster GitOps patterns
- Progressive delivery with Flagger
- GitOps for stateful applications
- Integrating GitOps with CI pipelines

The journey from manual kubectl commands to fully automated GitOps has been rewarding. If you're managing Kubernetes, I highly recommend exploring this approach!

---

*Want to implement GitOps in your cluster? Check out the [FluxCD documentation](https://fluxcd.io/docs/) or explore my [GitOps repository](https://github.com/lyzetam/fakocluster-apps) for real examples.*
