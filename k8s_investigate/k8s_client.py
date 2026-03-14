"""Kubernetes client wrapper."""

from __future__ import annotations

from functools import lru_cache

from kubernetes import client
from kubernetes import config as k8s_config

from k8s_investigate.config import ScanOptions


def load_k8s_config(opts: ScanOptions) -> client.ApiClient:
    """Load Kubernetes configuration and return an ApiClient."""
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config(
            config_file=opts.kubeconfig,
            context=opts.context,
        )
    return client.ApiClient()


class K8sClient:
    """Wrapper around Kubernetes API clients."""

    def __init__(self, opts: ScanOptions) -> None:
        self.api_client = load_k8s_config(opts)
        self.core_v1 = client.CoreV1Api(self.api_client)
        self.apps_v1 = client.AppsV1Api(self.api_client)
        self.batch_v1 = client.BatchV1Api(self.api_client)
        self.networking_v1 = client.NetworkingV1Api(self.api_client)
        self.rbac_v1 = client.RbacAuthorizationV1Api(self.api_client)
        self.autoscaling_v1 = client.AutoscalingV1Api(self.api_client)
        self.policy_v1 = client.PolicyV1Api(self.api_client)
        self.storage_v1 = client.StorageV1Api(self.api_client)
        self.scheduling_v1 = client.SchedulingV1Api(self.api_client)
        self.discovery_v1 = client.DiscoveryV1Api(self.api_client)
        self.custom_objects = client.CustomObjectsApi(self.api_client)

    def get_namespaces(self, opts: ScanOptions) -> list[str]:
        """Get list of namespaces to scan based on options."""
        if opts.namespaces:
            return opts.namespaces

        ns_list = self.core_v1.list_namespace()
        all_ns = [ns.metadata.name for ns in ns_list.items]

        if opts.exclude_namespaces:
            all_ns = [ns for ns in all_ns if ns not in opts.exclude_namespaces]

        return all_ns

    @lru_cache(maxsize=32)
    def list_pods_cached(self, namespace: str) -> list:
        """List pods in a namespace (cached to avoid repeated API calls)."""
        return self.core_v1.list_namespaced_pod(namespace).items

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.list_pods_cached.cache_clear()
