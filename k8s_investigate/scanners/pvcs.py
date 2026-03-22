"""PVC scanner - finds PersistentVolumeClaims not mounted by any pod."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


def _get_used_pvcs(pods: list) -> set[str]:
    """Extract PVC names referenced by pods."""
    used = set()
    for pod in pods:
        spec = pod.spec
        if not spec:
            continue
        for vol in spec.volumes or []:
            if vol.persistent_volume_claim:
                used.add(vol.persistent_volume_claim.claim_name)
            # Ephemeral volumes create PVCs named <pod>-<volume>
            if vol.ephemeral:
                used.add(f"{pod.metadata.name}-{vol.name}")
    return used


def _is_owned_by_statefulset(metadata) -> bool:
    """Return True if the resource is owned by a StatefulSet."""
    for ref in metadata.owner_references or []:
        if ref.kind == "StatefulSet":
            return True
    return False


@register_scanner
class PVCScanner(BaseScanner):
    resource_type = "pvcs"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        pods = self.k8s.list_pods_cached(namespace)
        used_pvcs = _get_used_pvcs(pods)
        pvcs = self.k8s.core_v1.list_namespaced_persistent_volume_claim(namespace).items

        for pvc in pvcs:
            if self.should_skip(pvc.metadata):
                continue
            if self.is_marked_unused(pvc.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="PVC",
                    name=pvc.metadata.name, reason="Marked as unused via label",
                ))
                continue
            if _is_owned_by_statefulset(pvc.metadata):
                continue
            if pvc.metadata.name not in used_pvcs:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="PVC",
                    name=pvc.metadata.name, reason="Not mounted in any pod",
                ))
        return results
