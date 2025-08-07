# Fako Cluster Architecture Overview

## Introduction

The Fako Cluster is a Kubernetes-based platform designed with modern cloud-native principles, emphasizing automation, security, and observability. This document provides a high-level overview of the cluster's architecture and core components.

## Core Architecture Principles

### GitOps-Driven Deployment
- **FluxCD** manages all deployments through Git repositories
- Infrastructure as Code (IaC) approach for all configurations
- Automated reconciliation ensures cluster state matches Git repository

### Security-First Design
- **External Secrets Operator** for secure secrets management
- Integration with AWS Secrets Manager
- SOPS encryption for sensitive configuration data
- Network policies and RBAC for defense in depth

### High Availability
- Multi-node cluster configuration
- Persistent volume claims for stateful workloads
- Regular automated backups
- Health checks and auto-recovery mechanisms

## Infrastructure Stack

### Container Orchestration
- **Kubernetes**: Core orchestration platform
- **K3s**: Lightweight Kubernetes distribution for edge computing

### Networking
- **NGINX Ingress Controller**: HTTP/HTTPS routing
- **Cert-Manager**: Automated TLS certificate management
- **Cloudflare Tunnels**: Secure external access without exposed ports

### Storage
- **NFS**: Network-attached storage for persistent volumes
- **Local Path Provisioner**: Dynamic volume provisioning

### Monitoring & Observability
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation and querying

## Application Architecture

### Service Categories

1. **Core Services**
   - Authentication (Keycloak)
   - Documentation (Hugo Blog)
   - Cluster Management (Headlamp)

2. **AI/ML Services**
   - Ollama (Local LLM inference)
   - Open WebUI (AI chat interface)
   - Whisper (Speech-to-text)
   - Piper (Text-to-speech)

3. **Productivity Tools**
   - n8n (Workflow automation)
   - Linkding (Bookmark management)
   - Audiobookshelf (Media server)

4. **Security & Compliance**
   - Gitleaks (Secret scanning)
   - Kubescape (Security compliance)
   - Kube-bench (CIS benchmarks)

## Deployment Patterns

### Namespace Isolation
Each service runs in its own namespace with:
- Dedicated service accounts
- Resource quotas
- Network policies
- RBAC rules

### Configuration Management
- ConfigMaps for application configuration
- Secrets for sensitive data
- External Secrets for cloud provider integration

### Health & Readiness
- Liveness probes for container health
- Readiness probes for traffic routing
- Startup probes for slow-starting containers

## Data Flow Architecture

```
Internet → Cloudflare → Ingress → Service → Pod
                ↓
            Cert-Manager
                ↓
            TLS Certs
```

## Security Architecture

### Layers of Security
1. **Network Level**: Cloudflare DDoS protection
2. **Ingress Level**: TLS termination, rate limiting
3. **Namespace Level**: Network policies, RBAC
4. **Pod Level**: Security contexts, non-root users
5. **Secret Level**: External secrets, encryption at rest

## Future Architecture Plans

- Service mesh implementation (Istio/Linkerd)
- Multi-cluster federation
- Enhanced observability with distributed tracing
- Automated disaster recovery procedures
