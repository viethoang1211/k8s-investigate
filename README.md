# K8s Investigate - Kubernetes Orphaned Resources Finder

A Python-based tool to discover and clean up unused Kubernetes resources in your cluster.

## Features

- **22 resource type scanners**: ConfigMaps, Secrets, Services, Deployments, StatefulSets, Pods, Ingresses, PVCs, PVs, Roles, ClusterRoles, RoleBindings, ClusterRoleBindings, ServiceAccounts, HPAs, Jobs, ReplicaSets, DaemonSets, PDBs, NetworkPolicies, StorageClasses, PriorityClasses
- **Multiple output formats**: Table (rich), JSON, YAML
- **Label-based filtering**: Include/exclude resources by labels
- **Age-based filtering**: Find resources older or newer than a threshold
- **Namespace filtering**: Scan specific namespaces or exclude namespaces
- **Deletion support**: Optionally delete unused resources (with confirmation)
- **Prometheus metrics**: Export orphaned resource metrics for monitoring
- **Label override**: Mark resources with `k8s-investigate/used: "false"` to force-flag them

## Installation

```bash
pip install k8s-investigate
```

Or install from source:

```bash
git clone https://github.com/<org>/k8s-investigate.git
cd k8s-investigate
pip install .
```

### Development

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# Scan all resource types across all namespaces
k8s-investigate scan all

# Scan with reasons why each resource is unused
k8s-investigate scan all --show-reason
```

## Usage

### Scan specific resource types

```bash
# Single resource type
k8s-investigate scan configmaps
k8s-investigate scan secrets --namespace default

# Multiple types using short names
k8s-investigate scan cm,svc,deploy,sa
```

**Short names**: `cm`=ConfigMaps, `svc`=Services, `deploy`=Deployments, `sts`=StatefulSets, `ds`=DaemonSets, `rs`=ReplicaSets, `ing`=Ingresses, `sa`=ServiceAccounts, `rb`=RoleBindings, `crb`=ClusterRoleBindings, `sc`=StorageClasses, `pc`=PriorityClasses, `netpol`=NetworkPolicies, `pdb`=PDBs

### Filter by namespace

```bash
k8s-investigate scan all -n default
k8s-investigate scan all -n dev,staging,production
k8s-investigate scan all --exclude-namespace kube-system,kube-public
```

### Filter by age

```bash
k8s-investigate scan all --older-than 7d      # Only resources older than 7 days
k8s-investigate scan all --newer-than 1h      # Only resources created in last hour
k8s-investigate scan all --older-than 1d12h   # Supports combined durations
```

### Output formats

```bash
k8s-investigate scan all -o table             # Rich table (default)
k8s-investigate scan all -o json              # JSON output
k8s-investigate scan all -o yaml              # YAML output
k8s-investigate scan all -o json > report.json  # Save to file
k8s-investigate scan all --group-by resource  # Group by type instead of namespace
```

### Delete unused resources

```bash
k8s-investigate scan all --delete             # Interactive confirmation
k8s-investigate scan all --delete --yes       # Skip confirmation (use with caution!)
k8s-investigate scan cm,secrets -n staging --delete  # Delete specific types in namespace
```

### Prometheus exporter

```bash
k8s-investigate exporter                      # Default: port 8080, 10min interval
k8s-investigate exporter --port 9090 --interval 300
k8s-investigate exporter --exclude-namespace kube-system
```

## Supported Resource Types

| Resource | Command | Detection Logic |
|----------|---------|-----------------|
| ConfigMaps | `configmaps` | Not mounted/referenced in any pod |
| Secrets | `secrets` | Not used in pods, ingress TLS, or imagePullSecrets |
| Services | `services` | No matching endpoints |
| Deployments | `deployments` | Zero replicas |
| StatefulSets | `statefulsets` | Zero replicas |
| DaemonSets | `daemonsets` | Not scheduled on any node |
| ReplicaSets | `replicasets` | Zero replicas and no ready/available pods |
| Pods | `pods` | Evicted or CrashLoopBackOff |
| Ingresses | `ingresses` | Backend services don't exist |
| PVCs | `pvcs` | Not mounted in any pod |
| PVs | `pvs` | Not bound to any PVC |
| Roles | `roles` | Not referenced by any RoleBinding |
| ClusterRoles | `clusterroles` | Not referenced by any binding |
| RoleBindings | `rolebindings` | Referenced role/subjects don't exist |
| ClusterRoleBindings | `clusterrolebindings` | Referenced role/subjects don't exist |
| ServiceAccounts | `serviceaccounts` | Not used by any pod or binding |
| HPAs | `hpas` | Target resource doesn't exist |
| Jobs | `jobs` | Completed or failed |
| PDBs | `pdbs` | Selector doesn't match any workload |
| NetworkPolicies | `networkpolicies` | Selector matches no pods |
| StorageClasses | `storageclasses` | Not used by any PV or PVC |
| PriorityClasses | `priorityclasses` | Not used by any pod |

## Docker

```bash
docker build -t k8s-investigate .
docker run --rm -v ~/.kube/config:/root/.kube/config k8s-investigate scan all
```

## Helm

```bash
helm install k8s-investigate ./charts/k8s-investigate --namespace k8s-investigate --create-namespace
```
