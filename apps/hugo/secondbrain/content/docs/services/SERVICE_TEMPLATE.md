# [Service Name]

## Overview

[Brief description of what the service does and its purpose in the cluster]

## Key Features

- **Feature 1**: [Description]
- **Feature 2**: [Description]
- **Feature 3**: [Description]

## Architecture

### Components

1. **Deployment**: [Description of deployment strategy]
2. **Service**: [Type of service and ports]
3. **Storage**: [Storage requirements if any]
4. **ConfigMap/Secrets**: [Configuration management]

### Resource Requirements

- **GPU**: [If applicable]
- **Memory**: [Request/Limit]
- **CPU**: [Request/Limit]
- **Storage**: [PVC size if applicable]

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VAR_1` | `value` | Description |
| `VAR_2` | `value` | Description |

### Configuration Files

[Describe any configuration files and their purpose]

## Usage

### Accessing the Service

[How to access the service within the cluster and externally if applicable]

### API/Protocol

[Describe the API or protocol used by the service]

### Example Usage

```bash
# Example commands or code snippets
```

## Operations

### Checking Service Status

```bash
# Commands to check status
kubectl get pods -n [namespace]
kubectl logs -n [namespace] deployment/[deployment-name]
```

### Common Tasks

[List common operational tasks with commands]

## Troubleshooting

### Issue 1: [Common Issue]

[Description and solution]

### Issue 2: [Common Issue]

[Description and solution]

## Integration

### With Other Services

[Describe how this service integrates with other services in the cluster]

### External Integrations

[Describe any external integrations]

## Security Considerations

- [Security consideration 1]
- [Security consideration 2]

## Monitoring

[Describe monitoring setup and key metrics]

## Backup and Recovery

[If applicable, describe backup procedures]

## Future Improvements

- [ ] [Planned improvement 1]
- [ ] [Planned improvement 2]
