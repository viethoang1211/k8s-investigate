"""Secret scanner - finds Secrets not used by any pod, ingress, or service account."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner

# Secret types that are managed by the system and should be skipped
_SYSTEM_SECRET_TYPES = {
    "helm.sh/release.v1",
    "kubernetes.io/dockerconfigjson",
    "kubernetes.io/dockercfg",
    "kubernetes.io/service-account-token",
}


def _get_used_secrets(pods: list, ingresses: list) -> set[str]:
    """Extract all Secret names referenced by pods and ingresses."""
    used = set()
    for pod in pods:
        spec = pod.spec
        if not spec:
            continue
        # Volumes
        for vol in spec.volumes or []:
            if vol.secret:
                used.add(vol.secret.secret_name)
            if vol.projected and vol.projected.sources:
                for src in vol.projected.sources:
                    if src.secret:
                        used.add(src.secret.name)
        # Image pull secrets
        for ips in spec.image_pull_secrets or []:
            used.add(ips.name)
        # Containers + init containers
        for container in (spec.containers or []) + (spec.init_containers or []):
            for env in container.env or []:
                if env.value_from and env.value_from.secret_key_ref:
                    used.add(env.value_from.secret_key_ref.name)
            for env_from in container.env_from or []:
                if env_from.secret_ref:
                    used.add(env_from.secret_ref.name)
    # Ingress TLS secrets
    for ing in ingresses:
        for tls in ing.spec.tls or []:
            if tls.secret_name:
                used.add(tls.secret_name)
    return used


@register_scanner
class SecretScanner(BaseScanner):
    resource_type = "secrets"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        pods = self.k8s.list_pods_cached(namespace)
        ingresses = self.k8s.networking_v1.list_namespaced_ingress(namespace).items
        used_secrets = _get_used_secrets(pods, ingresses)
        secrets = self.k8s.core_v1.list_namespaced_secret(namespace).items

        for secret in secrets:
            if self.should_skip(secret.metadata):
                continue
            # Skip system-managed secret types
            if secret.type in _SYSTEM_SECRET_TYPES:
                continue
            if self.is_marked_unused(secret.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Secret",
                    name=secret.metadata.name, reason="Marked as unused via label",
                ))
                continue
            if secret.metadata.name not in used_secrets:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="Secret",
                    name=secret.metadata.name, reason="Not used in any pod, ingress, or imagePullSecret",
                ))
        return results
