---
title: "Projects"
date: 2025-01-07
draft: false
description: "Explore the various projects and services running on the Fako Cluster"
menu:
  main:
    name: "Projects"
    weight: 2
---

# Projects

Welcome to the projects section! Here you'll find detailed documentation about the various services and applications running on the Fako Cluster. Each project represents a real-world implementation of modern cloud-native technologies.

## The Kubernetes Cluster

### Fako Cluster Infrastructure
The foundation of everything - a personal Kubernetes cluster built with:
- **K3s**: Lightweight Kubernetes distribution
- **3 Nodes**: Master and worker nodes configuration
- **GPU Support**: NVIDIA RTX 5070 for AI workloads
- **GitOps**: FluxCD for automated deployments
- **Monitoring**: Prometheus, Grafana, and Loki stack

## Featured Projects

### AI & Machine Learning

#### [Ollama AI Model Server](/pages/projects/ollama)
Run large language models locally with GPU acceleration. This project showcases how to self-host AI models for privacy, cost savings, and unlimited usage.

#### [Open WebUI - AI Chat Interface](/pages/projects/open-webui)
A ChatGPT-like web interface for interacting with local AI models. Features user management, conversation history, and seamless integration with GPUStack.

#### Voice Pipeline
Complete voice assistant infrastructure:
- **Whisper**: OpenAI's speech-to-text engine
- **Piper**: Fast, local text-to-speech system
- **OpenWakeWord**: Wake word detection service

### Automation & Integration

#### [N8N Workflow Automation](/pages/projects/n8n)
Visual workflow automation platform with 200+ integrations. Create complex automations without coding, from simple webhooks to sophisticated data pipelines.

### Health & Analytics

#### [Oura Dashboard](/pages/projects/oura-dashboard)
Interactive health data visualization platform for Oura Ring metrics. Features OAuth2 authentication, real-time charts, and comprehensive health insights.

#### Oura Collector
Backend service that continuously syncs data from Oura Ring API to PostgreSQL database.

## Infrastructure Services

### Core Platform
- **Keycloak**: Identity and access management platform
- **PostgreSQL Cluster**: High-availability database with automatic backups
- **PgAdmin**: Web-based PostgreSQL administration tool
- **NGINX Ingress**: Load balancing and SSL termination
- **Cert-Manager**: Automated TLS certificate management

### Monitoring & Observability
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Beautiful dashboards and data visualization
- **Loki**: Log aggregation and querying system
- **Headlamp**: Kubernetes cluster UI dashboard

### Security & Compliance
- **Gitleaks**: Automated secret scanning in Git repositories
- **Kubescape**: Kubernetes security compliance scanning
- **Kube-bench**: CIS Kubernetes benchmark assessments
- **External Secrets Operator**: AWS Secrets Manager integration

## Personal Services

### Knowledge Management
- **Linkding**: Self-hosted bookmark manager with tagging
- **Hugo Blog**: This documentation site you're reading
- **MCP Servers**: Model Context Protocol servers for AI tools

### Media & Entertainment
- **Audiobookshelf**: Personal audiobook and podcast library
- **Wger**: Workout manager and fitness tracker

### Development Tools
- **GitLab Runner**: CI/CD pipeline execution (planned)
- **Code Server**: VS Code in the browser (planned)

## Automation & Agents
- **Kagent**: Kubernetes agent for automated operations
- **Node Labeling**: Automatic node labeling based on hardware
- **Housekeeping**: Automated cluster maintenance tasks

## Supporting Services
- **GPUStack Proxy**: GPU resource management
- **Blog**: Technical blog platform
- **Ollama WebUI**: Alternative UI for Ollama

## Coming Soon

Planned additions to the cluster:
- **Vector Database**: Milvus or Qdrant for AI/RAG applications
- **Jupyter Hub**: Collaborative data science platform
- **Mastodon Instance**: Federated social media
- **Home Assistant**: Smart home automation
- **Vaultwarden**: Self-hosted password manager

## Technology Stack

All projects share common infrastructure patterns:

- **Kubernetes**: Container orchestration
- **GitOps**: Automated deployments with FluxCD
- **Security**: External secrets management, OAuth2, RBAC
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Storage**: Persistent volumes and database integration

## Getting Started

Each project documentation includes:

1. **Overview**: What the project does and why it's useful
2. **Architecture**: Technical components and design decisions
3. **Configuration**: Environment settings and customization options
4. **Usage**: Practical examples and integration patterns
5. **Operations**: Maintenance, monitoring, and troubleshooting

## Contributing

While this is a personal cluster, I welcome:

- **Feedback**: Share your thoughts on implementations
- **Questions**: Ask about specific configurations
- **Suggestions**: Propose improvements or new projects

## Future Projects

Planned additions to the cluster:

- **Vector Database**: For AI/RAG applications
- **GitLab Runner**: Self-hosted CI/CD
- **Jupyter Hub**: Collaborative data science platform
- **Mastodon Instance**: Federated social media
- **Home Bridge**: Smart home integration

---

*Explore each project to see how modern cloud-native technologies can be applied in a personal infrastructure context.*
