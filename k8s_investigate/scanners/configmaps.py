"""ConfigMap scanner - finds ConfigMaps not used by any pod."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


def _get_used_configmaps(pods: list) -> set[str]:
    """Extract all ConfigMap names referenced by pods."""
    used = set()
    for pod in pods:
        spec = pod.spec
        if not spec:
            continue
        # Check volumes
        for vol in spec.volumes or []:
            if vol.config_map:
                used.add(vol.config_map.name)
            if vol.projected and vol.projected.sources:
                for src in vol.projected.sources:
                    if src.config_map:
                        used.add(src.config_map.name)
        # Check containers + init containers
        for container in (spec.containers or []) + (spec.init_containers or []):
            for env in container.env or []:
                if env.value_from and env.value_from.config_map_key_ref:
                    used.add(env.value_from.config_map_key_ref.name)
            for env_from in container.env_from or []:
                if env_from.config_map_ref:
                    used.add(env_from.config_map_ref.name)
    return used


@register_scanner
class ConfigMapScanner(BaseScanner):
    resource_type = "configmaps"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        pods = self.k8s.list_pods_cached(namespace)
        used_cms = _get_used_configmaps(pods)
        configmaps = self.k8s.core_v1.list_namespaced_config_map(namespace).items

        for cm in configmaps:
            if self.should_skip(cm.metadata):
                continue
            if self.is_marked_unused(cm.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="ConfigMap",
                    name=cm.metadata.name, reason="Marked as unused via label",
                ))
                continue
            if cm.metadata.name not in used_cms:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="ConfigMap",
                    name=cm.metadata.name, reason="Not used in any pod volume or env",
                ))
        return results
