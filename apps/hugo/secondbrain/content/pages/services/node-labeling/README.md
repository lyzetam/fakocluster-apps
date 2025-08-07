# Node Labeling - Kubernetes Node Classification Service

## Overview

Node Labeling is an automated Kubernetes job deployed in the Fako cluster that applies strategic labels to cluster nodes. It classifies nodes based on their hardware capabilities, particularly focusing on GPU resources and performance tiers. This service ensures that workloads can be properly scheduled to appropriate nodes using node selectors and affinity rules. The labeling is crucial for GPU workloads, voice pipeline services, and general workload distribution across the heterogeneous cluster.

## Key Features

- **Automated Node Classification**: Labels nodes based on hardware capabilities
- **GPU Detection and Labeling**: Comprehensive GPU-related labels
- **Hardware Tiering**: Classifies nodes into performance tiers
- **Voice Pipeline Support**: Enables nodes for voice processing
- **Cleanup Operations**: Removes labels from decommissioned nodes
- **TTL Management**: Auto-cleanup of completed jobs
- **Idempotent Operations**: Safe to run multiple times
- **Summary Reporting**: Shows final labeling state

## Architecture

### Components

1. **Job**: One-time execution Kubernetes job
2. **ServiceAccount**: Node labeling permissions
3. **ClusterRole**: Permission to label nodes
4. **Container**: kubectl image for operations
5. **TTL**: Auto-cleanup after 300 seconds

### Node Categories

1. **Dual-GPU Nodes** (`yeezyai`):
   - RTX 5070 + RTX 3050
   - Full GPU compute capabilities
   
2. **High-Performance Nodes**:
   - `pgbee`, `pgmac01`, `pgmac02`
   - Voice pipeline enabled
   
3. **Standard Nodes**:
   - `pglenovo01`, `pglenovo02`, `thinkpad01`
   - General compute workloads

## Configuration

### Label Schema

#### GPU Labels
| Label | Value | Purpose |
|-------|-------|---------|
| `nvidia.com/gpu` | `true` | NVIDIA GPU present |
| `node-role.kubernetes.io/gpu-worker` | `true` | GPU worker role |
| `gpu.nvidia.present` | `true` | GPU availability |
| `gpu.count` | `2` | Number of GPUs |
| `gpu.rtx5070` | `true` | RTX 5070 present |
| `gpu.rtx3050` | `true` | RTX 3050 present |
| `accelerator` | `nvidia-gpu` | Accelerator type |

#### Hardware Tiers
| Label | Values | Description |
|-------|--------|-------------|
| `hardware.tier` | `dual-gpu`, `high-performance`, `standard` | Performance classification |
| `node-type` | `gpu-compute` | Node purpose |
| `voice-pipeline` | `enabled` | Voice processing capability |

## Usage

### Running the Job

Execute node labeling:
```bash
kubectl apply -f apps/base/node-labeling/label-nodes-job.yaml
```

Monitor execution:
```bash
# Watch job progress
kubectl logs -n node-labeling -l job-name=label-nodes-for-voice-pipeline -f

# Check job status
kubectl get job -n node-labeling label-nodes-for-voice-pipeline
```

### Verifying Labels

Check all node labels:
```bash
# View all nodes with key labels
kubectl get nodes -L hardware.tier,voice-pipeline,nvidia.com/gpu,gpu.count

# Check specific node
kubectl describe node yeezyai | grep Labels

# List GPU nodes
kubectl get nodes -l nvidia.com/gpu=true
```

### Using Labels for Scheduling

#### GPU Workload
```yaml
spec:
  nodeSelector:
    nvidia.com/gpu: "true"
    hardware.tier: "dual-gpu"
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

#### Voice Pipeline Workload
```yaml
spec:
  nodeSelector:
    voice-pipeline: "enabled"
  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
          - key: hardware.tier
            operator: In
            values: ["high-performance"]
```

## Operations

### Manual Labeling

Add custom labels:
```bash
# Add label
kubectl label nodes <node-name> custom-label=value

# Remove label
kubectl label nodes <node-name> custom-label-

# Update label
kubectl label nodes <node-name> custom-label=new-value --overwrite
```

### Cleanup Old Jobs

Remove completed jobs:
```bash
# List old jobs
kubectl get jobs -n node-labeling

# Delete specific job
kubectl delete job label-nodes-for-voice-pipeline -n node-labeling

# Delete all completed jobs
kubectl delete jobs -n node-labeling --field-selector status.successful=1
```

### Adding New Nodes

Update the job to include new nodes:
1. Edit `label-nodes-job.yaml`
2. Add node to appropriate section
3. Apply the updated job

Example:
```bash
# Add to high-performance section
for node in pgbee pgmac01 pgmac02 new-node; do
  # ... labeling logic
done
```

## Troubleshooting

### Job Failures

1. **Check job status**:
```bash
kubectl describe job -n node-labeling label-nodes-for-voice-pipeline
```

2. **View pod logs**:
```bash
kubectl logs -n node-labeling -l job-name=label-nodes-for-voice-pipeline
```

3. **Common issues**:
   - Node not found
   - Insufficient permissions
   - Label conflicts

### Permission Issues

1. **Verify RBAC**:
```bash
kubectl get clusterrole node-labeler -o yaml
kubectl get clusterrolebinding node-labeler -o yaml
```

2. **Test permissions**:
```bash
kubectl auth can-i update nodes \
  --as=system:serviceaccount:node-labeling:node-labeler
```

### Label Conflicts

1. **Check existing labels**:
```bash
kubectl get node <node-name> -o yaml | grep -A20 labels:
```

2. **Force overwrite**:
```bash
kubectl label nodes <node-name> label-key=value --overwrite
```

## Label Management

### Label Conventions

Follow naming standards:
- Use lowercase
- Separate words with hyphens
- Use namespaced labels for custom domains
- Keep labels concise but descriptive

### Reserved Labels

Avoid modifying:
- `kubernetes.io/*` - System labels
- `node.kubernetes.io/*` - Node properties
- `feature.node.kubernetes.io/*` - Feature discovery

### Custom Labels

Add project-specific labels:
```yaml
# Example custom labels
workload.myapp/database: "supported"
environment.myapp/type: "production"
team.owner: "platform"
```

## Security Considerations

### RBAC Permissions
- Limited to node labeling operations
- Cannot modify node specs
- No access to workloads or secrets

### Audit Trail
- All label changes logged in Kubernetes audit
- Job execution history preserved
- TTL ensures cleanup

### Best Practices
1. **Review changes**: Check label modifications
2. **Test first**: Try on non-production nodes
3. **Document labels**: Maintain label documentation
4. **Version control**: Track job changes in Git
5. **Monitor usage**: Audit label usage regularly

## Integration Examples

### With Node Feature Discovery

Combine with NFD labels:
```yaml
# Use both custom and NFD labels
nodeSelector:
  hardware.tier: "high-performance"
  feature.node.kubernetes.io/cpu-cpuid.AVX512: "true"
```

### With Cluster Autoscaler

Configure scaling groups:
```yaml
# Label for autoscaling groups
labels:
  cluster-autoscaler.kubernetes.io/gpu-type: "rtx5070"
  cluster-autoscaler.kubernetes.io/scale-down-disabled: "true"
```

### With Monitoring

Track labeled nodes:
```yaml
# Prometheus query
kube_node_labels{label_hardware_tier="dual-gpu"}
```

## Monitoring

### Key Metrics
- Node count by tier
- Label drift detection
- Job execution success rate
- Time to complete labeling

### Alerts

Configure alerts:
```yaml
# Alert on missing labels
- alert: NodeMissingLabels
  expr: |
    kube_node_info unless on(node) 
    kube_node_labels{label_hardware_tier=~".+"}
  annotations:
    summary: "Node {{ $labels.node }} missing tier label"
```

## Maintenance

### Regular Tasks

1. **Weekly**:
   - Verify all nodes labeled
   - Check for new nodes
   - Review label usage

2. **Monthly**:
   - Audit label schema
   - Clean unused labels
   - Update documentation

3. **Quarterly**:
   - Review labeling strategy
   - Plan label migrations
   - Update job configuration

### Label Evolution

Handle label changes:
```bash
#!/bin/bash
# migrate-labels.sh

# Rename label across all nodes
OLD_LABEL="old-key"
NEW_LABEL="new-key"

for node in $(kubectl get nodes -o name); do
  VALUE=$(kubectl get $node -o jsonpath="{.metadata.labels.$OLD_LABEL}")
  if [ -n "$VALUE" ]; then
    kubectl label $node $NEW_LABEL=$VALUE
    kubectl label $node $OLD_LABEL-
  fi
done
```

## Advanced Configuration

### Dynamic Labeling

Add conditional logic:
```bash
# Label based on node resources
CPU_COUNT=$(kubectl get node $node -o jsonpath='{.status.capacity.cpu}')
if [ $CPU_COUNT -ge 16 ]; then
  apply_label $node "cpu.class=high"
fi
```

### External Data Sources

Integrate with inventory:
```bash
# Pull labels from external source
LABELS=$(curl -s https://inventory.internal/api/nodes/$node/labels)
for label in $LABELS; do
  apply_label $node "$label"
done
```

### Validation

Add label validation:
```bash
# Validate required labels exist
REQUIRED_LABELS=("hardware.tier" "node-type")
for label in "${REQUIRED_LABELS[@]}"; do
  if ! kubectl get node $node -o jsonpath="{.metadata.labels.$label}" | grep -q .; then
    echo "ERROR: Missing required label $label on $node"
    exit 1
  fi
done
```

## Future Improvements

- [ ] Implement continuous labeling daemon
- [ ] Add webhook for automatic new node labeling
- [ ] Create label governance policies
- [ ] Add label validation admission controller
- [ ] Implement label-based cost allocation
- [ ] Create label dependency management
- [ ] Add automatic GPU model detection
- [ ] Implement label history tracking
- [ ] Create label migration tools
- [ ] Add integration with hardware inventory system
