# Cluster Maintenance Operations

## Overview

This document outlines standard maintenance procedures for the Fako Cluster, including routine tasks, troubleshooting steps, and emergency procedures.

## Daily Operations

### Health Checks

#### Check Cluster Status
```bash
kubectl get nodes
kubectl get pods --all-namespaces | grep -v Running
kubectl top nodes
kubectl top pods --all-namespaces
```

#### Check FluxCD Sync Status
```bash
flux get all
flux logs --all-namespaces
```

### Log Review
- Check for any failed pods or containers
- Review ingress logs for unusual traffic patterns
- Monitor resource usage trends

## Weekly Maintenance

### Backup Verification
1. Verify all PVC backups are current
2. Test restore procedures for critical services
3. Document any backup failures

### Certificate Status
```bash
kubectl get certificates --all-namespaces
kubectl describe certificate -n cert-manager
```

### Security Scans
```bash
# Run Gitleaks scan
kubectl create job --from=cronjob/gitleaks-scan -n gitleaks manual-scan-$(date +%s)

# Check Kubescape results
kubectl logs -n kubescape-operator -l app=kubescape
```

## Monthly Tasks

### Updates and Patches

#### Update Flux Components
```bash
flux check --pre
flux install --export > flux-system/gotk-components.yaml
git add flux-system/gotk-components.yaml
git commit -m "Update Flux components"
git push
```

#### Update Container Images
- Review container image versions
- Test updates in staging environment
- Apply updates through Git commits

### Resource Optimization
```bash
# Check resource requests vs actual usage
kubectl top pods --all-namespaces --sort-by=cpu
kubectl top pods --all-namespaces --sort-by=memory
```

## Troubleshooting Procedures

### Pod Issues

#### Pod Stuck in Pending
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

#### Pod CrashLoopBackOff
```bash
kubectl logs <pod-name> -n <namespace> --previous
kubectl describe pod <pod-name> -n <namespace>
```

### Storage Issues

#### PVC Not Binding
```bash
kubectl get pv
kubectl get pvc -n <namespace>
kubectl describe pvc <pvc-name> -n <namespace>
```

#### NFS Mount Issues
```bash
# Check NFS server connectivity
showmount -e <nfs-server-ip>
# Check mount inside pod
kubectl exec -it <pod-name> -n <namespace> -- df -h
```

### Networking Issues

#### Service Not Accessible
```bash
kubectl get svc -n <namespace>
kubectl get endpoints -n <namespace>
kubectl describe ingress -n <namespace>
```

#### DNS Resolution
```bash
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup <service-name>.<namespace>
```

## Emergency Procedures

### Cluster Recovery

#### Node Failure
1. Cordon the node: `kubectl cordon <node-name>`
2. Drain workloads: `kubectl drain <node-name> --ignore-daemonsets`
3. Fix node issues
4. Uncordon node: `kubectl uncordon <node-name>`

#### Etcd Backup and Restore
```bash
# Backup etcd
ETCDCTL_API=3 etcdctl snapshot save backup.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key

# Verify backup
ETCDCTL_API=3 etcdctl --write-out=table snapshot status backup.db
```

### Disaster Recovery

#### Full Cluster Restore
1. Restore etcd from backup
2. Re-apply Flux bootstrap
3. Wait for GitOps reconciliation
4. Verify all services are running
5. Restore persistent data from backups

## Monitoring and Alerts

### Key Metrics to Monitor
- CPU and Memory usage per node
- Disk usage on persistent volumes
- Network ingress/egress rates
- Pod restart counts
- Certificate expiration dates

### Alert Response

#### High Resource Usage
1. Identify resource-consuming pods
2. Check for memory leaks or runaway processes
3. Scale horizontally if needed
4. Consider resource limit adjustments

#### Service Degradation
1. Check pod health and logs
2. Verify external dependencies
3. Review recent changes via Git history
4. Rollback if necessary using Flux

## Documentation Updates

### After Each Incident
1. Document root cause
2. Update runbooks
3. Create or update alerts
4. Share lessons learned

### Regular Reviews
- Monthly review of procedures
- Quarterly disaster recovery drills
- Annual security audit
