# Fako Cluster Documentation

Welcome to the comprehensive documentation for the Fako Cluster. This documentation covers all services, infrastructure components, and operational procedures.

## Documentation Structure

### 📦 [Services](./services/)
Detailed documentation for each service deployed in the cluster:
- **AI/ML Services**: Whisper, Piper, Ollama, GPUStack
- **Monitoring & Security**: Kubescape, Kube-bench, Gitleaks
- **Management Tools**: Headlamp, Kagent, Keycloak
- **Application Services**: N8N, Blog, Linkding, Audiobookshelf
- **MCP Servers**: Various Model Context Protocol servers
- **Database**: PostgreSQL cluster, pgAdmin
- **Health & Fitness**: Wger, Oura collector/dashboard

### 🚀 [Active Use Cases](./use-cases/)
Real-world implementations and practical applications:
- **AI/ML Use Cases**: Personal assistant, voice automation, document analysis
- **Development & Automation**: GitOps workflows, security scanning, CI/CD
- **Personal Productivity**: Health analytics, knowledge management, media server
- **Infrastructure Management**: GPU scheduling, secure access, backup strategies

### 🏗️ [Infrastructure](./infrastructure/)
Core infrastructure components and configurations:
- Kubernetes cluster setup
- Flux CD configurations
- Networking setup
- Storage solutions
- External secrets management

### 📚 [Guides](./guides/)
Step-by-step guides and tutorials:
- Getting started with the cluster
- Adding new services
- Managing secrets
- Troubleshooting common issues

### 🎯 [Architecture](./architecture/)
High-level system design and architecture:
- GPU/CPU resource allocation
- Service communication patterns
- Security architecture
- Scaling strategies

### 🔧 [Operations](./operations/)
Operational procedures and runbooks:
- Backup and restore procedures
- Upgrade processes
- Incident response
- Monitoring and alerting

## Quick Links

- [Project Overview](./guides/project-overview.md)
- [Manifest Validation Report](./operations/manifest-validation-report.md)
- [GPU/CPU Architecture](./architecture/gpu-cpu-architecture.md)

## Contributing to Documentation

When adding or updating documentation:

1. Place files in the appropriate directory based on the category
2. Use clear, descriptive filenames
3. Include a title and brief description at the top of each document
4. Follow the existing markdown formatting conventions
5. Update relevant index files when adding new documents

## Automatic Blog Updates

Documentation in this directory is automatically synchronized to the Hugo blog at `https://blog.fako-cluster.local` every 6 hours via a CronJob. You can also trigger a manual sync if needed.
