"""StatefulSet scanner - finds StatefulSets with zero replicas."""

from __future__ import annotations

from k8s_purify.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class StatefulSetScanner(BaseScanner):
    resource_type = "statefulsets"
    namespaced = True

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        statefulsets = self.k8s.apps_v1.list_namespaced_stateful_set(namespace).items

        for sts in statefulsets:
            if self.should_skip(sts.metadata):
                continue
            if self.is_marked_unused(sts.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="StatefulSet",
                    name=sts.metadata.name, reason="Marked as unused via label",
                ))
                continue
            replicas = sts.spec.replicas if sts.spec.replicas is not None else 1
            if replicas == 0:
                results.append(UnusedResource(
                    namespace=namespace, resource_type="StatefulSet",
                    name=sts.metadata.name, reason="Zero replicas configured",
                ))
        return results
