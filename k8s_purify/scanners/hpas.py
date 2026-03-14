"""HPA scanner - finds HPAs targeting non-existent resources."""

from __future__ import annotations

from kubernetes.client.exceptions import ApiException

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class HPAScanner(BaseScanner):
    resource_type = "hpas"
    namespaced = True

    def _target_exists(self, namespace: str, kind: str, name: str) -> bool:
        try:
            if kind == "Deployment":
                self.k8s.apps_v1.read_namespaced_deployment(name, namespace)
            elif kind == "StatefulSet":
                self.k8s.apps_v1.read_namespaced_stateful_set(name, namespace)
            elif kind == "ReplicaSet":
                self.k8s.apps_v1.read_namespaced_replica_set(name, namespace)
            else:
                return True  # Unknown kind, assume valid
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        hpas = self.k8s.autoscaling_v1.list_namespaced_horizontal_pod_autoscaler(namespace).items

        for hpa in hpas:
            if self.should_skip(hpa.metadata):
                continue
            if self.is_marked_unused(hpa.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="HPA",
                    name=hpa.metadata.name, reason="Marked as unused via label",
                ))
                continue
            ref = hpa.spec.scale_target_ref
            if not self._target_exists(namespace, ref.kind, ref.name):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="HPA",
                    name=hpa.metadata.name,
                    reason=f"Target {ref.kind}/{ref.name} does not exist",
                ))
        return results
