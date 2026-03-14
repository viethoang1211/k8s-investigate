"""Delete unused resources with confirmation."""

from __future__ import annotations

import logging

from kubernetes.client.exceptions import ApiException
from rich.console import Console
from rich.prompt import Confirm

from k8s_investigate.k8s_client import K8sClient
from k8s_investigate.scanner import UnusedResource

logger = logging.getLogger(__name__)

# Map resource types to their delete functions
_DELETE_HANDLERS: dict[str, str] = {
    "ConfigMap": "delete_namespaced_config_map",
    "Secret": "delete_namespaced_secret",
    "Service": "delete_namespaced_service",
    "Deployment": "delete_namespaced_deployment",
    "StatefulSet": "delete_namespaced_stateful_set",
    "DaemonSet": "delete_namespaced_daemon_set",
    "ReplicaSet": "delete_namespaced_replica_set",
    "Pod": "delete_namespaced_pod",
    "Ingress": "delete_namespaced_ingress",
    "PVC": "delete_namespaced_persistent_volume_claim",
    "Role": "delete_namespaced_role",
    "RoleBinding": "delete_namespaced_role_binding",
    "ServiceAccount": "delete_namespaced_service_account",
    "HPA": "delete_namespaced_horizontal_pod_autoscaler",
    "Job": "delete_namespaced_job",
    "PDB": "delete_namespaced_pod_disruption_budget",
    "NetworkPolicy": "delete_namespaced_network_policy",
}

_CLUSTER_DELETE_HANDLERS: dict[str, str] = {
    "PV": "delete_persistent_volume",
    "ClusterRole": "delete_cluster_role",
    "ClusterRoleBinding": "delete_cluster_role_binding",
    "StorageClass": "delete_storage_class",
    "PriorityClass": "delete_priority_class",
}

# Map resource types to their API clients
_API_MAP: dict[str, str] = {
    "ConfigMap": "core_v1",
    "Secret": "core_v1",
    "Service": "core_v1",
    "Pod": "core_v1",
    "PVC": "core_v1",
    "PV": "core_v1",
    "ServiceAccount": "core_v1",
    "Deployment": "apps_v1",
    "StatefulSet": "apps_v1",
    "DaemonSet": "apps_v1",
    "ReplicaSet": "apps_v1",
    "Ingress": "networking_v1",
    "NetworkPolicy": "networking_v1",
    "Role": "rbac_v1",
    "RoleBinding": "rbac_v1",
    "ClusterRole": "rbac_v1",
    "ClusterRoleBinding": "rbac_v1",
    "HPA": "autoscaling_v1",
    "Job": "batch_v1",
    "PDB": "policy_v1",
    "StorageClass": "storage_v1",
    "PriorityClass": "scheduling_v1",
}


def delete_resources(
    k8s: K8sClient,
    resources: list[UnusedResource],
    auto_confirm: bool = False,
) -> int:
    """Delete a list of unused resources. Returns count of deleted resources."""
    console = Console()

    if not resources:
        console.print("[green]Nothing to delete.[/green]")
        return 0

    console.print(f"\n[bold red]About to delete {len(resources)} resources:[/bold red]")
    for r in resources:
        ns = f" in {r.namespace}" if r.namespace else ""
        console.print(f"  - {r.resource_type}/{r.name}{ns}")

    if not auto_confirm:
        if not Confirm.ask("\nProceed with deletion?", default=False):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return 0

    deleted = 0
    for r in resources:
        try:
            api_attr = _API_MAP.get(r.resource_type)
            if not api_attr:
                logger.warning("No API mapping for %s", r.resource_type)
                continue
            api = getattr(k8s, api_attr)

            if r.resource_type in _DELETE_HANDLERS:
                method = getattr(api, _DELETE_HANDLERS[r.resource_type])
                method(r.name, r.namespace)
            elif r.resource_type in _CLUSTER_DELETE_HANDLERS:
                method = getattr(api, _CLUSTER_DELETE_HANDLERS[r.resource_type])
                method(r.name)
            else:
                logger.warning("No delete handler for %s", r.resource_type)
                continue

            console.print(f"  [green]Deleted {r.resource_type}/{r.name}[/green]")
            deleted += 1
        except ApiException as e:
            console.print(f"  [red]Failed to delete {r.resource_type}/{r.name}: {e.reason}[/red]")
        except Exception as e:
            console.print(f"  [red]Error deleting {r.resource_type}/{r.name}: {e}[/red]")

    console.print(f"\n[bold]Deleted {deleted}/{len(resources)} resources.[/bold]")
    return deleted
