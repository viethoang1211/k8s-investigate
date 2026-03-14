# K8s Purify - Kubernetes Orphaned Resources Finder

A Python-based tool to discover and clean up unused Kubernetes resources in your cluster.

## Features

- **20+ resource type scanners**: ConfigMaps, Secrets, Services, Deployments, StatefulSets, Pods, Ingresses, PVCs, PVs, Roles, ClusterRoles, RoleBindings, ClusterRoleBindings, ServiceAccounts, HPAs, Jobs, ReplicaSets, DaemonSets, PDBs, NetworkPolicies, StorageClasses, PriorityClasses
- **Multiple output formats**: Table (rich), JSON, YAML
- **Label-based filtering**: Include/exclude resources by labels
- **Age-based filtering**: Find resources older or newer than a threshold
- **Namespace filtering**: Scan specific namespaces or exclude namespaces
- **Deletion support**: Optionally delete unused resources (with confirmation)
- **Prometheus metrics**: Export orphaned resource metrics for monitoring
- **Annotation override**: Mark resources with `k8s-purify/used: "false"` to force-flag them

## Installation

```bash
pip install .
```

### Development

```bash
pip install -e ".[dev]"
```

## Usage

```bash
# Scan all resource types in all namespaces
k8s-purify scan all

# Scan specific resource type
k8s-purify scan configmaps
k8s-purify scan secrets --namespace default

# Filter by namespace
k8s-purify scan all --namespace kube-system
k8s-purify scan all --exclude-namespace kube-system,kube-public

# Filter by age
k8s-purify scan all --older-than 24h
k8s-purify scan all --newer-than 1h

# Output formats
k8s-purify scan all --output json
k8s-purify scan all --output yaml
k8s-purify scan all --output table

# Show reasons why resources are considered unused
k8s-purify scan all --show-reason

# Delete unused resources (with confirmation)
k8s-purify scan all --delete
k8s-purify scan all --delete --yes  # Skip confirmation

# Run Prometheus exporter
k8s-purify exporter --port 8080 --interval 600
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
docker build -t k8s-purify .
docker run --rm -v ~/.kube/config:/root/.kube/config k8s-purify scan all
```

## Helm

```bash
helm install k8s-purify ./charts/k8s-purify --namespace k8s-purify --create-namespace
```
