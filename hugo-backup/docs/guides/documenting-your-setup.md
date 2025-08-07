# How to Document Your Fako Cluster Setup

This guide will help you systematically document all aspects of your Fako cluster using the Hugo blog system.

## Overview of the Documentation System

Your documentation system consists of:

1. **Central docs directory**: `/docs/` in your repository
2. **Hugo blog**: Automatically syncs and serves documentation
3. **CronJob**: Updates the blog every 6 hours from GitHub

## Step-by-Step Documentation Process

### 1. Document Your Services

For each service in `apps/base/`, create documentation using the template:

```bash
# Copy the template
cp docs/services/SERVICE_TEMPLATE.md docs/services/[service-name]/README.md

# Edit with your service details
```

Priority services to document:
- **AI/ML Stack**: Ollama, Piper, OpenWakeword, Open-WebUI
- **Infrastructure**: Keycloak, PostgreSQL, External Secrets
- **Monitoring**: Kubescape, Kube-bench, Headlamp
- **Applications**: N8N, Audiobookshelf, Linkding

### 2. Document Infrastructure Components

Create documentation for:

```bash
# Cluster setup
docs/infrastructure/cluster-setup.md

# Networking configuration
docs/infrastructure/networking.md

# Storage configuration  
docs/infrastructure/storage.md

# Flux CD setup
docs/infrastructure/flux-cd.md

# External secrets
docs/infrastructure/external-secrets.md
```

### 3. Create How-To Guides

Write guides for common tasks:

```bash
# Adding a new service
docs/guides/adding-new-service.md

# Managing secrets
docs/guides/managing-secrets.md

# GPU allocation
docs/guides/gpu-allocation.md

# Troubleshooting
docs/guides/troubleshooting.md
```

### 4. Document Architecture

Create architecture documentation:

```bash
# System architecture
docs/architecture/system-overview.md

# Security architecture
docs/architecture/security.md

# Networking architecture
docs/architecture/networking.md

# Data flow diagrams
docs/architecture/data-flow.md
```

### 5. Operational Procedures

Document your operations:

```bash
# Backup procedures
docs/operations/backup-procedures.md

# Disaster recovery
docs/operations/disaster-recovery.md

# Monitoring setup
docs/operations/monitoring.md

# Upgrade procedures
docs/operations/upgrades.md
```

## Documentation Best Practices

### 1. Use Consistent Structure

Follow the template structure for all service documentation:
- Overview
- Key Features
- Architecture
- Configuration
- Usage
- Operations
- Troubleshooting

### 2. Include Practical Examples

Always include:
- Command examples
- Configuration snippets
- Common use cases
- Troubleshooting steps

### 3. Keep Documentation Current

- Update docs when you modify services
- Document new services immediately
- Review and update quarterly

### 4. Use Diagrams

Create diagrams for:
- Architecture overviews
- Data flows
- Network topology
- Service dependencies

Use tools like:
- Mermaid (supported by many markdown renderers)
- draw.io
- PlantUML

### 5. Cross-Reference

Link between related documents:
```markdown
See also: [Keycloak Setup](../services/keycloak/README.md)
```

## Quick Start: Document a Service

Here's a quick example for documenting Piper:

```bash
# 1. Create the directory
mkdir -p docs/services/piper

# 2. Copy the template
cp docs/services/SERVICE_TEMPLATE.md docs/services/piper/README.md

# 3. Fill in the details (example content):
```

```markdown
# Piper Text-to-Speech Service

## Overview

Piper is a fast, local text-to-speech system that runs on GPU...

## Key Features

- **GPU Acceleration**: Runs on NVIDIA GPU
- **Multiple Voices**: Support for various voice models
- **Wyoming Protocol**: Compatible with Home Assistant
```

## Automation Tips

### 1. Generate Documentation from YAML

Create a script to extract information from your Kubernetes manifests:

```bash
#!/bin/bash
# extract-service-info.sh

SERVICE=$1
BASE_PATH="apps/base/$SERVICE"

echo "# $SERVICE Service Documentation"
echo ""
echo "## Deployment Configuration"
echo '```yaml'
cat $BASE_PATH/deployment.yaml
echo '```'
```

### 2. Auto-generate Service List

```bash
#!/bin/bash
# list-services.sh

echo "## Services in Cluster"
echo ""
for service in apps/base/*/; do
  name=$(basename "$service")
  echo "- [$name](./services/$name/README.md)"
done
```

### 3. Check Documentation Coverage

```bash
#!/bin/bash
# check-coverage.sh

echo "Services without documentation:"
for service in apps/base/*/; do
  name=$(basename "$service")
  if [ ! -f "docs/services/$name/README.md" ]; then
    echo "- $name"
  fi
done
```

## Viewing Your Documentation

### Local Preview

1. **Via Hugo blog**: Access at `https://blog.fako-cluster.local`
2. **In GitHub**: Browse the `/docs` directory
3. **VS Code**: Use markdown preview

### Manual Sync

To manually trigger documentation sync:

```bash
# Create a one-off job from the CronJob
kubectl create job --from=cronjob/sync-docs manual-sync-$(date +%s) -n blog

# Watch the job
kubectl logs -n blog -l job-name=manual-sync-* -f
```

## Next Steps

1. Start with documenting your most critical services
2. Create architecture diagrams for complex interactions
3. Write operational runbooks for common tasks
4. Set up a documentation review schedule

## Tips for Efficiency

1. **Document as you build**: Write docs when creating/modifying services
2. **Use comments in YAML**: Add inline documentation in your manifests
3. **Screenshot UI services**: Include screenshots for web interfaces
4. **Link to upstream docs**: Reference official documentation
5. **Create checklists**: For complex procedures

Remember: Good documentation is an investment that pays dividends in reduced troubleshooting time and easier onboarding of new team members.
