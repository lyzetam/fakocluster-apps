---
title: "Introducing the Fako Cluster: A Personal Kubernetes Infrastructure"
date: 2025-01-05
draft: false
description: "An introduction to my personal Kubernetes cluster showcasing GitOps, AI/ML services, and modern cloud-native practices"
tags: ["Kubernetes", "GitOps", "Infrastructure", "Self-Hosting"]
categories: ["Infrastructure", "Announcements"]
author: "Landry"
---

Welcome to the documentation hub for the Fako Cluster! This post marks the beginning of sharing my journey building and maintaining a personal Kubernetes infrastructure that showcases modern cloud-native technologies.

## What is the Fako Cluster?

The Fako Cluster is a self-hosted Kubernetes environment that I've built to explore and demonstrate:

- **GitOps practices** with FluxCD for declarative infrastructure management
- **AI/ML capabilities** with local LLM inference using Ollama and GPUStack
- **Security-first design** with external secrets management and RBAC
- **Comprehensive monitoring** using Prometheus and Grafana
- **Modern automation** with tools like n8n for workflow orchestration

## Why Build a Personal Cluster?

As someone driven by sheer curiosity, I wanted a playground where I could:

1. **Learn by doing**: Nothing beats hands-on experience with production-grade tools
2. **Self-host services**: Maintain control over my data and services
3. **Experiment freely**: Test new technologies without cloud provider constraints
4. **Share knowledge**: Document patterns and practices for others to learn from

## Key Features

### Infrastructure as Code

Everything in the cluster is managed through Git repositories:

```yaml
# Example FluxCD GitRepository
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: flux-system
  namespace: flux-system
spec:
  interval: 1m0s
  ref:
    branch: main
  url: https://github.com/lyzetam/fakocluster-apps
```

### GPU-Accelerated AI Services

With an RTX 5070 powering the cluster, I can run:
- Large language models locally through Ollama
- ChatGPT-like interfaces with Open WebUI
- Voice processing with Whisper and Piper

### Security Best Practices

- External Secrets Operator integrated with AWS Secrets Manager
- Network policies for service isolation
- OAuth2 authentication for external services
- Encrypted secrets with SOPS

## What's Coming Next?

In upcoming posts, I'll dive deep into:

1. **Architecture Deep Dives**: How the cluster is structured and why
2. **Service Spotlights**: Detailed looks at each deployed service
3. **Lessons Learned**: Challenges faced and solutions found
4. **Tutorials**: How to implement similar patterns in your own infrastructure

## Getting Started

If you're interested in exploring the cluster:

- Check out the [Architecture Overview](/pages/architecture/overview) for technical details
- Browse the [Projects](/pages/projects) section to see what's deployed
- Follow along as I document the journey

## Join the Journey

This cluster represents not just infrastructure, but a learning journey. Whether you're a seasoned Kubernetes operator or just getting started with self-hosting, I hope you'll find valuable insights in these pages.

Stay tuned for more posts covering everything from technical deep-dives to practical tutorials!

---

*Have questions or suggestions? Feel free to reach out or explore the documentation to learn more about the Fako Cluster.*
